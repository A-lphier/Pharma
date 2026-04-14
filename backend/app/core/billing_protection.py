"""
Middleware di protezione basato su tier di sottoscrizione.
Verifica che l'utente possa accedere a feature premium prima di permettere azioni.
"""
from fastapi import HTTPException, status
from typing import Optional

from app.services.stripe_service import TIER_FEATURES

# Feature che richiedono un tier minimo
PREMIUM_FEATURES = {
    "sdi": "professional",          # Richiede almeno Professional
    "bulk_invoices": "professional",  # Richiede almeno Professional
    "analytics": "professional",      # Richiede almeno Professional
    "api_access": "studio",           # Richiede Studio
    "multi_user": "professional",      # Richiede almeno Professional (gia controllato via max_users)
    "unlimited_reminders": "professional",  # Richiede almeno Professional
}

TIER_ORDER = ["free", "starter", "professional", "studio"]


def _tier_rank(tier: str) -> int:
    """Rank del tier (maggiore = piu alto)."""
    try:
        return TIER_ORDER.index(tier)
    except ValueError:
        return 0


def check_feature_access(tier: str, feature: str) -> bool:
    """
    Restituisce True se il tier ha accesso alla feature.
    """
    min_tier = PREMIUM_FEATURES.get(feature)
    if not min_tier:
        return True  # Feature non in lista, accesso libero
    return _tier_rank(tier) >= _tier_rank(min_tier)


def require_feature(tier: Optional[str], feature: str) -> None:
    """
    Solleva HTTPException se il tier non ha accesso alla feature.
    Da usare negli endpoint API come dipendenza.
    """
    tier = tier or "free"
    if not check_feature_access(tier, feature):
        min_tier = PREMIUM_FEATURES.get(feature, "professional")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Feature '{feature}' non disponibile nel piano attuale. "
                f"Esegui l'upgrade a {min_tier.capitalize()} per sbloccare questa funzionalita. "
                f"Vai su /billing per eseguire l'upgrade."
            ),
        )


def check_invoice_limit(tier: str, current_invoice_count: int) -> bool:
    """
    Restituisce True se l'utente puo ancora creare fatture.
    """
    max_invoices = TIER_FEATURES.get(tier, {}).get("max_invoices", 5)
    if max_invoices == -1:
        return True
    return current_invoice_count < max_invoices


def require_invoice_quota(tier: Optional[str], current_invoice_count: int) -> None:
    """
    Solleva HTTPException se l'utente ha raggiunto il limite fatture.
    """
    tier = tier or "free"
    if not check_invoice_limit(tier, current_invoice_count):
        max_invoices = TIER_FEATURES.get(tier, {}).get("max_invoices", 5)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Hai raggiunto il limite di {max_invoices} fatture per il piano {tier.capitalize()}. "
                f"Esegui l'upgrade per creare piu fatture. Vai su /billing."
            ),
        )


def require_user_quota(tier: Optional[str], current_user_count: int) -> None:
    """
    Solleva HTTPException se l'utente ha raggiunto il limite utenti.
    """
    tier = tier or "free"
    max_users = TIER_FEATURES.get(tier, {}).get("max_users", 1)
    if current_user_count >= max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Hai raggiunto il limite di {max_users} utenti per il piano {tier.capitalize()}. "
                f"Esegui l'upgrade per aggiungere piu utenti. Vai su /billing."
            ),
        )
