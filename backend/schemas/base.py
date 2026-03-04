"""
Base Pydantic schemas for core models.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    location: Optional[str] = None
    profile_verified: bool
    created_at: datetime
