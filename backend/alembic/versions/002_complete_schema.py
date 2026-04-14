"""
Migrazione 002 - Schema completo multi-tenant con indici compositi e RLS base.

Aggiunge:
- Tabella tenants per multiutenza
- Campo tenant_id su tutte le tabelle principali
- Indici compositi: (tenant_id, status, due_date), (tenant_id, created_at)
- Tabelle mancanti: email_logs, sdi_invoices, solleciti
- Funzioni RLS base per PostgreSQL

Revision ID: 002_complete_schema
Revises: 001_initial
Create Date: 2026-03-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_complete_schema'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === TENANTS TABLE ===
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('vat', sa.String(length=20), nullable=True, server_default=''),
        sa.Column('email', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('phone', sa.String(length=50), nullable=True, server_default=''),
        sa.Column('address', sa.String(length=500), nullable=True, server_default=''),
        sa.Column('sdi_code', sa.String(length=7), nullable=True, server_default=''),
        sa.Column('pec', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('iban', sa.String(length=34), nullable=True, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])

    # Aggiungi tenant_id agli users
    op.add_column('users', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_foreign_key('fk_users_tenant', 'users', 'tenants', ['tenant_id'], ['id'], ondelete='SET NULL')

    # Aggiungi tenant_id agli invoices
    op.add_column('invoices', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index('ix_invoices_tenant_id', 'invoices', ['tenant_id'])
    op.create_foreign_key('fk_invoices_tenant', 'invoices', 'tenants', ['tenant_id'], ['id'], ondelete='SET NULL')

    # === INDICE COMPOSITO invoices: (tenant_id, status, due_date) ===
    op.create_index(
        'ix_invoices_tenant_status_due',
        'invoices',
        ['tenant_id', 'status', 'due_date'],
        unique=False,
        postgresql_where=sa.text('tenant_id IS NOT NULL')
    )

    # === INDICE COMPOSITO invoices: (tenant_id, created_at) ===
    op.create_index(
        'ix_invoices_tenant_created',
        'invoices',
        ['tenant_id', 'created_at'],
        unique=False,
        postgresql_where=sa.text('tenant_id IS NOT NULL')
    )

    # Aggiungi tenant_id ai reminders (gia' aveva invoice_id FK)
    op.add_column('reminders', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index('ix_reminders_tenant_id', 'reminders', ['tenant_id'])

    # Aggiungi tenant_id ai clients
    op.add_column('clients', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('clients', sa.Column('created_by', sa.Integer(), nullable=True))
    op.create_index('ix_clients_tenant_id', 'clients', ['tenant_id'])
    op.create_foreign_key('fk_clients_tenant', 'clients', 'tenants', ['tenant_id'], ['id'], ondelete='SET NULL')

    # === INDICE COMPOSITO clients: (tenant_id, trust_score) ===
    op.create_index(
        'ix_clients_tenant_score',
        'clients',
        ['tenant_id', 'trust_score'],
        unique=False,
        postgresql_where=sa.text('tenant_id IS NOT NULL')
    )

    # Aggiungi tenant_id a payment_histories
    op.add_column('payment_histories', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('payment_histories', sa.Column('created_by', sa.Integer(), nullable=True))
    op.create_index('ix_payment_histories_tenant_id', 'payment_histories', ['tenant_id'])

    # Aggiungi tenant_id a business_config
    op.add_column('business_config', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index('ix_business_config_tenant_id', 'business_config', ['tenant_id'])

    # Aggiungi tenant_id a import_histories
    op.add_column('import_histories', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('import_histories', sa.Column('errors', sa.Text(), nullable=True))
    op.create_index('ix_import_histories_tenant_id', 'import_histories', ['tenant_id'])

    # Aggiungi tenant_id a late_reason_feedbacks
    op.add_column('late_reason_feedbacks', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('late_reason_feedbacks', sa.Column('created_by', sa.Integer(), nullable=True))
    op.create_index('ix_late_reason_feedbacks_tenant_id', 'late_reason_feedbacks', ['tenant_id'])

    # === EMAIL LOGS TABLE ===
    op.create_table(
        'email_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('email_type', sa.String(length=20), nullable=False, server_default='other'),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('recipient_name', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('body_preview', sa.String(length=500), nullable=True, server_default=''),
        sa.Column('template_id', sa.String(length=100), nullable=True),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('reminder_id', sa.Integer(), nullable=True),
        sa.Column('sollecito_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reminder_id'], ['reminders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_email_logs_tenant_id', 'email_logs', ['tenant_id'])
    op.create_index('ix_email_logs_email_type', 'email_logs', ['email_type'])
    op.create_index('ix_email_logs_status', 'email_logs', ['status'])
    op.create_index('ix_email_logs_created_at', 'email_logs', ['created_at'])

    # === SDI INVOICES TABLE ===
    op.create_table(
        'sdi_invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('sdi_id', sa.String(length=50), nullable=True),
        sa.Column('sdi_receipt_id', sa.String(length=100), nullable=True),
        sa.Column('xml_content', sa.Text(), nullable=True),
        sa.Column('sdi_xml_filename', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('sent_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sent_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sdi_invoices_tenant_id', 'sdi_invoices', ['tenant_id'])
    op.create_index('ix_sdi_invoices_sdi_id', 'sdi_invoices', ['sdi_id'])
    op.create_index('ix_sdi_invoices_status', 'sdi_invoices', ['status'])
    op.create_index('ix_sdi_invoices_invoice_id', 'sdi_invoices', ['invoice_id'])

    # === SOLLECITI TABLE ===
    op.create_table(
        'solleciti',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('style', sa.String(length=20), nullable=False, server_default='gentile'),
        sa.Column('tone', sa.String(length=20), nullable=False, server_default='reliable'),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('trust_score', sa.Integer(), nullable=False, server_default=sa.text('60')),
        sa.Column('days_late', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_overdue', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('generation_model', sa.String(length=50), nullable=True),
        sa.Column('sent_via', sa.String(length=20), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('sent_to', sa.String(length=255), nullable=True),
        sa.Column('cached_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('cache_ttl_hours', sa.Integer(), nullable=False, server_default=sa.text('24')),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_solleciti_tenant_id', 'solleciti', ['tenant_id'])
    op.create_index('ix_solleciti_invoice_id', 'solleciti', ['invoice_id'])
    op.create_index('ix_solleciti_client_id', 'solleciti', ['client_id'])
    op.create_index('ix_solleciti_cached_at', 'solleciti', ['cached_at'])

    # === RLS - Row Level Security (abilitato solo su PostgreSQL) ===
    # Abilita RLS su tutte le tabelle tenant-aware
    # Nota: richiede PostgreSQL 9.5+

    # Tenants RLS
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_tenants ON tenants USING (true)")

    # Users RLS
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_users ON users USING (tenant_id = current_setting('app.tenant_id', true)::integer OR current_setting('app.tenant_id', true) IS NULL)")

    # Invoices RLS
    op.execute("ALTER TABLE invoices ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_invoices ON invoices USING (tenant_id = current_setting('app.tenant_id', true)::integer OR current_setting('app.tenant_id', true) IS NULL)")

    # Clients RLS
    op.execute("ALTER TABLE clients ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_clients ON clients USING (tenant_id = current_setting('app.tenant_id', true)::integer OR current_setting('app.tenant_id', true) IS NULL)")

    # Reminders RLS
    op.execute("ALTER TABLE reminders ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_reminders ON reminders USING (tenant_id = current_setting('app.tenant_id', true)::integer OR current_setting('app.tenant_id', true) IS NULL)")

    # Email logs RLS
    op.execute("ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_email_logs ON email_logs USING (tenant_id = current_setting('app.tenant_id', true)::integer OR current_setting('app.tenant_id', true) IS NULL)")

    # SDI invoices RLS
    op.execute("ALTER TABLE sdi_invoices ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_sdi_invoices ON sdi_invoices USING (tenant_id = current_setting('app.tenant_id', true)::integer OR current_setting('app.tenant_id', true) IS NULL)")

    # Solleciti RLS
    op.execute("ALTER TABLE solleciti ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_solleciti ON solleciti USING (tenant_id = current_setting('app.tenant_id', true)::integer OR current_setting('app.tenant_id', true) IS NULL)")


def downgrade() -> None:
    # Rimuovi RLS
    op.execute("DROP POLICY IF EXISTS tenant_isolation_solleciti ON solleciti")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_sdi_invoices ON sdi_invoices")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_email_logs ON email_logs")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_reminders ON reminders")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_clients ON clients")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_invoices ON invoices")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_users ON users")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_tenants ON tenants")

    op.execute("ALTER TABLE solleciti DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sdi_invoices DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE email_logs DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE reminders DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE clients DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invoices DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")

    # Elimina tabelle
    op.drop_table('solleciti')
    op.drop_table('sdi_invoices')
    op.drop_table('email_logs')

    # Rimuovi colonne tenant_id
    op.drop_column('late_reason_feedbacks', 'created_by')
    op.drop_column('late_reason_feedbacks', 'tenant_id')
    op.drop_column('import_histories', 'errors')
    op.drop_column('import_histories', 'tenant_id')
    op.drop_column('business_config', 'tenant_id')
    op.drop_column('payment_histories', 'created_by')
    op.drop_column('payment_histories', 'tenant_id')
    op.drop_column('clients', 'created_by')
    op.drop_column('clients', 'tenant_id')
    op.drop_column('reminders', 'tenant_id')
    op.drop_column('invoices', 'tenant_id')
    op.drop_column('users', 'tenant_id')

    # Elimina indice composito
    op.drop_index('ix_invoices_tenant_status_due', table_name='invoices')
    op.drop_index('ix_invoices_tenant_created', table_name='invoices')

    op.drop_table('tenants')
