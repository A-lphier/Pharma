"""
Invoice API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List
from datetime import datetime, date, timedelta

from app.db.session import get_db
from app.models.user import User
from app.models.invoice import Invoice, Reminder, InvoiceStatus
from app.schemas.invoice import (
    InvoiceResponse, InvoiceCreate, InvoiceUpdate, InvoiceListResponse,
    InvoiceStats, ReminderResponse, BulkAction
)
from app.core.security import get_current_active_user
from app.services.invoice_parser import parse_invoice_xml, InvoiceParserError
from app.core.config import settings
from app.schemas.invoice import CalcoloInteressiResponse

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    status: Optional[InvoiceStatus] = None,
    due_soon: Optional[int] = Query(None, description="Days until due"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get paginated list of invoices."""
    query = select(Invoice).where(Invoice.created_by == current_user.id)

    # Apply filters
    if status:
        query = query.where(Invoice.status == status)

    if due_soon:
        today = date.today()
        future = today + timedelta(days=due_soon)
        query = query.where(
            and_(
                Invoice.due_date >= today,
                Invoice.due_date <= future,
                Invoice.status != InvoiceStatus.PAID
            )
        )

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Invoice.invoice_number.ilike(search_filter),
                Invoice.customer_name.ilike(search_filter),
                Invoice.supplier_name.ilike(search_filter)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Invoice.due_date.asc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    invoices = result.scalars().all()

    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(inv) for inv in invoices],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/stats", response_model=InvoiceStats)
async def get_invoice_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get invoice statistics."""
    base_query = select(Invoice).where(Invoice.created_by == current_user.id)

    today = date.today()
    week_future = today + timedelta(days=7)

    # Total
    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = total_result.scalar()

    # Paid
    paid_query = base_query.where(Invoice.status == InvoiceStatus.PAID)
    paid_result = await db.execute(select(func.count()).select_from(paid_query.subquery()))
    paid = paid_result.scalar()

    # Due soon
    due_soon_query = base_query.where(
        and_(
            Invoice.due_date >= today,
            Invoice.due_date <= week_future,
            Invoice.status != InvoiceStatus.PAID
        )
    )
    due_soon_result = await db.execute(select(func.count()).select_from(due_soon_query.subquery()))
    due_soon = due_soon_result.scalar()

    # Overdue
    overdue_query = base_query.where(
        and_(
            Invoice.due_date < today,
            Invoice.status != InvoiceStatus.PAID
        )
    )
    overdue_result = await db.execute(select(func.count()).select_from(overdue_query.subquery()))
    overdue = overdue_result.scalar()

    # Amounts
    amount_result = await db.execute(
        select(
            func.sum(Invoice.total_amount),
            func.sum(func.nullif(Invoice.total_amount, 0)).filter(Invoice.status == InvoiceStatus.PAID)
        ).select_from(base_query.subquery())
    )
    total_amount, paid_amount = amount_result.one()

    pending_query = base_query.where(Invoice.status == InvoiceStatus.PENDING)
    pending_result = await db.execute(
        select(func.count()).select_from(pending_query.subquery())
    )
    pending = pending_result.scalar()

    overdue_amount_query = overdue_query.with_only_columns(func.sum(Invoice.total_amount))
    overdue_amount_result = await db.execute(overdue_amount_query)
    overdue_amount = overdue_amount_result.scalar() or 0

    return InvoiceStats(
        total=total,
        paid=paid,
        pending=pending,
        overdue=overdue,
        due_soon=due_soon,
        total_amount=total_amount or 0,
        paid_amount=paid_amount or 0,
        pending_amount=(total_amount or 0) - (paid_amount or 0) - (overdue_amount or 0),
        overdue_amount=overdue_amount,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single invoice by ID."""
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice


@router.get("/{invoice_id}/escalation-status")
async def get_invoice_escalation_status(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get escalation status for a specific invoice."""
    from app.models.invoice import EscalationStage
    from datetime import date, datetime

    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    today = date.today()
    due_date = invoice.due_date
    if isinstance(due_date, str):
        due_date = date.fromisoformat(due_date)
    elif isinstance(due_date, datetime):
        due_date = due_date.date()
    days_overdue = (today - due_date).days if invoice.status == InvoiceStatus.OVERDUE else 0

    is_recurring = bool(invoice.customer_vat and invoice.customer_vat not in ("", "0", None))

    STAGE_LABELS = {
        EscalationStage.NONE: "Nessuno",
        EscalationStage.SOLLECITO_1: "1° Sollecito",
        EscalationStage.SOLLECITO_2: "2° Sollecito",
        EscalationStage.PENALTY_APPLICATA: "Penalty Applicata",
        EscalationStage.DIFFIDA: "Diffida",
        EscalationStage.STOP_SERVIZI: "Stop Servizi",
        EscalationStage.LEGAL_ACTION: "Azione Legale",
    }

    STAGE_THRESHOLDS = {
        EscalationStage.NONE: None,
        EscalationStage.SOLLECITO_1: 7,
        EscalationStage.SOLLECITO_2: 30,
        EscalationStage.PENALTY_APPLICATA: 60,
        EscalationStage.DIFFIDA: 90,
        EscalationStage.STOP_SERVIZI: 120,
        EscalationStage.LEGAL_ACTION: 120,
    }

    STAGE_ORDER = [
        EscalationStage.NONE, EscalationStage.SOLLECITO_1, EscalationStage.SOLLECITO_2,
        EscalationStage.PENALTY_APPLICATA, EscalationStage.DIFFIDA,
        EscalationStage.STOP_SERVIZI, EscalationStage.LEGAL_ACTION,
    ]

    def days_until_next(stage: EscalationStage, overdue: int) -> Optional[int]:
        next_map = {
            EscalationStage.NONE: 7, EscalationStage.SOLLECITO_1: 30,
            EscalationStage.SOLLECITO_2: 60, EscalationStage.PENALTY_APPLICATA: 90,
            EscalationStage.DIFFIDA: 120,
        }
        thr = next_map.get(stage)
        if thr is None:
            return None
        return max(thr - overdue, 0)

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "customer_name": invoice.customer_name,
        "total_amount": invoice.total_amount,
        "due_date": due_date.isoformat(),
        "days_overdue": max(days_overdue, 0),
        "escalation_stage": invoice.escalation_stage.value,
        "escalation_label": STAGE_LABELS.get(invoice.escalation_stage, "Sconosciuto"),
        "escalation_updated_at": invoice.escalation_updated_at.isoformat() if invoice.escalation_updated_at else None,
        "penalty_applied": invoice.penalty_applied,
        "days_until_next_stage": days_until_next(invoice.escalation_stage, max(days_overdue, 0)),
        "all_stages": [s.value for s in STAGE_ORDER],
        "stage_labels": {s.value: STAGE_LABELS[s] for s in STAGE_ORDER},
        "stage_thresholds": {s.value: STAGE_THRESHOLDS.get(s) for s in STAGE_ORDER},
        "is_recurring": is_recurring,
        "status": invoice.status.value,
    }


@router.post("", response_model=InvoiceResponse, status_code=201)
async def upload_invoice(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload and parse an XML FatturaPA file."""
    if not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Only XML files supported")

    content = await file.read()

    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    if len(content) < 50:
        raise HTTPException(status_code=400, detail="File too small or empty")

    try:
        xml_str = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8")

    try:
        invoice_data = parse_invoice_xml(xml_str)
    except InvoiceParserError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse failed: {str(e)}")

    # Save file
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_filename = f"{file.filename}"
    xml_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    
    # Create invoice record
    invoice = Invoice(
        invoice_number=invoice_data.get('invoice_number', ''),
        invoice_date=invoice_data.get('invoice_date', date.today()),
        due_date=invoice_data.get('due_date', date.today() + timedelta(days=30)),
        customer_name=invoice_data.get('customer_name', 'Unknown'),
        customer_vat=invoice_data.get('customer_vat', ''),
        customer_address=invoice_data.get('customer_address', ''),
        customer_phone=invoice_data.get('customer_phone', ''),
        customer_pec=invoice_data.get('customer_pec', ''),
        customer_sdi=invoice_data.get('customer_sdi', ''),
        customer_cf=invoice_data.get('customer_cf', ''),
        customer_email=invoice_data.get('customer_email', ''),
        supplier_name=invoice_data.get('supplier_name', ''),
        supplier_vat=invoice_data.get('supplier_vat', ''),
        supplier_address=invoice_data.get('supplier_address', ''),
        supplier_phone=invoice_data.get('supplier_phone', ''),
        supplier_pec=invoice_data.get('supplier_pec', ''),
        supplier_iban=invoice_data.get('supplier_iban', ''),
        supplier_sdi=invoice_data.get('supplier_sdi', ''),
        supplier_cf=invoice_data.get('supplier_cf', ''),
        supplier_email=invoice_data.get('supplier_email', ''),
        amount=invoice_data.get('amount', 0),
        vat_amount=invoice_data.get('vat_amount', 0),
        total_amount=invoice_data.get('total_amount', 0),
        description=invoice_data.get('description', ''),
        xml_filename=safe_filename,
        raw_xml=xml_str,
        created_by=current_user.id,
    )

    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)

    # Write file in background
    if background_tasks:
        background_tasks.add_task(_save_xml_file, xml_path, content)

    return invoice


async def _save_xml_file(path: str, content: bytes):
    """Save XML file to disk (runs in background)."""
    import aiofiles
    async with aiofiles.open(path, 'wb') as f:
        await f.write(content)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    update_data: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an invoice."""
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(invoice, key, value)

    invoice.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(invoice)

    return invoice


@router.post("/{invoice_id}/paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark an invoice as paid."""
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.status = InvoiceStatus.PAID
    invoice.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(invoice)

    return invoice


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete an invoice."""
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    await db.delete(invoice)
    await db.commit()


@router.post("/bulk/pay")
async def bulk_mark_paid(
    action: BulkAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark multiple invoices as paid."""
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.id.in_(action.invoice_ids),
                Invoice.created_by == current_user.id
            )
        )
    )
    invoices = result.scalars().all()

    updated = 0
    for invoice in invoices:
        invoice.status = InvoiceStatus.PAID
        invoice.updated_at = datetime.utcnow()
        updated += 1

    await db.commit()

    return {"success": True, "updated": updated}


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Genera e restituisce il PDF della fattura.
    
    Content-Type: application/pdf
    Content-Disposition: inline (mostra nel browser)
    """
    from app.services.pdf_service import generate_invoice_pdf
    
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Fattura non trovata")

    # Costruisci dizionario con i dati della fattura
    invoice_dict = {
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "customer_name": invoice.customer_name,
        "customer_vat": invoice.customer_vat or "",
        "customer_address": invoice.customer_address or "",
        "customer_phone": invoice.customer_phone or "",
        "customer_email": invoice.customer_email or "",
        "customer_pec": invoice.customer_pec or "",
        "customer_sdi": invoice.customer_sdi or "",
        "customer_cf": invoice.customer_cf or "",
        "supplier_name": invoice.supplier_name,
        "supplier_vat": invoice.supplier_vat or "",
        "supplier_address": invoice.supplier_address or "",
        "supplier_phone": invoice.supplier_phone or "",
        "supplier_email": invoice.supplier_email or "",
        "supplier_pec": invoice.supplier_pec or "",
        "supplier_sdi": invoice.supplier_sdi or "",
        "supplier_cf": invoice.supplier_cf or "",
        "supplier_iban": invoice.supplier_iban or "",
        "amount": invoice.amount,
        "vat_amount": invoice.vat_amount,
        "total_amount": invoice.total_amount,
        "description": invoice.description or "",
        "status": invoice.status.value if invoice.status else "pending",
        "payment_days": invoice.payment_days or 30,
        "payment_method": invoice.payment_method or "Bonifico bancario",
    }

    pdf_bytes = generate_invoice_pdf(invoice_dict)

    from fastapi.responses import Response
    filename = f"fattura_{invoice.invoice_number.replace('/', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Content-Length": str(len(pdf_bytes)),
        }
    )


@router.post("/{invoice_id}/remind", response_model=ReminderResponse)
async def send_reminder(
    invoice_id: int,
    message: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Send a reminder for an invoice."""
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=400, detail="Cannot remind paid invoice")

    reminder = Reminder(
        invoice_id=invoice_id,
        reminder_date=datetime.utcnow(),
        reminder_type="manual",
        sent_via="telegram",
        status="pending",
        message=message or f"Sollecito per fattura {invoice.invoice_number}",
        sent_by=current_user.id,
    )

    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)

    # Queue async task
    from app.tasks.reminders import send_reminder_task
    send_reminder_task.delay(reminder.id, invoice.id)

    return reminder


# ─── Interessi di Mora ────────────────────────────────────────────────────────

def calcola_interessi(
    importo: float,
    data_scadenza: date,
    data_pagamento: Optional[date] = None,
) -> CalcoloInteressiResponse:
    """
    Calcola interessi di mora e penalty progressiva per ritardato pagamento B2B.

    D.Lgs 231/2002: tasso BCE (4%) + 8% spread = 12% annuo base.
    Penalty: +1% ogni 30gg oltre i 60gg di ritardo.

    La penalty si applica solo dopo i primi 60 giorni di ritardo.
    Ogni blocco di PENALTY_GIORNI (30gg) oltre i 60gg aggiunge PENALTY_PERCENTUALE (1%).
    """
    tasso_base = settings.INTERESSI_TASSO_BASE        # 0.12 = 12%
    penalty_pct = settings.PENALTY_PERCENTUALE       # 0.01 = 1%
    penalty_giorni = settings.PENALTY_GIORNI          # 30

    today = data_pagamento if data_pagamento else date.today()
    giorni_ritardo = (today - data_scadenza).days

    if giorni_ritardo <= 0:
        # Non scaduto o pagamento in anticipo
        return CalcoloInteressiResponse(
            importo_originale=importo,
            interessi=0.0,
            penalty=0.0,
            totale=importo,
            giorni_ritardo=0,
            tasso_applicato=tasso_base,
            data_pagamento=today,
        )

    # Interessi giornalieri: (tasso_annuo / 365) * giorni_ritardo * importo
    interesse_giornaliero = (tasso_base / 365) * giorni_ritardo * importo

    # Penalty progressiva: solo oltre 60gg, ogni penalty_giorni (30gg) aggiunge penalty_pct (1%)
    if giorni_ritardo > 60:
        blocchi_penalty = (giorni_ritardo - 60) // penalty_giorni
        penalty = importo * blocchi_penalty * penalty_pct
    else:
        penalty = 0.0

    totale = importo + interesse_giornaliero + penalty

    return CalcoloInteressiResponse(
        importo_originale=importo,
        interessi=round(interesse_giornaliero, 2),
        penalty=round(penalty, 2),
        totale=round(totale, 2),
        giorni_ritardo=giorni_ritardo,
        tasso_applicato=tasso_base,
        data_pagamento=today,
    )


@router.get("/{invoice_id}/calcolo-interessi", response_model=CalcoloInteressiResponse)
async def get_calcolo_interessi(
    invoice_id: int,
    data_pagamento: Optional[date] = Query(
        None,
        description="Data pagamento ipotetica (default: oggi)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Calcola interessi di mora e penalty per una fattura."""
    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == invoice_id, Invoice.created_by == current_user.id)
        )
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return calcola_interessi(
        importo=invoice.total_amount,
        data_scadenza=invoice.due_date,
        data_pagamento=data_pagamento,
    )
