// Type definitions for API responses

export type InvoiceStatus = 'pending' | 'paid' | 'overdue' | 'cancelled'

export type EscalationStage = 'none' | 'sollecito_1' | 'sollecito_2' | 'penalty_applicata' | 'diffida' | 'stop_servizi' | 'legal_action'

export interface EscalationStatus {
  invoice_id: number
  invoice_number: string
  customer_name: string
  total_amount: number
  due_date: string
  days_overdue: number
  escalation_stage: EscalationStage
  escalation_label: string
  escalation_updated_at: string | null
  penalty_applied: number
  days_until_next_stage: number | null
  all_stages: EscalationStage[]
  stage_labels: Record<EscalationStage, string>
  stage_thresholds: Record<EscalationStage, number | null>
  is_recurring: boolean
  status: string
}

export interface User {
  id: number
  email: string
  username: string
  full_name?: string
  role: 'admin' | 'user'
  is_active: boolean
  telegram_chat_id?: string
  subscription_tier?: 'free' | 'starter' | 'professional' | 'studio'
  created_at: string
}

export interface Invoice {
  id: number
  invoice_number: string
  invoice_date: string
  due_date: string
  customer_name: string
  customer_vat: string
  customer_address: string
  customer_phone: string
  customer_pec: string
  customer_sdi: string
  customer_cf: string
  customer_email: string
  supplier_name: string
  supplier_vat: string
  supplier_address: string
  supplier_phone: string
  supplier_pec: string
  supplier_iban: string
  supplier_sdi: string
  supplier_cf: string
  supplier_email: string
  amount: number
  vat_amount: number
  total_amount: number
  status: InvoiceStatus
  description: string
  xml_filename: string
  created_at: string
  updated_at: string
  reminders: Reminder[]
  // Escalation fields
  escalation_stage?: EscalationStage
  escalation_updated_at?: string | null
  penalty_applied?: number
}

export interface Reminder {
  id: number
  invoice_id: number
  reminder_date: string
  reminder_type: string
  sent_via: string
  status: string
  message?: string
  created_at: string
}

export interface InvoiceStats {
  total: number
  paid: number
  pending: number
  overdue: number
  due_soon: number
  total_amount: number
  paid_amount: number
  pending_amount: number
  overdue_amount: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AuthToken {
  access_token: string
  refresh_token: string
  token_type: string
}

// Client types
export interface Client {
  id: number
  name: string
  vat: string
  fiscal_code: string
  email: string
  phone: string
  pec: string
  sdi: string
  iban: string
  address: string
  trust_score: number
  payment_pattern: string
  late_reason?: string
  notes: string
  is_new: boolean
  created_at: string
  updated_at: string
}

export interface ClientListResponse {
  items: Client[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface PaymentHistory {
  id: number
  client_id: number
  invoice_id?: number
  invoice_amount: number
  invoice_date: string
  due_date: string
  paid_date?: string
  days_late: number
  was_on_time: boolean
  created_at: string
}

export interface BusinessConfig {
  id: number
  style: 'gentile' | 'equilibrato' | 'fermo'
  legal_threshold: number
  new_client_score: number
  first_reminder_days: number
  warning_threshold_days: number
  escalation_days: number
  onboarding_completed: boolean
  created_at: string
  updated_at: string
}

export interface OnboardingStatus {
  status: 'not_started' | 'in_progress' | 'completed'
  current_step?: number
  total_steps: number
  answers?: Record<string, { answer: string | number }>
}

export interface OnboardingQuestion {
  step: number
  question: string
  options?: { value: string; label: string }[]
  input_type: 'single_choice' | 'multiple_choice' | 'slider'
  slider_min?: number
  slider_max?: number
  slider_default?: number
}

export interface OnboardingConfigProposal {
  style: string
  legal_threshold: number
  new_client_score: number
  first_reminder_days: number
  warning_threshold_days: number
  escalation_days: number
  reasoning: string
}

export interface ImportResult {
  success: boolean
  rows_imported: number
  clients_created: number
  clients_updated: number
  invoices_created: number
  errors: string[]
}

export interface ImportHistory {
  id: number
  filename: string
  rows_imported: number
  clients_created: number
  invoices_created: number
  imported_at: string
}

export type LateReason = 'not_received' | 'disputed' | 'financial_issues' | 'about_to_pay' | 'wrong_invoice' | 'refused'

export const LATE_REASON_OPTIONS: { value: LateReason; label: string }[] = [
  { value: 'not_received', label: 'Il cliente non ha ricevuto il sollecito' },
  { value: 'disputed', label: 'La fattura è in discussione o verifica' },
  { value: 'financial_issues', label: 'Problemi finanziari temporanei' },
  { value: 'about_to_pay', label: 'Il cliente sta per pagare' },
  { value: 'wrong_invoice', label: 'Fattura errata o errore nostro' },
  { value: 'refused', label: 'Rifiuto puro' },
]
