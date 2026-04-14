"""
Reminder tasks for Celery.
"""
from app.tasks.celery_app import celery_app
import httpx
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_reminder_task(self, reminder_id: int, invoice_id: int):
    """Send a reminder notification via Telegram."""
    from app.core.config import settings
    from app.db.session import async_session_maker
    from app.models.invoice import Reminder, Invoice
    from sqlalchemy import select
    import asyncio

    async def _send():
        async with async_session_maker() as db:
            # Get reminder and invoice
            result = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
            reminder = result.scalar_one_or_none()

            if not reminder:
                logger.error(f"Reminder {reminder_id} not found")
                return {"success": False, "error": "Reminder not found"}

            result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
            invoice = result.scalar_one_or_none()

            if not invoice:
                logger.error(f"Invoice {invoice_id} not found")
                return {"success": False, "error": "Invoice not found"}

            # Build message
            reminder_text = reminder.message or "Si prega di procedere al pagamento."
            message = f"""
🔔 *Sollecito di pagamento*

📄 Fattura: *{invoice.invoice_number}*
💶 Importo: *€{invoice.total_amount:,.2f}*
📅 Scadenza: {invoice.due_date}
🏢 Cliente: {invoice.customer_name}

{reminder_text}
            """.strip()

            # Send via Telegram
            if settings.TELEGRAM_BOT_TOKEN:
                try:
                    async with httpx.AsyncClient() as client:
                        # Get user's telegram chat_id from their profile
                        from app.models.user import User
                        from sqlalchemy import select
                        user_result = await db.execute(
                            select(User).where(User.id == reminder.sent_by)
                        )
                        user = user_result.scalar_one_or_none()

                        if user and user.telegram_chat_id:
                            response = await client.post(
                                f"https://api.telegram.org/{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                                json={
                                    "chat_id": user.telegram_chat_id,
                                    "text": message,
                                    "parse_mode": "Markdown",
                                },
                            )
                            if response.status_code == 200:
                                reminder.status = "sent"
                            else:
                                reminder.status = "failed"
                        else:
                            reminder.status = "failed"
                            logger.warning(f"No telegram_chat_id for user {user.id if user else 'unknown'}")

                    await db.commit()
                except Exception as e:
                    logger.error(f"Telegram send failed: {e}")
                    reminder.status = "failed"
                    await db.commit()
                    raise self.retry(exc=e, countdown=60)
            else:
                logger.warning("Telegram bot token not configured")
                reminder.status = "failed"
                await db.commit()

            return {"success": reminder.status == "sent", "reminder_id": reminder_id}

    return asyncio.run(_send())


@celery_app.task
def send_bulk_reminders(invoice_ids: list[int]):
    """Send reminders to multiple invoices."""
    results = []
    for invoice_id in invoice_ids:
        # Get reminder_id from db and call send_reminder_task
        from app.db.session import async_session_maker
        from app.models.invoice import Reminder
        from sqlalchemy import select
        import asyncio

        async def _get_and_send():
            async with async_session_maker() as db:
                result = await db.execute(
                    select(Reminder)
                    .where(Reminder.invoice_id == invoice_id)
                    .order_by(Reminder.created_at.desc())
                    .limit(1)
                )
                reminder = result.scalar_one_or_none()
                if reminder:
                    send_reminder_task.delay(reminder.id, invoice_id)

        asyncio.run(_get_and_send())
        results.append(invoice_id)

    return {"sent": results}
