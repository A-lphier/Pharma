"""
CSV Import API endpoints.

Handles importing historical client and invoice data from CSV files.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, date
import csv
import io

from app.db.session import get_db
from app.models.user import User
from app.models.client import Client, PaymentHistory, ImportHistory, BusinessConfig
from app.models.invoice import Invoice
from app.schemas.client import ImportResultResponse, ImportHistoryResponse
from app.core.security import get_current_active_user

router = APIRouter(prefix="/import", tags=["Import"])


async def parse_csv(content: bytes) -> List[dict]:
    """Parse CSV content into list of records."""
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    
    records = []
    for row in reader:
        # Normalize field names
        normalized = {
            "cliente": row.get("cliente", "").strip(),
            "data_fattura": row.get("data_fattura", "").strip(),
            "data_pagamento": row.get("data_pagamento", "").strip(),
            "importo": row.get("importo", "0").strip(),
        }
        records.append(normalized)
    
    return records


def parse_date(date_str: str) -> date:
    """Parse date string in various formats."""
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def parse_amount(amount_str: str) -> float:
    """Parse amount string."""
    # Remove currency symbols and whitespace
    cleaned = amount_str.replace("€", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


async def calculate_score_from_history(db: AsyncSession, client_id: int) -> int:
    """Calculate trust score based on imported payment history."""
    result = await db.execute(
        select(PaymentHistory).where(PaymentHistory.client_id == client_id)
    )
    histories = result.scalars().all()
    
    if not histories:
        return 60
    
    # Get base score from config
    config_result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = config_result.scalar_one_or_none()
    base_score = config.new_client_score if config else 60
    
    score = base_score
    
    for history in histories:
        if history.was_on_time:
            score += 3
            # Early payment: flat +5 bonus
            if history.paid_date and history.paid_date < history.due_date:
                score += 5
        else:
            if history.days_late >= 30:
                score -= 20
            else:
                score -= history.days_late
    
    return max(0, min(100, score))


def deduce_style_from_data(records: List[dict]) -> str:
    """Deduce business style from imported data distribution."""
    if not records:
        return "gentile"
    
    # Calculate average delay
    delays = []
    for r in records:
        if r.get("data_pagamento") and r.get("data_fattura"):
            try:
                pay_date = parse_date(r["data_pagamento"])
                inv_date = parse_date(r["data_fattura"])
                delay = (pay_date - inv_date).days
                if delay < 0:
                    delays.append(delay)  # Negative means early
                else:
                    delays.append(delay)
            except Exception:
                pass
    
    if not delays:
        return "gentile"
    
    avg_delay = sum(delays) / len(delays)
    
    if avg_delay <= 0:
        return "gentile"
    elif avg_delay <= 5:
        return "equilibrato"
    else:
        return "fermo"


def deduce_thresholds_from_data(records: List[dict]) -> dict:
    """Deduce thresholds from imported data."""
    amounts = []
    for r in records:
        try:
            amounts.append(parse_amount(r.get("importo", "0")))
        except Exception:
            pass
    
    if not amounts:
        return {
            "legal_threshold": 2000.0,
            "warning_threshold_days": 15,
            "escalation_days": 30,
        }
    
    avg_amount = sum(amounts) / len(amounts)
    max_amount = max(amounts)
    
    # Legal threshold is avg * 0.5
    legal = avg_amount * 0.5
    
    # If max amount is small, use smaller thresholds
    if max_amount < 500:
        warning = 7
        escalation = 14
    elif max_amount < 2000:
        warning = 15
        escalation = 30
    else:
        warning = 30
        escalation = 60
    
    return {
        "legal_threshold": max(500, legal),
        "warning_threshold_days": warning,
        "escalation_days": escalation,
    }


@router.post("/csv", response_model=ImportResultResponse)
async def import_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Import clients and payment history from CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files supported")

    content = await file.read()
    
    if len(content) < 10:
        raise HTTPException(status_code=400, detail="File is too small or empty")

    try:
        records = await parse_csv(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")

    if not records:
        raise HTTPException(status_code=400, detail="No valid records found in CSV")

    clients_created = 0
    clients_updated = 0
    invoices_created = 0
    errors = []
    client_map = {}  # Track created clients by name

    # Track amounts for threshold deduction
    all_amounts = []

    for i, record in enumerate(records):
        try:
            client_name = record.get("cliente", "")
            if not client_name:
                errors.append(f"Row {i+1}: Client name is required")
                continue

            data_fattura = record.get("data_fattura", "")
            data_pagamento = record.get("data_pagamento", "")
            importo_str = record.get("importo", "0")

            if not data_fattura:
                errors.append(f"Row {i+1}: Invoice date is required")
                continue

            importo = parse_amount(importo_str)
            all_amounts.append(importo)

            # Parse dates
            invoice_date = parse_date(data_fattura)
            paid_date = parse_date(data_pagamento) if data_pagamento else None

            # Calculate days late
            # Assume net 30 payment terms if no due date
            due_date = invoice_date.replace(day=min(invoice_date.day + 30, 28))
            days_late = 0
            was_on_time = True

            if paid_date:
                days_late = max(0, (paid_date - due_date).days)
                was_on_time = days_late == 0

            # Find or create client
            if client_name not in client_map:
                # Check if client exists in DB
                result = await db.execute(
                    select(Client).where(
                        Client.name == client_name,
                        Client.created_by == current_user.id,
                    )
                )
                existing_client = result.scalar_one_or_none()

                if existing_client:
                    client = existing_client
                    clients_updated += 1
                else:
                    # Create new client
                    client = Client(
                        name=client_name,
                        created_by=current_user.id,
                        trust_score=60,
                        is_new=True,
                    )
                    db.add(client)
                    await db.flush()
                    clients_created += 1

                client_map[client_name] = client
            else:
                client = client_map[client_name]

            # Create payment history record
            history = PaymentHistory(
                client_id=client.id,
                invoice_amount=importo,
                invoice_date=invoice_date,
                due_date=due_date,
                paid_date=paid_date,
                days_late=days_late,
                was_on_time=was_on_time,
                created_by=current_user.id,
            )
            db.add(history)
            invoices_created += 1

        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")

    # Commit all records
    await db.commit()

    # Recalculate scores for all created/updated clients
    for client_name, client in client_map.items():
        new_score = await calculate_score_from_history(db, client.id)
        client.trust_score = new_score
        if not was_on_time:
            client.payment_pattern = "importato_con_ritardi"
        else:
            client.payment_pattern = "importato_puntuale"
    await db.commit()

    # Deduce and apply business config if this is first import
    if clients_created > 0 or clients_updated > 0:
        config_result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
        config = config_result.scalar_one_or_none()

        if not config or not config.onboarding_completed:
            style = deduce_style_from_data(records)
            thresholds = deduce_thresholds_from_data(records)

            if config:
                config.style = style
                config.legal_threshold = thresholds["legal_threshold"]
                config.warning_threshold_days = thresholds["warning_threshold_days"]
                config.escalation_days = thresholds["escalation_days"]
            else:
                config = BusinessConfig(
                    id=1,
                    style=style,
                    legal_threshold=thresholds["legal_threshold"],
                    warning_threshold_days=thresholds["warning_threshold_days"],
                    escalation_days=thresholds["escalation_days"],
                    onboarding_completed=True,
                )
                db.add(config)

            await db.commit()

    # Save import history
    import_record = ImportHistory(
        filename=file.filename,
        rows_imported=len(records),
        clients_created=clients_created,
        invoices_created=invoices_created,
        imported_by=current_user.id,
    )
    db.add(import_record)
    await db.commit()

    return ImportResultResponse(
        success=True,
        rows_imported=len(records),
        clients_created=clients_created,
        clients_updated=clients_updated,
        invoices_created=invoices_created,
        errors=errors[:50],  # Limit errors to first 50
    )


@router.get("/history", response_model=List[ImportHistoryResponse])
async def get_import_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get import history for current user."""
    result = await db.execute(
        select(ImportHistory)
        .where(ImportHistory.imported_by == current_user.id)
        .order_by(ImportHistory.imported_at.desc())
        .limit(50)
    )
    histories = result.scalars().all()

    return [ImportHistoryResponse.model_validate(h) for h in histories]
