"""
Scheduler tasks for periodic invoice management.
"""
from app.tasks.celery_app import celery_app
from app.db.session import async_session_maker
from app.models.invoice import Invoice, InvoiceStatus, Reminder
from sqlalchemy import select, and_
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def check_overdue_invoices():
    """Check and update overdue invoices."""
    import asyncio

    async def _check():
        async with async_session_maker() as db:
            today = date.today()

            # Find pending invoices past due date
            result = await db.execute(
                select(Invoice).where(
                    and_(
                        Invoice.due_date < today,
                        Invoice.status == InvoiceStatus.PENDING
                    )
                )
            )
            overdue_invoices = result.scalars().all()

            updated = 0
            for invoice in overdue_invoices:
                invoice.status = InvoiceStatus.OVERDUE
                invoice.updated_at = datetime.utcnow()
                updated += 1

            await db.commit()
            logger.info(f"Marked {updated} invoices as overdue")

            return {"updated": updated}

    return asyncio.run(_check())


@celery_app.task
def send_due_reminders():
    """Send automatic reminders for invoices due within 7 days."""
    import asyncio

    async def _send():
        async with async_session_maker() as db:
            today = date.today()
            week_future = today + timedelta(days=7)

            # Find invoices due soon
            result = await db.execute(
                select(Invoice).where(
                    and_(
                        Invoice.due_date >= today,
                        Invoice.due_date <= week_future,
                        Invoice.status == InvoiceStatus.PENDING
                    )
                )
            )
            due_soon = result.scalars().all()

            created = 0
            for invoice in due_soon:
                # Check if we already sent a reminder today
                today_start = datetime.combine(today, datetime.min.time())
                existing = await db.execute(
                    select(Reminder).where(
                        and_(
                            Reminder.invoice_id == invoice.id,
                            Reminder.reminder_type == "automatic",
                            Reminder.created_at >= today_start
                        )
                    )
                )
                if not existing.scalar_one_or_none():
                    reminder = Reminder(
                        invoice_id=invoice.id,
                        reminder_date=datetime.utcnow(),
                        reminder_type="automatic",
                        sent_via="telegram",
                        status="pending",
                        message=f"Promemoria: fattura {invoice.invoice_number} in scadenza il {invoice.due_date}",
                    )
                    db.add(reminder)
                    created += 1

                    # Queue reminder task
                    from app.tasks.reminders import send_reminder_task
                    send_reminder_task.delay(reminder.id, invoice.id)

            await db.commit()
            logger.info(f"Created {created} automatic reminders")

            return {"created": created}

    return asyncio.run(_send())


@celery_app.task
def recalculate_all_trust_scores():
    """Recalculate trust scores for all clients with payment history."""
    import asyncio

    async def _recalculate():
        async with async_session_maker() as db:
            from sqlalchemy import select, distinct
            from app.models.client import Client, PaymentHistory
            from app.services.trust_score import calculate_trust_score

            # Get all client IDs that have payment history
            result = await db.execute(
                select(distinct(PaymentHistory.client_id))
            )
            client_ids = result.scalars().all()

            updated = 0
            for client_id in client_ids:
                try:
                    await calculate_trust_score(db, client_id)
                    updated += 1
                except Exception as e:
                    logger.error(f"Failed to recalculate score for client {client_id}: {e}")

            logger.info(f"Recalculated trust scores for {updated} clients")
            return {"updated": updated}

    return asyncio.run(_recalculate())


@celery_app.task
def cleanup_old_reminders(days: int = 90):
    """Clean up old processed reminders."""
    import asyncio

    async def _cleanup():
        async with async_session_maker() as db:
            cutoff = datetime.utcnow() - timedelta(days=days)

            result = await db.execute(
                select(Reminder).where(
                    Reminder.created_at < cutoff
                )
            )
            old_reminders = result.scalars().all()

            deleted = 0
            for reminder in old_reminders:
                await db.delete(reminder)
                deleted += 1

            await db.commit()
            logger.info(f"Deleted {deleted} old reminders")

            return {"deleted": deleted}

    return asyncio.run(_cleanup())
