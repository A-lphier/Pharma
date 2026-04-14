"""
Invoice feedback API endpoints.

Handles recording feedback on why invoices were paid late.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.client import LateReasonFeedback
from app.models.invoice import Invoice
from app.schemas.client import (
    LateReasonFeedbackRequest,
    LateReasonFeedbackResponse,
)
from app.core.security import get_current_active_user

router = APIRouter(tags=["Feedback"])

# Late reason options
LATE_REASON_OPTIONS = [
    {"value": "not_received", "label": "Il cliente non ha ricevuto il sollecito"},
    {"value": "disputed", "label": "La fattura è in discussione o verifica"},
    {"value": "financial_issues", "label": "Problemi finanziari temporanei"},
    {"value": "about_to_pay", "label": "Il cliente sta per pagare"},
    {"value": "wrong_invoice", "label": "Fattura errata o errore nostro"},
    {"value": "refused", "label": "Rifiuto puro"},
]


@router.post("/invoices/{invoice_id}/feedback", response_model=LateReasonFeedbackResponse, status_code=201)
async def submit_late_feedback(
    invoice_id: int,
    feedback_data: LateReasonFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submit feedback for why an invoice was paid late."""
    # Verify invoice exists and belongs to user
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.created_by == current_user.id,
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Check if feedback already exists
    existing = await db.execute(
        select(LateReasonFeedback).where(
            LateReasonFeedback.invoice_id == invoice_id,
        )
    )
    existing_feedback = existing.scalar_one_or_none()

    if existing_feedback:
        # Update existing feedback
        existing_feedback.reason = feedback_data.reason
        existing_feedback.notes = feedback_data.notes or ""
        await db.commit()
        await db.refresh(existing_feedback)
        return existing_feedback

    # Create new feedback
    feedback = LateReasonFeedback(
        invoice_id=invoice_id,
        reason=feedback_data.reason,
        notes=feedback_data.notes or "",
        created_by=current_user.id,
    )

    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return feedback


@router.get("/invoices/{invoice_id}/feedback", response_model=LateReasonFeedbackResponse)
async def get_late_feedback(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get feedback for a specific invoice."""
    # Verify invoice exists and belongs to user
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.created_by == current_user.id,
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    feedback_result = await db.execute(
        select(LateReasonFeedback).where(
            LateReasonFeedback.invoice_id == invoice_id,
        )
    )
    feedback = feedback_result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(status_code=404, detail="No feedback found for this invoice")

    return feedback


@router.get("/feedback-options")
async def get_feedback_options():
    """Get available late reason options."""
    return {"options": LATE_REASON_OPTIONS}
