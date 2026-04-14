"""
Modelli SQLAlchemy NUOVI per FatturaMVP.
I modelli principali (User, Invoice, Client, Reminder, etc.) sono gia definiti
nei rispettivi file: user.py, invoice.py, client.py.

Questo file definisce SOLO i modelli nuovi introdotti di recente.
"""
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class SdiStatus(str, Enum):
    """Stati di invio SDI."""
    DRAFT = "draft"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"


class EmailType(str, Enum):
    """Tipi di email inviate."""
    INVOICE = "invoice"
    REMINDER = "reminder"
    SOLLECITO = "sollecito"
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    OTHER = "other"


class EmailLog(SQLModel, table=True):
    """Log di tutte le email inviate dal sistema."""
    __tablename__ = "email_logs"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Who sent it
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    # Email details
    to_email: str = Field(max_length=255, index=True)
    subject: str = Field(max_length=500)
    email_type: EmailType = Field(default=EmailType.OTHER)
    body_text: Optional[str] = Field(default=None)
    body_html: Optional[str] = Field(default=None)

    # Delivery status
    status: str = Field(default="sent", max_length=50)  # sent, delivered, opened, bounced, failed
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = Field(default=None)
    opened_at: Optional[datetime] = Field(default=None)

    # Reference to invoice if applicable
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoices.id", index=True)

    # Provider info
    provider: str = Field(default="brevo", max_length=50)  # brevo, smtp, etc.
    provider_message_id: Optional[str] = Field(default=None, max_length=255)

    # Error info if failed
    error_message: Optional[str] = Field(default=None, max_length=500)


class SDIInvoice(SQLModel, table=True):
    """Tracciamento invii SDI per ogni fattura."""
    __tablename__ = "sdi_invoices"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Reference to our Invoice model
    invoice_id: int = Field(foreign_key="invoices.id", index=True, unique=True)

    # SDI identifiers
    sdi_id: Optional[str] = Field(default=None, max_length=50, index=True)  # Identificativo SDI
    sdi_receipt_id: Optional[str] = Field(default=None, max_length=100)  # Receipt ID from SDI

    # Status tracking
    status: SdiStatus = Field(default=SdiStatus.DRAFT, index=True)
    status_message: Optional[str] = Field(default=None, max_length=500)

    # Request/response from OpenAPI
    request_body: Optional[str] = Field(default=None)  # XML inviato
    response_body: Optional[str] = Field(default=None)  # Risposta SDI
    error_code: Optional[str] = Field(default=None, max_length=50)

    # Timing
    sent_at: Optional[datetime] = Field(default=None)
    delivered_at: Optional[datetime] = Field(default=None)
    last_check_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationChannel(str, Enum):
    """Canali di notifica."""
    EMAIL = "email"
    PEC = "pec"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class Notification(SQLModel, table=True):
    """Tabella notifications per tutti i canali (email, WhatsApp, SMS, etc.)."""
    __tablename__ = "notifications"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Riferimenti
    invoice_id: int = Field(foreign_key="invoices.id", index=True)
    client_id: Optional[int] = Field(default=None, foreign_key="clients.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    # Canale e contenuto
    channel: NotificationChannel = Field(default=NotificationChannel.EMAIL, index=True)
    recipient: str = Field(max_length=255)  # email, phone, WhatsApp number
    content: str = Field(default="")

    # Stato invio
    status: str = Field(default="pending", max_length=50, index=True)  # pending, sent, delivered, failed
    sent_at: Optional[datetime] = Field(default=None)
    delivered_at: Optional[datetime] = Field(default=None)

    # Provider info
    provider_sid: Optional[str] = Field(default=None, max_length=255)  # Twilio SID
    provider_message_id: Optional[str] = Field(default=None, max_length=255)

    # Errore
    error_message: Optional[str] = Field(default=None, max_length=500)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Sollecito(SQLModel, table=True):
    """Log dei solleciti di pagamento generati e inviati."""
    __tablename__ = "solleciti"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Reference
    invoice_id: int = Field(foreign_key="invoices.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    # Message content
    content: str  # Contenuto del messaggio generato
    tone: str = Field(default="gentile", max_length=20)  # gentle, equilibrato, fermo
    channel: str = Field(default="email", max_length=20)  # email, pec, telegram, sms

    # AI generation
    ai_generated: bool = Field(default=True)
    ai_model: Optional[str] = Field(default=None, max_length=100)

    # Sending status
    status: str = Field(default="pending", max_length=50)  # pending, sent, delivered, failed
    sent_at: Optional[datetime] = Field(default=None)
    delivered_at: Optional[datetime] = Field(default=None)

    # Tracking
    stage: str = Field(default="gentile", max_length=50)  # escalation stage
    is_final: bool = Field(default=False)  # True if this was the last reminder before escalation
