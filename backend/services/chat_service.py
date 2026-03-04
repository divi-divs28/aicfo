"""
Chat Service.
Handles chat session management and conversation history.
"""
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from models.chat import ChatMessage, ChatSession, SessionMember
from schemas.chat import ChatQuery, ChatResponse, CreateSessionRequest, CreateSessionResponse
from services.analytics_service import analytics_service
from utils.logging_config import chat_logger
from utils.json_serial import sanitize_chat_response


class ChatService:
    """Service for chat session and message management."""
    
    async def create_session(self, db: AsyncSession, user_id: int) -> CreateSessionResponse:
        """Create a new chat session in the database."""
        session_id = str(uuid.uuid4())
        
        # Create session with default title (will be updated after first message)
        chat_session = ChatSession(
            id=session_id,
            user_id=user_id,
            session_title="New Conversation",
            status="ACTIVE",
            created_at=datetime.utcnow()
        )
        
        db.add(chat_session)
        await db.commit()
        
        chat_logger.info(f"\n{'='*80}")
        chat_logger.info(f"NEW SESSION CREATED: {session_id}")
        chat_logger.info(f"USER: {user_id}")
        chat_logger.info(f"{'='*80}\n")
        
        return CreateSessionResponse(
            session_id=session_id,
            session_title="New Conversation"
        )
    
    async def generate_session_title(self, message: str) -> str:
        """Generate a short title based on the first message."""
        # Simple title generation: take first 50 chars and clean up
        title = message.strip()
        
        # Remove common question starters
        starters = ["what is", "show me", "give me", "list", "how many", "what are", "can you"]
        lower_title = title.lower()
        for starter in starters:
            if lower_title.startswith(starter):
                title = title[len(starter):].strip()
                break
        
        # Capitalize first letter and limit length
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
        
        # Limit to 50 characters
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title if title else "New Conversation"
    
    async def update_session_title(self, db: AsyncSession, session_id: str, title: str) -> None:
        """Update session title (after first message or user edit)."""
        await db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(session_title=title)
        )
        await db.commit()

    async def delete_session(self, db: AsyncSession, session_id: str) -> bool:
        """Delete a chat session and all its messages and members. Returns True if deleted."""
        await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        await db.execute(delete(SessionMember).where(SessionMember.session_id == session_id))
        result = await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
        await db.commit()
        return result.rowcount > 0

    async def update_session_last_message(self, db: AsyncSession, session_id: str) -> None:
        """Update last_message_at timestamp."""
        await db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(last_message_at=datetime.utcnow())
        )
        await db.commit()
    
    async def is_first_message(self, db: AsyncSession, session_id: str) -> bool:
        """Check if this is the first message in the session."""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .limit(1)
        )
        return result.scalar() is None
    
    async def get_conversation_history(self, db: AsyncSession, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Fetch conversation history for a session."""
        if not session_id:
            return []
        
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        history_messages = list(reversed(result.scalars().all()))
        
        chat_logger.info(f"FETCHED {len(history_messages)} HISTORY MESSAGES")
        
        conversation_history = []
        for msg in history_messages:
            user_content = f"User asked: {msg.message}"
            conversation_history.append({"role": "user", "content": user_content})
            
            if msg.response:
                response_content = msg.response
                if len(response_content) > 1000:
                    response_content = response_content[:1000] + "... [truncated]"
                conversation_history.append({"role": "assistant", "content": response_content})
        
        return conversation_history
    
    async def process_chat_message(self, query: ChatQuery, db: AsyncSession) -> ChatResponse:
        """Process a chat message and return response."""
        logging.info(f"Incoming chat query from user={query.user_id}, session={query.session_id}: {query.message}")
        chat_logger.info(f"\n{'='*80}")
        chat_logger.info(f"SESSION: {query.session_id}")
        chat_logger.info(f"USER ID: {query.user_id}")
        
        # Auto-create session if none provided
        if not query.session_id:
            session_response = await self.create_session(db, query.user_id)
            query.session_id = session_response.session_id
            chat_logger.info(f"AUTO-CREATED SESSION: {query.session_id}")
        
        # Check if this is the first message and update session title
        if query.session_id:
            is_first = await self.is_first_message(db, query.session_id)
            if is_first:
                title = await self.generate_session_title(query.message)
                await self.update_session_title(db, query.session_id, title)
                chat_logger.info(f"SESSION TITLE SET: {title}")
        
        # Get conversation history
        conversation_history = await self.get_conversation_history(db, query.session_id)
        
        # Get AI response
        response = await analytics_service.analyze_data(query.message, db, conversation_history)
        
        # Ensure date/datetime are JSON-serializable (fixes "Object of type date is not JSON serializable")
        sanitize_chat_response(response)
        
        # Save message to database
        await self.save_chat_message(db, query, response)
        
        # Update session last_message_at
        if query.session_id:
            await self.update_session_last_message(db, query.session_id)
        
        return response
    
    async def save_chat_message(self, db: AsyncSession, query: ChatQuery, response: ChatResponse) -> None:
        """Save chat message and response to database."""
        chat_message = ChatMessage(
            id=str(uuid.uuid4()),
            user_id=query.user_id,
            message=query.message,
            response=response.response,
            charts=json.dumps([chart.model_dump() for chart in response.charts]),
            tables=json.dumps([table.model_dump() for table in response.tables]),
            summary_points=json.dumps(response.summary_points),
            kpi_cards=json.dumps([kpi.model_dump() for kpi in response.kpi_cards]),
            session_id=query.session_id
        )
        db.add(chat_message)
        await db.commit()


# Singleton instance
chat_service = ChatService()
