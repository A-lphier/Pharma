"""
Business configuration API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.client import BusinessConfig
from app.schemas.client import BusinessConfigResponse, BusinessConfigUpdate
from app.core.security import get_current_active_user
from app.services.trust_score import update_config as update_trust_config

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("", response_model=BusinessConfigResponse)
async def get_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current business configuration."""
    result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = result.scalar_one_or_none()

    if not config:
        # Create default config
        config = BusinessConfig(id=1)
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return config


@router.put("", response_model=BusinessConfigResponse)
async def update_config(
    update_data: BusinessConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update business configuration."""
    config = await update_trust_config(
        db,
        style=update_data.style,
        legal_threshold=update_data.legal_threshold,
        new_client_score=update_data.new_client_score,
        first_reminder_days=update_data.first_reminder_days,
        warning_threshold_days=update_data.warning_threshold_days,
        escalation_days=update_data.escalation_days,
    )

    return config


@router.post("/reset-onboarding", response_model=BusinessConfigResponse)
async def reset_onboarding(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reset onboarding to start fresh."""
    result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = result.scalar_one_or_none()

    if not config:
        config = BusinessConfig(id=1)
        db.add(config)
    else:
        config.onboarding_completed = False
        config.onboarding_answers = "{}"

    await db.commit()
    await db.refresh(config)

    return config
