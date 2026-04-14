import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Button } from '../components/ui'
import { X, Bell, Send, AlertTriangle } from 'lucide-react'
import { format, differenceInDays } from 'date-fns'
import { it } from 'date-fns/locale'

interface SollecitoModalProps {
  invoice: InvoiceData
  open: boolean
  onClose: () => void
  onSent: () => void
}

interface InvoiceData {
  id: number
  invoice_number: string
  invoice_date: string
  due_date: string
  customer_name: string
  customer_email?: string
  customer_pec?: string
  customer_phone?: string
  customer_sdi?: string
  total_amount: number
  status: string
  trust_score?: number
  payment_pattern?: string
}

type Channel = 'email' | 'pec' | 'sms' | 'whatsapp'

const CHANNEL_LABELS: Record<Channel, string> = {
  email: '📧 Email',
  pec: '📨 PEC',
  sms: '📱 SMS',
  whatsapp: '💬 WA',
}

type Tone = 'gentile' | 'normale' | 'fermo'

const TONE_LABELS: Record<Tone, string> = {
  gentile: '🕊️ Gentile',
  normale: '📋 Normale',
  fermo: '⚡ Fermo',
}

function generatePreview(invoice: InvoiceData, tone: Tone): string {
  const amount = new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: 'EUR',
  }).format(invoice.total_amount)

  const dueDate = new Date(invoice.due_date)
  const today = new Date()
  const daysLate = differenceInDays(today, dueDate)
  const isOverdue = invoice.status === 'overdue' || daysLate > 0

  const trustScore = invoice.trust_score ?? (
    invoice.payment_pattern === 'Punctual' ? 85 :
    invoice.payment_pattern === 'Occasional delay' ? 60 : 35
  )

  const idx =
    trustScore >= 80 ? 0 :
    trustScore >= 60 ? 1 :
    trustScore >= 40 ? 2 :
    trustScore >= 20 ? 3 : 4

  const names: ToneLabel[] = ['eccellente', 'affidabile', 'verificare', 'problematico', 'inesistente']
  const label = names[idx]

  if (isOverdue && daysLate > 0) {
    const templates: Record<Tone, Record<ToneLabel, string>> = {
      gentile: {
        eccellente: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} risulta scaduta da ${daysLate} giorni. Potrebbe essere sfuggita? La ringraziamo per l'attenzione.`,
        affidabile: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} risulta scaduta da ${daysLate} giorni. La preghiamo di verificare e regolare. Grazie.`,
        verificare: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di procedere al pagamento entro 7 giorni.`,
        problematico: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Senza pagamento entro 5 giorni, saremo costretti a valutare azioni.`,
        inesistente: `La fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di regolare entro 5 giorni. In assenza, procederemo legalmente.`,
      },
      normale: {
        eccellente: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} risulta scaduta da ${daysLate} giorni. Le chiediamo di verificare la sua posizione.`,
        affidabile: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} risulta scaduta. La preghiamo di regolare. Grazie.`,
        verificare: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di procedere al pagamento.`,
        problematico: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di regolare entro 7 giorni. In caso contrario, saremo costretti a procedere.`,
        inesistente: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di regolare entro 5 giorni. In assenza, saremo costretti a valutare azioni legali.`,
      },
      fermo: {
        eccellente: `La informiamo che la fattura ${invoice.invoice_number} di ${amount} risulta scaduta da ${daysLate} giorni. Le chiediamo di provvedere al pagamento con urgenza.`,
        affidabile: `La fattura ${invoice.invoice_number} di ${amount} risulta scaduta. Le chiediamo di procedere al pagamento entro 7 giorni.`,
        verificare: `La fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Le chiediamo di regolare entro 7 giorni.`,
        problematico: `La fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Senza pagamento entro 7 giorni, saranno avviate le procedure di recupero crediti.`,
        inesistente: `La fattura ${invoice.invoice_number} di ${amount} è scaduta da ${daysLate} giorni. Senza pagamento entro 5 giorni, saremo costretti a procedere legalmente.`,
      },
    }
    return templates[tone][label]
  } else {
    const formattedDate = format(dueDate, 'dd/MM/yyyy', { locale: it })
    const templates: Record<Tone, Record<ToneLabel, string>> = {
      gentile: {
        eccellente: `Ciao ${invoice.customer_name}, ti ricordiamo la fattura ${invoice.invoice_number} di ${amount} in scadenza il ${formattedDate}. Grazie!`,
        affidabile: `Gentile ${invoice.customer_name}, ti ricordiamo che la fattura ${invoice.invoice_number} di ${amount} scade il ${formattedDate}. Grazie per l'attenzione.`,
        verificare: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} scade il ${formattedDate}. Potrebbe essere sfuggita? Grazie.`,
        problematico: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} scade il ${formattedDate}. La preghiamo di regolare il pagamento.`,
        inesistente: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} scade il ${formattedDate}. La preghiamo di regolare il pagamento entro la scadenza per evitare conseguenze.`,
      },
      normale: {
        eccellente: `Gentile ${invoice.customer_name}, desideriamo ricordare che la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. La ringraziamo per l'attenzione.`,
        affidabile: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. La preghiamo di verificare la sua posizione.`,
        verificare: `Gentile ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. Le chiediamo di cortesemente verificare.`,
        problematico: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. Le chiediamo di procedere al pagamento entro la data di scadenza.`,
        inesistente: `Egregio ${invoice.customer_name}, la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. Senza pagamento entro la scadenza, saremo costretti a valutare azioni.`,
      },
      fermo: {
        eccellente: `La informiamo che la fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. La preghiamo di provvedere.`,
        affidabile: `La fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. Le chiediamo di verificare e regolare.`,
        verificare: `La fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. Le chiediamo di procedere al pagamento entro la scadenza.`,
        problematico: `La fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. Senza pagamento entro la data indicata, saranno avviate le procedure di recupero.`,
        inesistente: `La fattura ${invoice.invoice_number} di ${amount} è in scadenza il ${formattedDate}. In assenza di pagamento, saremo costretti a procedere legalmente.`,
      },
    }
    return templates[tone][label]
  }
}

function generateWhatsAppPreview(invoice: InvoiceData, paymentLink?: string): string {
  const amount = new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: 'EUR',
  }).format(invoice.total_amount)

  const dueDate = new Date(invoice.due_date)
  const formattedDate = format(dueDate, 'dd/MM/yyyy', { locale: it })

  const template = `Gentile ${invoice.customer_name}, ricordiamo che la fattura ${invoice.invoice_number} di ${amount} è scaduta il ${formattedDate}.`

  if (paymentLink) {
    return `${template} Paga ora: ${paymentLink}`
  }
  return template
}

type ToneLabel = 'eccellente' | 'affidabile' | 'verificare' | 'problematico' | 'inesistente'

export function SollecitoModal({ invoice, open, onClose, onSent }: SollecitoModalProps) {
  const [tone, setTone] = useState<Tone>('normale')
  const [channel, setChannel] = useState<Channel>('email')
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)

  // Determine available channels based on contact info
  const availableChannels: Channel[] = []
  if (invoice.customer_email) availableChannels.push('email')
  if (invoice.customer_pec) availableChannels.push('pec')
  if (invoice.customer_phone) availableChannels.push('sms')
  if (invoice.customer_phone) availableChannels.push('whatsapp') // WhatsApp needs phone
  if (!availableChannels.length) availableChannels.push('email') // fallback

  const activeChannel = availableChannels.includes(channel) ? channel : availableChannels[0]

  // Mock payment link — in production this would come from the invoice
  const paymentLink = invoice.id ? `https://pay.fatturamvp.it/invoice/${invoice.id}` : undefined

  const getRecipient = () => {
    switch (activeChannel) {
      case 'email': return invoice.customer_email || '—'
      case 'pec': return invoice.customer_pec || '—'
      case 'sms': return invoice.customer_phone || '—'
      case 'whatsapp': return invoice.customer_phone || '—'
    }
  }

  useEffect(() => {
    if (open) {
      if (activeChannel === 'whatsapp') {
        setMessage(generateWhatsAppPreview(invoice, paymentLink))
      } else {
        setMessage(generatePreview(invoice, tone))
      }
    }
  }, [open, tone, invoice, activeChannel, paymentLink])

  const remindMutation = useMutation({
    mutationFn: async () => {
      // WhatsApp uses the dedicated notifications endpoint
      if (activeChannel === 'whatsapp') {
        const response = await api.post('/api/v1/notifications/whatsapp', {
          invoice_id: invoice.id,
          message,
        })
        return response.data
      }
      // All other channels use the reminders endpoint
      const response = await api.post('/api/v1/reminders', {
        invoice_id: invoice.id,
        message,
        sent_via: activeChannel === 'pec' ? 'pec' : activeChannel === 'sms' ? 'sms' : 'email',
      })
      return response.data
    },
    onSuccess: () => {
      setSending(false)
      onSent()
      onClose()
    },
    onError: () => {
      setSending(false)
    },
  })

  const handleSend = () => {
    setSending(true)
    remindMutation.mutate()
  }

  const handleToneChange = (newTone: Tone) => {
    setTone(newTone)
    if (activeChannel !== 'whatsapp') {
      setMessage(generatePreview(invoice, newTone))
    }
  }

  const handleChannelChange = (newChannel: Channel) => {
    setChannel(newChannel)
    if (newChannel === 'whatsapp') {
      setMessage(generateWhatsAppPreview(invoice, paymentLink))
    } else {
      setMessage(generatePreview(invoice, tone))
    }
  }

  if (!open) return null

  const dueDate = new Date(invoice.due_date)
  const today = new Date()
  const daysLate = differenceInDays(today, dueDate)
  const isOverdue = invoice.status === 'overdue' || daysLate > 0

  const isWhatsApp = activeChannel === 'whatsapp'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className={`flex items-center justify-between px-6 py-4 border-b ${isWhatsApp ? 'border-emerald-100 bg-emerald-50' : 'border-gray-100 bg-primary-50'}`}>
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isWhatsApp ? 'bg-emerald-100' : 'bg-primary-100'}`}>
              {isWhatsApp ? (
                <svg viewBox="0 0 24 24" className="w-5 h-5 text-emerald-600" fill="currentColor">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
                  <path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.853 5.067 2.33 7.113L.789 23.492a.75.75 0 00.917.918l4.38-1.54A11.955 11.955 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-2.21 0-4.28-.716-5.967-1.926l-.427.15-2.11.742.74-2.108-.157-.426A9.955 9.955 0 012 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"/>
                </svg>
              ) : (
                <Bell className="w-5 h-5 text-primary-600" />
              )}
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                {isWhatsApp ? 'Invia WhatsApp' : 'Invia Sollecito'}
              </h2>
              <p className="text-sm text-gray-500">{invoice.invoice_number}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Invoice summary */}
        <div className={`px-6 py-4 border-b ${isWhatsApp ? 'border-emerald-100 bg-emerald-50/50' : 'bg-gray-50 border-gray-100'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">{invoice.customer_name}</p>
              <p className="text-sm text-gray-500">
                {isOverdue ? (
                  <span className="text-red-600 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Scaduta da {daysLate} giorni
                  </span>
                ) : (
                  `Scadenza: ${format(dueDate, 'dd/MM/yyyy', { locale: it })}`
                )}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xl font-bold text-gray-900">
                {new Intl.NumberFormat('it-IT', {
                  style: 'currency',
                  currency: 'EUR',
                }).format(invoice.total_amount)}
              </p>
              {getRecipient() && (
                <p className={`text-xs truncate max-w-[150px] ${isWhatsApp ? 'text-emerald-600' : 'text-gray-500'}`} title={getRecipient()}>
                  {isWhatsApp && '💬 '}{getRecipient()}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Tone selector — hidden for WhatsApp */}
        {!isWhatsApp && (
          <div className="px-6 py-4 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-700 mb-2">Tono del messaggio</p>
            <div className="flex gap-2">
              {(Object.keys(TONE_LABELS) as Tone[]).map((t) => (
                <button
                  key={t}
                  onClick={() => handleToneChange(t)}
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
        )}

        {/* WhatsApp info badge */}
        {isWhatsApp && paymentLink && (
          <div className="mx-6 mt-4 px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-xl">
            <p className="text-xs text-emerald-700">
              💡 <strong>Anteprima WhatsApp:</strong> il messaggio include il link di pagamento diretto.
            </p>
            <p className="text-xs text-emerald-600 mt-1 truncate">
              🔗 {paymentLink}
            </p>
          </div>
        )}

        {/* Channel selector */}
        {availableChannels.length > 1 && (
          <div className="px-6 py-4 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-700 mb-2">Canale di invio</p>
            <div className="flex gap-2">
              {availableChannels.map((c) => {
                const isWA = c === 'whatsapp'
                const isActive = activeChannel === c
                return (
                  <button
                    key={c}
                    onClick={() => handleChannelChange(c)}
                    className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? isWA
                          ? 'bg-emerald-600 text-white shadow-md'
                          : 'bg-primary-600 text-white shadow-md'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {CHANNEL_LABELS[c]}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Message preview (editable) */}
        <div className="px-6 py-4">
          <p className={`text-sm font-medium mb-2 ${isWhatsApp ? 'text-emerald-700' : 'text-gray-700'}`}>
            {isWhatsApp ? 'Messaggio WhatsApp' : 'Anteprima messaggio'}
          </p>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={isWhatsApp ? 3 : 4}
            className={`w-full rounded-xl p-4 text-sm leading-relaxed border resize-none focus:outline-none focus:ring-2 ${
              isWhatsApp
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200 focus:ring-emerald-500 focus:border-emerald-500'
                : 'bg-gray-50 text-gray-700 border-gray-200 focus:ring-primary-500 focus:border-primary-500'
            }`}
            placeholder={isWhatsApp ? 'Il messaggio WhatsApp...' : 'Il messaggio di sollecito...'}
          />
          <p className="text-xs text-gray-400 mt-2">
            Il messaggio sarà inviato a: <span className={`font-medium ${isWhatsApp ? 'text-emerald-600' : 'text-gray-600'}`}>{getRecipient()}</span>
          </p>
        </div>

        {/* Actions */}
        <div className={`px-6 py-4 border-t flex gap-3 ${isWhatsApp ? 'border-emerald-100 bg-emerald-50/30' : 'border-gray-100 bg-gray-50'}`}>
          <Button variant="outline" onClick={onClose} className="flex-1">
            Annulla
          </Button>
          <Button
            onClick={handleSend}
            disabled={sending || remindMutation.isPending}
            className={`flex-1 ${isWhatsApp ? 'bg-emerald-600 hover:bg-emerald-700 border-emerald-600' : ''}`}
          >
            {sending || remindMutation.isPending ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Invio...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                {isWhatsApp ? (
                  <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
                    <path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.853 5.067 2.33 7.113L.789 23.492a.75.75 0 00.917.918l4.38-1.54A11.955 11.955 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0z"/>
                  </svg>
                ) : (
                  <Send className="w-4 h-4" />
                )}
                {isWhatsApp ? 'Invia WhatsApp' : 'Invia Sollecito'}
              </span>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
