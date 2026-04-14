"""
Servizio Stripe Billing - mock per sviluppo.
In produzione sostituire i mock con chiamate reali a Stripe API.
"""
from typing import Optional
from app.core.config import settings

# ─── Configurazione Stripe ───────────────────────────────────────────────────

# Solo se stripe e installato
try:
    import stripe
    stripe.api_key = settings.STRIPE_API_KEY or "sk_test_placeholder"
    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None
    STRIPE_AVAILABLE = False

# ─── Price IDs (da configurare in produzione) ────────────────────────────────

PRICE_IDS = {
    "starter": "price_starter_placeholder",
    "professional": "price_professional_placeholder",
    "studio": "price_studio_placeholder",
}

# ─── Tier per numero fatture ──────────────────────────────────────────────────

TIER_FEATURES = {
    "free": {"max_invoices": 5, "max_users": 1, "ai_reminders": 10, "sdi": False},
    "starter": {"max_invoices": 50, "max_users": 1, "ai_reminders": 100, "sdi": False},
    "professional": {"max_invoices": 500, "max_users": 5, "ai_reminders": -1, "sdi": True},
    "studio": {"max_invoices": -1, "max_users": 20, "ai_reminders": -1, "sdi": True},
}


def _is_mock() -> bool:
    """True se stiamo usando chiavi placeholder o stripe non installato."""
    return not STRIPE_AVAILABLE or not settings.STRIPE_API_KEY or "placeholder" in settings.STRIPE_API_KEY


# ─── Mock state (in-memory per demo) ────────────────────────────────────────

_mock_subscriptions: dict[str, dict] = {}


# ─── Servizio Stripe ─────────────────────────────────────────────────────────

class StripeService:
    """Servizio Stripe per sottoscrizioni e pagamenti."""

    @staticmethod
    def create_checkout_session(tier: str, user_id: int, success_url: str, cancel_url: str) -> str:
        """
        Crea una Stripe Checkout Session per il tier richiesto.
        In demo mode ritorna un URL fittizio.
        """
        if _is_mock():
            # Mock: ritorna un URL di esempio
            mock_session_id = f"cs_mock_{user_id}_{tier}"
            return f"https://checkout.stripe.com/mock/{mock_session_id}"

        price_id = PRICE_IDS.get(tier)
        if not price_id:
            raise ValueError(f"Tier sconosciuto: {tier}")

        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user_id),
                "tier": tier,
            },
            subscription_data={
                "metadata": {
                    "user_id": str(user_id),
                    "tier": tier,
                }
            },
        )
        return checkout_session.url

    @staticmethod
    def create_subscription(user_id: int, tier: str, stripe_customer_id: str) -> str:
        """
        Crea una sottoscrizione Stripe.
        In demo mode ritorna un subscription_id fittizio.
        """
        if _is_mock():
            sub_id = f"sub_mock_{user_id}_{tier}"
            _mock_subscriptions[str(user_id)] = {
                "id": sub_id,
                "customer": stripe_customer_id,
                "tier": tier,
                "status": "active",
            }
            return sub_id

        price_id = PRICE_IDS.get(tier)
        if not price_id:
            raise ValueError(f"Tier sconosciuto: {tier}")

        subscription = stripe.Subscription.create(
            customer=stripe_customer_id,
            items=[{"price": price_id}],
            metadata={"user_id": str(user_id), "tier": tier},
        )
        return subscription.id

    @staticmethod
    def cancel_subscription(subscription_id: str, user_id: Optional[int] = None) -> bool:
        """
        Cancella una sottoscrizione.
        In demo mode aggiorna lo stato in-memory.
        """
        if _is_mock():
            if user_id and str(user_id) in _mock_subscriptions:
                _mock_subscriptions[str(user_id)]["status"] = "canceled"
            return True

        subscription = stripe.Subscription.delete(subscription_id)
        return subscription.status == "canceled"

    @staticmethod
    def get_subscription_status(subscription_id: str, user_id: Optional[int] = None) -> dict:
        """
        Restituisce lo stato della sottoscrizione.
        In demo mode ritorna stato fittizio.
        """
        if _is_mock():
            if user_id and str(user_id) in _mock_subscriptions:
                sub = _mock_subscriptions[str(user_id)]
                return {
                    "id": sub["id"],
                    "status": sub["status"],
                    "tier": sub["tier"],
                    "current_period_end": None,
                    "cancel_at_period_end": False,
                }
            return {
                "id": subscription_id,
                "status": "active",
                "tier": "starter",
                "current_period_end": None,
                "cancel_at_period_end": False,
            }

        subscription = stripe.Subscription.retrieve(subscription_id)
        return {
            "id": subscription.id,
            "status": subscription.status,
            "tier": subscription.metadata.get("tier", "unknown"),
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }

    @staticmethod
    def get_customer_portal_url(user_id: int, return_url: str) -> str:
        """
        Restituisce l'URL del Customer Portal Stripe.
        In demo mode ritorna un URL fittizio.
        """
        if _is_mock():
            return f"https://billing.stripe.com/mock/portal/{user_id}"

        # Cerca il customer_id dell'utente (da salvare nei metadata utente)
        # Per ora creiamo una sessione portal generica
        session = stripe.billing_portal.Session.create(
            customer=user_id,  # In produzione: stripe_customer_id dell'utente
            return_url=return_url,
        )
        return session.url

    @staticmethod
    def handle_webhook(payload: bytes, sig_header: str) -> dict:
        """
        Gestisce gli eventi webhook Stripe.
        Eventi gestiti:
        - checkout.session.completed
        - customer.subscription.updated
        - customer.subscription.deleted
        """
        if _is_mock():
            # In demo mode non facciamo nulla
            return {"received": True, "mock": True}

        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            user_id = data["metadata"].get("user_id")
            tier = data["metadata"].get("tier")
            # Attivare la sottoscrizione per l'utente
            _activate_subscription(user_id, tier, data.get("subscription"))
            return {"received": True, "action": "subscription_activated"}

        elif event_type == "customer.subscription.updated":
            user_id = data["metadata"].get("user_id")
            tier = data["metadata"].get("tier")
            _update_subscription(user_id, tier, data["status"])
            return {"received": True, "action": "subscription_updated"}

        elif event_type == "customer.subscription.deleted":
            user_id = data["metadata"].get("user_id")
            _cancel_subscription(user_id)
            return {"received": True, "action": "subscription_canceled"}

        return {"received": True, "action": "ignored"}


def _activate_subscription(user_id: str, tier: str, subscription_id: str):
    """Attiva la sottoscrizione per l'utente (da implementare con DB)."""
    # TODO: aggiornare User.subscription_tier e subscription_id nel DB
    pass


def _update_subscription(user_id: str, tier: str, status: str):
    """Aggiorna la sottoscrizione (da implementare con DB)."""
    pass


def _cancel_subscription(user_id: str):
    """Cancella la sottoscrizione (da implementare con DB)."""
    # TODO: riportare l'utente al tier free
    pass


# Singleton
stripe_service = StripeService()
