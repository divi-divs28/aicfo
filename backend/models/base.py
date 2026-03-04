"""
Base/Core SQLAlchemy models.
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from datetime import datetime

from database import Base


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    profile_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    password = Column(String(100), nullable=True)
    role = Column(String(100), nullable=True)
