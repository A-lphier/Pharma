import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '../components/ui'
import {
  ArrowLeft, Check, Bell, Printer, Building, User, Phone, Mail,
  Send, X, AlertTriangle, MessageSquare, FileText, Download, Copy, CheckCheck,
  Calculator
} from 'lucide-react'
import { format, differenceInDays } from 'date-fns'
import { it } from 'date-fns/locale'
import { TrustScoreBadge } from '../components/TrustScoreBadge'
import { DeductibilityBadge } from '../components/DeductibilityBadge'
import { SDITimeline } from '../components/SDITimeline'

interface Invoice {
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
  amount: number
  vat_amount: number
  total_amount: number
  status: string
  description: string
  xml_filename?: string
  trust_score?: number
  payment_pattern?: string
  reminders: Array<{
    id: number
    reminder_date: string
    reminder_type: string
    sent_via: string
    status: string
    message?: string
  }>
}

interface CalcoloInteressiResponse {
  importo_originale: number
  interessi: number
  penalty: number
  totale: number
  giorni_ritardo: number
  tasso_applicato: number
  data_pagamento: string
}

interface SDIStatusResponse {
  status: 'draft' | 'sent' | 'sdi_received' | 'delivered' | 'accepted' | 'rejected'
  timestamps: {
    sent?: string
    sdi_received?: string
    delivered?: string
    accepted?: string
    rejected?: string
    rejected_reason?: string
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

type Tone = 'gentile' | 'normale' | 'fermo'
type Channel = 'email' | 'pec' | 'telegram' | 'sms'

const TONE_LABELS: Record<Tone, string> = {
  gentile: '🕊️ Gentile',
  normale: '📋 Normale',
  fermo: '⚡ Fermo',
}

const CHANNEL_LABELS: Record<Channel, string> = {
  email: '📧 Email',
  pec: '📨 PEC',
  telegram: '💬 Telegram',
  sms: '📱 SMS',
}

function buildReminderMessage(
  invoice: Invoice,
  tone: Tone,
  daysLate: number,
  _isOverdue: boolean,
  formattedDate: string
): string {
  const amount = new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: 'EUR',
  }).format(invoice.total_amount)

  const toneKey =
    daysLate > 30 ? 'inesistente' :
    daysLate > 14 ? 'problematico' :
    daysLate > 0 ? 'verificare' :
    daysLate >= -7 ? 'affidabile' : 'eccellente'

  const msgs: Record<Tone, Record<string, string>> = {
    gentile: {
      eccellente: `Ciao ${invoice.customer_name}, ti ricordiamo la fattura ${invoice.invoice_number} di ${amount} in scadenza il ${formattedDate}. Grazie!`,
      affidabile: `Gentile ${invoice.customer_name}, ti ricordiamo che la fattura ${invoice.invoice_number} di ${amount} scade il ${formattedDate}. Grazie per l'attenzione.`,
      verificare: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} scade il ${formattedDate}. Potrebbe essere sfuggita? Grazie.`,
      problematico: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di procedere al pagamento entro 7 giorni.`,
      inesistente: `La fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di regolare entro 5 giorni. In assenza, procederemo legalmente.`,
    },
    normale: {
      eccellente: `Gentile ${invoice.customer_name}, desideriamo ricordare che la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. La ringraziamo per l'attenzione.`,
      affidabile: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. La preghiamo di verificare la sua posizione.`,
      verificare: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. Le chiediamo di cortesemente verificare.`,
      problematico: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di regolare entro 7 giorni. In caso contrario, saremo costretti a procedere.`,
      inesistente: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di regolare entro 5 giorni. In assenza, saremo costretti a valutare azioni legali.`,
    },
    fermo: {
      eccellente: `La informiamo che la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. La preghiamo di provvedere.`,
      affidabile: `La fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. Le chiediamo di verificare e regolare.`,
      verificare: `La fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. Le chiediamo di procedere al pagamento entro la scadenza.`,
      problematico: `La fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Senza pagamento entro 7 giorni, saranno avviate le procedure di recupero crediti.`,
      inesistente: `La fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Senza pagamento entro 5 giorni, saremo costretti a procedere legalmente.`,
    },
  }

  return msgs[tone][toneKey]
}

// ─── Modal ────────────────────────────────────────────────────────────────────

function SollecitoModal({
  invoice,
  open,
  onClose,
  onSent,
}: {
  invoice: Invoice
  open: boolean
  onClose: () => void
  onSent: () => void
}) {
  const [tone, setTone] = useState<Tone>('normale')
  const [channel, setChannel] = useState<Channel>('email')
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)

  const dueDate = new Date(invoice.due_date)
  const today = new Date()
  const daysLate = differenceInDays(today, dueDate)
  const isOverdue = invoice.status === 'overdue' || daysLate > 0
  const formattedDate = format(dueDate, 'dd/MM/yyyy', { locale: it })

  // Interest calculation for payment urgency comparison
  const tassoBase = 0.12
  const penaltyPct = 0.01
  const penaltyGiorni = 30

  const calcInteressi = (giorniRitardo: number) => {
    const importo = invoice.total_amount
    if (giorniRitardo <= 0) return 0
    const interessi = (tassoBase / 365) * giorniRitardo * importo
    const penalty = giorniRitardo > 60 ? importo * Math.floor((giorniRitardo - 60) / penaltyGiorni) * penaltyPct : 0
    return Math.round((interessi + penalty) * 100) / 100
  }

  const todayTotal = invoice.total_amount + calcInteressi(Math.max(0, daysLate))
  const todayLate = Math.max(0, daysLate)
  const futureLate = todayLate + 30
  const futureTotal = invoice.total_amount + calcInteressi(futureLate)
  const extraCost = Math.round((futureTotal - todayTotal) * 100) / 100

  useEffect(() => {
    if (open) {
      setMessage(buildReminderMessage(invoice, tone, daysLate, isOverdue, formattedDate))
    }
  }, [open, tone, invoice, daysLate, isOverdue, formattedDate, invoice.trust_score, invoice.payment_pattern])

  const remindMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/api/v1/invoices/${invoice.id}/remind`, {
        tone,
        channel,
        message,
      })
      return response.data
    },
    onSuccess: () => {
      setSending(false)
      onSent()
      onClose()
    },
    onError: () => setSending(false),
  })

  const handleSend = () => {
    setSending(true)
    remindMutation.mutate()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-primary-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
              <Bell className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Invia Sollecito</h2>
              <p className="text-sm text-gray-500">{invoice.invoice_number}</p>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Invoice summary bar */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900 text-sm">{invoice.customer_name}</p>
              <p className="text-xs text-gray-500">
                {isOverdue ? (
                  <span className="text-red-600 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />Scaduta da {daysLate} giorni
                  </span>
                ) : (
                  `Scade ${formattedDate}`
                )}
              </p>
            </div>
            <p className="text-xl font-bold text-gray-900">
              {new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(invoice.total_amount)}
            </p>
          </div>
          {/* Payment urgency comparison */}
          {invoice.status !== 'paid' && (
            <div className="mt-2 pt-2 border-t border-gray-200 flex items-center gap-4 text-sm">
              <div className="flex-1">
                <span className="text-gray-500">Se paghi oggi: </span>
                <span className="font-semibold text-green-700">
                  {new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(todayTotal)}
                </span>
                {todayLate > 0 && (
                  <span className="text-xs text-gray-400 ml-1">(+{todayLate}gg ritardo)</span>
                )}
              </div>
              <div className="text-gray-300">|</div>
              <div className="flex-1">
                <span className="text-gray-500">Se aspetti 30gg: </span>
                <span className="font-semibold text-red-700">
                  {new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(futureTotal)}
                </span>
                {extraCost > 0 && (
                  <span className="text-xs text-red-500 ml-1">(+{new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(extraCost)})</span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Tone + Channel selectors */}
        <div className="px-6 py-4 space-y-4">
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Tono</p>
            <div className="flex gap-2">
              {(Object.keys(TONE_LABELS) as Tone[]).map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setTone(t)
                    setMessage(buildReminderMessage(invoice, t, daysLate, isOverdue, formattedDate))
                  }}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                    tone === t
                      ? 'bg-primary-600 text-white shadow-md'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {TONE_LABELS[t]}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Canale</p>
            <div className="flex gap-2 flex-wrap">
              {(Object.keys(CHANNEL_LABELS) as Channel[]).map((c) => {
                // Check if client has the contact info for this channel
                const hasContact: Record<Channel, boolean> = {
                  email: !!invoice.customer_email,
                  pec: !!invoice.customer_pec,
                  telegram: false, // Telegram would need a chat ID
                  sms: !!invoice.customer_phone,
                }
                const disabled = !hasContact[c]
                return (
                  <button
                    key={c}
                    onClick={() => !disabled && setChannel(c)}
                    className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all min-w-[80px] ${
                      channel === c
                        ? 'bg-primary-600 text-white shadow-md'
                        : disabled
                        ? 'bg-gray-50 text-gray-300 cursor-not-allowed'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                    title={disabled ? `Nessun ${c} disponibile per questo cliente` : ''}
                  >
                    {CHANNEL_LABELS[c]}
                  </button>
                )
              })}
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Invieremo a:{' '}
              {channel === 'email' && invoice.customer_email}
              {channel === 'pec' && invoice.customer_pec}
              {channel === 'telegram' && 'Chat Telegram'}
              {channel === 'sms' && invoice.customer_phone}
            </p>
          </div>

          {/* Message preview */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Anteprima messaggio</p>
            <div className="bg-gray-50 rounded-xl p-4 text-sm text-gray-700 leading-relaxed border border-gray-200 min-h-[80px]">
              {message}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex gap-3">
          <Button variant="outline" onClick={onClose} className="flex-1">
            Annulla
          </Button>
          <Button
            onClick={handleSend}
            disabled={sending || remindMutation.isPending}
            className="flex-1"
          >
            {sending || remindMutation.isPending ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Invio...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Send className="w-4 h-4" />
                Invia Sollecito
              </span>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const [showSollecito, setShowSollecito] = useState(false)
  const [copied, setCopied] = useState<'number' | 'iban' | null>(null)
  const [paymentDate, setPaymentDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  )

  const { data: invoice, isLoading } = useQuery<Invoice>({
    queryKey: ['invoice', id],
    queryFn: async () => {
      const response = await api.get(`/api/v1/invoices/${id}`)
      return response.data
    },
    enabled: !!id,
  })

  const markPaidMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/api/v1/invoices/${id}/paid`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoice', id] })
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const { data: sdiStatus } = useQuery<SDIStatusResponse>({
    queryKey: ['invoice-sdi-status', id],
    queryFn: async () => {
      const response = await api.get(`/api/v1/invoices/${id}/sdi-status`)
      return response.data
    },
    enabled: !!id,
  })

  const { data: calcoloInteressi } = useQuery<CalcoloInteressiResponse>({
    queryKey: ['invoice-interessi', id, paymentDate],
    queryFn: async () => {
      const params = paymentDate ? `?data_pagamento=${paymentDate}` : ''
      const response = await api.get(`/api/v1/invoices/${id}/calcolo-interessi${params}`)
      return response.data
    },
    enabled: !!id,
  })

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)

  const formatDate = (dateStr: string) =>
    format(new Date(dateStr), 'dd MMMM yyyy', { locale: it })

  const formatDateShort = (dateStr: string) =>
    format(new Date(dateStr), 'dd/MM/yyyy', { locale: it })

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'success' | 'warning' | 'destructive' | 'secondary'> = {
      paid: 'success',
      pending: 'warning',
      overdue: 'destructive',
    }
    const labels: Record<string, string> = {
      paid: 'Pagata',
      pending: 'In attesa',
      overdue: 'Scaduta',
    }
    return <Badge variant={variants[status] || 'secondary'}>{labels[status] || status}</Badge>
  }

  const handlePrint = () => {
    window.print()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!invoice) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Fattura non trovata</p>
        <Link to="/invoices">
          <Button variant="outline" className="mt-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Torna alle fatture
          </Button>
        </Link>
      </div>
    )
  }

  const dueDate = new Date(invoice.due_date)
  const today = new Date()
  const daysLate = differenceInDays(today, dueDate)
  const isOverdue = invoice.status === 'overdue' || daysLate > 0

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-0">
      <div className="space-y-4">
      {/* Sollecito Modal */}
      <SollecitoModal
        invoice={invoice}
        open={showSollecito}
        onClose={() => setShowSollecito(false)}
        onSent={() => {
          queryClient.invalidateQueries({ queryKey: ['invoice', id] })
          queryClient.invalidateQueries({ queryKey: ['invoices'] })
        }}
      />

      {/* Header */}
      <div className="flex items-center gap-4 no-print">
        <Link to="/invoices" className="no-print">
          <Button variant="ghost" size="icon" className="no-print">
            <ArrowLeft className="w-5 h-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">{invoice.invoice_number}</h1>
            <button
              onClick={() => {
                navigator.clipboard.writeText(invoice.invoice_number).catch(() => {})
                setCopied('number')
                setTimeout(() => setCopied(null), 2000)
              }}
              className="p-1.5 rounded-md hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
              title="Copia numero fattura"
            >
              {copied === 'number' ? <CheckCheck className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-sm text-gray-500 truncate">{invoice.customer_name}</p>
        </div>
        {getStatusBadge(invoice.status)}
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2 print:hidden no-print">
        {invoice.status !== 'paid' && (
          <Button
            onClick={() => markPaidMutation.mutate()}
            disabled={markPaidMutation.isPending}
          >
            <Check className="w-4 h-4 mr-2" />
            Segna pagata
          </Button>
        )}
        {invoice.status !== 'paid' && (
          <Button variant="outline" onClick={() => setShowSollecito(true)}>
            <Bell className="w-4 h-4 mr-2" />
            Invia sollecito
          </Button>
        )}
        <Button variant="outline" onClick={handlePrint} className="print:hidden">
          <Printer className="w-4 h-4 mr-2" />
          Stampa
        </Button>
        {invoice.xml_filename && (
          <Button
            variant="ghost"
            asChild
            className="text-gray-500 print:hidden"
          >
            <a href={`/api/v1/invoices/${invoice.id}/xml`} download={invoice.xml_filename}>
              <Download className="w-4 h-4 mr-2" />
              XML
            </a>
          </Button>
        )}
      </div>

      {/* Amount + Due date card */}
      <Card className={`border-2 overflow-hidden ${
        isOverdue ? 'border-red-200 bg-red-50' : 'border-primary-100 bg-primary-50'
      }`}>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className={`text-sm font-medium ${isOverdue ? 'text-red-600' : 'text-primary-600'}`}>
                Importo Totale
              </p>
              <p className={`text-2xl sm:text-3xl font-bold truncate ${isOverdue ? 'text-red-900' : 'text-primary-900'}`}>
                {formatCurrency(invoice.total_amount)}
              </p>
              {invoice.description && (
                <div className="mt-1.5">
                  <DeductibilityBadge description={invoice.description} />
                </div>
              )}
              {isOverdue && (
                <p className="text-xs text-red-600 mt-1 font-medium">
                  ⚠️ Scaduta da {daysLate} giorni
                </p>
              )}
              {!isOverdue && invoice.status === 'pending' && (
                <p className="text-xs text-primary-600 mt-1 font-medium">
                  ⏰ Scadenza tra {Math.abs(daysLate)} giorni
                </p>
              )}
            </div>
            <div className="text-right shrink-0">
              <p className={`text-sm ${isOverdue ? 'text-red-600' : 'text-primary-600'}`}>Scadenza</p>
              <p className={`text-lg font-semibold ${isOverdue ? 'text-red-900' : 'text-primary-900'}`}>
                {formatDate(invoice.due_date)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Emessa: {formatDateShort(invoice.invoice_date)}
              </p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-200 flex gap-8 overflow-hidden">
            <div className="min-w-0">
              <p className={`text-xs ${isOverdue ? 'text-red-500' : 'text-primary-500'}`}>Imponibile</p>
              <p className="font-medium truncate">{formatCurrency(invoice.amount)}</p>
            </div>
            <div className="min-w-0">
              <p className={`text-xs ${isOverdue ? 'text-red-500' : 'text-primary-500'}`}>IVA (22%)</p>
              <p className="font-medium truncate">{formatCurrency(invoice.vat_amount)}</p>
            </div>
            {invoice.description && (
              <div className="min-w-0">
                <p className={`text-xs ${isOverdue ? 'text-red-500' : 'text-primary-500'}`}>Descrizione</p>
                <p className="font-medium text-sm truncate max-w-[200px]">{invoice.description}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* SDI Timeline */}
      {sdiStatus && (
        <Card>
          <CardContent className="p-4">
            <SDITimeline
              invoiceId={invoice.id}
              currentStatus={sdiStatus.status}
              timestamps={sdiStatus.timestamps}
            />
          </CardContent>
        </Card>
      )}

      {/* Calcola Interessi Box */}
      {invoice.status !== 'paid' && (
        <Card className="border-2 border-amber-200 bg-amber-50 overflow-hidden print:hidden">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <Calculator className="w-5 h-5 text-amber-600" />
              <h3 className="font-bold text-amber-900">Calcola Interessi di Mora</h3>
            </div>
            <div className="flex items-end gap-3 flex-wrap">
              <div>
                <label className="text-xs text-amber-700 font-medium block mb-1">
                  Data pagamento ipotetica
                </label>
                <input
                  type="date"
                  value={paymentDate}
                  onChange={(e) => setPaymentDate(e.target.value)}
                  className="border border-amber-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
              <div className="text-xs text-amber-700">
                D.Lgs 231/2002 — Tasso BCE 4% + spread 8% = <strong>12% annuo</strong>
              </div>
            </div>
            {calcoloInteressi && (
              <div className="mt-4 pt-3 border-t border-amber-200 grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <p className="text-xs text-amber-600">Importo originale</p>
                  <p className="font-semibold text-amber-800">
                    {new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(calcoloInteressi.importo_originale)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-amber-600">Interessi ({calcoloInteressi.giorni_ritardo}gg)</p>
                  <p className="font-semibold text-amber-800">
                    +{new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(calcoloInteressi.interessi)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-amber-600">Penalty</p>
                  <p className="font-semibold text-amber-800">
                    +{new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(calcoloInteressi.penalty)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-amber-600">Totale dovuto</p>
                  <p className="font-bold text-green-700 text-lg">
                    {new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(calcoloInteressi.totale)}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Details grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Customer */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <User className="w-4 h-4 text-gray-400" />
              Cliente
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm overflow-hidden">
            <div className="flex items-center justify-between gap-2">
              <p className="font-medium truncate">{invoice.customer_name}</p>
              {invoice.trust_score !== undefined && invoice.trust_score !== null && (
                <TrustScoreBadge score={invoice.trust_score} size="sm" />
              )}
            </div>
            {invoice.customer_vat && <p className="text-gray-500 truncate">P.IVA: {invoice.customer_vat}</p>}
            {invoice.customer_cf && <p className="text-gray-500 truncate">CF: {invoice.customer_cf}</p>}
            {invoice.customer_address && <p className="text-gray-500 truncate">{invoice.customer_address}</p>}
            {invoice.customer_phone && (
              <p className="flex items-center gap-2 text-gray-500 truncate">
                <Phone className="w-3 h-3 shrink-0" />
                {invoice.customer_phone}
              </p>
            )}
            {invoice.customer_email && (
              <p className="flex items-center gap-2 text-gray-500 truncate">
                <Mail className="w-3 h-3 shrink-0" />
                {invoice.customer_email}
              </p>
            )}
            {invoice.customer_pec && (
              <p className="flex items-center gap-2 text-gray-500 truncate">
                <MessageSquare className="w-3 h-3 shrink-0" />
                {invoice.customer_pec}
              </p>
            )}
            {invoice.customer_sdi && <p className="text-gray-500 truncate">SDI: {invoice.customer_sdi}</p>}
          </CardContent>
        </Card>

        {/* Supplier */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Building className="w-4 h-4 text-gray-400" />
              Fornitore
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm overflow-hidden">
            <p className="font-medium truncate">{invoice.supplier_name}</p>
            {invoice.supplier_vat && <p className="text-gray-500 truncate">P.IVA: {invoice.supplier_vat}</p>}
            {invoice.supplier_cf && <p className="text-gray-500 truncate">CF: {invoice.supplier_cf}</p>}
            {invoice.supplier_address && <p className="text-gray-500 truncate">{invoice.supplier_address}</p>}
            {invoice.supplier_phone && (
              <p className="flex items-center gap-2 text-gray-500 truncate">
                <Phone className="w-3 h-3 shrink-0" />
                {invoice.supplier_phone}
              </p>
            )}
            {invoice.supplier_pec && (
              <p className="flex items-center gap-2 text-gray-500 truncate">
                <MessageSquare className="w-3 h-3 shrink-0" />
                {invoice.supplier_pec}
              </p>
            )}
            {invoice.supplier_sdi && <p className="text-gray-500 truncate">SDI: {invoice.supplier_sdi}</p>}
            {invoice.supplier_iban && (
              <div className="flex items-center gap-2">
                <p className="text-gray-500 font-mono text-xs bg-gray-50 p-1 rounded truncate flex-1">
                  IBAN: {invoice.supplier_iban}
                </p>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(invoice.supplier_iban || '').catch(() => {})
                    setCopied('iban')
                    setTimeout(() => setCopied(null), 2000)
                  }}
                  className="p-1 rounded hover:bg-gray-200 transition-colors shrink-0"
                  title="Copia IBAN"
                >
                  {copied === 'iban' ? <CheckCheck className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5 text-gray-400" />}
                </button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Reminders history */}
      {invoice.reminders && invoice.reminders.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="w-4 h-4 text-gray-400" />
              Storico Solleciti
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {invoice.reminders.map((reminder) => (
                <div
                  key={reminder.id}
                  className="flex items-start justify-between p-3 bg-gray-50 rounded-lg text-sm overflow-hidden"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium">{formatDate(reminder.reminder_date)}</span>
                      <Badge
                        variant={
                          reminder.sent_via === 'pec' ? 'default' :
                          reminder.sent_via === 'telegram' ? 'default' :
                          'secondary'
                        }
                        className="text-xs max-w-[100px] truncate"
                      >
                        {reminder.sent_via.toUpperCase()}
                      </Badge>
                      <Badge
                        variant={reminder.status === 'sent' ? 'success' : 'secondary'}
                        className="text-xs max-w-[100px] truncate"
                      >
                        {reminder.status}
                      </Badge>
                    </div>
                    <p className="text-gray-500 capitalize truncate">
                      {reminder.reminder_type} — {reminder.sent_via}
                    </p>
                    {reminder.message && (
                      <p className="text-gray-600 mt-1 italic truncate max-w-[300px]">"{reminder.message}"</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
        </div>
  </div>
  )
}
