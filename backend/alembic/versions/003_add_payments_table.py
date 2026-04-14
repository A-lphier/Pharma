"""
Migrazione 003 - Tabella payments per Stripe Checkout.

Aggiunge:
- Tabella payments con link a invoices
- Indici per ricerca veloce per invoice_id e stripe_session_id

Revision ID: 003_add_payments_table
Revises: 002_complete_schema
Create Date: 2026-03-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_payments_table'
down_revision: Union[str, None] = '002_complete_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('stripe_session_id', sa.String(length=255), nullable=False, unique=True),
        sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
        sa.Column('amount_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_payments_invoice_id'), 'payments', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_payments_stripe_session_id'), 'payments', ['stripe_session_id'], unique=True)
    op.create_index(op.f('ix_payments_stripe_payment_intent_id'), 'payments', ['stripe_payment_intent_id'], unique=False)
    op.create_index(op.f('ix_payments_status'), 'payments', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_payments_status'), table_name='payments')
    op.drop_index(op.f('ix_payments_stripe_payment_intent_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_stripe_session_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_invoice_id'), table_name='payments')
    op.drop_table('payments')
