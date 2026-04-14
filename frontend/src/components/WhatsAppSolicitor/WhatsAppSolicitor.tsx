import { useState, useEffect, useCallback } from 'react'
import { X, Send, Check, Clock, ExternalLink } from 'lucide-react'
import { api } from '../../lib/api'
import { Button } from '../ui'
import { format, formatDistanceToNow } from 'date-fns'
import { it } from 'date-fns/locale'

export interface WhatsAppSolicitorProps {
  invoiceId: number
  customerName: string
  customerPhone: string
  invoiceNumber: string
  amount: number
  dueDate: string
  companyName?: string
  onSent?: (message: string) => void
  onClose?: () => void
}

// Track sent messages in memory for demo
const sentMessagesCache: Record<number, WhatsAppMessage[]> = {}

export type SolicitorState = 'idle' | 'composing' | 'previewing' | 'sending' | 'sent'

type Tone = 'gentile' | 'equilibrato' | 'fermo'

interface WhatsAppMessage {
  id: string
  text: string
  sent_at: string
  tone: Tone
  status: 'sent' | 'failed'
  isOutgoing: true
}

interface WhatsAppHistoryResponse {
  messages: WhatsAppMessage[]
}

interface WhatsAppSendResponse {
  success: boolean
  message_id: string
  sent_at: string
  preview: string
}

const TONE_CONFIG: Record<Tone, { label: string; emoji: string; color: string }> = {
  gentile: { label: 'Gentile', emoji: '🕊️', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  equilibrato: { label: 'Equilibrato', emoji: '📋', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  fermo: { label: 'Fermo', emoji: '⚡', color: 'bg-orange-100 text-orange-700 border-orange-200' },
}

function buildMessage(
  customerName: string,
  companyName: string,
  invoiceNumber: string,
  amount: number,
  dueDate: string,
  tone: Tone,
  paymentLink?: string
): string {
  const amountFormatted = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)
  const dueDateFormatted = format(new Date(dueDate), 'dd/MM/yyyy', { locale: it })

  const templates: Record<Tone, string> = {
    gentile: `Gentile ${customerName},\n\nTi scrivo in merito alla fattura ${invoiceNumber} di ${amountFormatted} che risulta in scadenza il ${dueDateFormatted}.\n\nSaremmo grati se potessi verificare la tua posizione e provvedere al pagamento entro la data indicata.\n\nResta a disposizione per qualsiasi chiarimento.\n\nCordiali saluti,\n${companyName}`,
    equilibrato: `Gentile ${customerName},\n\nLa contattiamo per ricordare che la fattura ${invoiceNumber} di ${amountFormatted} è in scadenza il ${dueDateFormatted}.\n\nVi chiediamo di cortesemente verificare la vostra posizione contabile e di procedere al pagamento entro la scadenza.\n\nIn caso di difficoltà contattateci per trovare una soluzione.\n\nDistinti saluti,\n${companyName}`,
    fermo: `${customerName},\n\nLa fattura ${invoiceNumber} di ${amountFormatted} è in scadenza il ${dueDateFormatted}.\n\nSenza pagamento entro la data indicata, saremo costretti ad avviare le procedure di recupero crediti.\n\nPer qualsiasi informazione contattare i nostri uffici.\n\nDistinti saluti,\n${companyName}`,
  }

  let msg = templates[tone]
  if (paymentLink) {
    msg += `\n\nPaga ora: ${paymentLink}`
  }
  return msg
}

function buildCTAButtons(paymentLink?: string, phone?: string) {
  const buttons: { label: string; style: 'success' | 'primary' | 'secondary'; action: string; href?: string }[] = []

  if (paymentLink) {
    buttons.push({ label: '💰 Pago ora', style: 'success', action: 'pay_now', href: paymentLink })
  }
  buttons.push({ label: '📋 Rateizzo', style: 'primary', action: 'installment' })
  if (phone) {
    buttons.push({ label: '📞 Chiamami', style: 'secondary', action: 'callback', href: `tel:${phone}` })
  }

  return buttons
}

export function WhatsAppSolicitor({
  invoiceId,
  customerName,
  customerPhone,
  invoiceNumber,
  amount,
  dueDate,
  companyName = 'La Mia Azienda',
  onSent,
  onClose,
}: WhatsAppSolicitorProps) {
  const [state, setState] = useState<SolicitorState>('idle')
  const [tone, setTone] = useState<Tone>('equilibrato')
  const [message, setMessage] = useState('')
  const [history, setHistory] = useState<WhatsAppMessage[]>([])
  const [sending, setSending] = useState(false)
  const [sentConfirm, setSentConfirm] = useState(false)

  const paymentLink = `https://pay.fatturamvp.it/invoice/${invoiceId}`
  const ctaButtons = buildCTAButtons(paymentLink, customerPhone)

  // Load history on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const res = await api.get<WhatsAppHistoryResponse>(`/api/v1/solicitor/whatsapp/history/${invoiceId}`)
        const msgs = (res.data.messages || []).slice(-3)
        setHistory(msgs)
      } catch {
        // Use cached
        setHistory(sentMessagesCache[invoiceId] || [])
      }
    }
    loadHistory()
  }, [invoiceId])

  // Build message when tone changes
  useEffect(() => {
    const msg = buildMessage(customerName, companyName, invoiceNumber, amount, dueDate, tone, paymentLink)
    setMessage(msg)
    setState('composing')
  }, [tone]) // eslint-disable-line react-hooks/exhaustive-deps

  // Move to preview when message is ready
  useEffect(() => {
    if (state === 'composing' && message) {
      const t = setTimeout(() => setState('previewing'), 300)
      return () => clearTimeout(t)
    }
  }, [message, state])

  const handleSend = useCallback(async () => {
    setSending(true)
    setState('sending')

    try {
      const res = await api.post<WhatsAppSendResponse>('/api/v1/solicitor/whatsapp/send', {
        invoice_id: invoiceId,
        message,
        tone,
        phone: customerPhone,
      })

      if (res.data.success) {
        const newMsg: WhatsAppMessage = {
          id: res.data.message_id,
          text: message,
          sent_at: res.data.sent_at,
          tone,
          status: 'sent',
          isOutgoing: true,
        }

        // Update cache
        sentMessagesCache[invoiceId] = [...(sentMessagesCache[invoiceId] || []), newMsg].slice(-10)
        setHistory(prev => [...prev, newMsg])
        setSentConfirm(true)
        setState('sent')
        onSent?.(message)

        // Reset after 3s
        setTimeout(() => {
          setSentConfirm(false)
          setState('idle')
        }, 3000)
      }
    } catch {
      setState('previewing')
    } finally {
      setSending(false)
    }
  }, [invoiceId, message, tone, customerPhone, onSent])

  const handleEdit = () => {
    setState('composing')
  }

  const formatTime = (iso: string) => {
    try {
      return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: it })
    } catch {
      return ''
    }
  }

  const initials = (name: string) =>
    name.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase()

  return (
    <div className="flex flex-col h-full bg-gray-50 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-emerald-600 text-white shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-emerald-400 flex items-center justify-center text-emerald-900 font-bold text-sm">
            {initials(customerName)}
          </div>
          <div>
            <p className="font-semibold text-sm">{customerName}</p>
            <p className="text-xs text-emerald-200">{customerPhone}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-emerald-500 px-2 py-0.5 rounded-full">{invoiceNumber}</span>
          {onClose && (
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full hover:bg-emerald-500 flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Invoice summary bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-emerald-50 border-b border-emerald-100">
        <div className="flex items-center gap-2 text-xs text-emerald-700">
          <Clock className="w-3 h-3" />
          <span>Scadenza: {format(new Date(dueDate), 'dd/MM/yyyy', { locale: it })}</span>
        </div>
        <div className="text-xs font-bold text-emerald-800">
          {new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* History messages */}
        {history.map((msg) => (
          <div key={msg.id} className="flex justify-end">
            <div className="max-w-[75%]">
              <div className="bg-green-800 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
                {msg.text}
              </div>
              <div className="flex items-center justify-end gap-1 mt-1">
                <span className="text-[10px] text-gray-400">{formatTime(msg.sent_at)}</span>
                <Check className="w-3 h-3 text-gray-400" />
              </div>
            </div>
          </div>
        ))}

        {/* Current message preview */}
        {(state === 'composing' || state === 'previewing' || state === 'sending') && (
          <div className="flex justify-end">
            <div className="max-w-[75%]">
              <div className="bg-green-800 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
                {message}
                {/* CTA Buttons */}
                <div className="mt-3 flex flex-wrap gap-2">
                  {ctaButtons.map((btn) =>
                    btn.href ? (
                      <a
                        key={btn.action}
                        href={btn.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-white/10 backdrop-blur hover:bg-white/20 transition-colors ${
                          btn.style === 'success' ? 'text-green-300' : btn.style === 'primary' ? 'text-blue-300' : 'text-gray-300'
                        }`}
                      >
                        {btn.label}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <button
                        key={btn.action}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-white/10 backdrop-blur hover:bg-white/20 transition-colors ${
                          btn.style === 'success' ? 'text-green-300' : btn.style === 'primary' ? 'text-blue-300' : 'text-gray-300'
                        }`}
                      >
                        {btn.label}
                      </button>
                    )
                  )}
                </div>
              </div>
              {state === 'sending' && (
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-[10px] text-gray-400">Invio in corso...</span>
                  <div className="w-3 h-3 border border-gray-300 border-t-emerald-600 rounded-full animate-spin" />
                </div>
              )}
              {state === 'previewing' && !sending && (
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-[10px] text-gray-400">Anteprima</span>
                  <span className="text-[10px] text-emerald-500">·</span>
                  <button onClick={handleEdit} className="text-[10px] text-blue-500 hover:underline">
                    Modifica
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Sent confirmation */}
        {sentConfirm && state === 'sent' && (
          <div className="flex justify-end">
            <div className="max-w-[75%]">
              <div className="bg-green-800 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
                ✓ Messaggio inviato!
              </div>
              <div className="flex items-center justify-end gap-1 mt-1">
                <span className="text-[10px] text-emerald-500">Inviato</span>
                <Check className="w-3 h-3 text-emerald-500" />
                <Check className="w-3 h-3 text-emerald-500" />
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {state === 'idle' && history.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
              <svg viewBox="0 0 24 24" className="w-8 h-8 text-emerald-600" fill="currentColor">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
                <path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.853 5.067 2.33 7.113L.789 23.492a.75.75 0 00.917.918l4.38-1.54A11.955 11.955 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0z"/>
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-700 mb-1">Nessun sollecito WhatsApp</p>
            <p className="text-xs text-gray-400">Inizia una conversazione con il cliente</p>
          </div>
        )}
      </div>

      {/* Tone selector */}
      <div className="px-4 py-2 bg-white border-t border-gray-100">
        <p className="text-xs text-gray-400 mb-1.5">Tono del messaggio</p>
        <div className="flex gap-1.5">
          {(Object.keys(TONE_CONFIG) as Tone[]).map((t) => {
            const cfg = TONE_CONFIG[t]
            return (
              <button
                key={t}
                onClick={() => setTone(t)}
                className={`flex-1 flex items-center justify-center gap-1 py-1.5 px-2 rounded-full text-xs font-medium border transition-all ${
                  tone === t ? cfg.color : 'bg-gray-50 text-gray-400 border-gray-200 hover:border-gray-300'
                }`}
              >
                <span>{cfg.emoji}</span>
                <span>{cfg.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Message composer */}
      <div className="px-4 py-3 bg-white border-t border-gray-100">
        {state === 'previewing' || state === 'composing' ? (
          <div className="space-y-2">
            <textarea
              value={message}
              onChange={(e) => {
                setMessage(e.target.value)
                setState('previewing')
              }}
              rows={4}
              className="w-full rounded-xl bg-gray-50 border border-gray-200 px-4 py-3 text-sm text-gray-700 resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              placeholder="Personalizza il messaggio..."
            />
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleEdit}
                className="flex-1 text-xs"
              >
                Modifica
              </Button>
              <Button
                size="sm"
                onClick={handleSend}
                disabled={sending || !message.trim()}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-xs gap-1"
              >
                {sending ? (
                  <>
                    <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                    Invio...
                  </>
                ) : (
                  <>
                    <Send className="w-3 h-3" />
                    Invia WhatsApp
                  </>
                )}
              </Button>
            </div>
          </div>
        ) : state === 'sent' || sentConfirm ? (
          <div className="flex items-center justify-center gap-2 py-2 text-emerald-600">
            <Check className="w-5 h-5" />
            <span className="text-sm font-medium">Messaggio inviato!</span>
          </div>
        ) : null}
      </div>
    </div>
  )
}
