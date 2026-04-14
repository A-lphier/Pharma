"""
Client management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List

from app.db.session import get_db
from app.models.user import User
from app.models.client import Client, PaymentHistory, BusinessConfig
from app.schemas.client import (
    ClientResponse, ClientCreate, ClientUpdate, ClientListResponse,
    ClientScoreUpdate, PaymentHistoryResponse,
)
from app.core.security import get_current_active_user
from app.services.trust_score import calculate_trust_score, get_trust_score_label

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("", response_model=ClientListResponse)
async def list_clients(
    search: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    is_new: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get paginated list of clients with trust scores."""
    query = select(Client).where(Client.created_by == current_user.id)

    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Client.name.ilike(search_filter),
                Client.vat.ilike(search_filter),
                Client.email.ilike(search_filter),
            )
        )

    if min_score is not None:
        query = query.where(Client.trust_score >= min_score)

    if max_score is not None:
        query = query.where(Client.trust_score <= max_score)

    if is_new is not None:
        query = query.where(Client.is_new == is_new)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Client.trust_score.desc(), Client.name.asc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    clients = result.scalars().all()

    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in clients],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new client."""
    # Check if client with same VAT already exists
    if client_data.vat:
        existing = await db.execute(
            select(Client).where(
                Client.vat == client_data.vat,
                Client.created_by == current_user.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Client with this VAT already exists")

    # Get default score from config
    config_result = await db.execute(select(BusinessConfig).where(BusinessConfig.id == 1))
    config = config_result.scalar_one_or_none()
    default_score = config.new_client_score if config else 60

    client = Client(
        **client_data.model_dump(),
        trust_score=default_score,
        created_by=current_user.id,
    )

    db.add(client)
    await db.commit()
    await db.refresh(client)

    return client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single client by ID."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.created_by == current_user.id,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    update_data: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a client."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.created_by == current_user.id,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(client, key, value)

    from datetime import datetime
    client.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(client)

    return client


@router.patch("/{client_id}/score", response_model=ClientResponse)
async def update_client_score(
    client_id: int,
    score_data: ClientScoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a client's trust score manually."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.created_by == current_user.id,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.trust_score = score_data.trust_score
    from datetime import datetime
    client.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(client)

    return client


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a client and their payment history."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.created_by == current_user.id,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Delete payment histories first
    history_result = await db.execute(
        select(PaymentHistory).where(PaymentHistory.client_id == client_id)
    )
    histories = history_result.scalars().all()
    for history in histories:
        await db.delete(history)

    await db.delete(client)
    await db.commit()


@router.get("/{client_id}/history", response_model=List[PaymentHistoryResponse])
async def get_client_payment_history(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get payment history for a client."""
    # Verify client exists and belongs to user
    client_result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.created_by == current_user.id,
        )
    )
    if not client_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")

    result = await db.execute(
        select(PaymentHistory)
        .where(PaymentHistory.client_id == client_id)
        .order_by(PaymentHistory.invoice_date.desc())
    )
    histories = result.scalars().all()

    return [PaymentHistoryResponse.model_validate(h) for h in histories]


@router.post("/{client_id}/recalculate-score", response_model=ClientResponse)
async def recalculate_client_score(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Recalculate client trust score based on payment history."""
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.created_by == current_user.id,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    new_score = await calculate_trust_score(db, client_id)
    
    return ClientResponse.model_validate(client)
