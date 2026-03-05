"""
Chat Service
Handles conversation logic and integrates with LLM
"""

from typing import AsyncGenerator, Optional, List, Dict
from pathlib import Path
import base64
from datetime import datetime
from loguru import logger

from app.models.llm import llm_client
from app.services.rag import RAGService
from app.services.web_services import web_services


from app.services.pywhatkit_service import pywhatkit_service


class ChatService:
    """Main chat service handling conversation flow"""
    
    def __init__(self):
        self.llm = llm_client
        self.rag_service = RAGService()
    
    async def _get_realtime_context(self, message: str) -> Optional[str]:
        """Check if the message needs real-time data and fetch it"""
        intent = web_services.detect_intent(message)
        
        if intent["type"] == "action":
            # Handle WhatsApp name resolution
            if intent.get("action") == "whatsapp_message" and not intent.get("phone") and intent.get("recipient_name"):
                name = intent.get("recipient_name").lower()
                contacts = await self._get_contacts()
                if name in contacts:
                    intent["phone"] = contacts[name]
                else:
                    return f"I couldn't find a contact named '{intent.get('recipient_name')}'. Please add them to your contacts list or provide a phone number."

            # Execute action using pywhatkit
            result = await pywhatkit_service.handle_command(intent)
            return result
        
        elif intent["type"] == "weather":
            location = intent.get("location", "")
            data = await web_services.get_weather(location or "auto")
            return data
        
        elif intent["type"] == "news":
            query = intent.get("query", "")
            data = await web_services.get_news(query)
            return data
        
        elif intent["type"] == "time":
            now = datetime.now()
            return f"🕐 Current date and time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}"
        
        return None
    
    async def generate(
        self,
        message: str,
        history: Optional[List[Dict]] = None,
        image: Optional[bytes] = None,
        use_rag: bool = True
    ) -> str:
        """Generate a response for the given message"""
        
        # Convert image to base64 if provided
        image_base64 = None
        if image:
            image_base64 = base64.b64encode(image).decode("utf-8")
        
        # Check for real-time data needs
        realtime_context = await self._get_realtime_context(message)
        
        # Get user profile
        user_profile = await self._get_user_profile()
        
        # Check if we should use RAG for document context
        system_prompt = self._build_system_prompt(
            rag_context=await self._get_rag_context(message) if use_rag else None,
            realtime_context=realtime_context,
            user_profile=user_profile
        )
        
        # Generate response
        response = await self.llm.generate(
            prompt=message,
            system_prompt=system_prompt,
            image_base64=image_base64,
            history=history
        )
        
        return response
    
    async def generate_stream(
        self,
        message: str,
        history: Optional[List[Dict]] = None,
        image_base64: Optional[str] = None,
        use_rag: bool = True
    ) -> AsyncGenerator[str, None]:
        """Stream a response for the given message"""
        
        # Strip data URL prefix from image if present (e.g., "data:image/png;base64,...")
        if image_base64 and "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]
        
        # Check for real-time data needs
        realtime_context = await self._get_realtime_context(message)
        
        # Get user profile
        user_profile = await self._get_user_profile()
        
        # Check if we should use RAG for document context
        system_prompt = self._build_system_prompt(
            rag_context=await self._get_rag_context(message) if use_rag else None,
            realtime_context=realtime_context,
            user_profile=user_profile
        )
        
        # Stream response
        async for chunk in self.llm.generate_stream(
            prompt=message,
            system_prompt=system_prompt,
            image_base64=image_base64,
            history=history
        ):
            yield chunk
    
    async def _get_user_profile(self) -> str:
        """Read user profile from any markdown file in data/user"""
        try:
            user_dir = Path("data/user")
            if not user_dir.exists():
                return ""
            
            # Find first markdown file
            md_files = list(user_dir.glob("*.md"))
            if not md_files:
                return ""
                
            profile_path = md_files[0]
            with open(profile_path, "r", encoding="utf-8") as f:
                return f.read()
                
        except Exception as e:
            logger.warning(f"Failed to read user profile: {e}")
            return ""

    async def _get_contacts(self) -> Dict[str, str]:
        """Read contacts from markdown file"""
        contacts = {}
        try:
            contacts_path = Path("data/user/contacts.md")
            if not contacts_path.exists():
                return contacts
            
            with open(contacts_path, "r", encoding="utf-8") as f:
                for line in f:
                    if ":" in line and not line.strip().startswith("#"):
                        parts = line.split(":", 1)
                        name = parts[0].strip().lower()
                        phone = parts[1].strip()
                        contacts[name] = phone
            return contacts
        except Exception as e:
            logger.warning(f"Failed to read contacts: {e}")
            return contacts

    def _build_system_prompt(
        self, 
        rag_context: Optional[str] = None, 
        realtime_context: Optional[str] = None,
        user_profile: Optional[str] = None
    ) -> str:
        """Build system prompt with all available context"""
        
        # Base identity
        parts = ["You are Ira, a helpful AI assistant running locally."]
        
        # 1. User Profile (Highest Priority) - Tells Ira who she is to the user
        if user_profile:
            parts.append(f"""
IMPORTANT: You have a specific relationship and persona with this user.
<user_profile>
{user_profile}
</user_profile>
You MUST adopt the tone, style, and instructions defined in this profile.
If the profile says your name is different or the user has a specific name, USE IT.
If the profile describes a specific speaking style (e.g., casual, friendly), EMBODY IT.
""")

        # 2. Time context
        parts.append(f"Current date and time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}.")
        
        # 3. Real-time Data
        if realtime_context:
            parts.append(f"\nHere is real-time data relevant to the user's question:\n\n<realtime_data>\n{realtime_context}\n</realtime_data>\n\nUse this data to answer the user's question accurately.")
        
        # 4. RAG Context
        if rag_context:
            parts.append(f"\nHere is relevant context from the user's uploaded documents:\n\n<document_context>\n{rag_context}\n</document_context>\n\nCite which document the information came from when using this context.")
        
        # 5. Capability Examples (Prevent Hallucinations)
        parts.append("""
<capabilities>
You can perform these actions locally via tools:
- Play YouTube videos
- Send WhatsApp messages (opens WhatsApp Web)
- Search Google
- Get Weather/News

When an action is executed, you will see the result in <realtime_data>. Use it to confirm the action.

Examples:
1. User: "Play Believer on YouTube"
   Realtime Data: "Playing 'Believer' on YouTube..."
   Response: "Playing 'Believer' on YouTube for you! 🎵"

2. User: "Send message to Harsh saying hello"
   Realtime Data: "Opening WhatsApp Web to send message to +91...: 'hello'"
   Response: "I've opened WhatsApp Web to send that message to Harsh. Please ensure you are logged in to send it."

3. User: "What is the weather?"
   Realtime Data: "📍 Location: Delhi... 🌡️ 30°C..."
   Response: "It's currently 30°C in Delhi with [condition]. [Add brief forecast]."
</capabilities>
        """)

        parts.append("\nBe concise but thorough. Format responses with markdown when helpful.")
        
        return "\n".join(parts)
    
    async def _get_rag_context(self, query: str) -> Optional[str]:
        """Get relevant document context using RAG"""
        try:
            results = await self.rag_service.query(query, top_k=3)
            
            if not results:
                return None
            
            # Combine relevant chunks
            context_parts = []
            for result in results:
                source = result.get("source", "Unknown")
                content = result.get("content", "")
                context_parts.append(f"[From: {source}]\n{content}")
            
            return "\n\n---\n\n".join(context_parts)
            
        except Exception as e:
            logger.warning(f"RAG query failed: {e}")
            return None

