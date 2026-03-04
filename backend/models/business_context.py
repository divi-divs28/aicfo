"""
Business Context model for Vanna training data storage.
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from database import Base


class BusinessContext(Base):
    """Model for storing business context training data."""
    __tablename__ = "business_context"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    is_sync = Column(Integer, default=0, nullable=False)  # 0=not synced to Vanna, 1=synced
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
