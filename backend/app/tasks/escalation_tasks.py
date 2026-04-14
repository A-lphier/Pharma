"""
Task Celery per la gestione automatica dell'escalation delle fatture scadute.
Esegue ogni giorno alle 9:00 via Celery Beat.
"""
from app.tasks.celery_app import celery_app
from celery import Task
import logging
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


class EscalationTask(Task):
    """Task base con retry automatico per escalation."""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True


# Threshold in days for each escalation stage
STAGE_THRESHOLDS = {
    "sollecito_1": 7,
    "sollecito_2": 30,
    "penalty_applicata": 60,
    "diffida": 90,
    "stop_servizi": 120,
    "legal_action": 120,
}

ANNUAL_INTEREST_RATE = 0.08  # 8% annual


def calculate_interest(total_amount: float, days_overdue: int) -> float:
    """Calculate interest on overdue amount."""
    daily_rate = ANNUAL_INTEREST_RATE / 365
    return round(total_amount * daily_rate * days_overdue, 2)


def compute_escalation_stage(days_overdue: int, is_recurring: bool) -> str:
    """Compute the appropriate escalation stage based on days overdue."""
    if days_overdue < 7:
        return "none"
    elif days_overdue < 30:
        return "sollecito_1"
    elif days_overdue < 60:
        return "sollecito_2"
    elif days_overdue < 90:
        return "penalty_applicata"
    elif days_overdue < 120:
        return "diffida"
    else:
        return "stop_servizi" if is_recurring else "legal_action"


@celery_app.task(
    bind=True,
    base=EscalationTask,
    name="app.tasks.escalation_tasks.process_overdue_escalation",
)
def process_overdue_escalation(self, user_id: int = None) -> dict:
    """
    Process all overdue invoices and advance their escalation stage.
    Scheduled: every day at 9:00 AM via Celery Beat.
    
    Logic:
      - 7 days overdue  → SOLLECITO_1
      - 30 days overdue  → SOLLECITO_2
      - 60 days overdue  → PENALTY_APPLICATA + interest
      - 90 days overdue  → DIFFIDA
      - 120 days overdue → STOP_SERVIZI (recurring) or LEGAL_ACTION (non-recurring)
    
    Args:
        user_id: ID utente opzionale (se None, elabora tutti gli utenti)
    
    Returns:
        dict con riepilogo elaborazione
    """
    logger.info(f"Escalation: Avvio processo giornaliero (user_id={user_id})")
    
    async def _process():
        from app.db.session import async_session_maker
        from app.models.user import User
        from app.models.invoice import Invoice, InvoiceStatus, EscalationStage
        from sqlalchemy import select, and_

        async with async_session_maker() as db:
            # Get all users to process
            if user_id:
                users_query = select(User).where(
                    and_(User.id == user_id, User.is_active == True)
                )
            else:
                users_query = select(User).where(User.is_active == True)
            
            users_result = await db.execute(users_query)
            users = users_result.scalars().all()

            total_updated = 0
            all_details = []

            for user in users:
                # Get all overdue invoices for this user that haven't reached max stage
                invoices_result = await db.execute(
                    select(Invoice).where(
                        and_(
                            Invoice.created_by == user.id,
                            Invoice.status == InvoiceStatus.OVERDUE,
                            Invoice.escalation_stage != EscalationStage.LEGAL_ACTION,
                        )
                    )
                )
                invoices = invoices_result.scalars().all()

                for invoice in invoices:
                    due_date_val = invoice.due_date
                    if isinstance(due_date_val, str):
                        due_date_val = date.fromisoformat(due_date_val)
                    elif isinstance(due_date_val, datetime):
                        due_date_val = due_date_val.date()

                    days_overdue = (date.today() - due_date_val).days
                    if days_overdue < 0:
                        continue

                    # Determine if recurring client (has a VAT number = likely real business)
                    is_recurring = bool(invoice.customer_vat and invoice.customer_vat not in ("", "0", None))

                    new_stage_value = compute_escalation_stage(days_overdue, is_recurring)
                    new_stage = EscalationStage(new_stage_value)

                    if new_stage != invoice.escalation_stage:
                        old_stage = invoice.escalation_stage
                        invoice.escalation_stage = new_stage
                        invoice.escalation_updated_at = datetime.utcnow()

                        # Calculate penalty when entering PENALTY_APPLICATA
                        penalty = 0.0
                        if new_stage == EscalationStage.PENALTY_APPLICATA and invoice.penalty_applied == 0:
                            penalty = calculate_interest(invoice.total_amount, days_overdue)
                            invoice.penalty_applied = penalty

                        all_details.append({
                            "invoice_id": invoice.id,
                            "invoice_number": invoice.invoice_number,
                            "customer_name": invoice.customer_name,
                            "days_overdue": days_overdue,
                            "old_stage": old_stage.value,
                            "new_stage": new_stage.value,
                            "penalty_applied": penalty,
                        })
                        total_updated += 1

            if all_details:
                await db.commit()
                logger.info(f"Escalation: Aggiornate {total_updated} fatture")
            else:
                logger.info("Escalation: Nessuna fattura da aggiornare")

            return {
                "processed_users": len(users),
                "total_invoices_updated": total_updated,
                "details": all_details,
                "executed_at": datetime.utcnow().isoformat(),
            }

    # Run the async function synchronously
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_process())
        return result
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    base=EscalationTask,
    name="app.tasks.escalation_tasks.advance_single_invoice",
)
def advance_single_invoice(self, invoice_id: int, target_stage: str = None) -> dict:
    """
    Advance a single invoice to the specified escalation stage.
    
    Args:
        invoice_id: ID della fattura
        target_stage: Stage target opzionale (e.g. "sollecito_1", "diffida")
    
    Returns:
        dict con il nuovo stato
    """
    logger.info(f"Escalation: Avanzamento fattura {invoice_id} → {target_stage}")
    
    async def _advance():
        from app.db.session import async_session_maker
        from app.models.invoice import Invoice, EscalationStage
        from sqlalchemy import select
        from datetime import date

        ANNUAL_INTEREST_RATE = 0.08

        async with async_session_maker() as db:
            result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
            invoice = result.scalar_one_or_none()

            if not invoice:
                return {"error": "Invoice not found", "invoice_id": invoice_id}

            # Determine target stage
            if target_stage:
                try:
                    new_stage = EscalationStage(target_stage)
                except ValueError:
                    return {"error": f"Invalid stage: {target_stage}"}
            else:
                # Advance to next stage in order
                STAGE_ORDER = [
                    EscalationStage.NONE,
                    EscalationStage.SOLLECITO_1,
                    EscalationStage.SOLLECITO_2,
                    EscalationStage.PENALTY_APPLICATA,
                    EscalationStage.DIFFIDA,
                    EscalationStage.STOP_SERVIZI,
                    EscalationStage.LEGAL_ACTION,
                ]
                try:
                    current_idx = STAGE_ORDER.index(invoice.escalation_stage)
                    if current_idx < len(STAGE_ORDER) - 1:
                        new_stage = STAGE_ORDER[current_idx + 1]
                    else:
                        return {"message": "Already at max stage", "stage": invoice.escalation_stage.value}
                except ValueError:
                    new_stage = EscalationStage.SOLLECITO_1

            # Calculate penalty for PENALTY_APPLICATA
            penalty = invoice.penalty_applied
            if new_stage == EscalationStage.PENALTY_APPLICATA:
                due_date_val = invoice.due_date
                if isinstance(due_date_val, str):
                    due_date_val = date.fromisoformat(due_date_val)
                elif isinstance(due_date_val, datetime):
                    due_date_val = due_date_val.date()
                days_overdue = max((date.today() - due_date_val).days, 0)
                penalty = round(invoice.total_amount * (0.08 / 365) * days_overdue, 2)
                invoice.penalty_applied = penalty

            invoice.escalation_stage = new_stage
            invoice.escalation_updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(invoice)

            return {
                "invoice_id": invoice.id,
                "new_stage": new_stage.value,
                "penalty_applied": penalty,
            }

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_advance())
        return result
    finally:
        loop.close()
