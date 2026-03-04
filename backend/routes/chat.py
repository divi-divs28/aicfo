"""
Chat routes.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from pydantic import BaseModel
from typing import Optional
import logging

from database import get_db
from schemas.chat import ChatQuery, ChatResponse, CreateSessionRequest, CreateSessionResponse
from services.chat_service import chat_service
from services.llm_service import llm_service
from models.chat import ChatSession, ChatMessage, SessionMember
from models.base import User

router = APIRouter(prefix="/chat")


class JoinSessionRequest(BaseModel):
    session_id: str
    user_id: int


class UpdateSessionTitleRequest(BaseModel):
    title: str


class ShareLinkResponse(BaseModel):
    session_id: str
    share_url: str


@router.post("/session", response_model=CreateSessionResponse)
async def create_chat_session(request: CreateSessionRequest, db: AsyncSession = Depends(get_db)):
    """Create a new chat session and return session_id."""
    try:
        response = await chat_service.create_session(db, request.user_id)
        
        # Add owner to session_members
        member = SessionMember(
            session_id=response.session_id,
            user_id=request.user_id,
            is_owner=True
        )
        db.add(member)
        await db.commit()
        
        return response
    except Exception as e:
        logging.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/warmup")
async def warmup_llm(db: AsyncSession = Depends(get_db)):
    """
    Warm up the LLM connection. Call after creating a new session so the first
    user query does not hit a cold connection. Not stored in chat history or shown on UI.
    """
    try:
        ok = await llm_service.warmup_llm(db)
        return {"success": ok}
    except Exception as e:
        logging.warning(f"LLM warmup failed: {e}")
        return {"success": False}


@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: int, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get chat sessions for a user, separated by type (group/private)."""
    try:
        # Get sessions where user is owner OR is a member
        member_result = await db.execute(
            select(SessionMember.session_id).where(SessionMember.user_id == user_id)
        )
        member_session_ids = [r[0] for r in member_result.fetchall()]
        
        # Get all sessions (owned or member of)
        result = await db.execute(
            select(ChatSession)
            .where(
                or_(
                    ChatSession.user_id == user_id,
                    ChatSession.id.in_(member_session_ids) if member_session_ids else False
                )
            )
            .where(ChatSession.session_title != "New Conversation")
            .order_by(desc(ChatSession.last_message_at), desc(ChatSession.created_at))
            .limit(limit)
        )
        sessions = result.scalars().all()
        
        # Separate into group and private
        group_sessions = []
        private_sessions = []
        
        for s in sessions:
            session_data = {
                "id": s.id,
                "title": s.session_title,
                "status": s.status,
                "session_type": s.session_type or 'PRIVATE',
                "is_owner": s.user_id == user_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None
            }
            
            if s.session_type == 'GROUP':
                group_sessions.append(session_data)
            else:
                private_sessions.append(session_data)
        
        return {
            "success": True,
            "group_sessions": group_sessions,
            "private_sessions": private_sessions,
            "sessions": group_sessions + private_sessions  # For backward compatibility
        }
    except Exception as e:
        logging.error(f"Error fetching user sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/session/{session_id}/title")
async def update_session_title(
    session_id: str,
    request: UpdateSessionTitleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update the title of a chat session."""
    try:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        await chat_service.update_session_title(db, session_id, request.title.strip() or session.session_title)
        return {"success": True, "title": request.title.strip()}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating session title: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a chat session and all its messages. Refreshes chat history on client."""
    try:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        deleted = await chat_service.delete_session(db, session_id)
        return {"success": True, "deleted": deleted}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/info")
async def get_session_info(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get session information including members."""
    try:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get members
        members_result = await db.execute(
            select(SessionMember).where(SessionMember.session_id == session_id)
        )
        members = members_result.scalars().all()
        
        return {
            "success": True,
            "session": {
                "id": session.id,
                "title": session.session_title,
                "session_type": session.session_type or 'PRIVATE',
                "status": session.status,
                "owner_id": session.user_id,
                "created_at": session.created_at.isoformat() if session.created_at else None
            },
            "members": [
                {
                    "user_id": m.user_id,
                    "is_owner": m.is_owner,
                    "joined_at": m.joined_at.isoformat() if m.joined_at else None
                }
                for m in members
            ],
            "member_count": len(members)
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching session info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/join")
async def join_session(session_id: str, request: JoinSessionRequest, db: AsyncSession = Depends(get_db)):
    """Join an existing chat session (makes it a group chat)."""
    try:
        # Check if session exists
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if user is already a member
        member_check = await db.execute(
            select(SessionMember)
            .where(SessionMember.session_id == session_id)
            .where(SessionMember.user_id == request.user_id)
        )
        existing_member = member_check.scalar_one_or_none()
        
        if existing_member:
            return {
                "success": True,
                "message": "Already a member of this session",
                "session_id": session_id
            }
        
        # Add user as member
        new_member = SessionMember(
            session_id=session_id,
            user_id=request.user_id,
            is_owner=False
        )
        db.add(new_member)
        
        # Update session type to GROUP
        session.session_type = 'GROUP'
        
        await db.commit()
        
        logging.info(f"User {request.user_id} joined session {session_id}")
        
        return {
            "success": True,
            "message": "Successfully joined the group chat",
            "session_id": session_id,
            "session_title": session.session_title
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error joining session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/share")
async def get_share_link(session_id: str, db: AsyncSession = Depends(get_db)):
    """Generate a shareable link for a session."""
    try:
        # Verify session exists
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # The share URL will be constructed on the frontend using this session_id
        return {
            "success": True,
            "session_id": session_id,
            "session_title": session.session_title
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error generating share link: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/messages")
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get all messages for a specific session."""
    try:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        messages = result.scalars().all()
        # Resolve user names for group chat display
        user_ids = list({m.user_id for m in messages})
        user_names = {}
        if user_ids:
            users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
            for u in users_result.scalars().all():
                user_names[u.id] = u.name or f"User {u.id}"

        formatted_messages = []
        for m in messages:
            # Parse JSON fields
            charts = []
            tables = []
            summary_points = []
            kpi_cards = []
            
            try:
                if m.charts:
                    charts = json.loads(m.charts) if isinstance(m.charts, str) else m.charts
            except (json.JSONDecodeError, TypeError):
                pass
                
            try:
                if m.tables:
                    tables = json.loads(m.tables) if isinstance(m.tables, str) else m.tables
            except (json.JSONDecodeError, TypeError):
                pass
                
            try:
                if m.summary_points:
                    summary_points = json.loads(m.summary_points) if isinstance(m.summary_points, str) else m.summary_points
            except (json.JSONDecodeError, TypeError):
                pass
            
            # kpi_cards: prefer dedicated column, fall back to parsing from response JSON (old rows)
            try:
                if getattr(m, 'kpi_cards', None):
                    kpi_cards = json.loads(m.kpi_cards) if isinstance(m.kpi_cards, str) else m.kpi_cards
                elif m.response and m.response.startswith('{'):
                    response_json = json.loads(m.response)
                    if isinstance(response_json, dict) and 'kpi_cards' in response_json:
                        kpi_cards = response_json.get('kpi_cards', [])
            except (json.JSONDecodeError, TypeError):
                pass
            
            formatted_messages.append({
                "id": m.id,
                "user_id": m.user_id,
                "user_name": user_names.get(m.user_id, f"User {m.user_id}"),
                "message": m.message,
                "response": m.response,
                "charts": charts,
                "tables": tables,
                "summary_points": summary_points,
                "kpi_cards": kpi_cards,
                "created_at": m.created_at.isoformat() if m.created_at else None
            })
        
        return {
            "success": True,
            "messages": formatted_messages
        }
    except Exception as e:
        logging.error(f"Error fetching session messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ChatResponse)
async def chat_endpoint(query: ChatQuery, db: AsyncSession = Depends(get_db)):
    """Process a chat message and return AI response."""
    try:
        return await chat_service.process_chat_message(query, db)
    except Exception as e:
        logging.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
