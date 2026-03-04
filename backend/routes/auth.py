"""
Authentication routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib

from schemas.auth import LoginRequest
from database import get_db
from models.base import User

router = APIRouter(prefix="/auth")


def hash_password(password: str) -> str:
    """Simple password hashing using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/login")
async def login(login_request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login endpoint - verifies against database and returns user with role."""
    if not login_request.email or not login_request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Fetch user from database
    result = await db.execute(
        select(User).where(User.email == login_request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    password_hash = hash_password(login_request.password)
    if user.password != password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return {
        "token": "demo_token_123",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    }
