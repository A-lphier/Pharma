"""
User model using SQLModel.
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class User(SQLModel, table=True):
    """User model for authentication."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, max_length=100)
    hashed_password: str = Field(max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    telegram_chat_id: Optional[str] = Field(default=None, max_length=50)
    # Billing / Subscription
    subscription_tier: Optional[str] = Field(default="free", max_length=20)
    subscription_id: Optional[str] = Field(default=None, max_length=100)
    stripe_customer_id: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
