import axios from 'axios'

// Use environment variable or default to backend port 8000
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Demo mode flag - when true, return mock data
const DEMO_MODE = true

// Mock data for demo mode - STRUCTURE MUST MATCH TypeScript types
const mockData = {
  // Invoice expects PaginatedResponse<Invoice> with .items
  invoices: {
    items: [
      { 
        id: 1, invoice_number: 'FT/2026/0001', invoice_date: '2026-03-01', due_date: '2026-03-15',
        customer_name: 'Acme Italia S.p.A.', customer_vat: 'IT12345678901', customer_address: 'Via Roma 1, Milano',
        customer_phone: '0212345678', customer_pec: 'acme@pec.it', customer_sdi: 'M5UXCR1',
        customer_cf: '12345678901', customer_email: 'contalti@acme.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 4300.00, vat_amount: 950.00, total_amount: 5250.00, status: 'paid',
        description: 'Consulenza tecnica', xml_filename: 'FT20260001.xml',
        created_at: '2026-03-01T10:00:00Z', updated_at: '2026-03-15T14:30:00Z',
        reminders: [{ id: 1, reminder_date: '2026-03-18T10:00:00Z', reminder_type: 'gentile', sent_via: 'email', status: 'sent' }],
        trust_score: 85, payment_pattern: 'Punctual',
      },
      { 
        id: 2, invoice_number: 'FT/2026/0002', invoice_date: '2026-03-10', due_date: '2026-04-01',
        customer_name: 'Digital Works S.r.l.', customer_vat: 'IT23456789012', customer_address: 'Via Torino 5, Roma',
        customer_phone: '0612345678', customer_pec: 'digital@pec.it', customer_sdi: 'T9BZCR4',
        customer_cf: '23456789012', customer_email: 'info@digitalworks.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 2581.97, vat_amount: 568.03, total_amount: 3150.00, status: 'pending',
        description: 'Sviluppo software', xml_filename: 'FT20260002.xml',
        created_at: '2026-03-10T09:00:00Z', updated_at: '2026-03-10T09:00:00Z',
        reminders: [], trust_score: 72, payment_pattern: 'Occasional delay',
      },
      { 
        id: 3, invoice_number: 'FT/2026/0003', invoice_date: '2026-02-15', due_date: '2026-02-28',
        customer_name: 'Tech Solutions S.r.l.', customer_vat: 'IT34567890123', customer_address: 'Piazza Venezia 8, Napoli',
        customer_phone: '0812345678', customer_pec: 'tech@pec.it', customer_sdi: 'K1PTAL7',
        customer_cf: '34567890123', customer_email: 'tech@techsol.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 7295.08, vat_amount: 1604.92, total_amount: 8900.00, status: 'overdue',
        description: 'Implementazione sistema', xml_filename: 'FT20260003.xml',
        created_at: '2026-02-15T11:00:00Z', updated_at: '2026-02-28T23:59:59Z',
        reminders: [
          { id: 1, reminder_date: '2026-03-07T09:00:00Z', reminder_type: 'gentile', sent_via: 'email', status: 'sent' },
          { id: 2, reminder_date: '2026-03-14T09:00:00Z', reminder_type: 'normale', sent_via: 'pec', status: 'sent' },
        ],
        trust_score: 45, payment_pattern: 'Often late',
      },
      { 
        id: 4, invoice_number: 'FT/2026/0004', invoice_date: '2026-03-20', due_date: '2026-04-10',
        customer_name: 'Global Service S.p.A.', customer_vat: 'IT45678901234', customer_address: 'Corso Vittorio 12, Torino',
        customer_phone: '0112345678', customer_pec: 'global@pec.it', customer_sdi: 'L4GMNR2',
        customer_cf: '45678901234', customer_email: 'global@globalservice.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 1721.31, vat_amount: 378.69, total_amount: 2100.00, status: 'pending',
        description: 'Assistenza tecnica', xml_filename: 'FT20260004.xml',
        created_at: '2026-03-20T15:00:00Z', updated_at: '2026-03-20T15:00:00Z',
        reminders: [], trust_score: 90, payment_pattern: 'Punctual',
      },
      { 
        id: 5, invoice_number: 'FT/2026/0005', invoice_date: '2026-01-10', due_date: '2026-01-25',
        customer_name: 'Nuovo Cliente Srl', customer_vat: 'IT56789012345', customer_address: 'Via Firenze 3, Bologna',
        customer_phone: '0512345678', customer_pec: 'nuovo@pec.it', customer_sdi: 'M2BNVR5',
        customer_cf: '56789012345', customer_email: 'info@nuovocliente.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 2950.00, vat_amount: 649.00, total_amount: 3599.00, status: 'paid',
        description: 'Formazione personale', xml_filename: 'FT20260005.xml',
        created_at: '2026-01-10T08:00:00Z', updated_at: '2026-01-25T16:00:00Z',
        reminders: [], trust_score: 60, payment_pattern: 'Occasional delay',
      },
      { 
        id: 6, invoice_number: 'FT/2026/0006', invoice_date: '2026-03-05', due_date: '2026-03-20',
        customer_name: 'Logistica Express S.p.A.', customer_vat: 'IT67890123456', customer_address: 'Via Genova 22, Verona',
        customer_phone: '0451234567', customer_pec: 'logistica@pec.it', customer_sdi: 'P7ABRQ2',
        customer_cf: '67890123456', customer_email: 'ordini@logisticaexpress.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 1350.00, vat_amount: 297.00, total_amount: 1647.00, status: 'paid',
        description: 'Trasporto merci', xml_filename: 'FT20260006.xml',
        created_at: '2026-03-05T08:00:00Z', updated_at: '2026-03-18T12:00:00Z',
        reminders: [], trust_score: 78, payment_pattern: 'Punctual',
      },
      { 
        id: 7, invoice_number: 'FT/2026/0007', invoice_date: '2026-03-15', due_date: '2026-03-29',
        customer_name: 'Marketing Pro S.r.l.', customer_vat: 'IT78901234567', customer_address: 'Corso Como 10, Milano',
        customer_phone: '0223456789', customer_pec: 'marketing@pec.it', customer_sdi: 'X2CTR88',
        customer_cf: '78901234567', customer_email: 'campagne@marketingpro.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 4200.00, vat_amount: 924.00, total_amount: 5124.00, status: 'pending',
        description: 'Campagna advertising Q1', xml_filename: 'FT20260007.xml',
        created_at: '2026-03-15T10:00:00Z', updated_at: '2026-03-15T10:00:00Z',
        reminders: [], trust_score: 82, payment_pattern: 'Punctual',
      },
      { 
        id: 8, invoice_number: 'FT/2026/0008', invoice_date: '2026-02-01', due_date: '2026-02-15',
        customer_name: 'Consulenze Riuniti S.p.A.', customer_vat: 'IT89012345678', customer_address: 'Piazza Duomo 1, Milano',
        customer_phone: '0234567890', customer_pec: 'consulenze@pec.it', customer_sdi: 'F3A5TQ9',
        customer_cf: '89012345678', customer_email: 'segreteria@consulenze.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 5800.00, vat_amount: 1276.00, total_amount: 7076.00, status: 'paid',
        description: 'Consulenza fiscale', xml_filename: 'FT20260008.xml',
        created_at: '2026-02-01T09:00:00Z', updated_at: '2026-02-14T16:00:00Z',
        reminders: [], trust_score: 91, payment_pattern: 'Punctual',
      },
      { 
        id: 9, invoice_number: 'FT/2026/0009', invoice_date: '2026-01-20', due_date: '2026-02-05',
        customer_name: 'Tech Solutions S.r.l.', customer_vat: 'IT34567890123', customer_address: 'Piazza Venezia 8, Napoli',
        customer_phone: '0812345678', customer_pec: 'tech@pec.it', customer_sdi: 'K1PTAL7',
        customer_cf: '34567890123', customer_email: 'tech@techsol.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 3100.00, vat_amount: 682.00, total_amount: 3782.00, status: 'paid',
        description: 'Manutenzione server', xml_filename: 'FT20260009.xml',
        created_at: '2026-01-20T11:00:00Z', updated_at: '2026-02-03T14:00:00Z',
        reminders: [], trust_score: 45, payment_pattern: 'Often late',
      },
      { 
        id: 10, invoice_number: 'FT/2026/0010', invoice_date: '2026-03-25', due_date: '2026-04-08',
        customer_name: 'Acme Italia S.p.A.', customer_vat: 'IT12345678901', customer_address: 'Via Roma 1, Milano',
        customer_phone: '0212345678', customer_pec: 'acme@pec.it', customer_sdi: 'M5UXCR1',
        customer_cf: '12345678901', customer_email: 'contalti@acme.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 2150.00, vat_amount: 473.00, total_amount: 2623.00, status: 'pending',
        description: 'Setup infrastruttura', xml_filename: 'FT20260010.xml',
        created_at: '2026-03-25T09:00:00Z', updated_at: '2026-03-25T09:00:00Z',
        reminders: [], trust_score: 85, payment_pattern: 'Punctual',
      },
      { 
        id: 11, invoice_number: 'FT/2025/0011', invoice_date: '2025-12-10', due_date: '2025-12-24',
        customer_name: 'Digital Works S.r.l.', customer_vat: 'IT23456789012', customer_address: 'Via Torino 5, Roma',
        customer_phone: '0612345678', customer_pec: 'digital@pec.it', customer_sdi: 'T9BZCR4',
        customer_cf: '23456789012', customer_email: 'info@digitalworks.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 1800.00, vat_amount: 396.00, total_amount: 2196.00, status: 'paid',
        description: 'Setup ambiente dev', xml_filename: 'FT20250011.xml',
        created_at: '2025-12-10T10:00:00Z', updated_at: '2025-12-22T11:00:00Z',
        reminders: [], trust_score: 72, payment_pattern: 'Occasional delay',
      },
      { 
        id: 12, invoice_number: 'FT/2025/0012', invoice_date: '2025-11-15', due_date: '2025-11-30',
        customer_name: 'Global Service S.p.A.', customer_vat: 'IT45678901234', customer_address: 'Corso Vittorio 12, Torino',
        customer_phone: '0112345678', customer_pec: 'global@pec.it', customer_sdi: 'L4GMNR2',
        customer_cf: '45678901234', customer_email: 'global@globalservice.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 6500.00, vat_amount: 1430.00, total_amount: 7930.00, status: 'paid',
        description: 'Progetto annuale', xml_filename: 'FT20250012.xml',
        created_at: '2025-11-15T09:00:00Z', updated_at: '2025-11-28T15:00:00Z',
        reminders: [], trust_score: 90, payment_pattern: 'Punctual',
      },
      { 
        id: 13, invoice_number: 'FT/2025/0013', invoice_date: '2025-10-01', due_date: '2025-10-15',
        customer_name: 'Logistica Express S.p.A.', customer_vat: 'IT67890123456', customer_address: 'Via Genova 22, Verona',
        customer_phone: '0451234567', customer_pec: 'logistica@pec.it', customer_sdi: 'P7ABRQ2',
        customer_cf: '67890123456', customer_email: 'ordini@logisticaexpress.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 980.00, vat_amount: 215.60, total_amount: 1195.60, status: 'paid',
        description: 'Spedizioni ottobre', xml_filename: 'FT20250013.xml',
        created_at: '2025-10-01T08:00:00Z', updated_at: '2025-10-12T10:00:00Z',
        reminders: [], trust_score: 78, payment_pattern: 'Punctual',
      },
      { 
        id: 14, invoice_number: 'FT/2026/0014', invoice_date: '2026-03-01', due_date: '2026-03-16',
        customer_name: 'Marketing Pro S.r.l.', customer_vat: 'IT78901234567', customer_address: 'Corso Como 10, Milano',
        customer_phone: '0223456789', customer_pec: 'marketing@pec.it', customer_sdi: 'X2CTR88',
        customer_cf: '78901234567', customer_email: 'campagne@marketingpro.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 3400.00, vat_amount: 748.00, total_amount: 4148.00, status: 'paid',
        description: 'Content marketing', xml_filename: 'FT20260014.xml',
        created_at: '2026-03-01T10:00:00Z', updated_at: '2026-03-14T16:00:00Z',
        reminders: [], trust_score: 82, payment_pattern: 'Punctual',
      },
      { 
        id: 15, invoice_number: 'FT/2026/0015', invoice_date: '2026-03-22', due_date: '2026-04-05',
        customer_name: 'Consulenze Riuniti S.p.A.', customer_vat: 'IT89012345678', customer_address: 'Piazza Duomo 1, Milano',
        customer_phone: '0234567890', customer_pec: 'consulenze@pec.it', customer_sdi: 'F3A5TQ9',
        customer_cf: '89012345678', customer_email: 'segreteria@consulenze.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 4750.00, vat_amount: 1045.00, total_amount: 5795.00, status: 'pending',
        description: 'Revisione trimestrale', xml_filename: 'FT20260015.xml',
        created_at: '2026-03-22T09:00:00Z', updated_at: '2026-03-22T09:00:00Z',
        reminders: [], trust_score: 91, payment_pattern: 'Punctual',
      },
      { 
        id: 16, invoice_number: 'FT/2025/0016', invoice_date: '2025-09-10', due_date: '2025-09-25',
        customer_name: 'Tech Solutions S.r.l.', customer_vat: 'IT34567890123', customer_address: 'Piazza Venezia 8, Napoli',
        customer_phone: '0812345678', customer_pec: 'tech@pec.it', customer_sdi: 'K1PTAL7',
        customer_cf: '34567890123', customer_email: 'tech@techsol.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 2200.00, vat_amount: 484.00, total_amount: 2684.00, status: 'paid',
        description: 'Supporto tecnico', xml_filename: 'FT20250016.xml',
        created_at: '2025-09-10T11:00:00Z', updated_at: '2025-09-23T09:00:00Z',
        reminders: [], trust_score: 45, payment_pattern: 'Often late',
      },
      { 
        id: 17, invoice_number: 'FT/2025/0017', invoice_date: '2025-08-20', due_date: '2025-09-05',
        customer_name: 'Nuovo Cliente Srl', customer_vat: 'IT56789012345', customer_address: 'Via Firenze 3, Bologna',
        customer_phone: '0512345678', customer_pec: 'nuovo@pec.it', customer_sdi: 'M2BNVR5',
        customer_cf: '56789012345', customer_email: 'info@nuovocliente.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 1100.00, vat_amount: 242.00, total_amount: 1342.00, status: 'paid',
        description: 'Prima consulenza', xml_filename: 'FT20250017.xml',
        created_at: '2025-08-20T10:00:00Z', updated_at: '2025-09-03T14:00:00Z',
        reminders: [], trust_score: 60, payment_pattern: 'Occasional delay',
      },
      { 
        id: 18, invoice_number: 'FT/2026/0018', invoice_date: '2026-02-20', due_date: '2026-03-07',
        customer_name: 'Digital Works S.r.l.', customer_vat: 'IT23456789012', customer_address: 'Via Torino 5, Roma',
        customer_phone: '0612345678', customer_pec: 'digital@pec.it', customer_sdi: 'T9BZCR4',
        customer_cf: '23456789012', customer_email: 'info@digitalworks.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 3900.00, vat_amount: 858.00, total_amount: 4758.00, status: 'paid',
        description: 'Sviluppo API', xml_filename: 'FT20260018.xml',
        created_at: '2026-02-20T09:00:00Z', updated_at: '2026-03-05T11:00:00Z',
        reminders: [], trust_score: 72, payment_pattern: 'Occasional delay',
      },
      { 
        id: 19, invoice_number: 'FT/2026/0019', invoice_date: '2026-03-18', due_date: '2026-04-02',
        customer_name: 'Acme Italia S.p.A.', customer_vat: 'IT12345678901', customer_address: 'Via Roma 1, Milano',
        customer_phone: '0212345678', customer_pec: 'acme@pec.it', customer_sdi: 'M5UXCR1',
        customer_cf: '12345678901', customer_email: 'contalti@acme.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 5100.00, vat_amount: 1122.00, total_amount: 6222.00, status: 'pending',
        description: 'Progetto redesign', xml_filename: 'FT20260019.xml',
        created_at: '2026-03-18T10:00:00Z', updated_at: '2026-03-18T10:00:00Z',
        reminders: [], trust_score: 85, payment_pattern: 'Punctual',
      },
      { 
        id: 20, invoice_number: 'FT/2026/0020', invoice_date: '2026-03-26', due_date: '2026-04-15',
        customer_name: 'Global Service S.p.A.', customer_vat: 'IT45678901234', customer_address: 'Corso Vittorio 12, Torino',
        customer_phone: '0112345678', customer_pec: 'global@pec.it', customer_sdi: 'L4GMNR2',
        customer_cf: '45678901234', customer_email: 'global@globalservice.it',
        supplier_name: 'La Mia Azienda Srl', supplier_vat: 'IT98765432109', supplier_address: 'Via Milano 10',
        supplier_phone: '0219876543', supplier_pec: 'lamia@pec.it', supplier_iban: 'IT60X0542811101000000123456',
        supplier_sdi: 'FABBH65', supplier_cf: '98765432109', supplier_email: 'info@lamia.it',
        amount: 2700.00, vat_amount: 594.00, total_amount: 3294.00, status: 'pending',
        description: 'Setup nuovo sistema', xml_filename: 'FT20260020.xml',
        created_at: '2026-03-26T09:00:00Z', updated_at: '2026-03-26T09:00:00Z',
        reminders: [], trust_score: 90, payment_pattern: 'Punctual',
      },
    ],
    total: 20,
    page: 1,
    page_size: 50,
    pages: 1
  },
  // Stats expects InvoiceStats with paid_amount, pending_amount etc.
  stats: {
    total: 20,
    paid: 12,
    pending: 7,
    overdue: 1,
    due_soon: 3,
    total_amount: 89450.00,
    paid_amount: 52350.00,
    pending_amount: 28089.00,
    overdue_amount: 8900.00,
  },
  // Clients expects ClientListResponse with .items
  clients: {
    items: [
      { id: 1, name: 'Acme Italia S.p.A.', vat: 'IT12345678901', fiscal_code: '12345678901', email: 'contalti@acme.it', phone: '0212345678', pec: 'acme@pec.it', sdi: 'M5UXCR1', iban: 'IT60X0542811101000000123456', address: 'Via Roma 1, Milano', trust_score: 85, payment_pattern: 'Punctual', notes: 'Cliente storico', is_new: false, created_at: '2025-01-15T10:00:00Z', updated_at: '2026-03-01T10:00:00Z' },
      { id: 2, name: 'Digital Works S.r.l.', vat: 'IT23456789012', fiscal_code: '23456789012', email: 'info@digitalworks.it', phone: '0612345678', pec: 'digital@pec.it', sdi: 'T9BZCR4', iban: 'IT60X0542811101000000234567', address: 'Via Torino 5, Roma', trust_score: 72, payment_pattern: 'Occasional delay', notes: '', is_new: false, created_at: '2025-03-20T14:00:00Z', updated_at: '2026-03-10T09:00:00Z' },
      { id: 3, name: 'Tech Solutions S.r.l.', vat: 'IT34567890123', fiscal_code: '34567890123', email: 'tech@techsol.it', phone: '0812345678', pec: 'tech@pec.it', sdi: 'K1PTAL7', iban: 'IT60X0542811101000000345678', address: 'Piazza Venezia 8, Napoli', trust_score: 45, payment_pattern: 'Often late', late_reason: 'financial_issues', notes: 'Situazione da monitorare', is_new: false, created_at: '2024-11-05T09:00:00Z', updated_at: '2026-02-28T23:59:59Z' },
      { id: 4, name: 'Global Service S.p.A.', vat: 'IT45678901234', fiscal_code: '45678901234', email: 'global@globalservice.it', phone: '0112345678', pec: 'global@pec.it', sdi: 'L4GMNR2', iban: 'IT60X0542811101000000456789', address: 'Corso Vittorio 12, Torino', trust_score: 90, payment_pattern: 'Punctual', notes: 'Nuovo cliente 2026', is_new: true, created_at: '2026-03-20T15:00:00Z', updated_at: '2026-03-20T15:00:00Z' },
    ],
    total: 4,
    page: 1,
    page_size: 20,
    pages: 1
  },
  business_config: {
    id: 1,
    style: 'gentile',
    legal_threshold: 2000,
    new_client_score: 60,
    first_reminder_days: 7,
    warning_threshold_days: 3,
    escalation_days: 14,
    onboarding_completed: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2026-03-26T10:00:00Z',
  }
}

// Intercept requests in demo mode
api.interceptors.request.use(async (config) => {
  if (!DEMO_MODE) return config
  
  // Return mock data based on endpoint
  // NOTE: Order matters! More specific routes must come before general ones
  const url = config.url || ''
  
  if (url.includes('/auth/login')) {
    config.adapter = () => Promise.resolve({
      data: { access_token: 'demo-token', refresh_token: 'demo-refresh' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/auth/me')) {
    config.adapter = () => Promise.resolve({
      data: { id: 1, username: 'admin', email: 'admin@demo.local', role: 'admin' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url === '/api/v1/reminders' || url.includes('/api/v1/reminders')) {
    // POST /api/v1/reminders - create reminder
    let invoiceId = 0
    let message = ''
    let sentVia = 'telegram'
    try {
      if (typeof config.data === 'string' && config.data) {
        const body = JSON.parse(config.data)
        invoiceId = body.invoice_id || 0
        message = body.message || ''
        sentVia = body.sent_via || 'telegram'
      }
    } catch { /* ignore parse errors */ }
    const invoice = mockData.invoices.items.find(i => i.id === invoiceId)
    const newReminder = {
      id: Date.now(),
      invoice_id: invoiceId,
      reminder_date: new Date().toISOString(),
      reminder_type: 'manual',
      sent_via: sentVia,
      status: 'sent',
      message: message || `Sollecito inviato per fattura ${invoice?.invoice_number || invoiceId}`,
      created_at: new Date().toISOString(),
    }
    // Also update the invoice's reminders array in mock data
    if (invoice) {
      invoice.reminders = invoice.reminders || []
      invoice.reminders.push(newReminder)
    }
    config.adapter = () => Promise.resolve({
      data: newReminder,
      status: 201,
      statusText: 'Created',
      headers: {},
      config,
    })
  } else if (url.includes('/invoices/stats')) {
    // More specific - check before /invoices
    config.adapter = () => Promise.resolve({
      data: mockData.stats,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/invoices/') && url.match(/\/invoices\/\d+$/)) {
    // Specific invoice by ID - must come BEFORE general /invoices check
    const invoiceId = parseInt(url.split('/invoices/')[1])
    const invoice = mockData.invoices.items.find(i => i.id === invoiceId)
    config.adapter = () => Promise.resolve({
      data: invoice || mockData.invoices.items[0],
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/invoices')) {
    config.adapter = () => Promise.resolve({
      data: mockData.invoices,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/clients/') && url.match(/\/clients\/\d+$/)) {
    // Specific client by ID - extract from URL
    const clientId = parseInt(url.split('/clients/')[1])
    const client = mockData.clients.items.find(c => c.id === clientId)
    config.adapter = () => Promise.resolve({
      data: client || mockData.clients.items[0],
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/clients/') && url.includes('/history')) {
    // Client payment history
    const clientId = url.split('/clients/')[1].split('/')[0]
    config.adapter = () => Promise.resolve({
      data: [
        { id: 1, client_id: parseInt(clientId), invoice_id: 1, invoice_amount: 5250.00, invoice_date: '2026-03-01', due_date: '2026-03-15', paid_date: '2026-03-14', days_late: 0, was_on_time: true, created_at: '2026-03-01T10:00:00Z' },
        { id: 2, client_id: parseInt(clientId), invoice_id: 3, invoice_amount: 8900.00, invoice_date: '2026-02-15', due_date: '2026-02-28', paid_date: '2026-03-10', days_late: 10, was_on_time: false, created_at: '2026-02-15T11:00:00Z' },
      ],
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/clients/') && url.includes('/recalculate')) {
    // Recalculate client score
    const clientId = url.split('/clients/')[1].split('/')[0]
    const client = mockData.clients.items.find(c => c.id === parseInt(clientId))
    config.adapter = () => Promise.resolve({
      data: client || mockData.clients.items[0],
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/clients')) {
    config.adapter = () => Promise.resolve({
      data: mockData.clients,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/invoices/') && url.includes('/paid')) {
    // Mark invoice as paid
    const invoiceId = parseInt(url.split('/invoices/')[1])
    const invoice = mockData.invoices.items.find(i => i.id === invoiceId)
    if (invoice) invoice.status = 'paid'
    config.adapter = () => Promise.resolve({
      data: invoice || mockData.invoices.items[0],
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.match(/\/invoices\/\d+\/sdi-status/)) {
    // GET /api/v1/invoices/:id/sdi-status
    const invoiceId = parseInt(url.split('/invoices/')[1])
    // Different SDI statuses per invoice for demo variety
    const sdiMockData: Record<number, { status: string; timestamps: Record<string, string> }> = {
      1: { status: 'accepted', timestamps: { sent: '2026-03-01T10:05:00Z', sdi_received: '2026-03-01T10:06:00Z', delivered: '2026-03-01T14:00:00Z', accepted: '2026-03-01T14:30:00Z' } },
      2: { status: 'delivered', timestamps: { sent: '2026-03-10T09:05:00Z', sdi_received: '2026-03-10T09:06:00Z', delivered: '2026-03-10T15:00:00Z' } },
      3: { status: 'rejected', timestamps: { sent: '2026-02-15T11:05:00Z', sdi_received: '2026-02-15T11:06:00Z', delivered: '2026-02-15T16:00:00Z', rejected: '2026-02-15T16:30:00Z', rejected_reason: 'Codice_destinatario non valido' } },
      4: { status: 'sdi_received', timestamps: { sent: '2026-03-20T15:05:00Z', sdi_received: '2026-03-20T15:06:00Z' } },
      5: { status: 'accepted', timestamps: { sent: '2026-01-10T08:05:00Z', sdi_received: '2026-01-10T08:06:00Z', delivered: '2026-01-10T12:00:00Z', accepted: '2026-01-10T12:30:00Z' } },
      6: { status: 'accepted', timestamps: { sent: '2026-03-05T08:05:00Z', sdi_received: '2026-03-05T08:06:00Z', delivered: '2026-03-05T13:00:00Z', accepted: '2026-03-05T13:30:00Z' } },
      7: { status: 'sent', timestamps: { sent: '2026-03-15T10:05:00Z' } },
      8: { status: 'accepted', timestamps: { sent: '2026-02-01T09:05:00Z', sdi_received: '2026-02-01T09:06:00Z', delivered: '2026-02-01T14:00:00Z', accepted: '2026-02-01T14:30:00Z' } },
      9: { status: 'accepted', timestamps: { sent: '2026-01-20T11:05:00Z', sdi_received: '2026-01-20T11:06:00Z', delivered: '2026-01-20T15:00:00Z', accepted: '2026-01-20T15:30:00Z' } },
      10: { status: 'sdi_received', timestamps: { sent: '2026-03-25T09:05:00Z', sdi_received: '2026-03-25T09:06:00Z' } },
      11: { status: 'accepted', timestamps: { sent: '2025-12-10T10:05:00Z', sdi_received: '2025-12-10T10:06:00Z', delivered: '2025-12-10T14:00:00Z', accepted: '2025-12-10T14:30:00Z' } },
      12: { status: 'accepted', timestamps: { sent: '2025-11-15T09:05:00Z', sdi_received: '2025-11-15T09:06:00Z', delivered: '2025-11-15T13:00:00Z', accepted: '2025-11-15T13:30:00Z' } },
      13: { status: 'accepted', timestamps: { sent: '2025-10-01T08:05:00Z', sdi_received: '2025-10-01T08:06:00Z', delivered: '2025-10-01T12:00:00Z', accepted: '2025-10-01T12:30:00Z' } },
      14: { status: 'accepted', timestamps: { sent: '2026-03-01T10:05:00Z', sdi_received: '2026-03-01T10:06:00Z', delivered: '2026-03-01T14:00:00Z', accepted: '2026-03-01T14:30:00Z' } },
      15: { status: 'delivered', timestamps: { sent: '2026-03-22T09:05:00Z', sdi_received: '2026-03-22T09:06:00Z', delivered: '2026-03-22T13:00:00Z' } },
      16: { status: 'accepted', timestamps: { sent: '2025-09-10T11:05:00Z', sdi_received: '2025-09-10T11:06:00Z', delivered: '2025-09-10T15:00:00Z', accepted: '2025-09-10T15:30:00Z' } },
      17: { status: 'accepted', timestamps: { sent: '2025-08-20T10:05:00Z', sdi_received: '2025-08-20T10:06:00Z', delivered: '2025-08-20T14:00:00Z', accepted: '2025-08-20T14:30:00Z' } },
      18: { status: 'accepted', timestamps: { sent: '2026-02-20T09:05:00Z', sdi_received: '2026-02-20T09:06:00Z', delivered: '2026-02-20T13:00:00Z', accepted: '2026-02-20T13:30:00Z' } },
      19: { status: 'sdi_received', timestamps: { sent: '2026-03-18T10:05:00Z', sdi_received: '2026-03-18T10:06:00Z' } },
      20: { status: 'sent', timestamps: { sent: '2026-03-26T09:05:00Z' } },
    }
    const sdiInfo = sdiMockData[invoiceId] || sdiMockData[1]
    config.adapter = () => Promise.resolve({
      data: { status: sdiInfo.status, timestamps: sdiInfo.timestamps },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/invoices/') && url.includes('/remind')) {
    // Send reminder - read tone and channel from request body
    const invoiceId = parseInt(url.split('/invoices/')[1])
    const invoice = mockData.invoices.items.find(i => i.id === invoiceId)
    let tone = 'normale'
    let channel = 'email'
    let message = ''
    // config.data is the raw JSON string body
    try {
      if (typeof config.data === 'string' && config.data) {
        const body = JSON.parse(config.data)
        tone = body.tone || 'normale'
        channel = body.channel || 'email'
        message = body.message || ''
      }
    } catch { /* ignore parse errors */ }
    const sentViaMap: Record<string, string> = {
      email: 'email',
      pec: 'pec',
      telegram: 'telegram',
      sms: 'sms',
    }
    const reminderTypeMap: Record<string, string> = {
      gentile: 'gentile',
      normale: 'normale',
      fermo: 'fermo',
    }
    const newReminder = {
      id: Date.now(),
      invoice_id: invoiceId,
      reminder_date: new Date().toISOString(),
      reminder_type: reminderTypeMap[tone] || 'normale',
      sent_via: sentViaMap[channel] || 'email',
      status: 'sent',
      message: message || `Sollecito inviato per fattura ${invoice?.invoice_number || invoiceId}`,
      created_at: new Date().toISOString(),
    }
    config.adapter = () => Promise.resolve({
      data: { success: true, reminder: newReminder },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/invoices/') && url.includes('/calcolo-interessi')) {
    // Interest calculation
    const invoiceId = parseInt(url.split('/invoices/')[1].split('/')[0])
    const invoice = mockData.invoices.items.find(i => i.id === invoiceId)
    const today = new Date()
    const dueDate = invoice ? new Date(invoice.due_date) : today
    const giorniRitardo = Math.max(0, Math.floor((today.getTime() - dueDate.getTime()) / (1000 * 60 * 60 * 24)))
    const tassoBase = 0.12
    const penaltyPct = 0.01
    const penaltyGiorni = 30
    const importo = invoice?.total_amount || 1000
    const interessi = giorniRitardo > 0 ? (tassoBase / 365) * giorniRitardo * importo : 0
    const penalty = giorniRitardo > 60 ? importo * Math.floor((giorniRitardo - 60) / penaltyGiorni) * penaltyPct : 0
    config.adapter = () => Promise.resolve({
      data: {
        importo_originale: importo,
        interessi: Math.round(interessi * 100) / 100,
        penalty: Math.round(penalty * 100) / 100,
        totale: Math.round((importo + interessi + penalty) * 100) / 100,
        giorni_ritardo: giorniRitardo,
        tasso_applicato: tassoBase,
        data_pagamento: today.toISOString().split('T')[0],
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/invoices/bulk/pay')) {
    // Bulk mark as paid
    config.adapter = () => Promise.resolve({
      data: { success: true, updated: 5 },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/config')) {
    config.adapter = () => Promise.resolve({
      data: mockData.business_config,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/import/history')) {
    config.adapter = () => Promise.resolve({
      data: [
        { id: 1, filename: 'storico_2025.csv', rows_imported: 45, clients_created: 12, invoices_created: 33, imported_at: '2026-03-20T14:30:00Z' },
        { id: 2, filename: 'anagrafica_clienti.csv', rows_imported: 8, clients_created: 3, invoices_created: 5, imported_at: '2026-03-15T10:00:00Z' },
      ],
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/import/csv')) {
    config.adapter = () => Promise.resolve({
      data: { success: true, rows_imported: 10, clients_created: 2, clients_updated: 3, invoices_created: 5, errors: [] },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/onboarding')) {
    config.adapter = () => Promise.resolve({
      data: { status: 'completed' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/payments/create-checkout')) {
    // POST /api/v1/payments/create-checkout
    let invoiceId = 0
    try {
      if (typeof config.data === 'string' && config.data) {
        const body = JSON.parse(config.data)
        invoiceId = body.invoice_id || 0
      }
    } catch { /* ignore */ }
    const mockSessionId = `cs_mock_${Date.now()}_${invoiceId}`
    config.adapter = () => Promise.resolve({
      data: {
        checkout_url: `https://checkout.stripe.com/mock/${mockSessionId}#pay`,
        session_id: mockSessionId,
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.match(/\/payments\/invoice\/\d+\/status/)) {
    // GET /api/v1/payments/invoice/:invoice_id/status
    const invoiceId = parseInt(url.split('/invoice/')[1].split('/')[0])
    const invoice = mockData.invoices.items.find(i => i.id === invoiceId)
    config.adapter = () => Promise.resolve({
      data: {
        invoice_id: invoiceId,
        status: invoice?.status === 'paid' ? 'completed' : 'pending',
        paid_at: invoice?.status === 'paid' ? invoice.updated_at : null,
        amount_cents: Math.round((invoice?.total_amount || 0) * 100),
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/admin/collection-summary')) {
    // GET /api/v1/admin/collection-summary
    const overdueInvoices = mockData.invoices.items.filter(i => i.status === 'overdue')
    const totalInsoluto = overdueInvoices.reduce((sum, i) => sum + i.total_amount, 0)
    const avgDaysOverdue = 21
    const stages = [
      { stage: 'stage_1', stage_label: '1° Sollecito', stage_color: '#22c55e', invoice_count: 2, total_amount: 5200 },
      { stage: 'stage_2', stage_label: '2° Sollecito', stage_color: '#eab308', invoice_count: 1, total_amount: 3150 },
      { stage: 'stage_3', stage_label: 'Diffida', stage_color: '#f97316', invoice_count: 1, total_amount: 8900 },
      { stage: 'stage_4', stage_label: 'Presidio Legale', stage_color: '#ef4444', invoice_count: 0, total_amount: 0 },
      { stage: 'stage_5', stage_label: 'Recupero Legale', stage_color: '#991b1b', invoice_count: 0, total_amount: 0 },
    ]
    const topRiskClients = [
      { client_id: 3, client_name: 'Tech Solutions S.r.l.', trust_score: 45, total_insoluto: 8900, overdue_invoice_count: 1, days_avg_overdue: 28 },
      { client_id: 2, client_name: 'Digital Works S.r.l.', trust_score: 72, total_insoluto: 3150, overdue_invoice_count: 1, days_avg_overdue: 12 },
    ]
    config.adapter = () => Promise.resolve({
      data: {
        total_insoluto: totalInsoluto,
        total_overdue_count: overdueInvoices.length,
        total_overdue_amount: totalInsoluto,
        risk_client_count: 2,
        avg_days_overdue: avgDaysOverdue,
        stages,
        top_risk_clients: topRiskClients,
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/admin/collection-invoices')) {
    // GET /api/v1/admin/collection-invoices
    const overdueInvoices = mockData.invoices.items.filter(i => i.status === 'overdue')
    const items = overdueInvoices.map(inv => ({
      id: inv.id,
      invoice_number: inv.invoice_number,
      customer_name: inv.customer_name,
      total_amount: inv.total_amount,
      due_date: inv.due_date,
      status: inv.status,
      days_overdue: 28,
      escalation_stage: 'stage_3',
      escalation_label: 'Diffida',
      escalation_color: '#f97316',
      trust_score: inv.trust_score || 50,
      reminder_count: inv.reminders?.length || 0,
    }))
    config.adapter = () => Promise.resolve({
      data: { items, total: items.length, page: 1, page_size: 50, pages: 1 },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/admin/actions/available')) {
    // GET /api/v1/admin/actions/available?invoice_id=X
    let invoiceId = 0
    try {
      const u = new URL(`http://localhost${url}`)
      invoiceId = parseInt(u.searchParams.get('invoice_id') || '0')
    } catch { invoiceId = 3 }
    const invoice = mockData.invoices.items.find(i => i.id === invoiceId)
    const daysOverdue = invoice?.status === 'overdue' ? 28 : 5
    const stage = daysOverdue > 15 ? 'stage_3' : daysOverdue > 7 ? 'stage_2' : 'stage_1'
    const stageLabels: Record<string, {label: string; color: string}> = {
      stage_1: { label: '1° Sollecito', color: '#22c55e' },
      stage_2: { label: '2° Sollecito', color: '#eab308' },
      stage_3: { label: 'Diffida', color: '#f97316' },
    }
    const cfg = stageLabels[stage] || stageLabels.stage_1
    config.adapter = () => Promise.resolve({
      data: {
        invoice_id: invoiceId,
        escalation_stage: stage,
        escalation_label: cfg.label,
        escalation_color: cfg.color,
        days_overdue: daysOverdue,
        actions: [
          { action: 'send_reminder_gentle', action_label: '1° Sollecito Gentile', action_description: 'Email di sollecito cortese e professionale', available: true },
          { action: 'send_reminder_normale', action_label: '2° Sollecito Normale', action_description: 'Sollecito con tono più deciso', available: daysOverdue > 7, reason: daysOverdue <= 7 ? 'Non ancora necessario' : null },
          { action: 'apply_penalty', action_label: ' Applica Penale', action_description: 'Applicare interessi di mora (D.Lgs 231/2002)', available: daysOverdue > 15, reason: daysOverdue <= 15 ? 'Superata soglia 60gg richiesta' : null },
          { action: 'send_diffida', action_label: 'Diffida', action_description: 'Invio diffida formale con termini di pagamento', available: daysOverdue > 15, reason: daysOverdue <= 15 ? 'Non ancora in questa fase' : null },
          { action: 'mark_paid', action_label: 'Segna come Pagata', action_description: 'Registra il pagamento ricevuto', available: true },
        ],
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/admin/actions/execute')) {
    // POST /api/v1/admin/actions/execute
    let action = 'unknown'
    let invoiceId = 0
    try {
      if (typeof config.data === 'string' && config.data) {
        const body = JSON.parse(config.data)
        action = body.action || 'unknown'
        invoiceId = body.invoice_id || 0
      }
    } catch { /* ignore */ }
    const invoice = mockData.invoices.items.find(i => i.id === invoiceId)
    const messages: Record<string, string> = {
      send_reminder_gentle: `gentile sollecito inviato per ${invoice?.invoice_number || invoiceId}`,
      send_reminder_normale: `normale sollecito inviato per ${invoice?.invoice_number || invoiceId}`,
      send_diffida: `Diffida inviata per ${invoice?.invoice_number || invoiceId}`,
      apply_penalty: `Penale calcolata: 89.00€ (1 periodo, 1% ogni 30gg oltre 60)`,
      mark_paid: `Fattura ${invoice?.invoice_number || invoiceId} segnata come pagata`,
    }
    if (action === 'mark_paid' && invoice) invoice.status = 'paid'
    config.adapter = () => Promise.resolve({
      data: { success: true, message: messages[action] || `Azione ${action} eseguita`, action, invoice_id: invoiceId },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/billing/status')) {
    config.adapter = () => Promise.resolve({
      data: {
        subscription_tier: 'professional',
        status: 'active',
        current_period_end: '2026-04-29',
        next_billing_date: '2026-04-29',
        amount_due: 3900,
        currency: 'EUR',
        payment_method: 'card',
        invoices_count: 14,
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/billing/checkout')) {
    config.adapter = () => Promise.resolve({
      data: { checkout_url: '/billing?success=true', session_id: 'cs_demo_' + Date.now() },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/billing/portal')) {
    config.adapter = () => Promise.resolve({
      data: { portal_url: '/billing?portal=true', session_id: 'pb_demo_' + Date.now() },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/billing/cancel')) {
    config.adapter = () => Promise.resolve({
      data: { success: true, message: 'Abbonamento cancellato. Accesso fino a fine periodo.' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/fiscal-calendar')) {
    const now = new Date()
    const year = now.getFullYear()
    const events = [
      { id: 'apr-1', date: `${year}-04-16`, label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a marzo 2026', tipo: 'IVA', actionable: true },
      { id: 'apr-2', date: `${year}-04-20`, label: 'Intrastat mensile', description: 'Elenco Intrastat — mensile marzo', tipo: 'IVA', actionable: false },
      { id: 'apr-3', date: `${year}-04-30`, label: 'Esterometro', description: 'Comunicazione operazioni con l\'estero — dati trim. 1', tipo: 'COMUNICAZIONE', actionable: true },
      { id: 'mag-1', date: `${year}-05-16`, label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a aprile 2026', tipo: 'IVA', actionable: true },
      { id: 'giu-1', date: `${year}-06-16`, label: '1° Acconto IRPEF/IRES/IRAP', description: 'Primo acconto — rateizzazione possibile (40% + 20% + 20%)', tipo: 'ACCONTO', actionable: true },
      { id: 'giu-2', date: `${year}-06-30`, label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a maggio 2026', tipo: 'IVA', actionable: true },
      { id: 'lug-1', date: `${year}-07-16`, label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a giugno 2026', tipo: 'IVA', actionable: true },
      { id: 'lug-2', date: `${year}-07-31`, label: 'Comunicazione Liquidazioni IVA', description: 'Comunicazione liquidazioni IVA — 2° trim. 2026', tipo: 'IVA', actionable: true },
      { id: 'set-1', date: `${year}-09-16`, label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a agosto 2026', tipo: 'IVA', actionable: true },
      { id: 'nov-1', date: `${year}-11-16`, label: '2° Acconto IRPEF/IRES/IRAP', description: 'Secondo acconto — saldo + acconto', tipo: 'ACCONTO', actionable: true },
      { id: 'dic-1', date: `${year}-12-16`, label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a novembre 2026', tipo: 'IVA', actionable: true },
    ]
    config.adapter = () => Promise.resolve({
      data: { events },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/analytics/dso')) {
    // Mock DSO analytics endpoint
    const dsoData = {
      current_dso: 48,
      previous_dso: 52,
      trend: -4,
      forecast_30: 18500,
      forecast_60: 14200,
      forecast_90: 8200,
      cash_gap_date: '2026-04-16',
      cash_gap_amount: -6800,
      top_delayers: [
        { name: 'Tech Solutions S.r.l.', amount: 8900, dso: 28 },
        { name: 'Digital Works S.r.l.', amount: 3150, dso: 12 },
        { name: 'Marketing Pro S.r.l.', amount: 5124, dso: 5 },
      ],
    }
    config.adapter = () => Promise.resolve({
      data: dsoData,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/deductibility/analyze')) {
    const desc = typeof config.data === 'string' ? JSON.parse(config.data || '{}').description || '' : (config.data?.description || '')
    const rules: Array<{ kw: string[]; status: string; iva: number; irpef: number; cat: string; norma: string; warn?: string }> = [
      { kw: ['autovettura', 'automobile', 'veicolo'], status: 'partial', iva: 40, irpef: 20, cat: 'Autovettura', norma: 'Art. 164 TUIR', warn: 'Deduzione limitata al 20%' },
      { kw: ['consulenza', 'parere', 'avvocato'], status: 'full', iva: 100, irpef: 100, cat: 'Consulenza professionale', norma: 'Art. 54 TUIR' },
      { kw: ['software', 'licenza', 'saas', 'cloud'], status: 'full', iva: 100, irpef: 100, cat: 'Digitale/Software', norma: 'Art. 54 TUIR' },
      { kw: ['hotel', 'albergo', 'ristorante', 'vitto'], status: 'partial', iva: 100, irpef: 75, cat: 'Vitto/Alloggio', norma: 'Art. 95 c.3 TUIR', warn: 'Deduzione vitto 75%' },
      { kw: ['smartphone', 'cellulare', 'telefono'], status: 'partial', iva: 50, irpef: 50, cat: 'Telefonia', norma: 'Art. 54-bis TUIR' },
      { kw: ['omaggio', 'regalo', 'gratis'], status: 'none', iva: 0, irpef: 0, cat: 'Omaggi', norma: 'Art. 108 TUIR', warn: 'Nessuna deduzione su omaggi' },
      { kw: ['materiale edile', 'cemento', 'cantieri'], status: 'full', iva: 100, irpef: 100, cat: 'Immobili/Cantieri', norma: 'Art. 17 c.6 DPR 633/72', warn: 'Reverse charge edilizia' },
    ]
    const lower = desc.toLowerCase()
    const match = rules.find(r => r.kw.some(k => lower.includes(k)))
    if (match) {
      config.adapter = () => Promise.resolve({
        data: {
          status: match.status,
          ivaDetraibile: match.iva > 0,
          ivaDetraibilePct: match.iva,
          irpefDeduzionePct: match.irpef,
          categoria: match.cat,
          warning: match.warn || null,
          norma: match.norma,
          message: match.status === 'full' ? `Completamente deducibile — ${match.cat}` : `Parzialmente deducibile: IRPEF ${match.irpef}% · IVA ${match.iva}% — ${match.cat}`,
        },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      })
    } else {
      config.adapter = () => Promise.resolve({
        data: {
          status: 'unknown',
          ivaDetraibile: true,
          ivaDetraibilePct: 100,
          irpefDeduzionePct: 100,
          categoria: 'Generico',
          warning: null,
          norma: null,
          message: 'Voce non classificata — verifica con il tuo commercialista',
        },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      })
    }
  } else if (url.match(/\/solicitor\/whatsapp\/history\/\d+/)) {
    // GET /api/v1/solicitor/whatsapp/history/:invoiceId
    const invoiceId = parseInt(url.split('/history/')[1])
    config.adapter = () => Promise.resolve({
      data: {
        messages: [
          { id: `wa_demo_${invoiceId}_1`, text: `Gentile cliente, ricordiamo che la fattura FT/2026/00${invoiceId} di € 1.500,00 è in scadenza il 15/04/2026.`, sent_at: new Date(Date.now() - 86400000 * 2).toISOString(), tone: 'gentile', status: 'sent', isOutgoing: true },
          { id: `wa_demo_${invoiceId}_2`, text: `Gentile cliente, la fattura FT/2026/00${invoiceId} di € 1.500,00 è scaduta il 15/04/2026. Vi chiediamo di procedere al pagamento.`, sent_at: new Date(Date.now() - 86400000).toISOString(), tone: 'equilibrato', status: 'sent', isOutgoing: true },
        ].filter((_, i) => i < 3),
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/solicitor/whatsapp/send') && config.method === 'post') {
    // POST /api/v1/solicitor/whatsapp/send
    let invoiceId = 0
    let message = ''
    try {
      if (typeof config.data === 'string' && config.data) {
        const body = JSON.parse(config.data)
        invoiceId = body.invoice_id || 0
        message = body.message || ''
      }
    } catch { /* ignore */ }
    const invoice = mockData.invoices.items.find(i => i.id === invoiceId)
    config.adapter = () => Promise.resolve({
      data: {
        success: true,
        message_id: `wa_${Date.now()}_${invoiceId}`,
        sent_at: new Date().toISOString(),
        preview: message || `Sollecito WhatsApp inviato per ${invoice?.invoice_number || invoiceId}`,
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  } else if (url.includes('/recoverer/generate-plan')) {
    const mockInvoices = [
      { id: 3, customer_name: 'Tech Solutions S.r.l.', total_amount: 8900 },
      { id: 5, customer_name: 'Freelance Verdi', total_amount: 1500 },
      { id: 8, customer_name: 'Consulenze Riuniti S.p.A.', total_amount: 6200 },
    ]
    const body = typeof config.data === 'string' ? JSON.parse(config.data || '{}') : (config.data || {})
    const inv = mockInvoices.find((i: {id:number}) => i.id === body.invoiceId) || mockInvoices[0]
    const n = Math.min(Math.ceil(inv.total_amount / 1500), 6)
    const rate = Math.round(inv.total_amount / n)
    const plan = Array.from({ length: n }, (_: unknown, i: number) => ({
      amount: i === n - 1 ? inv.total_amount - rate * (n - 1) : rate,
      due_date: new Date(Date.now() + (i + 1) * 7 * 24 * 60 * 60 * 1000).toLocaleDateString('it-IT'),
    }))
    config.adapter = () => Promise.resolve({
      data: {
        installments: plan,
        whatsapp_text: `Gentile ${inv.customer_name},\n\npropongo rateizzazione:\n${plan.map((r: {amount:number,due_date:string}, i: number) => `${i+1}. €${r.amount.toLocaleString('it')} entro il ${r.due_date}`).join('\n')}`,
        message_preview: `${n} rate da €${rate.toLocaleString('it')}`,
      },
      status: 200, statusText: 'OK', headers: {}, config,
    })
  } else if (url.includes('/recoverer/send-proposal')) {
    config.adapter = () => Promise.resolve({
      data: { success: true, sent_at: new Date().toISOString(), channel: 'whatsapp' },
      status: 200, statusText: 'OK', headers: {}, config,
    })
  } else if (url.includes('/recoverer/voice-call')) {
    config.adapter = () => Promise.resolve({
      data: {
        call_id: 'call_' + Date.now(), duration_seconds: 45,
        transcript: [
          { speaker: 'AI', text: 'Buongiorno, la chiamo da La Mia Azienda.' },
          { speaker: 'Cliente', text: 'Sì, mi dica.' },
          { speaker: 'AI', text: 'Propongo 3 rate.' },
          { speaker: 'Cliente', text: 'Va bene, grazie.' },
        ],
        outcome: 'proposal_sent',
      },
      status: 200, statusText: 'OK', headers: {}, config,
    })
  } else if (url.includes('/recoverer/escalate')) {
    config.adapter = () => Promise.resolve({
      data: { ticket_id: 'ESC-' + Date.now(), estimated_cost: 425, documents_ready: true },
      status: 200, statusText: 'OK', headers: {}, config,
    })
  }
  // @ts-ignore — DEMO_MODE interceptor structure
  return config
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('fatturamvp-auth')
    if (token) {
      try {
        const auth = JSON.parse(token)
        if (auth.accessToken) {
          config.headers.Authorization = `Bearer ${auth.accessToken}`
        }
      } catch {
        // Ignore parse errors
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const token = localStorage.getItem('fatturamvp-auth')
        if (token) {
          const auth = JSON.parse(token)
          const response = await axios.post(`${API_BASE}/api/v1/auth/refresh`, {
            refresh_token: auth.refreshToken,
          })

          const newAuth = {
            ...auth,
            accessToken: response.data.access_token,
            refreshToken: response.data.refresh_token,
            isAuthenticated: true,
          }

          localStorage.setItem('fatturamvp-auth', JSON.stringify(newAuth))
          originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`
          return api(originalRequest)
        }
      } catch {
        localStorage.removeItem('fatturamvp-auth')
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)
