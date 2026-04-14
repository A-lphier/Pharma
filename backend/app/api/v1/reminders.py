"""
Reminders API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice, Reminder, InvoiceStatus
from app.schemas.invoice import ReminderResponse, ReminderCreate
from app.core.security import get_current_active_user

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.post("", response_model=ReminderResponse, status_code=201)
async def create_reminder(
    reminder_data: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create and send a reminder for an invoice.
    
    Body: { invoice_id, message, sent_via: 'telegram' }
    """
    # Verify invoice exists and belongs to user
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == reminder_data.invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Cannot remind paid invoice")

    # Create reminder record
    reminder = Reminder(
        invoice_id=reminder_data.invoice_id,
        reminder_date=datetime.utcnow(),
        reminder_type=reminder_data.reminder_type or "manual",
        sent_via=reminder_data.sent_via or "telegram",
        status="pending",
        message=reminder_data.message,
        sent_by=current_user.id,
    )

    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)

    # Queue async task to send the reminder
    from app.tasks.reminders import send_reminder_task
    try:
        send_reminder_task.delay(reminder.id, invoice.id)
    except Exception:
        # If celery is not available, mark as failed
        reminder.status = "failed"
        await db.commit()

    return reminder
