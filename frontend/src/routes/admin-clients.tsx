import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui'
import { Input } from '../components/ui/input'
import { TrustScoreBadge } from '../components/TrustScoreBadge'
import {
  Search, Users, AlertTriangle, RefreshCw,
  Loader2, ChevronRight, Euro, Clock, FileText,
} from 'lucide-react'
import { Link } from 'react-router-dom'

// ─── Types ─────────────────────────────────────────────────────────────────────

interface ClientRisk {
  client_id: number
  client_name: string
  trust_score: number
  total_insoluto: number
  overdue_invoice_count: number
  days_avg_overdue: number
}

interface CollectionSummary {
  total_insoluto: number
  total_overdue_count: number
  total_overdue_amount: number
  risk_client_count: number
  avg_days_overdue: number
  stages: StageSummary[]
  top_risk_clients: ClientRisk[]
}

interface StageSummary {
  stage: string
  stage_label: string
  stage_color: string
  invoice_count: number
  total_amount: number
}

interface ClientListItem {
  id: number
  name: string
  vat: string
  fiscal_code: string
  email: string
  phone: string
  pec: string
  sdi: string
  address: string
  trust_score: number
  payment_pattern: string
  notes: string
  is_new: boolean
  created_at: string
  updated_at: string
}

// ─── Utils ─────────────────────────────────────────────────────────────────────

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)
}

function RiskScoreBadge({ score }: { score: number }) {
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#eab308' : score >= 40 ? '#f97316' : '#ef4444'
  const label = score >= 80 ? 'Basso' : score >= 60 ? 'Medio' : score >= 40 ? 'Alto' : 'Critico'
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold"
      style={{ backgroundColor: `${color}20`, color }}
    >
      {label}
    </span>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function AdminClientsPage() {
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'risk' | 'name' | 'insoluto'>('risk')

  // Get collection summary for top risk clients
  const { data: summary, isLoading: summaryLoading, isError, refetch } = useQuery<CollectionSummary>({
    queryKey: ['collection-summary'],
    queryFn: async () => {
      const response = await api.get('/api/v1/admin/collection-summary')
      return response.data
    },
  })

  // Get all clients from regular clients endpoint
  const { data: allClientsData, isLoading: clientsLoading } = useQuery({
    queryKey: ['clients', { search }],
    queryFn: async () => {
      const params: Record<string, string | number> = { page: 1, page_size: 100 }
      if (search) params.search = search
      const response = await api.get('/api/v1/clients', { params })
      return response.data
    },
  })

  // Build enriched client list with risk data
  const enrichedClients = (() => {
    if (!allClientsData?.items) return []
    const riskMap = new Map(
      (summary?.top_risk_clients || []).map(c => [c.client_name, c])
    )

    return allClientsData.items.map((client: ClientListItem) => {
      const riskData = riskMap.get(client.name)
      return {
        ...client,
        total_insoluto: riskData?.total_insoluto || 0,
        overdue_invoice_count: riskData?.overdue_invoice_count || 0,
        days_avg_overdue: riskData?.days_avg_overdue || 0,
        has_overdue: (riskData?.overdue_invoice_count || 0) > 0,
      }
    })
  })()

  // Sort clients
  const sortedClients = [...enrichedClients].sort((a, b) => {
    if (sortBy === 'risk') {
      // Risk = low trust_score + high insoluto
      const riskA = a.trust_score - a.total_insoluto / 1000
      const riskB = b.trust_score - b.total_insoluto / 1000
      return riskA - riskB
    }
    if (sortBy === 'insoluto') return b.total_insoluto - a.total_insoluto
    return a.name.localeCompare(b.name)
  })

  // Separate at-risk clients (have overdue invoices)
  const atRiskClients = sortedClients.filter(c => c.has_overdue)
  const healthyClients = sortedClients.filter(c => !c.has_overdue)
  const displayClients = sortBy === 'risk' ? [...atRiskClients, ...healthyClients] : sortedClients

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clienti e Rischio</h1>
          <p className="text-sm text-gray-500">Analisi clienti per rischio di credito e storico pagamenti</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${summaryLoading ? 'animate-spin' : ''}`} />
          Aggiorna
        </button>
      </div>

      {/* Error Banner */}
      {isError && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
          <p className="text-sm text-red-700">Impossibile caricare i dati di rischio creditizio</p>
          <button onClick={() => refetch()} className="ml-auto text-xs text-red-600 font-medium hover:underline">Riprova</button>
        </div>
      )}

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-orange-200 bg-gradient-to-br from-orange-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-100">
                <AlertTriangle className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{atRiskClients.length}</p>
                <p className="text-xs text-gray-500">Clienti a rischio</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-red-200 bg-gradient-to-br from-red-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-100">
                <Euro className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-xl font-bold text-gray-900">{formatCurrency(summary?.total_insoluto || 0)}</p>
                <p className="text-xs text-gray-500">Totale insoluto</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-yellow-200 bg-gradient-to-br from-yellow-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-yellow-100">
                <Clock className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{summary?.avg_days_overdue || 0}gg</p>
                <p className="text-xs text-gray-500">Ritardo medio</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-green-200 bg-gradient-to-br from-green-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-100">
                <Users className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{healthyClients.length}</p>
                <p className="text-xs text-gray-500">Clienti in regola</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Sort */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Cerca cliente per nome, partita IVA..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Ordina:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="risk">Per rischio</option>
                <option value="name">Per nome</option>
                <option value="insoluto">Per insoluto</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Clients Table */}
      <Card>
        <CardHeader className="pb-0">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="w-4 h-4 text-blue-500" />
            Anagrafica Clienti
            <span className="text-sm font-normal text-gray-500">
              ({displayClients.length})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {clientsLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
          ) : displayClients.length === 0 ? (
            <div className="text-center py-16">
              <Users className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-900">Nessun cliente</h3>
              <p className="text-gray-500 text-sm mt-1">Non hai ancora clienti registrati</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/50">
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Cliente</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">P.IVA / CF</th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Trust Score</th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Stato Rischio</th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Totale Insoluto</th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Fatt. Scadute</th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Ritardo Avg</th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Pattern</th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {displayClients.map((client) => (
                    <tr
                      key={client.id}
                      className={`hover:bg-gray-50/80 transition-colors ${client.has_overdue ? 'bg-red-50/30' : ''}`}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {client.has_overdue && (
                            <AlertTriangle className="w-3.5 h-3.5 text-orange-500 shrink-0" />
                          )}
                          <div>
                            <Link
                              to={`/clients/${client.id}`}
                              className="font-medium text-gray-900 hover:text-blue-600 transition-colors"
                            >
                              {client.name}
                            </Link>
                            {client.is_new && (
                              <span className="ml-1.5 text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded font-medium">
                                NEW
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        <div>{client.vat || '—'}</div>
                        <div className="text-gray-400">{client.fiscal_code || '—'}</div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <TrustScoreBadge score={client.trust_score} size="sm" />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <RiskScoreBadge score={client.trust_score} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        {client.total_insoluto > 0 ? (
                          <span className="font-medium text-red-600">
                            {formatCurrency(client.total_insoluto)}
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {client.overdue_invoice_count > 0 ? (
                          <span className="inline-flex items-center gap-1 text-orange-600 font-medium">
                            <FileText className="w-3 h-3" />
                            {client.overdue_invoice_count}
                          </span>
                        ) : (
                          <span className="text-gray-400">0</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {client.days_avg_overdue > 0 ? (
                          <span className="text-orange-600 font-medium">
                            {client.days_avg_overdue}gg
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-xs text-gray-500">
                          {client.payment_pattern
                            ? client.payment_pattern.replace(/_/g, ' ')
                            : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/clients/${client.id}`}
                          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 font-medium"
                        >
                          Dettaglio
                          <ChevronRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
