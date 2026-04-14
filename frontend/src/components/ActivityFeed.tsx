import { useState } from 'react'
import { Card, CardContent } from '../components/ui'
import {
  CheckCircle2, AlertTriangle, Bell, FileText,
  Zap, ArrowUpRight
} from 'lucide-react'
import { format, differenceInMinutes } from 'date-fns'
import { it } from 'date-fns/locale'
import { formatCurrency } from '../lib/utils'

interface ActivityEvent {
  id: string
  type: 'payment_received' | 'invoice_overdue' | 'sollecito_sent' | 'sdi_received' | 'invoice_created' | 'client_added'
  title: string
  description: string
  amount?: number
  time: Date
  meta?: string
}

function generateMockEvents(): ActivityEvent[] {
  const now = new Date()
  return [
    {
      id: '1',
      type: 'payment_received',
      title: 'Pagamento ricevuto',
      description: 'Tech Solutions S.r.l.',
      amount: 5200,
      time: new Date(now.getTime() - 12 * 60 * 1000),
      meta: 'FT/2026/0001',
    },
    {
      id: '2',
      type: 'sdi_received',
      title: 'Fattura SDI ricevuta',
      description: 'Nuova fattura da Fornitore XYZ',
      amount: 1850,
      time: new Date(now.getTime() - 45 * 60 * 1000),
      meta: 'FT/2026/0008',
    },
    {
      id: '3',
      type: 'invoice_overdue',
      title: 'Fattura scaduta',
      description: 'MarketingPro S.r.l.',
      amount: 3400,
      time: new Date(now.getTime() - 3 * 60 * 60 * 1000),
      meta: '3 giorni fa',
    },
    {
      id: '4',
      type: 'sollecito_sent',
      title: 'Sollecito inviato',
      description: 'Campagne Web S.r.l. — sollecito livello 2',
      amount: 2100,
      time: new Date(now.getTime() - 6 * 60 * 60 * 1000),
    },
    {
      id: '5',
      type: 'invoice_created',
      title: 'Fattura creata',
      description: 'Nuova fattura per GlobalTrade S.p.A.',
      amount: 6700,
      time: new Date(now.getTime() - 24 * 60 * 60 * 1000),
      meta: 'FT/2026/0010',
    },
    {
      id: '6',
      type: 'client_added',
      title: 'Nuovo cliente',
      description: 'Logistica Express S.r.l. aggiunto',
      time: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000),
    },
  ]
}

const EVENT_CONFIG = {
  payment_received: {
    icon: CheckCircle2,
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    pulse: 'bg-emerald-500',
    label: 'Pagamento',
  },
  sdi_received: {
    icon: Zap,
    color: 'text-violet-600',
    bg: 'bg-violet-50',
    border: 'border-violet-200',
    pulse: 'bg-violet-500',
    label: 'SDI',
  },
  invoice_overdue: {
    icon: AlertTriangle,
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    pulse: 'bg-red-500',
    label: 'Scaduto',
  },
  sollecito_sent: {
    icon: Bell,
    color: 'text-amber-600',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    pulse: 'bg-amber-500',
    label: 'Sollecito',
  },
  invoice_created: {
    icon: FileText,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    pulse: 'bg-blue-500',
    label: 'Creata',
  },
  client_added: {
    icon: ArrowUpRight,
    color: 'text-cyan-600',
    bg: 'bg-cyan-50',
    border: 'border-cyan-200',
    pulse: 'bg-cyan-500',
    label: 'Cliente',
  },
}

function timeAgo(date: Date): string {
  const mins = differenceInMinutes(new Date(), date)
  if (mins < 1) return 'Ora'
  if (mins < 60) return `${mins}m fa`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h fa`
  return format(date, 'd MMM', { locale: it })
}

export function ActivityFeed() {
  const [events] = useState<ActivityEvent[]>(generateMockEvents)
  const [live] = useState(true)

  return (
    <Card className="border border-gray-200 shadow-sm">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900">Attività</h3>
          {live && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 rounded-full">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-medium text-emerald-700">Live</span>
            </div>
          )}
        </div>
        <span className="text-xs text-gray-400">{events.length} eventi recenti</span>
      </div>
      <CardContent className="p-0">
        <div className="divide-y divide-gray-50">
          {events.map((event, idx) => {
            const cfg = EVENT_CONFIG[event.type]
            const Icon = cfg.icon
            const isFirst = idx === 0 && live

            return (
              <div key={event.id} className={`flex items-start gap-3 px-5 py-3.5 hover:bg-gray-50/60 transition-colors ${isFirst ? 'animate-[fadeIn_0.3s_ease-out]' : ''}`}>
                {/* Icon */}
                <div className="relative shrink-0 mt-0.5">
                  <div className={`w-8 h-8 rounded-xl ${cfg.bg} border ${cfg.border} flex items-center justify-center`}>
                    <Icon className={`w-4 h-4 ${cfg.color}`} />
                  </div>
                  {isFirst && (
                    <div className={`absolute -inset-1 ${cfg.pulse} rounded-xl opacity-30 animate-ping`} />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 leading-tight">{event.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5 leading-tight">{event.description}</p>
                      {event.meta && (
                        <p className="text-xs text-gray-400 mt-0.5 font-mono">{event.meta}</p>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      {event.amount && (
                        <p className={`text-sm font-bold ${event.type === 'payment_received' ? 'text-emerald-600' : 'text-gray-900'}`}>
                          {event.type === 'payment_received' ? '+' : ''}{formatCurrency(event.amount)}
                        </p>
                      )}
                      <p className="text-xs text-gray-400 mt-0.5">{timeAgo(event.time)}</p>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-gray-100 text-center">
          <button className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
            Vedi tutte le attività →
          </button>
        </div>
      </CardContent>
    </Card>
  )
}
