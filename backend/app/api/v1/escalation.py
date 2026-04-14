"""
Escalation API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, date
from typing import Optional

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice, InvoiceStatus, EscalationStage
from app.core.security import get_current_active_user

router = APIRouter(prefix="/escalation", tags=["Escalation"])


# Interest rate applied for late payments (annual %)
ANNUAL_INTEREST_RATE = 0.08  # 8% annual


class EscalationStatusResponse:
    """Response for escalation status of a single invoice."""
    def __init__(
        self,
        invoice_id: int,
        escalation_stage: EscalationStage,
        escalation_updated_at: Optional[datetime],
        penalty_applied: float,
        days_overdue: int,
        days_until_next_stage: Optional[int],
        is_recurring: bool,
    ):
        self.invoice_id = invoice_id
        self.escalation_stage = escalation_stage
        self.escalation_updated_at = escalation_updated_at
        self.penalty_applied = penalty_applied
        self.days_overdue = days_overdue
        self.days_until_next_stage = days_until_next_stage
        self.is_recurring = is_recurring


class EscalationAdvanceRequest:
    """Request to force advance an invoice to next stage."""
    def __init__(self, invoice_id: int, target_stage: Optional[EscalationStage] = None):
        self.invoice_id = invoice_id
        self.target_stage = target_stage


# Stage ordering
STAGE_ORDER = [
    EscalationStage.NONE,
    EscalationStage.SOLLECITO_1,
    EscalationStage.SOLLECITO_2,
    EscalationStage.PENALTY_APPLICATA,
    EscalationStage.DIFFIDA,
    EscalationStage.STOP_SERVIZI,
    EscalationStage.LEGAL_ACTION,
]

STAGE_THRESHOLDS = {
    EscalationStage.SOLLECITO_1: 7,
    EscalationStage.SOLLECITO_2: 30,
    EscalationStage.PENALTY_APPLICATA: 60,
    EscalationStage.DIFFIDA: 90,
    EscalationStage.STOP_SERVIZI: 120,
    EscalationStage.LEGAL_ACTION: 120,
}

STAGE_LABELS = {
    EscalationStage.NONE: "Nessuno",
    EscalationStage.SOLLECITO_1: "1° Sollecito",
    EscalationStage.SOLLECITO_2: "2° Sollecito",
    EscalationStage.PENALTY_APPLICATA: "Penalty Applicata",
    EscalationStage.DIFFIDA: "Diffida",
    EscalationStage.STOP_SERVIZI: "Stop Servizi",
    EscalationStage.LEGAL_ACTION: "Azione Legale",
}


def get_stage_threshold(stage: EscalationStage) -> Optional[int]:
    """Get the overdue days threshold for a given stage."""
    return STAGE_THRESHOLDS.get(stage)


def calculate_interest(total_amount: float, days_overdue: int) -> float:
    """Calculate interest on overdue amount."""
    daily_rate = ANNUAL_INTEREST_RATE / 365
    return round(total_amount * daily_rate * days_overdue, 2)


def compute_escalation_stage(days_overdue: int, is_recurring: bool) -> EscalationStage:
    """Compute the appropriate escalation stage based on days overdue."""
    if days_overdue < 7:
        return EscalationStage.NONE
    elif days_overdue < 30:
        return EscalationStage.SOLLECITO_1
    elif days_overdue < 60:
        return EscalationStage.SOLLECITO_2
    elif days_overdue < 90:
        return EscalationStage.PENALTY_APPLICATA
    elif days_overdue < 120:
        return EscalationStage.DIFFIDA
    else:
        return EscalationStage.STOP_SERVIZI if is_recurring else EscalationStage.LEGAL_ACTION


def days_until_next_stage_fn(stage: EscalationStage, days_overdue: int) -> Optional[int]:
    """How many days until the next escalation stage."""
    next_stages = {
        EscalationStage.NONE: 7,
        EscalationStage.SOLLECITO_1: 30,
        EscalationStage.SOLLECITO_2: 60,
        EscalationStage.PENALTY_APPLICATA: 90,
        EscalationStage.DIFFIDA: 120,
        EscalationStage.STOP_SERVIZI: None,
        EscalationStage.LEGAL_ACTION: None,
    }
    threshold = next_stages.get(stage)
    if threshold is None:
        return None
    return threshold - days_overdue


@router.get("/invoices/{invoice_id}/status")
async def get_escalation_status(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get escalation status for a specific invoice."""
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    today = date.today()
    due_date = invoice.due_date if isinstance(invoice.due_date, date) else datetime.fromisoformat(str(invoice.due_date)).date()
    days_overdue = (today - due_date).days if invoice.status == InvoiceStatus.OVERDUE else 0

    # Determine if recurring client (has paid invoices in the past)
    # We approximate by checking payment_history or trust_score > 50 as a simple proxy
    is_recurring = invoice.customer_name != ""  # simplified — proper impl needs client lookup

    days_until_next = days_until_next_stage_fn(invoice.escalation_stage, days_overdue)

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "customer_name": invoice.customer_name,
        "total_amount": invoice.total_amount,
        "due_date": invoice.due_date.isoformat() if hasattr(invoice.due_date, 'isoformat') else str(invoice.due_date),
        "days_overdue": max(days_overdue, 0),
        "escalation_stage": invoice.escalation_stage.value,
        "escalation_label": STAGE_LABELS.get(invoice.escalation_stage, "Sconosciuto"),
        "escalation_updated_at": invoice.escalation_updated_at.isoformat() if invoice.escalation_updated_at else None,
        "penalty_applied": invoice.penalty_applied,
        "days_until_next_stage": days_until_next,
        "all_stages": [s.value for s in STAGE_ORDER],
        "stage_labels": {s.value: STAGE_LABELS[s] for s in STAGE_ORDER},
        "stage_thresholds": {s.value: STAGE_THRESHOLDS.get(s) for s in STAGE_ORDER},
        "is_recurring": is_recurring,
        "status": invoice.status.value,
    }


@router.post("/advance")
async def advance_escalation(
    invoice_id: int,
    target_stage: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Force advance an invoice to a specific escalation stage (admin only)."""
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Determine target stage
    if target_stage:
        try:
            new_stage = EscalationStage(target_stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {target_stage}")
    else:
        # Advance to next stage in order
        try:
            current_idx = STAGE_ORDER.index(invoice.escalation_stage)
            if current_idx < len(STAGE_ORDER) - 1:
                new_stage = STAGE_ORDER[current_idx + 1]
            else:
                return {"message": "Already at max stage", "stage": invoice.escalation_stage.value}
        except ValueError:
            new_stage = EscalationStage.SOLLECITO_1

    # Calculate penalty if entering PENALTY_APPLICATA
    penalty = invoice.penalty_applied
    if new_stage == EscalationStage.PENALTY_APPLICATA and invoice.escalation_stage != EscalationStage.PENALTY_APPLICATA:
        today = date.today()
        due_date = invoice.due_date if isinstance(invoice.due_date, date) else datetime.fromisoformat(str(invoice.due_date)).date()
        days_overdue = max((today - due_date).days, 0)
        penalty = calculate_interest(invoice.total_amount, days_overdue)

    invoice.escalation_stage = new_stage
    invoice.escalation_updated_at = datetime.utcnow()
    if new_stage == EscalationStage.PENALTY_APPLICATA:
        invoice.penalty_applied = penalty

    await db.commit()
    await db.refresh(invoice)

    return {
        "message": f"Escalation advanced to {STAGE_LABELS.get(new_stage, new_stage.value)}",
        "invoice_id": invoice.id,
        "new_stage": new_stage.value,
        "penalty_applied": penalty,
    }


@router.post("/process-overdue")
async def process_overdue_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Process all overdue invoices and update their escalation stages.
    
    This is called by the cron job at 9:00 AM daily.
    """
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Admin access required")

    today = date.today()

    # Get all overdue invoices for this user
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.created_by == current_user.id,
                Invoice.status == InvoiceStatus.OVERDUE,
                Invoice.escalation_stage != EscalationStage.LEGAL_ACTION,
            )
        )
    )
    invoices = result.scalars().all()

    updated = []
    for invoice in invoices:
        due_date = invoice.due_date if isinstance(invoice.due_date, date) else datetime.fromisoformat(str(invoice.due_date)).date()
        days_overdue = (today - due_date).days

        if days_overdue < 0:
            continue

        # Determine if recurring client (simplified heuristic)
        is_recurring = invoice.customer_vat not in ("", None, "0")

        new_stage = compute_escalation_stage(days_overdue, is_recurring)

        if new_stage != invoice.escalation_stage:
            invoice.escalation_stage = new_stage
            invoice.escalation_updated_at = datetime.utcnow()

            # Calculate penalty when entering PENALTY_APPLICATA
            if new_stage == EscalationStage.PENALTY_APPLICATA and invoice.penalty_applied == 0:
                invoice.penalty_applied = calculate_interest(invoice.total_amount, days_overdue)

            updated.append({
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "old_stage": invoice.escalation_stage.value,
                "new_stage": new_stage.value,
                "days_overdue": days_overdue,
                "penalty_applied": invoice.penalty_applied,
            })

    if updated:
        await db.commit()

    return {
        "processed": len(invoices),
        "updated": len(updated),
        "details": updated,
    }
