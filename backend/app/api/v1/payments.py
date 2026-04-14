"""
Payment API - Stripe Checkout for invoices.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus
from app.core.security import get_current_active_user
from app.core.config import settings

router = APIRouter(prefix="/payments", tags=["Payments"])

# ─── Stripe helpers ──────────────────────────────────────────────────────────

def _is_mock() -> bool:
    return (
        not settings.STRIPE_API_KEY
        or "placeholder" in (settings.STRIPE_API_KEY or "")
    )


def _get_stripe():
    try:
        import stripe
        stripe.api_key = settings.STRIPE_API_KEY
        return stripe
    except ImportError:
        return None


# ─── Schemas ─────────────────────────────────────────────────────────────────

from pydantic import BaseModel


class CreateCheckoutRequest(BaseModel):
    invoice_id: int


class CreateCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PaymentStatusResponse(BaseModel):
    invoice_id: int
    status: PaymentStatus
    paid_at: Optional[datetime] = None
    amount_cents: int


class WebhookResponse(BaseModel):
    received: bool
    action: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/create-checkout", response_model=CreateCheckoutResponse)
async def create_checkout(
    body: CreateCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Crea una Stripe Checkout Session per una fattura.
    Restituisce l'URL del checkout Stripe.
    """
    # Fetch invoice
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == body.invoice_id,
            Invoice.created_by == current_user.id,
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Fattura non trovata")

    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Fattura già pagata")

    if invoice.total_amount <= 0:
        raise HTTPException(status_code=400, detail="Importo non valido")

    amount_cents = int(invoice.total_amount * 100)

    # Check if a pending payment already exists for this invoice
    existing = await db.execute(
        select(Payment).where(
            Payment.invoice_id == body.invoice_id,
            Payment.status == PaymentStatus.PENDING,
        )
    )
    existing_payment = existing.scalar_one_or_none()

    if existing_payment and not _is_mock():
        # Return existing session URL (query Stripe for it)
        stripe = _get_stripe()
        if stripe:
            try:
                session = stripe.checkout.Session.retrieve(existing_payment.stripe_session_id)
                return CreateCheckoutResponse(
                    checkout_url=session.url,
                    session_id=session.id,
                )
            except Exception:
                pass  # create new session below

    # Base URLs
    base_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS and settings.CORS_ORIGINS[0] != "*" else "http://localhost:5173"
    success_url = f"{base_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/payment-cancel?invoice_id={body.invoice_id}"

    if _is_mock():
        # Mock mode: return fake checkout URL
        import uuid
        mock_session_id = f"cs_mock_{uuid.uuid4().hex[:12]}"
        mock_url = f"https://checkout.stripe.com/mock/{mock_session_id}#pay"

        payment = Payment(
            invoice_id=body.invoice_id,
            stripe_session_id=mock_session_id,
            amount_cents=amount_cents,
            status=PaymentStatus.PENDING,
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        return CreateCheckoutResponse(
            checkout_url=mock_url,
            session_id=mock_session_id,
        )

    stripe = _get_stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe non configurato")

    # Build line items description
    line_description = f"Fattura {invoice.invoice_number} - {invoice.customer_name}"

    checkout_session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "unit_amount": amount_cents,
                "product_data": {
                    "name": f"Fattura {invoice.invoice_number}",
                    "description": line_description[:500],
                },
            },
            "quantity": 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "invoice_id": str(body.invoice_id),
            "user_id": str(current_user.id),
        },
        customer_email=invoice.customer_email or None,
    )

    # Save payment record
    payment = Payment(
        invoice_id=body.invoice_id,
        stripe_session_id=checkout_session.id,
        amount_cents=amount_cents,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return CreateCheckoutResponse(
        checkout_url=checkout_session.url,
        session_id=checkout_session.id,
    )


@router.get("/invoice/{invoice_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Restituisce lo stato del pagamento per una fattura.
    """
    # Verify invoice belongs to user
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.created_by == current_user.id,
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Fattura non trovata")

    # Find latest payment record
    payment_result = await db.execute(
        select(Payment).where(Payment.invoice_id == invoice_id).order_by(Payment.created_at.desc())
    )
    payment = payment_result.scalar_one_or_none()

    if not payment:
        # No payment record - check invoice status
        return PaymentStatusResponse(
            invoice_id=invoice_id,
            status=PaymentStatus.PENDING if invoice.status != InvoiceStatus.PAID else PaymentStatus.COMPLETED,
            paid_at=None,
            amount_cents=int(invoice.total_amount * 100),
        )

    return PaymentStatusResponse(
        invoice_id=invoice_id,
        status=payment.status,
        paid_at=payment.paid_at,
        amount_cents=payment.amount_cents,
    )


@router.post("/webhook", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Gestisce i webhook Stripe per i pagamenti.
    Endpoint pubblico (non richiede auth) - verifica la signature Stripe.
    """
    body = await request.body()

    if _is_mock():
        return WebhookResponse(received=True, action="mock")

    stripe = _get_stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe non configurato")

    sig_header = request.headers.get("stripe-signature")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not sig_header or not webhook_secret:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    try:
        event = stripe.Webhook.construct_event(body, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        session_id = data["id"]
        payment_status = data["payment_status"]

        if payment_status == "paid":
            result = await db.execute(
                select(Payment).where(Payment.stripe_session_id == session_id)
            )
            payment = result.scalar_one_or_none()

            if payment:
                payment.status = PaymentStatus.COMPLETED
                payment.paid_at = datetime.utcnow()
                if data.get("payment_intent"):
                    payment.stripe_payment_intent_id = data["payment_intent"]
                payment.updated_at = datetime.utcnow()

                # Update invoice status
                invoice_result = await db.execute(
                    select(Invoice).where(Invoice.id == payment.invoice_id)
                )
                invoice = invoice_result.scalar_one_or_none()
                if invoice:
                    invoice.status = InvoiceStatus.PAID
                    invoice.updated_at = datetime.utcnow()

                await db.commit()

        return WebhookResponse(received=True, action="payment_completed")

    elif event_type == "checkout.session.expired":
        session_id = data["id"]
        result = await db.execute(
            select(Payment).where(Payment.stripe_session_id == session_id)
        )
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = PaymentStatus.FAILED
            payment.updated_at = datetime.utcnow()
            await db.commit()

        return WebhookResponse(received=True, action="session_expired")

    return WebhookResponse(received=True, action="ignored")
