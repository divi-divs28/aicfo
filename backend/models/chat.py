"""
Chat-related SQLAlchemy models.
Question categories, suggested questions, dashboard cards, chat messages, chat sessions.
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, Enum
from datetime import datetime
import uuid
import enum

from database import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    __table_args__ = {'extend_existing': True}
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False)
    session_title = Column(String(255), nullable=False)
    session_type = Column(String(20), default='PRIVATE')  # PRIVATE or GROUP
    status = Column(String(20), default='ACTIVE')
    created_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, nullable=True)


class SessionMember(Base):
    __tablename__ = 'session_members'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False)
    user_id = Column(Integer, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_owner = Column(Boolean, default=False)


class QuestionCategory(Base):
    __tablename__ = 'question_categories'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    color = Column(String(100), default='bg-blue-50 border-blue-100')
    icon_bg = Column(String(100), default='bg-blue-500')
    text_color = Column(String(100), default='text-blue-700')
    icon_type = Column(String(50), default='chart')
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SuggestedQuestion(Base):
    __tablename__ = 'suggested_questions'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id = Column(String(36), nullable=False)
    question_text = Column(Text, nullable=False)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DashboardCard(Base):
    __tablename__ = 'dashboard_cards'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    icon = Column(String(50))
    description = Column(String(255))
    gradient = Column(String(100))
    bg_color = Column(String(100))
    text_color = Column(String(100))
    query_type = Column(String(100), nullable=False)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    __table_args__ = {'extend_existing': True}
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text)
    charts = Column(Text)
    tables = Column(Text)
    summary_points = Column(Text)
    kpi_cards = Column(Text)  # JSON array of {label, value, unit} for KPI cards
    session_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
