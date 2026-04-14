"""
Pydantic schemas for client management API.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ClientBase(BaseModel):
    """Base client schema."""
    name: str = Field(..., max_length=255)
    vat: Optional[str] = Field(default="", max_length=20)
    fiscal_code: Optional[str] = Field(default="", max_length=20)
    email: Optional[str] = Field(default="", max_length=255)
    phone: Optional[str] = Field(default="", max_length=50)
    pec: Optional[str] = Field(default="", max_length=255)
    sdi: Optional[str] = Field(default="", max_length=10)
    iban: Optional[str] = Field(default="", max_length=34)
    address: Optional[str] = Field(default="", max_length=500)
    notes: Optional[str] = Field(default="", max_length=1000)


class ClientCreate(ClientBase):
    """Schema for creating a client."""
    pass


class ClientUpdate(BaseModel):
    """Schema for updating a client."""
    name: Optional[str] = Field(default=None, max_length=255)
    vat: Optional[str] = Field(default=None, max_length=20)
    fiscal_code: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    pec: Optional[str] = Field(default=None, max_length=255)
    sdi: Optional[str] = Field(default=None, max_length=10)
    iban: Optional[str] = Field(default=None, max_length=34)
    address: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=1000)


class ClientResponse(ClientBase):
    """Schema for client response."""
    id: int
    trust_score: int
    payment_pattern: str
    late_reason: Optional[str]
    is_new: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    """Schema for paginated client list."""
    items: List[ClientResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ClientScoreUpdate(BaseModel):
    """Schema for updating client score manually."""
    trust_score: int = Field(..., ge=0, le=100)


# Business Config schemas

class BusinessConfigResponse(BaseModel):
    """Schema for business config response."""
    id: int
    style: str
    legal_threshold: float
    new_client_score: int
    first_reminder_days: int
    warning_threshold_days: int
    escalation_days: int
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BusinessConfigUpdate(BaseModel):
    """Schema for updating business config."""
    style: Optional[str] = Field(default=None, pattern="^(gentile|equilibrato|fermo)$")
    legal_threshold: Optional[float] = Field(default=None, ge=0)
    new_client_score: Optional[int] = Field(default=None, ge=0, le=100)
    first_reminder_days: Optional[int] = Field(default=None, ge=0)
    warning_threshold_days: Optional[int] = Field(default=None, ge=0)
    escalation_days: Optional[int] = Field(default=None, ge=0)


# Onboarding schemas

class OnboardingStatusResponse(BaseModel):
    """Schema for onboarding status."""
    status: str  # not_started, in_progress, completed
    current_step: Optional[int] = None
    total_steps: int = 4
    answers: Optional[dict] = None


class OnboardingQuestionResponse(BaseModel):
    """Schema for onboarding question."""
    step: int
    question: str
    options: Optional[List[dict]] = None
    input_type: str  # single_choice, multiple_choice, slider
    slider_min: Optional[int] = None
    slider_max: Optional[int] = None
    slider_default: Optional[int] = None


class OnboardingAnswerRequest(BaseModel):
    """Schema for answering onboarding question."""
    step: int
    answer: str | int | List[str]


class OnboardingConfigProposal(BaseModel):
    """Schema for proposed config after onboarding."""
    style: str
    legal_threshold: float
    new_client_score: int
    first_reminder_days: int
    warning_threshold_days: int
    escalation_days: int
    reasoning: str


class OnboardingApproveRequest(BaseModel):
    """Schema for approving onboarding config."""
    approved: bool


# Import schemas

class ImportHistoryResponse(BaseModel):
    """Schema for import history response."""
    id: int
    filename: str
    rows_imported: int
    clients_created: int
    invoices_created: int
    imported_at: datetime

    class Config:
        from_attributes = True


class ImportResultResponse(BaseModel):
    """Schema for import result."""
    success: bool
    rows_imported: int
    clients_created: int
    clients_updated: int
    invoices_created: int
    errors: List[str] = []


# Feedback schemas

class LateReasonFeedbackRequest(BaseModel):
    """Schema for submitting late reason feedback."""
    reason: str = Field(..., pattern="^(not_received|disputed|financial_issues|about_to_pay|wrong_invoice|refused)$")
    notes: Optional[str] = Field(default="", max_length=1000)


class LateReasonFeedbackResponse(BaseModel):
    """Schema for feedback response."""
    id: int
    invoice_id: int
    reason: str
    notes: str
    created_at: datetime

    class Config:
        from_attributes = True


# Payment History schemas

class PaymentHistoryResponse(BaseModel):
    """Schema for payment history response."""
    id: int
    client_id: int
    invoice_id: Optional[int]
    invoice_amount: float
    invoice_date: datetime
    due_date: datetime
    paid_date: Optional[datetime]
    days_late: int
    was_on_time: bool
    created_at: datetime

    class Config:
        from_attributes = True
