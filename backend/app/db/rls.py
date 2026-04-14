"""
Utility per Row Level Security e contesto multi-tenant.

Fornisce:
- TenantContext: context variable per tenant_id corrente
- get_current_tenant_id(): recupera tenant_id dal contesto
- set_tenant_context(): imposta il tenant per la sessione corrente
- rls_query_filter(): applica filtro RLS a query SQLAlchemy
"""
from contextvars import ContextVar
from typing import Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import logging

logger = logging.getLogger(__name__)

# Context variable per tenant_id
_tenant_context: ContextVar[Optional[int]] = ContextVar('tenant_id', default=None)


def get_current_tenant_id() -> Optional[int]:
    """Restituisce il tenant_id del contesto corrente."""
    return _tenant_context.get()


def set_tenant_context(tenant_id: Optional[int]) -> None:
    """Imposta il tenant_id nel contesto della sessione corrente."""
    _tenant_context.set(tenant_id)


def clear_tenant_context() -> None:
    """Pulisce il contesto tenant."""
    _tenant_context.set(None)


async def set_postgres_rls_tenant(session: AsyncSession, tenant_id: Optional[int]) -> None:
    """
    Imposta il parametro RLS di PostgreSQL per la sessione.

    In PostgreSQL con RLS abilitato, ogni sessione deve impostare
    il parametro app.tenant_id per filtrare le righe.
    """
    if tenant_id is not None:
        await session.execute(
            text("SET LOCAL app.tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        )
    else:
        await session.execute(
            text("SET LOCAL app.tenant_id = NULL")
        )


class TenantContext:
    """
    Context manager per gestire il tenant_id delle query.

    Usage:
        async with TenantContext(session, tenant_id):
            result = await db.execute(select(Invoice)...)
    """

    def __init__(self, session: AsyncSession, tenant_id: Optional[int]):
        self.session = session
        self.tenant_id = tenant_id
        self._token = None

    async def __aenter__(self) -> "TenantContext":
        self._token = _tenant_context.set(self.tenant_id)
        if self.tenant_id is not None:
            await set_postgres_rls_tenant(self.session, self.tenant_id)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        _tenant_context.reset(self._token)
        # Resetta il parametro PostgreSQL
        try:
            await self.session.execute(text("RESET app.tenant_id"))
        except Exception as e:
            logger.warning(f"Errore reset RLS: {e}")


def rls_filter(model_class, tenant_id: Optional[int]):
    """
    Restituisce una condizione di filtro per query RLS.

    Usage:
        query = select(Invoice).where(rls_filter(Invoice, tenant_id))
    """
    from sqlalchemy import and_, Column

    if tenant_id is None:
        return True  # Admin vede tutto

    conditions = []
    for column in model_class.__table__.columns:
        if column.name == 'tenant_id':
            conditions.append(column == tenant_id)

    if conditions:
        return and_(*conditions)
    return True


class TenantAwareMixin:
    """
    Mixin per modelli che supportano automaticamente il filtro tenant.

    Usage:
        class Invoice(TenantAwareMixin, SQLModel):
            ...
    """

    @classmethod
    def get_tenant_filter(cls, tenant_id: Optional[int]):
        """Restituisce il filtro tenant per la classe."""
        return rls_filter(cls, tenant_id)


# === Sync RLS per Celery tasks (worker sincroni) ===
import threading

_tenant_sync_context = threading.local()


def set_tenant_context_sync(tenant_id: Optional[int]) -> None:
    """Versione sincrona di set_tenant_context per Celery workers."""
    _tenant_sync_context.tenant_id = tenant_id


def get_current_tenant_id_sync() -> Optional[int]:
    """Versione sincrona di get_current_tenant_id per Celery workers."""
    return getattr(_tenant_sync_context, 'tenant_id', None)
