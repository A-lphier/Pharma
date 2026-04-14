"""
User schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class Token(BaseModel):
    """JWT Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: int
    role: str
    type: str  # "access" or "refresh"


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(min_length=8)
    role: Optional[UserRole] = UserRole.USER


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    """User response schema."""
    id: int
    role: UserRole
    is_active: bool
    telegram_chat_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """User with hashed password (internal)."""
    hashed_password: str
