"""
Trust Score Algorithm Service.

Calculates client trust score based on payment history.
Score ranges from 0-100:
- 80-100: Eccellente 🌟
- 60-79: Affidabile 👍
- 40-59: Da verificare ⚠️
- 20-39: Problemi 🔴
- 0-19: Inaffidabile ⛔
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional, Tuple

from app.models.client import Client, PaymentHistory, BusinessConfig


def get_trust_score_label(score: int) -> Tuple[str, str]:
    """Get label and emoji for a trust score."""
    if score >= 80:
        return "Eccellente", "🌟"
    elif score >= 60:
        return "Affidabile", "👍"
    elif score >= 40:
        return "Da verificare", "⚠️"
    elif score >= 20:
        return "Problemi", "🔴"
    else:
        return "Inaffidabile", "⛔"


async def calculate_trust_score(db: AsyncSession, client_id: int) -> int:
    """
    Calculate trust score for a client based on payment history.
    
    Algorithm:
    - Base from business_config.new_client_score (default 60)
    - +3 for each invoice paid on time
    - +5 for early payment (paid before due date)
    - -1 for each day of delay
    - -20 for unpaid invoices 30+ days late
    
    Returns score clamped to 0-100.
    """
    # Get client
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    
    if not client:
        return 60
    
    # Get business config for base score
    config_result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = config_result.scalar_one_or_none()
    base_score = config.new_client_score if config else 60
    
    # Get payment history
    history_result = await db.execute(
        select(PaymentHistory).where(PaymentHistory.client_id == client_id)
    )
    histories = history_result.scalars().all()
    
    score = base_score
    
    for history in histories:
        if history.was_on_time:
            # Paid on time: +3
            score += 3
            # Check if paid early (paid_date < due_date) → flat +5 bonus
            if history.paid_date and history.paid_date < history.due_date:
                score += 5
        else:
            # Was late
            if history.days_late >= 30:
                # Unpaid 30+ days: -20
                score -= 20
            else:
                # -1 per day of delay
                score -= history.days_late
    
    # Mark client as not new after first calculation
    if client.is_new and histories:
        client.is_new = False
    
    # Clamp to 0-100
    score = max(0, min(100, score))
    
    # Update client score
    client.trust_score = score
    client.payment_pattern = _calculate_pattern(histories)
    await db.commit()
    
    return score


def _calculate_pattern(histories: list) -> str:
    """Calculate payment pattern string from history."""
    if not histories:
        return "nesso_storico"
    
    total = len(histories)
    on_time = sum(1 for h in histories if h.was_on_time)
    early = sum(1 for h in histories if h.paid_date and h.paid_date < h.due_date) if histories else 0
    avg_days_late = sum(h.days_late for h in histories if not h.was_on_time) / max(1, total - on_time) if total > on_time else 0
    
    if on_time == total:
        return "sempre_puntuale"
    elif on_time / total >= 0.8:
        return "generalmente_puntuale"
    elif on_time / total >= 0.5:
        return "saltuariamente_in_ritardo"
    else:
        return "frequentemente_in_ritardo"


async def get_or_create_config(db: AsyncSession) -> BusinessConfig:
    """Get existing config or create default one."""
    result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = result.scalar_one_or_none()
    
    if not config:
        config = BusinessConfig(id=1)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    
    return config


async def update_config(
    db: AsyncSession,
    style: Optional[str] = None,
    legal_threshold: Optional[float] = None,
    new_client_score: Optional[int] = None,
    first_reminder_days: Optional[int] = None,
    warning_threshold_days: Optional[int] = None,
    escalation_days: Optional[int] = None,
) -> BusinessConfig:
    """Update business configuration."""
    config = await get_or_create_config(db)
    
    if style is not None and style in ("gentile", "equilibrato", "fermo"):
        config.style = style
    if legal_threshold is not None:
        config.legal_threshold = legal_threshold
    if new_client_score is not None:
        config.new_client_score = max(0, min(100, new_client_score))
    if first_reminder_days is not None:
        config.first_reminder_days = first_reminder_days
    if warning_threshold_days is not None:
        config.warning_threshold_days = warning_threshold_days
    if escalation_days is not None:
        config.escalation_days = escalation_days
    
    config.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(config)
    
    return config
