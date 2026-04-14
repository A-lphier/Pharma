"""Initial migration

Revision ID: 001_initial
Revises:
Create Date: 2026-01-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('telegram_chat_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])

    # Invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('customer_name', sa.String(length=255), nullable=False),
        sa.Column('customer_vat', sa.String(length=20), nullable=True, server_default=''),
        sa.Column('customer_address', sa.String(length=500), nullable=True, server_default=''),
        sa.Column('customer_phone', sa.String(length=50), nullable=True, server_default=''),
        sa.Column('customer_pec', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('customer_sdi', sa.String(length=10), nullable=True, server_default=''),
        sa.Column('customer_cf', sa.String(length=20), nullable=True, server_default=''),
        sa.Column('customer_email', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('supplier_name', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('supplier_vat', sa.String(length=20), nullable=True, server_default=''),
        sa.Column('supplier_address', sa.String(length=500), nullable=True, server_default=''),
        sa.Column('supplier_phone', sa.String(length=50), nullable=True, server_default=''),
        sa.Column('supplier_pec', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('supplier_iban', sa.String(length=34), nullable=True, server_default=''),
        sa.Column('supplier_sdi', sa.String(length=10), nullable=True, server_default=''),
        sa.Column('supplier_cf', sa.String(length=20), nullable=True, server_default=''),
        sa.Column('supplier_email', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('amount', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('vat_amount', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_amount', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('description', sa.String(length=1000), nullable=True, server_default=''),
        sa.Column('xml_filename', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('raw_xml', sa.Text(), nullable=True),
        sa.Column('payment_days', sa.Integer(), nullable=True),
        sa.Column('payment_method', sa.String(length=100), nullable=True, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('ix_invoices_due_date', 'invoices', ['due_date'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])

    # Reminders table
    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('reminder_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('reminder_type', sa.String(length=20), nullable=False, server_default='manual'),
        sa.Column('sent_via', sa.String(length=20), nullable=False, server_default='telegram'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('message', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('sent_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sent_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reminders_invoice_id', 'reminders', ['invoice_id'])


def downgrade() -> None:
    op.drop_table('reminders')
    op.drop_table('invoices')
    op.drop_table('users')
