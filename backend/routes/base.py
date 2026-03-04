"""
Base/Core API routes.
Health check and sample questions.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from database import get_db
from models.base import User
from schemas.base import UserResponse

router = APIRouter()


@router.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Asset Manager API"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Asset Manager API"}


@router.get("/users", response_model=List[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db)):
    """Get all users."""
    result = await db.execute(select(User))
    return result.scalars().all()

