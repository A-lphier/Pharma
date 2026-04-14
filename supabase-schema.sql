-- =====================================================
-- FATTURAMVP - SCHEMA TABELLE SUPABASE
-- Esegui questo codice nel SQL Editor di Supabase
-- https://supabase.com/dashboard/project/szeevxyldaxvmchsvpju/sql
-- =====================================================

-- =====================================================
-- 1. CLIENTS - Anagrafica clienti con trust score
-- =====================================================
CREATE TABLE IF NOT EXISTS public.clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    vat TEXT,
    fiscal_code TEXT,
    email TEXT,
    phone TEXT,
    pec TEXT,
    sdi TEXT,
    iban TEXT,
    address TEXT,
    trust_score INTEGER DEFAULT 60 CHECK (trust_score >= 0 AND trust_score <= 100),
    payment_pattern TEXT,
    late_reason TEXT,
    notes TEXT,
    is_new BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index per ricerche veloci
CREATE INDEX IF NOT EXISTS idx_clients_trust_score ON public.clients(trust_score);
CREATE INDEX IF NOT EXISTS idx_clients_name ON public.clients(name);

-- =====================================================
-- 2. PAYMENT_HISTORY - Storico pagamenti per cliente
-- =====================================================
CREATE TABLE IF NOT EXISTS public.payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES public.clients(id) ON DELETE CASCADE,
    invoice_id TEXT,
    invoice_amount REAL,
    invoice_date DATE,
    due_date DATE,
    paid_date DATE,
    days_late INTEGER GENERATED ALWAYS AS (CASE WHEN paid_date IS NOT NULL AND due_date IS NOT NULL THEN paid_date - due_date ELSE NULL END) STORED,
    was_on_time BOOLEAN GENERATED ALWAYS AS (CASE WHEN paid_date IS NOT NULL AND due_date IS NOT NULL THEN paid_date <= due_date ELSE NULL END) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_history_client ON public.payment_history(client_id);

-- =====================================================
-- 3. BUSINESS_CONFIG - Configurazione filosofia impresa
-- =====================================================
CREATE TABLE IF NOT EXISTS public.business_config (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    style TEXT DEFAULT 'gentile' CHECK (style IN ('gentile', 'equilibrato', 'fermo')),
    legal_threshold REAL DEFAULT 2000.00,
    new_client_score INTEGER DEFAULT 60,
    first_reminder_days INTEGER DEFAULT 7,
    warning_threshold_days INTEGER DEFAULT 15,
    escalation_days INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inserisci config di default se non esiste
INSERT INTO public.business_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- 4. IMPORT_HISTORY - Traccia importazioni CSV
-- =====================================================
CREATE TABLE IF NOT EXISTS public.import_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT,
    rows_imported INTEGER,
    clients_created INTEGER,
    invoices_created INTEGER,
    imported_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 5. LATE_REASON_FEEDBACK - Feedback motivo ritardo
-- =====================================================
CREATE TABLE IF NOT EXISTS public.late_reason_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('not_received', 'disputed', 'financial_issues', 'about_to_pay', 'wrong_invoice', 'refused')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_late_feedback_invoice ON public.late_reason_feedback(invoice_id);

-- =====================================================
-- 6. Trigger per updated_at automatico
-- =====================================================
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER clients_updated_at
    BEFORE UPDATE ON public.clients
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER business_config_updated_at
    BEFORE UPDATE ON public.business_config
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- =====================================================
-- 7. Row Level Security (RLS) - Sicurezza dati
-- =====================================================
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.late_reason_feedback ENABLE ROW LEVEL SECURITY;

-- Policy: chiunque puo leggere e scrivere (verrà implementato auth in seguito)
CREATE POLICY "Allow all" ON public.clients FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON public.payment_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON public.business_config FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON public.import_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON public.late_reason_feedback FOR ALL USING (true) WITH CHECK (true);

-- =====================================================
-- 8. Enable Realtime (opzionale per WS/SSE)
-- =====================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.clients;
ALTER PUBLICATION supabase_realtime ADD TABLE public.payment_history;

-- =====================================================
-- FATTO! ✅
-- =====================================================
