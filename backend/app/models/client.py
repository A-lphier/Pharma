"""
Client and payment history models for intelligent customer management.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


class Client(SQLModel, table=True):
    """Client model for tracking customer payment behavior."""

    __tablename__ = "clients"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, index=True)
    vat: Optional[str] = Field(default="", max_length=20)
    fiscal_code: Optional[str] = Field(default="", max_length=20)
    email: Optional[str] = Field(default="", max_length=255)
    phone: Optional[str] = Field(default="", max_length=50)
    pec: Optional[str] = Field(default="", max_length=255)
    sdi: Optional[str] = Field(default="", max_length=10)
    iban: Optional[str] = Field(default="", max_length=34)
    address: Optional[str] = Field(default="", max_length=500)
    
    # Trust scoring
    trust_score: int = Field(default=60, ge=0, le=100)
    payment_pattern: Optional[str] = Field(default="")
    late_reason: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default="")
    is_new: bool = Field(default=True)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")

    # Relationships
    payment_histories: List["PaymentHistory"] = Relationship(back_populates="client")


class PaymentHistory(SQLModel, table=True):
    """Payment history for tracking client payment behavior over time."""

    __tablename__ = "payment_histories"

    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="clients.id", index=True)
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoices.id")
    
    # Invoice details
    invoice_amount: float = Field(default=0)
    invoice_date: datetime
    due_date: datetime
    paid_date: Optional[datetime] = Field(default=None)
    
    # Calculated fields
    days_late: int = Field(default=0)
    was_on_time: bool = Field(default=True)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")

    # Relationships
    client: Optional[Client] = Relationship(back_populates="payment_histories")


class BusinessConfig(SQLModel, table=True):
    """Business configuration for sollecito system (singleton)."""

    __tablename__ = "business_config"

    id: int = Field(default=1, primary_key=True)
    
    # Style configuration
    style: str = Field(default="gentile")  # 'gentile' | 'equilibrato' | 'fermo'
    
    # Thresholds
    legal_threshold: float = Field(default=2000.00)
    new_client_score: int = Field(default=60)
    first_reminder_days: int = Field(default=7)
    warning_threshold_days: int = Field(default=15)
    escalation_days: int = Field(default=30)
    
    # Onboarding state
    onboarding_completed: bool = Field(default=False)
    onboarding_answers: Optional[str] = Field(default=None)  # JSON string
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ImportHistory(SQLModel, table=True):
    """Track CSV import history."""

    __tablename__ = "import_histories"

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255)
    rows_imported: int = Field(default=0)
    clients_created: int = Field(default=0)
    invoices_created: int = Field(default=0)
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    imported_by: Optional[int] = Field(default=None, foreign_key="users.id")


class LateReasonFeedback(SQLModel, table=True):
    """Feedback on why an invoice was paid late."""

    __tablename__ = "late_reason_feedbacks"

    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoices.id", index=True)
    reason: str = Field(max_length=100)  # not_received, disputed, financial_issues, etc.
    notes: Optional[str] = Field(default="", max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
