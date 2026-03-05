"""
Conversation Manager
CRUD operations for conversations and messages
"""

import uuid
from typing import List, Dict, Optional
from datetime import datetime

from app.memory.database import Database


class ConversationManager:
    """Manage conversations and messages"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_conversation(self, title: str = "New Chat") -> Dict:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        
        await self.db.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (conversation_id, title)
        )
        
        return {
            "id": conversation_id,
            "title": title,
            "created_at": datetime.now().isoformat()
        }
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a conversation with its messages"""
        conversation = await self.db.fetch_one(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        
        if not conversation:
            return None
        
        messages = await self.get_messages(conversation_id)
        
        return {
            **conversation,
            "messages": messages
        }
    
    async def list_conversations(self) -> List[Dict]:
        """List all conversations"""
        conversations = await self.db.fetch_all(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        )
        return conversations
    
    async def update_conversation(self, conversation_id: str, title: str):
        """Update conversation title"""
        await self.db.execute(
            "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, conversation_id)
        )
    
    async def delete_conversation(self, conversation_id: str):
        """Delete a conversation and its messages"""
        await self.db.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,)
        )
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> int:
        """Add a message to a conversation"""
        cursor = await self.db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content)
        )
        
        # Update conversation timestamp
        await self.db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        
        return cursor.lastrowid
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get messages for a conversation"""
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at"
        
        if limit:
            query += f" DESC LIMIT {limit}"
            messages = await self.db.fetch_all(query, (conversation_id,))
            return list(reversed(messages))
        
        return await self.db.fetch_all(query, (conversation_id,))
    
    async def clear_messages(self, conversation_id: str):
        """Clear all messages in a conversation"""
        await self.db.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
