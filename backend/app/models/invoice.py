"""
Invoice models using SQLModel.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class EscalationStage(str, Enum):
    """Escalation stages for overdue invoices."""
    NONE = "none"                       # Not overdue / paid
    SOLLECITO_1 = "sollecito_1"         # 7 days overdue
    SOLLECITO_2 = "sollecito_2"         # 30 days overdue
    PENALTY_APPLICATA = "penalty_applicata"  # 60 days overdue + interest
    DIFFIDA = "diffida"                 # 90 days overdue
    STOP_SERVIZI = "stop_servizi"       # 120 days overdue (recurring)
    LEGAL_ACTION = "legal_action"       # 120 days overdue (non-recurring)


class Invoice(SQLModel, table=True):
    """Invoice model for FatturaPA documents."""

    __tablename__ = "invoices"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Invoice identification
    invoice_number: str = Field(max_length=50, index=True)
    invoice_date: date
    due_date: date = Field(index=True)
    
    # Customer (CessionarioCommittente)
    customer_name: str = Field(max_length=255)
    customer_vat: Optional[str] = Field(default="", max_length=20)
    customer_address: Optional[str] = Field(default="", max_length=500)
    customer_phone: Optional[str] = Field(default="", max_length=50)
    customer_pec: Optional[str] = Field(default="", max_length=255)
    customer_sdi: Optional[str] = Field(default="", max_length=10)
    customer_cf: Optional[str] = Field(default="", max_length=20)
    customer_email: Optional[str] = Field(default="", max_length=255)
    
    # Supplier (CedentePrestatore)
    supplier_name: str = Field(default="", max_length=255)
    supplier_vat: Optional[str] = Field(default="", max_length=20)
    supplier_address: Optional[str] = Field(default="", max_length=500)
    supplier_phone: Optional[str] = Field(default="", max_length=50)
    supplier_pec: Optional[str] = Field(default="", max_length=255)
    supplier_iban: Optional[str] = Field(default="", max_length=34)
    supplier_sdi: Optional[str] = Field(default="", max_length=10)
    supplier_cf: Optional[str] = Field(default="", max_length=20)
    supplier_email: Optional[str] = Field(default="", max_length=255)
    
    # Amounts
    amount: float = Field(default=0)
    vat_amount: float = Field(default=0)
    total_amount: float = Field(default=0)
    
    # Status & Description
    status: InvoiceStatus = Field(default=InvoiceStatus.PENDING, index=True)
    description: Optional[str] = Field(default="", max_length=1000)
    
    # File storage
    xml_filename: Optional[str] = Field(default="", max_length=255)
    raw_xml: Optional[str] = Field(default=None)
    
    # Metadata
    payment_days: Optional[int] = Field(default=None)
    payment_method: Optional[str] = Field(default="", max_length=100)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    
    # Relationships
    reminders: List["Reminder"] = Relationship(back_populates="invoice")

    # Escalation tracking
    escalation_stage: EscalationStage = Field(default=EscalationStage.NONE, index=True)
    escalation_updated_at: Optional[datetime] = Field(default=None)
    penalty_applied: float = Field(default=0)  # Interest penalty amount applied


class Reminder(SQLModel, table=True):
    """Reminder model for invoice follow-ups."""

    __tablename__ = "reminders"

    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoices.id", index=True)
    
    reminder_date: datetime = Field(default_factory=datetime.utcnow)
    reminder_type: str = Field(default="manual")  # manual, automatic, sms, email
    sent_via: str = Field(default="telegram")  # telegram, email, sms
    status: str = Field(default="pending")  # pending, sent, failed
    message: Optional[str] = Field(default=None, max_length=1000)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_by: Optional[int] = Field(default=None, foreign_key="users.id")
    
    # Relationships
    invoice: Optional[Invoice] = Relationship(back_populates="reminders")
