"""
Authentication Pydantic schemas.
"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str
