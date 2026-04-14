"""
SSE (Server-Sent Events) for real-time updates.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import logging

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.invoice import Invoice, InvoiceStatus
from sqlalchemy import select, func, and_
from datetime import date, timedelta

router = APIRouter(prefix="/events", tags=["Real-time Events"])


async def invoice_event_generator(user_id: int, db: AsyncSession):
    """Generate invoice-related events."""
    last_check = None

    while True:
        try:
            # Check for changes in user's invoices
            today = date.today()
            week_future = today + timedelta(days=7)

            # Get counts
            base_query = select(func.count()).select_from(Invoice).where(Invoice.created_by == user_id)

            total_result = await db.execute(base_query)
            total = total_result.scalar()

            overdue_result = await db.execute(
                base_query.where(
                    and_(
                        Invoice.due_date < today,
                        Invoice.status != InvoiceStatus.PAID
                    )
                )
            )
            overdue = overdue_result.scalar()

            due_soon_result = await db.execute(
                base_query.where(
                    and_(
                        Invoice.due_date >= today,
                        Invoice.due_date <= week_future,
                        Invoice.status == InvoiceStatus.PENDING
                    )
                )
            )
            due_soon = due_soon_result.scalar()

            # Build event data
            event_data = {
                "type": "stats_update",
                "data": {
                    "total": total,
                    "overdue": overdue,
                    "due_soon": due_soon,
                }
            }

            # Only yield if changed
            if event_data != last_check:
                last_check = event_data
                yield {
                    "event": "invoice_stats",
                    "data": json.dumps(event_data)
                }

            await asyncio.sleep(30)  # Check every 30 seconds

        except Exception as e:
            logging.error(f"SSE generator error: {e}")
            await asyncio.sleep(60)


@router.get("/stream")
async def stream_invoice_events(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream real-time invoice events via SSE."""
    return EventSourceResponse(
        invoice_event_generator(current_user.id, db)
    )


@router.post("/broadcast")
async def broadcast_event(
    event_type: str,
    message: str,
    current_user: User = Depends(get_current_active_user),
):
    """Broadcast an event to all connected clients (admin only)."""
    if current_user.role != "admin":
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # In production, use Redis pub/sub for broadcasting
    # For now, just log it
    logging.info(f"Broadcast event: {event_type} - {message}")

    return {"success": True, "event_type": event_type}
