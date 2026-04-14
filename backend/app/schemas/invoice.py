"""
Invoice schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from app.models.invoice import InvoiceStatus, EscalationStage


class ReminderBase(BaseModel):
    """Base reminder schema."""
    reminder_type: str = "manual"
    sent_via: str = "telegram"
    message: Optional[str] = None


class ReminderCreate(ReminderBase):
    """Reminder creation schema."""
    invoice_id: int


class ReminderResponse(ReminderBase):
    """Reminder response schema."""
    id: int
    invoice_id: int
    reminder_date: datetime
    status: str

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    """Base invoice schema."""
    invoice_number: str = Field(max_length=50)
    invoice_date: date
    due_date: date
    customer_name: str = Field(max_length=255)
    customer_vat: Optional[str] = ""
    customer_address: Optional[str] = ""
    customer_phone: Optional[str] = ""
    customer_pec: Optional[str] = ""
    customer_sdi: Optional[str] = ""
    customer_cf: Optional[str] = ""
    supplier_name: Optional[str] = ""
    supplier_vat: Optional[str] = ""
    amount: float = 0
    vat_amount: float = 0
    total_amount: float = 0
    status: InvoiceStatus = InvoiceStatus.PENDING
    description: Optional[str] = ""


class InvoiceCreate(InvoiceBase):
    """Invoice creation from XML upload."""
    xml_content: Optional[str] = None


class InvoiceUpdate(BaseModel):
    """Invoice update schema."""
    status: Optional[InvoiceStatus] = None
    due_date: Optional[date] = None
    description: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    """Invoice response schema."""
    id: int
    supplier_phone: Optional[str] = ""
    supplier_pec: Optional[str] = ""
    supplier_iban: Optional[str] = ""
    supplier_sdi: Optional[str] = ""
    supplier_cf: Optional[str] = ""
    customer_email: Optional[str] = ""
    xml_filename: Optional[str] = ""
    created_at: datetime
    updated_at: datetime
    reminders: List[ReminderResponse] = []
    # Escalation
    escalation_stage: EscalationStage = EscalationStage.NONE
    escalation_updated_at: Optional[datetime] = None
    penalty_applied: float = 0

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    """Paginated invoice list response."""
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class InvoiceStats(BaseModel):
    """Dashboard statistics."""
    total: int
    paid: int
    pending: int
    overdue: int
    due_soon: int
    total_amount: float
    paid_amount: float
    pending_amount: float
    overdue_amount: float


class InvoiceFilter(BaseModel):
    """Filter parameters for invoice list."""
    status: Optional[InvoiceStatus] = None
    due_soon: Optional[int] = None  # days
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20


class BulkAction(BaseModel):
    """Bulk action on invoices."""
    invoice_ids: List[int]


class CalcoloInteressiResponse(BaseModel):
    """Response for interest/penalty calculation."""
    importo_originale: float
    interessi: float
    penalty: float
    totale: float
    giorni_ritardo: int
    tasso_applicato: float
    data_pagamento: Optional[date] = None
