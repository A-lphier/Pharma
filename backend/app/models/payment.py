"""
Payment model for Stripe Checkout.
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(SQLModel, table=True):
    """Payment record linked to an invoice via Stripe Checkout."""

    __tablename__ = "payments"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Link to invoice
    invoice_id: int = Field(foreign_key="invoices.id", index=True)

    # Stripe identifiers
    stripe_session_id: str = Field(max_length=255, unique=True, index=True)
    stripe_payment_intent_id: Optional[str] = Field(default=None, max_length=255, index=True)

    # Amount in EUR cents (to avoid float issues)
    amount_cents: int = Field(default=0)

    # Status
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
