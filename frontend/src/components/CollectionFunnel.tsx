import { useMemo } from 'react'
import { Card, CardContent } from '../components/ui'
import { formatCurrency } from '../lib/utils'
import { ArrowDown, AlertTriangle, Clock, ShieldCheck, Zap } from 'lucide-react'

interface Invoice {
  id: number
  invoice_number: string
  customer_name: string
  total_amount: number
  due_date: string
  status: 'paid' | 'pending' | 'overdue'
  escalation_stage?: string
}

interface FunnelStage {
  label: string
  count: number
  amount: number
  color: string
  bg: string
  barColor: string
  border: string
  icon: typeof AlertTriangle
  sublabel: string
}

export function CollectionFunnel({ invoices }: { invoices: Invoice[] }) {
  const stages = useMemo<FunnelStage[]>(() => {
    const pending = invoices.filter(i => i.status === 'pending')
    const overdue = invoices.filter(i => i.status === 'overdue')
    const escalating = overdue.filter(i => i.escalation_stage && i.escalation_stage !== 'none')

    return [
      {
        label: 'Generate',
        count: pending.length + overdue.length,
        amount: [...pending, ...overdue].reduce((s, i) => s + i.total_amount, 0),
        color: 'text-blue-600',
        bg: 'bg-blue-50',
        barColor: 'bg-blue-500',
        border: 'border-blue-200',
        icon: Zap,
        sublabel: 'Fatture emesse',
      },
      {
        label: 'Pending',
        count: pending.length,
        amount: pending.reduce((s, i) => s + i.total_amount, 0),
        color: 'text-amber-600',
        bg: 'bg-amber-50',
        barColor: 'bg-amber-500',
        border: 'border-amber-200',
        icon: Clock,
        sublabel: 'In attesa',
      },
      {
        label: 'Overdue',
        count: overdue.length,
        amount: overdue.reduce((s, i) => s + i.total_amount, 0),
        color: 'text-red-600',
        bg: 'bg-red-50',
        barColor: 'bg-red-500',
        border: 'border-red-200',
        icon: AlertTriangle,
        sublabel: 'Scadute',
      },
      {
        label: 'Escalated',
        count: escalating.length,
        amount: escalating.reduce((s, i) => s + i.total_amount, 0),
        color: 'text-orange-600',
        bg: 'bg-orange-50',
        barColor: 'bg-orange-500',
        border: 'border-orange-200',
        icon: ShieldCheck,
        sublabel: 'In escalation',
      },
    ]
  }, [invoices])

  const totalOutstanding = stages[0].amount
  const recoveryRate = invoices.length > 0
    ? Math.round((invoices.filter(i => i.status === 'paid').length / invoices.length) * 100)
    : 0

  if (invoices.length === 0) {
    return (
      <Card className="border border-gray-200 shadow-sm">
        <div className="px-5 py-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">Funnel di incasso</h3>
          <p className="text-xs text-gray-500 mt-0.5">Dove sono i tuoi soldi</p>
        </div>
        <CardContent className="p-5 flex flex-col items-center justify-center py-8 text-center">
          <div className="w-12 h-12 rounded-2xl bg-violet-50 flex items-center justify-center mb-3">
            <ArrowDown className="w-5 h-5 text-violet-400" />
          </div>
          <p className="text-sm font-medium text-gray-900">Nessun dato disponibile</p>
          <p className="text-xs text-gray-500 mt-1">Importa le fatture per vedere il funnel</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border border-gray-200 shadow-sm">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900">Funnel di incasso</h3>
        <p className="text-xs text-gray-500 mt-0.5">Dove sono i tuoi soldi</p>
      </div>
      <CardContent className="p-5">
        {/* Recovery rate */}
        <div className="flex items-center justify-between mb-5 p-3 bg-gray-50 rounded-xl">
          <span className="text-sm text-gray-500">Tasso di recupero</span>
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-2 bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-700"
                style={{ width: `${recoveryRate}%` }}
              />
            </div>
            <span className="text-sm font-bold text-emerald-600">{recoveryRate}%</span>
          </div>
        </div>

        {/* Funnel stages */}
        <div className="space-y-2">
          {stages.map((stage, idx) => {
            const maxAmount = Math.max(...stages.map(s => s.amount), 1)
            const widthPct = Math.max((stage.amount / maxAmount) * 100, stage.count > 0 ? 30 : 0)
            const Icon = stage.icon

            return (
              <div key={stage.label} className="relative">
                {/* Connector arrow */}
                {idx < stages.length - 1 && stages[idx + 1].count > 0 && (
                  <div className="absolute left-1/2 -translate-x-1/2 -bottom-2 z-10">
                    <ArrowDown className="w-3 h-3 text-gray-300" />
                  </div>
                )}

                <div className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${stage.border} ${stage.bg}`}>
                  <div className={`shrink-0 w-8 h-8 rounded-lg ${stage.bg} border ${stage.border} flex items-center justify-center`}>
                    <Icon className={`w-4 h-4 ${stage.color}`} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-sm font-semibold text-gray-900">{stage.label}</span>
                      <span className="text-xs text-gray-600">{stage.sublabel}</span>
                    </div>
                    {/* Bar */}
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden mt-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all duration-700 ${stage.barColor}`}
                        style={{ width: `${widthPct}%` }}
                      />
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <p className={`text-sm font-bold ${stage.color}`}>{stage.count}</p>
                    <p className="text-xs text-gray-400">{formatCurrency(stage.amount)}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Total */}
        <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
          <span className="text-sm font-medium text-gray-500">Totale da incassare</span>
          <span className="text-xl font-bold text-gray-900">{formatCurrency(totalOutstanding)}</span>
        </div>
      </CardContent>
    </Card>
  )
}
