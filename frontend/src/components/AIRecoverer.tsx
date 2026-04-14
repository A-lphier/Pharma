import { useState } from 'react'
import { Phone, MessageSquare, FileText, AlertTriangle, CheckCircle2, ArrowRight, User } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './ui'
import { formatCurrency } from '../lib/utils'

interface RecovererInvoice {
  id: number
  customer_name: string
  customer_phone?: string
  total_amount: number
  days_overdue: number
  status: 'negotiating' | 'proposal_sent' | 'accepted' | 'escalated'
  last_action?: string
  probability: number
}

interface AIRecovererProps {
  invoices?: RecovererInvoice[]
  onEscalate?: (invoiceId: number) => void
}

const defaultInvoices: RecovererInvoice[] = [
  { id: 3, customer_name: 'Tech Solutions S.r.l.', customer_phone: '+39 02 1234567', total_amount: 8900, days_overdue: 62, status: 'negotiating', last_action: '2 solleciti WhatsApp inviati', probability: 65 },
  { id: 5, customer_name: 'Freelance Verdi', customer_phone: '+39 333 9876543', total_amount: 1500, days_overdue: 88, status: 'proposal_sent', last_action: 'Rateizzazione proposta il 20/03', probability: 40 },
  { id: 8, customer_name: 'Consulenze Riuniti S.p.A.', total_amount: 6200, days_overdue: 91, status: 'escalated', last_action: 'Rifiutata rateizzazione', probability: 10 },
]

const TRANSCRIPT_STEPS = [
  { speaker: 'AI', text: 'Buongiorno, la chiamo da [Azienda]. Volevo parlare della fattura scaduta da 62 giorni.' },
  { speaker: 'Cliente', text: 'Sì, mi scusi, avevo dimenticato. Che devo fare?' },
  { speaker: 'AI', text: 'Possiamo splittare in 3 rate da €2.967. Prima rata tra 7 giorni. Le va bene?' },
  { speaker: 'Cliente', text: 'Sì, va bene. Mi mandi pure.' },
  { speaker: 'AI', text: 'Perfetto. Le invio la proposta su WhatsApp per confermare. Grazie e buongiorno.' },
]

function generatePlan(invoice: RecovererInvoice) {
  const installments = Math.min(Math.ceil(invoice.total_amount / 1500), 6)
  const rate = Math.round(invoice.total_amount / installments)
  const plan = Array.from({ length: installments }, (_, i) => ({
    amount: i === installments - 1 ? invoice.total_amount - rate * (installments - 1) : rate,
    due_date: new Date(Date.now() + (i + 1) * 7 * 24 * 60 * 60 * 1000).toLocaleDateString('it-IT'),
  }))
  return {
    installments: plan,
    whatsapp_text: `Gentile ${invoice.customer_name},\n\nin riferimento alla fattura di ${formatCurrency(invoice.total_amount)} scaduta da ${invoice.days_overdue} giorni, le propongo la seguente rateizzazione:\n\n${plan.map((r, i) => `${i + 1}. €${r.amount.toLocaleString('it')} entro il ${r.due_date}`).join('\n')}\n\nResto a disposizione.`,
    message_preview: `Proposta rateizzazione: ${installments} rate da €${rate.toLocaleString('it')}`,
  }
}

export function AIRecoverer({ invoices = defaultInvoices, onEscalate }: AIRecovererProps) {
  const [selected, setSelected] = useState<RecovererInvoice | null>(null)
  const [calling, setCalling] = useState(false)
  const [transcriptStep, setTranscriptStep] = useState(0)
  const [callDone, setCallDone] = useState(false)
  const [planSent, setPlanSent] = useState(false)

  const startCall = () => {
    if (!selected) return
    setCalling(true)
    setCallDone(false)
    setTranscriptStep(0)
    let step = 0
    const interval = setInterval(() => {
      step++
      setTranscriptStep(step)
      if (step >= TRANSCRIPT_STEPS.length) {
        clearInterval(interval)
        setCalling(false)
        setCallDone(true)
      }
    }, 2000)
  }

  const sendProposal = () => {
    if (!selected) return
    setPlanSent(true)
    onEscalate?.(selected.id)
  }

  const statusColors: Record<string, string> = {
    negotiating: 'bg-amber-100 text-amber-700 border-amber-200',
    proposal_sent: 'bg-blue-100 text-blue-700 border-blue-200',
    accepted: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    escalated: 'bg-red-100 text-red-700 border-red-200',
  }
  const statusLabels: Record<string, string> = {
    negotiating: 'In trattativa',
    proposal_sent: 'Proposta inviata',
    accepted: 'Accettata',
    escalated: 'Escalated',
  }

  const selectedPlan = selected ? generatePlan(selected) : null

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Recupero Crediti AI</h2>
          <p className="text-sm text-gray-500">{invoices.length} pratiche in gestione</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="flex items-center gap-1 text-emerald-600">
            <CheckCircle2 className="w-3.5 h-3.5" /> {invoices.filter(i => i.status === 'accepted').length} risolte
          </span>
          <span className="flex items-center gap-1 text-red-600">
            <AlertTriangle className="w-3.5 h-3.5" /> {invoices.filter(i => i.status === 'escalated').length} escalated
          </span>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Left: Invoice list */}
        <div className="space-y-2">
          {invoices.map(inv => (
            <button
              key={inv.id}
              onClick={() => { setSelected(inv); setPlanSent(false); setCallDone(false) }}
              className={`w-full text-left p-3.5 rounded-xl border transition-all duration-150 ${
                selected?.id === inv.id
                  ? 'border-blue-300 bg-blue-50/50 shadow-sm'
                  : 'border-gray-100 bg-white hover:border-gray-200 hover:shadow-sm'
              } ${inv.status === 'escalated' ? 'border-red-200' : ''}`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{inv.customer_name}</p>
                  <p className="text-xs text-gray-400">{inv.days_overdue} giorni fa · {formatCurrency(inv.total_amount)}</p>
                </div>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border shrink-0 ${statusColors[inv.status]}`}>
                  {statusLabels[inv.status]}
                </span>
              </div>
              {/* Probability bar */}
              <div className="mt-2">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Probabilità recupero</span>
                  <span className="font-medium">{inv.probability}%</span>
                </div>
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${inv.probability >= 60 ? 'bg-emerald-500' : inv.probability >= 30 ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${inv.probability}%` }}
                  />
                </div>
              </div>
              {inv.last_action && (
                <p className="text-xs text-gray-400 mt-1.5 truncate">→ {inv.last_action}</p>
              )}
            </button>
          ))}
        </div>

        {/* Right: Action panel */}
        <div>
          {!selected ? (
            <Card className="border border-dashed border-gray-200 bg-gray-50/50">
              <CardContent className="p-6 text-center">
                <MessageSquare className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Seleziona una fattura per gestire il recupero</p>
              </CardContent>
            </Card>
          ) : (
            <Card className={`border ${selected.status === 'escalated' ? 'border-red-200' : 'border-gray-200'} shadow-sm`}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <User className="w-4 h-4 text-gray-500" />
                  {selected.customer_name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Info row */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-gray-50 rounded-lg p-2.5">
                    <p className="text-xs text-gray-500">Importo</p>
                    <p className="text-sm font-bold text-gray-900">{formatCurrency(selected.total_amount)}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2.5">
                    <p className="text-xs text-gray-500">Scaduti</p>
                    <p className="text-sm font-bold text-red-600">{selected.days_overdue}gg</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2.5">
                    <p className="text-xs text-gray-500">Recupero</p>
                    <p className={`text-sm font-bold ${selected.probability >= 60 ? 'text-emerald-600' : selected.probability >= 30 ? 'text-amber-600' : 'text-red-600'}`}>
                      {selected.probability}%
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-2">
                  {/* Piano rateizzazione */}
                  <div className="bg-gray-50 rounded-xl p-3 border border-gray-100">
                    <p className="text-xs font-semibold text-gray-700 mb-2">Piano rateizzazione suggerito</p>
                    {selectedPlan?.installments.map((inst, i) => (
                      <div key={i} className="flex items-center justify-between text-xs py-0.5">
                        <span className="text-gray-500">Rate {i + 1}</span>
                        <span className="font-medium text-gray-700">{formatCurrency(inst.amount)} — {inst.due_date}</span>
                      </div>
                    ))}
                    {selectedPlan && (
                      <p className="text-xs text-gray-500 mt-2 italic">"{selectedPlan.message_preview}"</p>
                    )}
                  </div>

                  {/* Call AI */}
                  {selected.customer_phone && (
                    <button
                      onClick={startCall}
                      disabled={calling}
                      className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium rounded-xl transition-colors"
                    >
                      <Phone className="w-4 h-4" />
                      {calling ? 'Chiamata in corso...' : 'Chiama cliente con AI'}
                    </button>
                  )}

                  {/* Send proposal */}
                  {!planSent && selected.status !== 'accepted' && (
                    <button
                      onClick={sendProposal}
                      className="w-full flex items-center justify-center gap-2 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-xl transition-colors"
                    >
                      <ArrowRight className="w-4 h-4" />
                      Invia proposta di rateizzazione
                    </button>
                  )}
                  {planSent && (
                    <div className="flex items-center gap-2 py-2.5 px-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-sm font-medium">
                      <CheckCircle2 className="w-4 h-4 shrink-0" />
                      Proposta inviata ✓
                    </div>
                  )}

                  {/* Escalate */}
                  {(selected.status === 'escalated' || selected.status === 'negotiating') && (
                    <button
                      onClick={() => onEscalate?.(selected.id)}
                      className="w-full flex items-center justify-center gap-2 py-2.5 bg-white border border-red-200 hover:bg-red-50 text-red-600 text-sm font-medium rounded-xl transition-colors"
                    >
                      <FileText className="w-4 h-4" />
                      Escalate ad avvocato (~€350-500)
                    </button>
                  )}
                </div>

                {/* Transcript */}
                {(calling || callDone) && (
                  <div className="bg-gray-900 rounded-xl p-3 space-y-2">
                    <p className="text-xs font-semibold text-gray-400 mb-2">
                      {callDone ? '✓ Chiamata completata' : `Chiamata... ${transcriptStep}/${TRANSCRIPT_STEPS.length}`}
                    </p>
                    {TRANSCRIPT_STEPS.slice(0, callDone ? TRANSCRIPT_STEPS.length : transcriptStep).map((step, i) => (
                      <div key={i} className={`text-xs ${step.speaker === 'AI' ? 'text-blue-300' : 'text-gray-300'}`}>
                        <span className="font-semibold">{step.speaker}:</span> {step.text}
                      </div>
                    ))}
                    {!callDone && (
                      <div className="animate-pulse text-xs text-gray-500">...</div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
