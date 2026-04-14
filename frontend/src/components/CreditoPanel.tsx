import { useMemo } from 'react'
import { TrustScoreBadge } from './TrustScoreBadge'
import { Card, CardContent, CardHeader, CardTitle } from './ui'
import { AlertCircle, TrendingUp, ChevronRight } from 'lucide-react'
import { formatCurrency } from '../lib/utils'
import { Link } from 'react-router-dom'

interface CreditoPanelProps {
  invoices: Array<{
    id: number
    customer_name: string
    total_amount: number
    due_date: string
    status: string
    trust_score: number
  }>
}

function aggregateTrustScore(invoices: CreditoPanelProps['invoices']): number {
  if (!invoices.length) return 0
  const scores = invoices.filter(i => i.trust_score > 0).map(i => i.trust_score)
  if (!scores.length) return 0
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
}

function getClientStats(invoices: CreditoPanelProps['invoices']) {
  const clientMap = new Map<string, { score: number; outstanding: number; overdue: number; count: number }>()
  invoices.forEach(inv => {
    const existing = clientMap.get(inv.customer_name) || { score: inv.trust_score || 0, outstanding: 0, overdue: 0, count: 0 }
    existing.outstanding += inv.total_amount
    if (inv.status === 'overdue') existing.overdue += 1
    existing.count += 1
    clientMap.set(inv.customer_name, existing)
  })
  return Array.from(clientMap.entries())
    .map(([name, data]) => ({
      name,
      trust_score: data.score,
      total_outstanding: data.outstanding,
      overdue_count: data.overdue,
      invoice_count: data.count,
    }))
    .sort((a, b) => a.trust_score - b.trust_score)
}

export function CreditoPanel({ invoices }: CreditoPanelProps) {
  const trustScore = useMemo(() => aggregateTrustScore(invoices), [invoices])
  const clientStats = useMemo(() => getClientStats(invoices), [invoices])

  const atRisk = clientStats.filter(c => c.trust_score < 60)
  const safe = clientStats.filter(c => c.trust_score >= 80)
  const totalOutstanding = invoices
    .filter(i => i.status !== 'paid')
    .reduce((sum, i) => sum + i.total_amount, 0)
  const overdueAmount = invoices
    .filter(i => i.status === 'overdue')
    .reduce((sum, i) => sum + i.total_amount, 0)

  const scoreColor = trustScore >= 80 ? 'text-emerald-600' : trustScore >= 60 ? 'text-blue-600' : trustScore >= 40 ? 'text-amber-600' : 'text-red-600'
  const barColor = trustScore >= 80 ? 'bg-emerald-500' : trustScore >= 60 ? 'bg-blue-500' : trustScore >= 40 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="space-y-3">
      {/* ── Main Trust Score Card ── */}
      <Card className="border border-gray-200 shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
                Affidabilità Media Clienti
              </p>
              <div className="flex items-baseline gap-2">
                <span className={`text-5xl font-bold tabular-nums ${scoreColor}`}>
                  {trustScore}
                </span>
                <span className="text-lg text-gray-400">/100</span>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                su {invoices.length} fatture analizzate
              </p>
            </div>
            <TrustScoreBadge score={trustScore} size="lg" showLabel />
          </div>

          {/* Score bar */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-gray-400">
              <span>Rischioso</span>
              <span>Sicuro</span>
            </div>
            <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
              <div
                className={`h-2.5 rounded-full ${barColor} transition-all duration-500`}
                style={{ width: `${trustScore}%` }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Stats row ── */}
      <div className="grid grid-cols-3 gap-2">
        <Card className="border border-gray-200 shadow-sm">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-gray-400 mb-1">Da ricevere</p>
            <p className="text-base font-bold text-gray-900 tabular-nums">{formatCurrency(totalOutstanding)}</p>
          </CardContent>
        </Card>
        <Card className="border border-red-200 shadow-sm bg-red-50/50">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-red-400 mb-1">Scaduti</p>
            <p className="text-base font-bold text-red-600 tabular-nums">{formatCurrency(overdueAmount)}</p>
          </CardContent>
        </Card>
        <Card className="border border-gray-200 shadow-sm">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-gray-400 mb-1">Clienti</p>
            <p className="text-base font-bold text-gray-900 tabular-nums">{clientStats.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* ── At Risk Clients ── */}
      {atRisk.length > 0 && (
        <Card className="border border-red-200 shadow-sm">
          <CardHeader className="pb-2 px-4 pt-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500" />
              Da monitorare ({atRisk.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-1">
            {atRisk.slice(0, 4).map((client) => (
              <Link
                key={client.name}
                to="/clients"
                className="flex items-center justify-between py-2 px-2 rounded-lg hover:bg-red-50/50 transition-colors group"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <TrustScoreBadge score={client.trust_score} size="sm" showLabel={false} />
                  <span className="text-sm font-medium text-gray-700 truncate">{client.name}</span>
                  {client.overdue_count > 0 && (
                    <span className="text-xs text-red-500 font-semibold shrink-0">
                      {client.overdue_count} scad.
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 text-gray-400 group-hover:text-gray-600 transition-colors">
                  <span className="text-xs font-semibold tabular-nums">{formatCurrency(client.total_outstanding)}</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>
      )}

      {/* ── Safe Clients ── */}
      {safe.length > 0 && (
        <Card className="border border-emerald-200 shadow-sm">
          <CardHeader className="pb-2 px-4 pt-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              Affidabili ({safe.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-1">
            {safe.slice(0, 3).map((client) => (
              <div
                key={client.name}
                className="flex items-center justify-between py-2 px-2"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <TrustScoreBadge score={client.trust_score} size="sm" showLabel={false} />
                  <span className="text-sm font-medium text-gray-700 truncate">{client.name}</span>
                </div>
                <span className="text-xs text-gray-400 tabular-nums font-medium">
                  {formatCurrency(client.total_outstanding)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
