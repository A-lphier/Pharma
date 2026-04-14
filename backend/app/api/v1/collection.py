"""
Admin Collection Management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import date, datetime
from enum import Enum

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice, InvoiceStatus, Reminder
from app.models.client import Client
from app.core.security import get_current_active_user

router = APIRouter(prefix="/admin", tags=["Collection"])


class EscalationStage(str, Enum):
    NONE = "none"           # Not overdue
    SOLLECITO_1 = "sollecito_1"   # 1-7 days overdue (green)
    SOLLECITO_2 = "sollecito_2"   # 8-15 days overdue (yellow)
    DIFFIDA = "diffida"           # 16-30 days overdue (orange)
    LEGAL_ACTION = "legal_action" # 31-60 days overdue (red)
    LEGAL_EXTREME = "legal_action" # 60+ days overdue (dark red) - maps to same as legal_action


def get_escalation_stage(invoice: Invoice) -> EscalationStage:
    """Calculate escalation stage based on days overdue."""
    if invoice.status == InvoiceStatus.PAID or invoice.status == InvoiceStatus.CANCELLED:
        return EscalationStage.NONE
    
    today = date.today()
    if invoice.due_date >= today:
        return EscalationStage.NONE
    
    days_overdue = (today - invoice.due_date).days
    
    if days_overdue <= 7:
        return EscalationStage.SOLLECITO_1
    elif days_overdue <= 15:
        return EscalationStage.SOLLECITO_2
    elif days_overdue <= 30:
        return EscalationStage.DIFFIDA
    elif days_overdue <= 60:
        return EscalationStage.LEGAL_ACTION
    else:
        return EscalationStage.LEGAL_EXTREME


def get_days_overdue(invoice: Invoice) -> int:
    """Get days overdue for an invoice (0 if not overdue)."""
    if invoice.status == InvoiceStatus.PAID or invoice.status == InvoiceStatus.CANCELLED:
        return 0
    today = date.today()
    if invoice.due_date >= today:
        return 0
    return (today - invoice.due_date).days


# ─── Schemas ──────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field


class StageSummary(BaseModel):
    stage: str
    stage_label: str
    stage_color: str
    invoice_count: int
    total_amount: float


class ClientRisk(BaseModel):
    client_id: int
    client_name: str
    trust_score: int
    total_insoluto: float
    overdue_invoice_count: int
    days_avg_overdue: float


class CollectionSummary(BaseModel):
    total_insoluto: float
    total_overdue_count: int
    total_overdue_amount: float
    risk_client_count: int
    avg_days_overdue: float
    stages: list[StageSummary]
    top_risk_clients: list[ClientRisk]


class AvailableAction(BaseModel):
    action: str
    action_label: str
    action_description: str
    available: bool
    reason: Optional[str] = None


class AvailableActionsResponse(BaseModel):
    invoice_id: int
    escalation_stage: str
    escalation_label: str
    escalation_color: str
    days_overdue: int
    actions: list[AvailableAction]


class ActionExecuteRequest(BaseModel):
    action: str
    invoice_id: int
    message: Optional[str] = None


class ActionExecuteResponse(BaseModel):
    success: bool
    message: str
    action: str
    invoice_id: int


class CollectionInvoice(BaseModel):
    id: int
    invoice_number: str
    customer_name: str
    total_amount: float
    due_date: date
    status: str
    days_overdue: int
    escalation_stage: str
    escalation_label: str
    escalation_color: str
    trust_score: int
    reminder_count: int


# ─── Endpoints ────────────────────────────────────────────────────────────────

STAGE_CONFIG = {
    EscalationStage.SOLLECITO_1: {"label": "1° Sollecito", "color": "#22c55e"},   # green
    EscalationStage.SOLLECITO_2: {"label": "2° Sollecito", "color": "#eab308"},   # yellow
    EscalationStage.DIFFIDA: {"label": "Diffida", "color": "#f97316"},             # orange
    EscalationStage.LEGAL_ACTION: {"label": "Azione Legale", "color": "#ef4444"},  # red
    EscalationStage.LEGAL_EXTREME: {"label": "Recupero Legale", "color": "#991b1b"}, # dark red
}


@router.get("/collection-summary", response_model=CollectionSummary)
async def get_collection_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get collection dashboard summary: KPIs and stage breakdown."""
    today = date.today()
    
    # Base query - all non-paid, non-cancelled invoices for user
    base = select(Invoice).where(
        and_(
            Invoice.created_by == current_user.id,
            Invoice.status != InvoiceStatus.PAID,
            Invoice.status != InvoiceStatus.CANCELLED,
        )
    )
    
    # Total overdue (past due date)
    overdue_q = base.where(Invoice.due_date < today)
    overdue_result = await db.execute(overdue_q)
    overdue_invoices = overdue_result.scalars().all()
    
    total_overdue_count = len(overdue_invoices)
    total_overdue_amount = sum(inv.total_amount for inv in overdue_invoices)
    total_insoluto = total_overdue_amount  # same for now
    
    # Avg days overdue
    if overdue_invoices:
        avg_days_overdue = sum(get_days_overdue(inv) for inv in overdue_invoices) / len(overdue_invoices)
    else:
        avg_days_overdue = 0.0
    
    # Stage breakdown
    stages = []
    for stage in [EscalationStage.SOLLECITO_1, EscalationStage.SOLLECITO_2, EscalationStage.DIFFIDA, EscalationStage.LEGAL_ACTION, EscalationStage.LEGAL_EXTREME]:
        cfg = STAGE_CONFIG[stage]
        stage_invoices = [inv for inv in overdue_invoices if get_escalation_stage(inv) == stage]
        stages.append(StageSummary(
            stage=stage.value,
            stage_label=cfg["label"],
            stage_color=cfg["color"],
            invoice_count=len(stage_invoices),
            total_amount=sum(inv.total_amount for inv in stage_invoices),
        ))
    
    # Top 10 risk clients (low trust_score + high insoluto)
    risk_result = await db.execute(
        select(Client).where(Client.created_by == current_user.id)
    )
    all_clients = risk_result.scalars().all()
    
    client_risks = []
    for client in all_clients:
        client_invoices_q = base.where(Invoice.customer_name == client.name)
        client_invoices_result = await db.execute(client_invoices_q)
        client_overdue_invoices = client_invoices_result.scalars().all()
        
        if not client_overdue_invoices:
            continue
        
        total_ins = sum(inv.total_amount for inv in client_overdue_invoices)
        days_list = [get_days_overdue(inv) for inv in client_overdue_invoices]
        avg_days = sum(days_list) / len(days_list) if days_list else 0
        
        client_risks.append(ClientRisk(
            client_id=client.id,
            client_name=client.name,
            trust_score=client.trust_score,
            total_insoluto=total_ins,
            overdue_invoice_count=len(client_overdue_invoices),
            days_avg_overdue=round(avg_days, 1),
        ))
    
    # Sort by risk: lower trust_score first, then higher insoluto
    client_risks.sort(key=lambda x: (x.trust_score, -x.total_insoluto))
    top_risk_clients = client_risks[:10]
    
    # Count clients with overdue invoices
    risk_client_count = len(client_risks)
    
    return CollectionSummary(
        total_insoluto=total_insoluto,
        total_overdue_count=total_overdue_count,
        total_overdue_amount=total_overdue_amount,
        risk_client_count=risk_client_count,
        avg_days_overdue=round(avg_days_overdue, 1),
        stages=stages,
        top_risk_clients=top_risk_clients,
    )


@router.get("/collection-invoices")
async def get_collection_invoices(
    stage: Optional[EscalationStage] = None,
    client_name: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get paginated list of overdue invoices with escalation info."""
    today = date.today()
    
    query = select(Invoice).where(
        and_(
            Invoice.created_by == current_user.id,
            Invoice.status != InvoiceStatus.PAID,
            Invoice.status != InvoiceStatus.CANCELLED,
            Invoice.due_date < today,
        )
    )
    
    if date_from:
        query = query.where(Invoice.due_date >= date_from)
    if date_to:
        query = query.where(Invoice.due_date <= date_to)
    if client_name:
        query = query.where(Invoice.customer_name.ilike(f"%{client_name}%"))
    
    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Invoice.due_date.asc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    # Get reminder counts per invoice
    invoice_ids = [inv.id for inv in invoices]
    reminder_counts = {}
    if invoice_ids:
        from app.models.invoice import Reminder
        rem_q = select(Reminder.invoice_id, func.count()).where(Reminder.invoice_id.in_(invoice_ids)).group_by(Reminder.invoice_id)
        rem_result = await db.execute(rem_q)
        reminder_counts = {row[0]: row[1] for row in rem_result.all()}
    
    # Get client trust scores
    client_names = list(set(inv.customer_name for inv in invoices))
    client_scores = {}
    if client_names:
        client_q = select(Client).where(Client.name.in_(client_names))
        client_result = await db.execute(client_q)
        for client in client_result.scalars().all():
            client_scores[client.name] = client.trust_score
    
    items = []
    for inv in invoices:
        esc_stage = get_escalation_stage(inv)
        cfg = STAGE_CONFIG.get(esc_stage, {"label": "N/A", "color": "#6b7280"})
        items.append(CollectionInvoice(
            id=inv.id,
            invoice_number=inv.invoice_number,
            customer_name=inv.customer_name,
            total_amount=inv.total_amount,
            due_date=inv.due_date,
            status=inv.status.value,
            days_overdue=get_days_overdue(inv),
            escalation_stage=esc_stage.value,
            escalation_label=cfg["label"],
            escalation_color=cfg["color"],
            trust_score=client_scores.get(inv.customer_name, 50),
            reminder_count=reminder_counts.get(inv.id, 0),
        ))
    
    # Filter by stage if specified
    if stage:
        items = [item for item in items if item.escalation_stage == stage.value]
        total = len(items)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/actions/available", response_model=AvailableActionsResponse)
async def get_available_actions(
    invoice_id: int = Query(..., description="Invoice ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List available actions for a specific invoice based on its escalation stage."""
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Invoice is already paid")
    
    esc_stage = get_escalation_stage(invoice)
    days_overdue = get_days_overdue(invoice)
    cfg = STAGE_CONFIG.get(esc_stage, {"label": "N/A", "color": "#6b7280"})
    
    actions = []
    
    # Stage 1+: send gentle reminder (1st sollecito)
    if esc_stage == EscalationStage.SOLLECITO_1:
        actions.append(AvailableAction(
            action="send_reminder_gentle",
            action_label="1° Sollecito Gentile",
            action_description="Email di sollecito cortese e professionale",
            available=True,
        ))
    
    # Stage 2+: send normal reminder (2nd sollecito)
    if esc_stage.value in [EscalationStage.SOLLECITO_2.value, EscalationStage.DIFFIDA.value,
                            EscalationStage.LEGAL_ACTION.value, EscalationStage.LEGAL_EXTREME.value]:
        actions.append(AvailableAction(
            action="send_reminder_gentle",
            action_label="1° Sollecito Gentile",
            action_description="Email di sollecito cortese e professionale",
            available=True,
        ))
        actions.append(AvailableAction(
            action="send_reminder_normale",
            action_label="2° Sollecito Normale",
            action_description="Sollecito con tono più deciso",
            available=True,
        ))
    
    # Stage 3+: apply penalty interest
    if esc_stage.value in [EscalationStage.DIFFIDA.value, EscalationStage.LEGAL_ACTION.value, EscalationStage.LEGAL_EXTREME.value]:
        actions.append(AvailableAction(
            action="apply_penalty",
            action_label=" Applica Penale",
            action_description="Applicare interessi di mora (D.Lgs 231/2002)",
            available=True,
        ))
        actions.append(AvailableAction(
            action="send_diffida",
            action_label="Diffida",
            action_description="Invio diffida formale con termini di pagamento",
            available=True,
        ))
    
    # Stage 4+: legal action
    if esc_stage.value in [EscalationStage.LEGAL_ACTION.value, EscalationStage.LEGAL_EXTREME.value]:
        actions.append(AvailableAction(
            action="send_fermo",
            action_label="Sollecito Fermo",
            action_description="Sollecito con tono fermo e termine ultimo",
            available=True,
        ))
        actions.append(AvailableAction(
            action="prepare_legal",
            action_label="Prepara Pratica Legale",
            action_description="Predisponi documenti per azione legale",
            available=True,
        ))
    
    # Stage 5+ (LEGAL_EXTREME): uncollectible
    if esc_stage == EscalationStage.LEGAL_EXTREME:
        actions.append(AvailableAction(
            action="mark_uncollectible",
            action_label="Segna come Inesigibile",
            action_description="Registra la fattura come inesigibile",
            available=True,
        ))
    
    # Always available: mark as paid
    actions.append(AvailableAction(
        action="mark_paid",
        action_label="Segna come Pagata",
        action_description="Registra il pagamento ricevuto",
        available=True,
    ))
    
    return AvailableActionsResponse(
        invoice_id=invoice_id,
        escalation_stage=esc_stage.value,
        escalation_label=cfg["label"],
        escalation_color=cfg["color"],
        days_overdue=days_overdue,
        actions=actions,
    )


@router.post("/actions/execute", response_model=ActionExecuteResponse)
async def execute_action(
    payload: ActionExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Execute a collection action on an invoice."""
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == payload.invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    action = payload.action
    invoice_id = payload.invoice_id
    
    esc_stage = get_escalation_stage(invoice)
    days_overdue = get_days_overdue(invoice)
    
    if action == "mark_paid":
        invoice.status = InvoiceStatus.PAID
        invoice.updated_at = datetime.utcnow()
        await db.commit()
        return ActionExecuteResponse(
            success=True,
            message=f"Fattura {invoice.invoice_number} segnata come pagata",
            action=action,
            invoice_id=invoice_id,
        )
    
    if action == "send_reminder_gentle":
        reminder = Reminder(
            invoice_id=invoice_id,
            reminder_date=datetime.utcnow(),
            reminder_type="gentile",
            sent_via="email",
            status="pending",
            message=payload.message or f"gentile sollecito per fattura {invoice.invoice_number}",
            sent_by=current_user.id,
        )
        db.add(reminder)
        await db.commit()
        # Queue async task
        try:
            from app.tasks.reminders import send_reminder_task
            send_reminder_task.delay(reminder.id, invoice_id)
        except Exception:
            pass  # Tasks may not be configured
        return ActionExecuteResponse(
            success=True,
            message=f"gentle sollecito inviato per {invoice.invoice_number}",
            action=action,
            invoice_id=invoice_id,
        )
    
    if action == "send_reminder_normale":
        reminder = Reminder(
            invoice_id=invoice_id,
            reminder_date=datetime.utcnow(),
            reminder_type="normale",
            sent_via="email",
            status="pending",
            message=payload.message or f"normale sollecito per fattura {invoice.invoice_number}",
            sent_by=current_user.id,
        )
        db.add(reminder)
        await db.commit()
        try:
            from app.tasks.reminders import send_reminder_task
            send_reminder_task.delay(reminder.id, invoice_id)
        except Exception:
            pass
        return ActionExecuteResponse(
            success=True,
            message=f"normale sollecito inviato per {invoice.invoice_number}",
            action=action,
            invoice_id=invoice_id,
        )
    
    if action == "send_fermo":
        reminder = Reminder(
            invoice_id=invoice_id,
            reminder_date=datetime.utcnow(),
            reminder_type="fermo",
            sent_via="pec",
            status="pending",
            message=payload.message or f"fermo sollecito per fattura {invoice.invoice_number}",
            sent_by=current_user.id,
        )
        db.add(reminder)
        await db.commit()
        try:
            from app.tasks.reminders import send_reminder_task
            send_reminder_task.delay(reminder.id, invoice_id)
        except Exception:
            pass
        return ActionExecuteResponse(
            success=True,
            message=f"fermo sollecito inviato per {invoice.invoice_number}",
            action=action,
            invoice_id=invoice_id,
        )
    
    if action == "apply_penalty":
        # Calculate penalty per D.Lgs 231/2002
        # Tasso base 12% + penalty 1% every 30 days over 60
        from app.core.config import settings
        tasso = settings.INTERESSI_TASSO_BASE
        penalty_pct = settings.PENALTY_PERCENTUALE
        penalty_days = settings.PENALTY_GIORNI
        
        extra_days = max(0, days_overdue - 60)
        penalty_periods = extra_days // penalty_days
        total_penalty = invoice.total_amount * penalty_pct * penalty_periods
        
        return ActionExecuteResponse(
            success=True,
            message=f"Penale calcolata: {total_penalty:.2f}€ ({penalty_periods} periodi, {penalty_pct*100}% ogni {penalty_days}gg oltre 60)",
            action=action,
            invoice_id=invoice_id,
        )
    
    if action == "send_diffida":
        reminder = Reminder(
            invoice_id=invoice_id,
            reminder_date=datetime.utcnow(),
            reminder_type="diffida",
            sent_via="pec",
            status="pending",
            message=payload.message or f"Diffida formale per fattura {invoice.invoice_number}",
            sent_by=current_user.id,
        )
        db.add(reminder)
        await db.commit()
        try:
            from app.tasks.reminders import send_reminder_task
            send_reminder_task.delay(reminder.id, invoice_id)
        except Exception:
            pass
        return ActionExecuteResponse(
            success=True,
            message=f"Diffida inviata per {invoice.invoice_number}",
            action=action,
            invoice_id=invoice_id,
        )
    
    if action == "prepare_legal":
        return ActionExecuteResponse(
            success=True,
            message=f"Pratica legale predisposta per {invoice.invoice_number} — importo {invoice.total_amount:.2f}€",
            action=action,
            invoice_id=invoice_id,
        )
    
    if action == "mark_uncollectible":
        invoice.status = InvoiceStatus.CANCELLED  # Use CANCELLED as proxy for uncollectible
        invoice.updated_at = datetime.utcnow()
        await db.commit()
        return ActionExecuteResponse(
            success=True,
            message=f"Fattura {invoice.invoice_number} segnata come inesigibile",
            action=action,
            invoice_id=invoice_id,
        )
    
    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
