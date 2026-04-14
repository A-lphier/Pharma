"""
SDI API Endpoints - Invio e gestione fatture al Sistema di Interscambio.

Endpoints:
- POST /api/v1/sdi/send - Invia una fattura a SDI
- GET /api/v1/sdi/status/{sdi_id} - Verifica stato notifica SDI
- POST /api/v1/sdi/webhook - Callback webhook SDI per aggiornamenti asincroni
- GET /api/v1/sdi/invoices - Lista fatture inviate a SDI
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.database import SDIInvoice, SdiStatus, EmailLog
from app.models.invoice import Invoice
from app.core.security import get_current_active_user
from app.services.sdi_service import (
    OpenAPISDI,
    get_sdi_service,
    SDISendRequest,
    SDISendResponse,
    SDIStatusResponse,
    SDIWebhookPayload,
    SDIInvoiceResponse,
    create_sdi_record,
    update_sdi_status,
)
from app.services.telegram_service import get_telegram_service
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sdi", tags=["SDI"])


class SDIInvoiceDBResponse(BaseModel):
    """Response per fatture SDI dal database."""
    id: int
    invoice_id: int
    sdi_id: Optional[str]
    status: str
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    accepted_at: Optional[datetime]
    rejected_at: Optional[datetime]
    error_message: Optional[str]
    invoice_number: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/send", response_model=SDISendResponse)
async def send_invoice_to_sdi(
    request: SDISendRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    x_tenant_id: Optional[int] = Header(None, alias="X-Tenant-ID"),
):
    """
    Invia una fattura al Sistema di Interscambio (SDI).

    La fattura viene cercata nel database, convertita in XML FatturaPA
    se necessario, e inviata a SDI tramite OpenAPI.

    Il processo e' asincrono: la risposta indica l'avvio dell'invio,
    lo stato viene aggiornato via webhook o polling.
    """
    # Trova la fattura
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.id == request.invoice_id,
                Invoice.created_by == current_user.id,
            )
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Fattura non trovata")

    # Verifica destinatario
    recipient_sdi = request.recipient_sdi or invoice.customer_sdi
    recipient_pec = request.recipient_pec or invoice.customer_pec

    if not recipient_sdi and not recipient_pec:
        raise HTTPException(
            status_code=400,
            detail="Destinatario SDI o PEC mancante. Specificare recipient_sdi o recipient_pec."
        )

    # Ottieni XML (usa raw_xml se disponibile)
    xml_content = invoice.raw_xml

    if not xml_content:
        raise HTTPException(
            status_code=400,
            detail="Contenuto XML fattura non disponibile"
        )

    # Crea record SDIInvoice nel database
    sdi_record = await create_sdi_record(
        db=db,
        invoice_id=invoice.id,
        tenant_id=x_tenant_id or current_user.tenant_id,
        xml_content=xml_content,
        status="sending",
    )

    try:
        # Invia a SDI
        sdi_service = get_sdi_service()
        sdi_result = await sdi_service.send_invoice(xml_content=xml_content)

        sdi_id = sdi_result.get("sdi_id")
        status = sdi_result.get("status", "sent")

        # Aggiorna record SDIInvoice
        await update_sdi_status(
            db=db,
            sdi_record_id=sdi_record.id,
            status=status,
            sdi_id=sdi_id,
        )

        logger.info(
            f"[SDI API] Fattura {invoice.invoice_number} inviata a SDI: {sdi_id}",
            extra={
                "sdi_invoice_id": invoice.id,
                "sdi_record_id": sdi_record.id,
                "sdi_id": sdi_id,
            }
        )

        return SDISendResponse(
            success=True,
            sdi_id=sdi_id,
            status=status,
            message=f"Fattura {invoice.invoice_number} inviata a SDI con ID {sdi_id}",
            sdi_record_id=sdi_record.id,
        )

    except Exception as e:
        # Aggiorna stato a error
        await update_sdi_status(
            db=db,
            sdi_record_id=sdi_record.id,
            status="error",
            error_message=str(e),
        )

        logger.error(f"[SDI API] Errore invio fattura {invoice.invoice_number}: {e}")

        return SDISendResponse(
            success=False,
            status="error",
            message=f"Errore invio SDI: {str(e)}",
            sdi_record_id=sdi_record.id,
        )


@router.get("/status/{sdi_id}", response_model=SDIStatusResponse)
async def get_sdi_status(
    sdi_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Verifica lo stato di una notifica SDI.

    Effettua una chiamata diretta all'API SDI per ottenere
    lo stato piu' aggiornato della fattura.
    """
    sdi_service = get_sdi_service()

    try:
        result = await sdi_service.get_status(sdi_id)

        return SDIStatusResponse(
            sdi_id=sdi_id,
            status=result.get("status", "unknown"),
            sent_at=result.get("sent_at"),
            delivered_at=result.get("delivered_at"),
            accepted_at=result.get("accepted_at"),
            rejected_at=result.get("rejected_at"),
            error_message=result.get("error_message"),
        )

    except Exception as e:
        logger.error(f"[SDI API] Errore get_status per {sdi_id}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Errore comunicazione con SDI: {str(e)}"
        )


@router.post("/webhook")
async def sdi_webhook(
    payload: SDIWebhookPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook per callback asincroni da SDI.

    SDI chiama questo endpoint per notificare aggiornamenti
    di stato sulle fatture inviate.

    Gli aggiornamenti vengono processati in background.
    """
    logger.info(
        f"[SDI WEBHOOK] Ricevuto callback per sdi_id={payload.sdi_id}, status={payload.status}",
        extra={
            "sdi_id": payload.sdi_id,
            "sdi_status": payload.status,
            "sdi_invoice_id": payload.invoice_id,
        }
    )

    # Trova il record SDIInvoice
    result = await db.execute(
        select(SDIInvoice).where(SDIInvoice.sdi_id == payload.sdi_id)
    )
    sdi_record = result.scalar_one_or_none()

    if not sdi_record:
        logger.warning(f"[SDI WEBHOOK] Record SDI non trovato per {payload.sdi_id}")
        return {"status": "ignored", "message": "Record non trovato"}

    # Mappa status SDI a status interno
    status_map = {
        "delivered": "delivered",
        "accepted": "accepted",
        "rejected": "rejected",
        "error": "error",
    }
    new_status = status_map.get(payload.status, payload.status)

    # Aggiorna record
    await update_sdi_status(
        db=db,
        sdi_record_id=sdi_record.id,
        status=new_status,
        error_message=payload.error_message,
    )

    # Aggiorna anche la fattura se accettata o rifiutata
    invoice_result = await db.execute(
        select(Invoice).where(Invoice.id == sdi_record.invoice_id)
    )
    invoice = invoice_result.scalar_one_or_none()

    if invoice and new_status == "accepted":
        from app.models.invoice import InvoiceStatus
        invoice.status = InvoiceStatus.PAID
        await db.commit()

    # Notifica Telegram in background se la fattura e' stata rifiutata
    if new_status == "rejected" and invoice:
        background_tasks.add_task(
            _notify_sdi_rejection,
            invoice_id=invoice.id,
            invoice_number=invoice.invoice_number,
            error_message=payload.error_message,
        )

    return {"status": "ok"}


@router.get("/invoices", response_model=List[SDIInvoiceDBResponse])
async def list_sdi_invoices(
    status: Optional[str] = None,
    invoice_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lista le fatture inviate a SDI con filtri.

    Restituisce i record SDIInvoice dal database locale con
    possibilita' di filtrare per stato o ID fattura.
    """
    query = select(SDIInvoice, Invoice.invoice_number).join(
        Invoice, SDIInvoice.invoice_id == Invoice.id
    ).where(Invoice.created_by == current_user.id)

    if status:
        query = query.where(SDIInvoice.status == status)

    if invoice_id:
        query = query.where(SDIInvoice.invoice_id == invoice_id)

    # Paginazione
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for sdi_record, invoice_number in rows:
        item = SDIInvoiceDBResponse(
            id=sdi_record.id,
            invoice_id=sdi_record.invoice_id,
            sdi_id=sdi_record.sdi_id,
            status=sdi_record.status,
            sent_at=sdi_record.sent_at,
            delivered_at=sdi_record.delivered_at,
            accepted_at=sdi_record.accepted_at,
            rejected_at=sdi_record.rejected_at,
            error_message=sdi_record.error_message,
            invoice_number=invoice_number,
        )
        items.append(item)

    return items


# === Background tasks ===

async def _notify_sdi_rejection(
    invoice_id: int,
    invoice_number: str,
    error_message: Optional[str],
) -> None:
    """
    Notifica su Telegram quando una fattura viene rifiutata da SDI.

    Args:
        invoice_id: ID della fattura
        invoice_number: Numero della fattura
        error_message: Motivo del rifiuto
    """
    try:
        from app.db.session import async_session_maker
        from sqlalchemy import select

        async with async_session_maker() as db:
            result = await db.execute(
                select(Invoice).where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()

            if not invoice or not invoice.created_by:
                return

            # Trova l'utente per ottenere il chat_id Telegram
            from app.models.user import User
            user_result = await db.execute(
                select(User).where(User.id == invoice.created_by)
            )
            user = user_result.scalar_one_or_none()

            if not user or not user.telegram_chat_id:
                return

            telegram = get_telegram_service()
            await telegram.send_sdi_status(
                chat_id=user.telegram_chat_id,
                invoice_number=invoice_number,
                sdi_id="",
                status="rejected",
                error_message=error_message,
            )

    except Exception as e:
        logger.error(f"[SDI] Errore notifica rifiuto Telegram: {e}")


import logging
logger = logging.getLogger(__name__)
