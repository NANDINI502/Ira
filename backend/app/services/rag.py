"""
RAG Service
Document ingestion, embedding, and retrieval for Q&A
"""

import hashlib
import uuid
from pathlib import Path
from typing import List, Dict, Optional
import json
from loguru import logger
import ollama

from app.config import settings

# Lazy imports to avoid startup errors if deps missing
chromadb = None
Document = None


class OllamaEmbeddingFunction:
    """Custom embedding function using Ollama's nomic-embed-text"""
    
    def __init__(self, model_name: str = "nomic-embed-text"):
        self.model_name = model_name
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        embeddings = []
        for text in input:
            response = ollama.embeddings(model=self.model_name, prompt=text)
            embeddings.append(response["embedding"])
        return embeddings


def _init_chromadb():
    """Lazy initialize ChromaDB"""
    global chromadb, Document
    if chromadb is None:
        import chromadb as _chromadb
        from chromadb.config import Settings as ChromaSettings
        chromadb = _chromadb
    return chromadb


class RAGService:
    """Service for document ingestion and retrieval"""
    
    def __init__(self):
        self._client = None
        self._collection = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of ChromaDB"""
        if self._initialized:
            return
            
        _init_chromadb()
        
        self._client = chromadb.PersistentClient(
            path=str(settings.CHROMA_DB_DIR)
        )
        
        self._collection = self._client.get_or_create_collection(
            name="ira_documents",
            metadata={"hnsw:space": "cosine"},
            embedding_function=OllamaEmbeddingFunction(settings.EMBEDDING_MODEL)
        )
        
        self._initialized = True
        logger.info("RAG service initialized with ChromaDB")
    
    async def ingest_document(
        self,
        filename: str,
        content: bytes
    ) -> str:
        """Ingest a document into the vector store"""
        self._ensure_initialized()
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Extract text based on file type
        text = await self._extract_text(filename, content)
        
        if not text:
            raise ValueError(f"Could not extract text from {filename}")
        
        # Chunk the text
        chunks = self._chunk_text(text)
        
        # Generate embeddings and store
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            chunk_ids.append(chunk_id)
            
            # Store in ChromaDB (it will generate embeddings)
            self._collection.add(
                ids=[chunk_id],
                documents=[chunk],
                metadatas=[{
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }]
            )
        
        # Save document metadata
        metadata_path = settings.DOCUMENTS_DIR / f"{doc_id}.json"
        metadata = {
            "id": doc_id,
            "filename": filename,
            "chunks": len(chunks),
            "chunk_ids": chunk_ids
        }
        metadata_path.write_text(json.dumps(metadata))
        
        logger.info(f"Ingested document: {filename} ({len(chunks)} chunks)")
        return doc_id
    
    async def query(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """Query the document store"""
        self._ensure_initialized()
        
        try:
            # Check if collection has any documents
            if self._collection.count() == 0:
                return []
            
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            if not results or not results.get("documents"):
                return []
            
            # Format results
            formatted = []
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                
                formatted.append({
                    "content": doc,
                    "source": metadata.get("filename", "Unknown"),
                    "relevance": 1 - distance,  # Convert distance to similarity
                    "chunk_index": metadata.get("chunk_index", 0)
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return []
    
    async def list_documents(self) -> List[Dict]:
        """List all indexed documents"""
        documents = []
        
        for metadata_file in settings.DOCUMENTS_DIR.glob("*.json"):
            try:
                metadata = json.loads(metadata_file.read_text())
                documents.append({
                    "id": metadata["id"],
                    "filename": metadata["filename"],
                    "chunks": metadata["chunks"]
                })
            except Exception as e:
                logger.warning(f"Error reading metadata {metadata_file}: {e}")
        
        return documents
    
    async def delete_document(self, doc_id: str):
        """Delete a document from the store"""
        self._ensure_initialized()
        
        # Load metadata
        metadata_path = settings.DOCUMENTS_DIR / f"{doc_id}.json"
        if not metadata_path.exists():
            raise ValueError(f"Document {doc_id} not found")
        
        metadata = json.loads(metadata_path.read_text())
        
        # Delete from ChromaDB
        self._collection.delete(ids=metadata["chunk_ids"])
        
        # Delete metadata file
        metadata_path.unlink()
        
        logger.info(f"Deleted document: {doc_id}")
    
    async def _extract_text(self, filename: str, content: bytes) -> Optional[str]:
        """Extract text from various file formats"""
        suffix = Path(filename).suffix.lower()
        
        try:
            if suffix == ".txt" or suffix == ".md":
                return content.decode("utf-8")
            
            elif suffix == ".pdf":
                from pypdf import PdfReader
                import io
                reader = PdfReader(io.BytesIO(content))
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text())
                return "\n\n".join(text_parts)
            
            elif suffix == ".docx":
                from docx import Document
                import io
                doc = Document(io.BytesIO(content))
                text_parts = []
                for para in doc.paragraphs:
                    text_parts.append(para.text)
                return "\n\n".join(text_parts)
            
            else:
                # Try to decode as plain text
                return content.decode("utf-8")
                
        except Exception as e:
            logger.error(f"Text extraction error for {filename}: {e}")
            return None
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        
        # Simple sentence-aware chunking
        sentences = text.replace("\n", " ").split(". ")
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(". ".join(current_chunk) + ".")
                
                # Keep overlap
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")
        
        return chunks
