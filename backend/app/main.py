"""
Ira - Local AI Assistant
FastAPI Backend Entry Point
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import asyncio
from loguru import logger
import sys

from app.config import settings
from app.services.chat import ChatService
from app.services.rag import RAGService
from app.services.voice import VoiceService
from app.memory.database import Database
from app.memory.conversation import ConversationManager


# Configure logging
logger.remove()
logger.add(sys.stderr, level="DEBUG" if settings.DEBUG else "INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize services
    app.state.db = Database()
    await app.state.db.initialize()
    
    app.state.chat_service = ChatService()
    app.state.rag_service = RAGService()
    app.state.voice_service = VoiceService()
    app.state.conversation_manager = ConversationManager(app.state.db)
    
    logger.info("All services initialized successfully")
    
    yield
    
    # Cleanup
    await app.state.db.close()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A fully offline, multimodal AI assistant",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ REST API Endpoints ============

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/api/conversations")
async def list_conversations():
    """Get all conversations"""
    conversations = await app.state.conversation_manager.list_conversations()
    return {"conversations": conversations}


@app.post("/api/conversations")
async def create_conversation(title: str = "New Chat"):
    """Create a new conversation"""
    conversation = await app.state.conversation_manager.create_conversation(title)
    return conversation


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation with messages"""
    conversation = await app.state.conversation_manager.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.put("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, title: dict):
    """Update a conversation (title)"""
    new_title = title.get("title")
    if not new_title:
        raise HTTPException(status_code=400, detail="Title is required")
    
    await app.state.conversation_manager.update_conversation(conversation_id, new_title)
    return {"status": "updated", "title": new_title}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    await app.state.conversation_manager.delete_conversation(conversation_id)
    return {"status": "deleted"}


# ============ Chat Endpoints ============

@app.post("/api/chat")
async def chat(
    conversation_id: str,
    message: str,
    image: UploadFile = File(None)
):
    """Send a chat message and get a response (non-streaming)"""
    
    # Handle image if provided
    image_data = None
    if image:
        image_data = await image.read()
    
    # Get conversation history
    history = await app.state.conversation_manager.get_messages(conversation_id)
    
    # Generate response
    response = await app.state.chat_service.generate(
        message=message,
        history=history,
        image=image_data
    )
    
    # Save messages
    await app.state.conversation_manager.add_message(conversation_id, "user", message)
    await app.state.conversation_manager.add_message(conversation_id, "assistant", response)
    
    return {"response": response}


@app.post("/api/chat/stream")
async def chat_stream(
    conversation_id: str,
    message: str
):
    """Stream chat response"""
    
    history = await app.state.conversation_manager.get_messages(conversation_id)
    
    async def generate():
        full_response = ""
        async for chunk in app.state.chat_service.generate_stream(message, history):
            full_response += chunk
            yield f"data: {chunk}\n\n"
        
        # Save messages after streaming completes
        await app.state.conversation_manager.add_message(conversation_id, "user", message)
        await app.state.conversation_manager.add_message(conversation_id, "assistant", full_response)
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


# ============ Voice Endpoints ============

@app.post("/api/voice/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio to text using Whisper"""
    audio_data = await audio.read()
    text = await app.state.voice_service.transcribe(audio_data)
    return {"text": text}


@app.post("/api/voice/synthesize")
async def synthesize_speech(text: str):
    """Convert text to speech using Piper"""
    audio_data = await app.state.voice_service.synthesize(text)
    return StreamingResponse(
        iter([audio_data]),
        media_type="audio/wav"
    )


# ============ Document/RAG Endpoints ============

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a document for RAG"""
    content = await file.read()
    doc_id = await app.state.rag_service.ingest_document(
        filename=file.filename,
        content=content
    )
    return {"document_id": doc_id, "filename": file.filename}


@app.get("/api/documents")
async def list_documents():
    """List all indexed documents"""
    documents = await app.state.rag_service.list_documents()
    return {"documents": documents}


@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """Remove a document from the index"""
    await app.state.rag_service.delete_document(document_id)
    return {"status": "deleted"}


@app.post("/api/documents/query")
async def query_documents(query: str, top_k: int = 5):
    """Query documents using RAG"""
    results = await app.state.rag_service.query(query, top_k)
    return {"results": results}


# ============ WebSocket for Real-time Chat ============

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time streaming chat"""
    await websocket.accept()
    logger.info(f"WebSocket connected for conversation: {conversation_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")
            image_base64 = data.get("image")  # Optional base64 encoded image
            
            # Debug logging
            logger.info(f"Received message: {message[:50] if message else 'empty'}...")
            logger.info(f"Image received: {bool(image_base64)}, length: {len(image_base64) if image_base64 else 0}")
            
            # Get conversation history
            history = await app.state.conversation_manager.get_messages(conversation_id)
            
            # Save user message
            await app.state.conversation_manager.add_message(conversation_id, "user", message)
            
            # Stream response
            full_response = ""
            async for chunk in app.state.chat_service.generate_stream(
                message=message,
                history=history,
                image_base64=image_base64
            ):
                full_response += chunk
                await websocket.send_json({"type": "chunk", "content": chunk})
            
            # Save assistant response
            await app.state.conversation_manager.add_message(conversation_id, "assistant", full_response)
            
            # Send completion signal
            await websocket.send_json({"type": "done", "content": full_response})
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation: {conversation_id}")


# ============ Home Assistant Endpoints ============

@app.get("/api/home/entities")
async def list_home_entities():
    """List all Home Assistant entities"""
    from app.services.home_assistant import HomeAssistantService
    ha_service = HomeAssistantService()
    entities = await ha_service.get_entities()
    return {"entities": entities}


@app.post("/api/home/command")
async def execute_home_command(command: str):
    """Execute a natural language home command"""
    from app.services.home_assistant import HomeAssistantService
    ha_service = HomeAssistantService()
    result = await ha_service.execute_command(command)
    return {"result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
