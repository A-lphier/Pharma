"""
Notifications API endpoints - canale WhatsApp.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice
from app.core.security import get_current_active_user
from app.services.whatsapp_service import get_whatsapp_service, WhatsAppService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class WhatsAppNotificationRequest(BaseModel):
    """Request body per invio WhatsApp."""
    invoice_id: int
    message: str


class WhatsAppNotificationResponse(BaseModel):
    """Response per invio WhatsApp."""
    success: bool
    sid: str | None = None
    mock: bool = False
    to: str | None = None
    message: str


@router.post("/whatsapp", response_model=WhatsAppNotificationResponse, status_code=201)
async def send_whatsapp_notification(
    payload: WhatsAppNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service),
):
    """
    Invia un sollecito WhatsApp per una fattura.

    Body: { invoice_id, message }

    - Se TWILIO_ACCOUNT_SID è configurato → usa Twilio WhatsApp API
    - Altrimenti → mock mode (logga il messaggio)
    - Salva sempre la notification in DB con channel='whatsapp'
    """
    # Verify invoice exists and belongs to user
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == payload.invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if not invoice.customer_phone:
        raise HTTPException(status_code=400, detail="Invoice has no customer phone number for WhatsApp")

    # Formatta il numero WhatsApp
    to_number = invoice.customer_phone.strip()
    if not to_number.startswith('+'):
        # Assume Italian numbers without + prefix
        if to_number.startswith('3'):
            to_number = f"+39{to_number}"
        else:
            to_number = f"+{to_number}"

    # Prepara i dati per il template WhatsApp
    due_date_str = invoice.due_date.strftime('%d/%m/%Y') if hasattr(invoice.due_date, 'strftime') else str(invoice.due_date)

    # Prova a ottenere payment link dalla fattura (mock per ora)
    payment_link = None
    # TODO: integrare con Stripe payment link quando disponibile
    # payment_link = f"https://pay.fatturamvp.it/invoice/{invoice.id}" if invoice.stripe_payment_link else None

    # Invia via WhatsApp
    try:
        result = await whatsapp_service.send_sollecito(
            invoice_id=invoice.id,
            to_number=to_number,
            customer_name=invoice.customer_name,
            invoice_number=invoice.invoice_number,
            invoice_amount=invoice.total_amount,
            due_date=due_date_str,
            payment_link=payment_link,
            client_id=None,  # TODO: look up client_id from invoice if available
        )

        return WhatsAppNotificationResponse(
            success=result.get("success", False),
            sid=result.get("sid"),
            mock=whatsapp_service.is_mock,
            to=result.get("to"),
            message=payload.message,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WhatsApp send failed: {str(e)}")
