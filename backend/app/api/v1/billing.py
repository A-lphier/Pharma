"""
API Billing - Stripe subscription management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import logging

from app.db.session import get_db

logger = logging.getLogger(__name__)
from app.models.user import User
from app.services.stripe_service import stripe_service, TIER_FEATURES

router = APIRouter(prefix="/billing", tags=["Billing"])


# ─── Schemi ──────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    tier: str
    success_url: str = "http://localhost:5173/billing?success=true"
    cancel_url: str = "http://localhost:5173/billing?canceled=true"


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalRequest(BaseModel):
    return_url: str = "http://localhost:5173/billing"


class PortalResponse(BaseModel):
    portal_url: str


class BillingStatusResponse(BaseModel):
    tier: str
    status: str
    max_invoices: int
    max_users: int
    ai_reminders: int
    sdi_enabled: bool
    next_billing_date: Optional[str] = None
    price: int


class CancelResponse(BaseModel):
    success: bool
    message: str


class WebhookResponse(BaseModel):
    received: bool


TIERS_PRICES = {
    "free": 0,
    "starter": 19,
    "professional": 29,
    "studio": 79,
}


# ─── Dipendenza: utente corrente ─────────────────────────────────────────────

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> User:
    """Estrae l'utente corrente dal token JWT."""
    from app.core.security import decode_token
    from fastapi import HTTPException, status

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non autorizzato")

    token = authorization.replace("Bearer ", "")
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token non valido")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utente non trovato")
    return user


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    req: CheckoutRequest,
    user: User = Depends(get_current_user),
):
    """
    Avvia una Stripe Checkout Session per il tier richiesto.
    """
    valid_tiers = ["starter", "professional", "studio"]
    if req.tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Tier non valido. Scegli tra: {valid_tiers}")

    try:
        checkout_url = stripe_service.create_checkout_session(
            tier=req.tier,
            user_id=user.id,
            success_url=req.success_url,
            cancel_url=req.cancel_url,
        )
        return CheckoutResponse(checkout_url=checkout_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore Stripe: {e}")


@router.get("/status", response_model=BillingStatusResponse)
async def get_billing_status(
    user: User = Depends(get_current_user),
):
    """
    Restituisce lo stato corrente della sottoscrizione dell'utente.
    """
    # Tier dell'utente (default free se non impostato)
    tier = getattr(user, "subscription_tier", "free") or "free"
    features = TIER_FEATURES.get(tier, TIER_FEATURES["free"])
    price = TIERS_PRICES.get(tier, 0)

    # In demo mode non abbiamo date reali
    next_billing_date = None
    if tier != "free":
        # Mock: data fittizia tra 30 giorni
        from datetime import datetime, timedelta
        next_billing_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    return BillingStatusResponse(
        tier=tier,
        status="active" if tier != "free" else "free",
        max_invoices=features["max_invoices"],
        max_users=features["max_users"],
        ai_reminders=features["ai_reminders"],
        sdi_enabled=features["sdi"],
        next_billing_date=next_billing_date,
        price=price,
    )


@router.post("/cancel", response_model=CancelResponse)
async def cancel_subscription(
    user: User = Depends(get_current_user),
):
    """
    Annulla la sottoscrizione dell'utente.
    """
    if not getattr(user, "subscription_id", None):
        raise HTTPException(status_code=400, detail="Nessuna sottoscrizione attiva")

    try:
        success = stripe_service.cancel_subscription(
            subscription_id=user.subscription_id,
            user_id=user.id,
        )
        if success:
            # TODO: aggiornare il tier dell'utente a free nel DB
            return CancelResponse(success=True, message="Sottoscrizione annullata correttamente.")
        return CancelResponse(success=False, message="Impossibile annullare la sottoscrizione.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portal", response_model=PortalResponse)
async def get_customer_portal(
    return_url: str = "http://localhost:5173/billing",
    user: User = Depends(get_current_user),
):
    """
    Restituisce l'URL del Stripe Customer Portal per gestire la sottoscrizione.
    """
    try:
        portal_url = stripe_service.get_customer_portal_url(
            user_id=user.id,
            return_url=return_url,
        )
        return PortalResponse(portal_url=portal_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portal", response_model=PortalResponse)
async def post_customer_portal(
    req: PortalRequest,
    user: User = Depends(get_current_user),
):
    """Stesso del GET, ma via POST (per comodita del frontend)."""
    return await get_customer_portal(return_url=req.return_url, user=user)


@router.post("/webhook", response_model=WebhookResponse)
async def stripe_webhook(
    req: Request,
    stripe_sig: Optional[str] = Header(None),
):
    """
    Gestisce i webhook Stripe.
    Nota: in produzione verificare la signature con STRIPE_WEBHOOK_SECRET.
    """
    payload = await req.body()
    try:
        result = stripe_service.handle_webhook(payload, stripe_sig or "")
        return WebhookResponse(received=True)
    except Exception as e:
        # Logga l'errore ma ritorna 200 per non ritentare all'infinito
        logger.error(f"[Stripe Webhook Error] {e}")
        return WebhookResponse(received=True)
