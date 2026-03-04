"""
Admin/Configuration SQLAlchemy models.
SMTP, LLM, Prompt templates, System logs, Preferences.
"""
from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime, Text
from datetime import datetime
import uuid

from database import Base


class SmtpConfiguration(Base):
    __tablename__ = 'smtp_configurations'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), nullable=False)  # gmail, outlook, office365, custom
    smtp_host = Column(String(255), nullable=False)
    smtp_port = Column(Integer, nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(500), nullable=False)  # Encrypted/App password
    use_tls = Column(Boolean, default=True)
    use_ssl = Column(Boolean, default=False)
    from_name = Column(String(255))
    from_email = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_tested_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LlmConfiguration(Base):
    __tablename__ = 'llm_configurations'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), nullable=False)  # openai, anthropic, google, local_llm, etc.
    api_key = Column(String(500), nullable=True)  # Encrypted API key (optional for local_llm)
    model = Column(String(100), nullable=False)  # e.g., gpt-4, gpt-3.5-turbo, qwen2.5:7b
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    # Local LLM specific fields
    local_llm_url = Column(String(500), nullable=True)  # URL for local LLM API
    local_llm_stream = Column(Boolean, default=False)  # Stream responses
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_tested_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptTemplate(Base):
    __tablename__ = 'prompt_templates'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text)
    use_case = Column(String(100))  # report, analysis, summary, custom
    agent_role = Column(Text)  # Agent role description for this template
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemLog(Base):
    __tablename__ = 'system_logs'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36))
    user_email = Column(String(255))
    action = Column(String(100), nullable=False)  # login, logout, chat, config_update, etc.
    module = Column(String(100))  # auth, chat, admin, smtp, llm, etc.
    details = Column(Text)  # JSON string with additional details
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    status = Column(String(20), default='success')  # success, failure, warning
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemPreference(Base):
    __tablename__ = 'system_preferences'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    data_type = Column(String(20), default='string')  # string, boolean, number, json
    category = Column(String(50))  # general, chat, reports, notifications, etc.
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
