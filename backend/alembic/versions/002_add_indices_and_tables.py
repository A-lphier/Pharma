"""Aggiunge tabelle mancanti, indici compositi e preparazione partizionamento

Revision ID: 002_add_indices_and_tables
Revises: 001_initial
Create Date: 2026-03-27

Questa migration:
- Aggiunge la tabella clients con trust scoring
- Aggiunge le tabelle di configurazione e storico pagamenti
- Crea indici compositi per query frequenti
- Prepara la struttura per partizionamento annuale delle fatture (future)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_add_indices_and_tables'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================
    # TABella CLIENTS - Clienti con trust scoring
    # ============================================
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('vat', sa.String(length=20), nullable=True, server_default=''),
        sa.Column('fiscal_code', sa.String(length=20), nullable=True, server_default=''),
        sa.Column('email', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('phone', sa.String(length=50), nullable=True, server_default=''),
        sa.Column('pec', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('sdi', sa.String(length=10), nullable=True, server_default=''),
        sa.Column('iban', sa.String(length=34), nullable=True, server_default=''),
        sa.Column('address', sa.String(length=500), nullable=True, server_default=''),
        sa.Column('trust_score', sa.Integer(), nullable=False, server_default=sa.text('60')),
        sa.Column('payment_pattern', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('late_reason', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_new', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Indice base su name
    op.create_index('ix_clients_name', 'clients', ['name'])
    
    # Indice composito per ricerca clienti per P.IVA o CF
    op.create_index('ix_clients_vat_fiscal_code', 'clients', ['vat', 'fiscal_code'])
    
    # Indice per trust score (per ordinamento)
    op.create_index('ix_clients_trust_score', 'clients', ['trust_score'])


    # ============================================
    # TABella PAYMENT_HISTORIES - Storico pagamenti
    # ============================================
    op.create_table(
        'payment_histories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('invoice_amount', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('invoice_date', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('paid_date', sa.DateTime(), nullable=True),
        sa.Column('days_late', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('was_on_time', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Indice su client_id per storico cliente
    op.create_index('ix_payment_histories_client_id', 'payment_histories', ['client_id'])
    
    # Indice composito per calcolo puntualità medio
    op.create_index('ix_payment_histories_client_was_on_time', 'payment_histories', ['client_id', 'was_on_time'])


    # ============================================
    # TABella BUSINESS_CONFIG - Configurazione singleton
    # ============================================
    op.create_table(
        'business_config',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('style', sa.String(length=20), nullable=False, server_default='gentile'),
        sa.Column('legal_threshold', sa.Float(), nullable=False, server_default=sa.text('2000.00')),
        sa.Column('new_client_score', sa.Integer(), nullable=False, server_default=sa.text('60')),
        sa.Column('first_reminder_days', sa.Integer(), nullable=False, server_default=sa.text('7')),
        sa.Column('warning_threshold_days', sa.Integer(), nullable=False, server_default=sa.text('15')),
        sa.Column('escalation_days', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('onboarding_answers', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )


    # ============================================
    # TABella IMPORT_HISTORIES - Storico importazioni CSV
    # ============================================
    op.create_table(
        'import_histories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('rows_imported', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('clients_created', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('invoices_created', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('imported_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('imported_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['imported_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )


    # ============================================
    # TABella LATE_REASON_FEEDBACKS - Feedback pagamenti tardivi
    # ============================================
    op.create_table(
        'late_reason_feedbacks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('notes', sa.String(length=1000), nullable=True, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    op.create_index('ix_late_reason_feedbacks_invoice_id', 'late_reason_feedbacks', ['invoice_id'])


    # ============================================
    # INDICI COMPOSITI SULLE FATTURE
    # ============================================
    
    # Indice composito per scadenziario: status + due_date
    # Query: "Fatture in scadenza o scadute, ordinate per data"
    op.create_index(
        'ix_invoices_status_due_date',
        'invoices',
        ['status', 'due_date']
    )
    
    # Indice composito per ricerca cliente + data fattura
    # Query: "Fatture di un cliente in un periodo"
    op.create_index(
        'ix_invoices_customer_vat_invoice_date',
        'invoices',
        ['customer_vat', 'invoice_date']
    )
    
    # Indice per totale importi per status (aggregazioni)
    op.create_index(
        'ix_invoices_status_total_amount',
        'invoices',
        ['status', 'total_amount']
    )
    
    # Indice per ricerca full-text-like su descrizione (PostgreSQL-only - skip per MySQL)
    # op.create_index(
    #     'ix_invoices_description_trgm',
    #     'invoices',
    #     ['description'],
    #     postgresql_using='gin',
    #     postgresql_ops={'description': 'gin_trgm_ops'}
    # )


    # ============================================
    # INDICI COMPOSITI SUI REMINDERS
    # ============================================
    
    # Indice composito per reminder pendenti per data
    op.create_index(
        'ix_reminders_status_reminder_date',
        'reminders',
        ['status', 'reminder_date']
    )


    # ============================================
    # INDICI COMPOSITI SUGLI UTENTI
    # ============================================
    
    # Indice per login rapido email
    op.create_index(
        'ix_users_email_active',
        'users',
        ['email', 'is_active']
    )


    # ============================================
    # PREPARAZIONE PARTIZIONAMENTO (commentato per futuro)
    # Il partizionamento annuale richiede PostgreSQL 10+
    # Da decommentare quando serve:
    #
    # -- Creare tabella partizionata per anno (es. anno 2026)
    # CREATE TABLE invoices_2026 (
    #     CHECK (invoice_date >= DATE '2026-01-01' AND invoice_date < DATE '2027-01-01')
    # ) INHERITS (invoices);
    #
    # -- Trigger per routing automatico su insert
    # CREATE OR REPLACE FUNCTION invoices_insert_trigger()
    # RETURNS TRIGGER AS $$
    # BEGIN
    #     IF NEW.invoice_date >= DATE '2026-01-01' AND NEW.invoice_date < DATE '2027-01-01' THEN
    #         INSERT INTO invoices_2026 VALUES (NEW.*);
    #     ELSE
    #         RAISE EXCEPTION 'Invoice date out of range. Check invoices_insert_trigger()';
    #     END IF;
    #     RETURN NULL;
    # END;
    # $$ LANGUAGE plpgsql;
    #
    # CREATE TRIGGER insert_invoices_trigger
    #     BEFORE INSERT ON invoices
    #     FOR EACH ROW EXECUTE FUNCTION invoices_insert_trigger();


def downgrade() -> None:
    # Rimuovi indici compositi
    op.drop_index('ix_users_email_active', table_name='users')
    op.drop_index('ix_reminders_status_reminder_date', table_name='reminders')
    op.drop_index('ix_invoices_description_trgm', table_name='invoices')
    op.drop_index('ix_invoices_status_total_amount', table_name='invoices')
    op.drop_index('ix_invoices_customer_vat_invoice_date', table_name='invoices')
    op.drop_index('ix_invoices_status_due_date', table_name='invoices')
    
    # Rimuovi tabelle (ordine inverso per foreign keys)
    op.drop_table('late_reason_feedbacks')
    op.drop_table('import_histories')
    op.drop_table('business_config')
    op.drop_table('payment_histories')
    op.drop_table('clients')
