"""
User management routes.
CRUD operations for users.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
import logging
import hashlib

from database import get_db
from models.base import User

router = APIRouter(prefix="/api/admin/users", tags=["users"])


# Pydantic schemas
class UserCreate(BaseModel):
    email: EmailStr
    name: str
    role: str
    password: Optional[str] = "password123"
    profile_verified: Optional[bool] = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    profile_verified: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    profile_verified: bool
    created_at: datetime

    @field_validator("role", mode="before")
    @classmethod
    def role_default(cls, v):
        """Handle DB rows where role is NULL (legacy data)."""
        return v if v is not None else "viewer"

    class Config:
        from_attributes = True


def hash_password(password: str) -> str:
    """Simple password hashing using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


@router.get("", response_model=List[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db)):
    """Get all users."""
    try:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
        return users
    except Exception as e:
        logging.error(f"Error fetching users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single user by ID."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")


@router.post("", response_model=UserResponse)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user."""
    try:
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Create new user
        new_user = User(
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            password=hash_password(user_data.password) if user_data.password else None,
            profile_verified=user_data.profile_verified,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logging.info(f"User created: {new_user.email}")
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing user."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if new email already exists (for another user)
        if user_data.email and user_data.email != user.email:
            email_check = await db.execute(select(User).where(User.email == user_data.email))
            if email_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Email already exists")
        
        # Update fields
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.name is not None:
            user.name = user_data.name
        if user_data.role is not None:
            user.role = user_data.role
        if user_data.password is not None:
            user.password = hash_password(user_data.password)
        if user_data.profile_verified is not None:
            user.profile_verified = user_data.profile_verified
        
        await db.commit()
        await db.refresh(user)
        
        logging.info(f"User updated: {user.email}")
        return user
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a user."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        email = user.email
        await db.delete(user)
        await db.commit()
        
        logging.info(f"User deleted: {email}")
        return {"success": True, "message": f"User {email} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@router.get("/roles/list")
async def get_available_roles():
    """Get available user roles."""
    return [
        {"id": "admin", "name": "Admin", "description": "Full system access"},
        {"id": "manager", "name": "Manager", "description": "Management access"},
        {"id": "analyst", "name": "Analyst", "description": "Analytics and reporting access"},
        {"id": "viewer", "name": "Viewer", "description": "Read-only access"}
    ]
