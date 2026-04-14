import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { EscalationTimeline, EscalationBadge } from '../components/EscalationTimeline'
import { useToast } from '../components/ui/toast'
import {
  AlertTriangle, Euro, Users, Clock,
  Search, ChevronDown, Check, Bell,
  Gavel, Mail, X, RefreshCw,
  FileText, Loader2,
} from 'lucide-react'
import { format } from 'date-fns'
import { it } from 'date-fns/locale'
import { Link } from 'react-router-dom'

// ─── Types ────────────────────────────────────────────────────────────────────

interface StageSummary {
  stage: string
  stage_label: string
  stage_color: string
  invoice_count: number
  total_amount: number
}

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

interface CollectionInvoice {
  id: number
  invoice_number: string
  customer_name: string
  total_amount: number
  due_date: string
  status: string
  days_overdue: number
  escalation_stage: string
  escalation_label: string
  escalation_color: string
  trust_score: number
  reminder_count: number
}

interface AvailableAction {
  action: string
  action_label: string
  action_description: string
  available: boolean
  reason?: string
}

interface AvailableActionsResponse {
  invoice_id: number
  escalation_stage: string
  escalation_label: string
  escalation_color: string
  days_overdue: number
  actions: AvailableAction[]
}

// ─── Utils ────────────────────────────────────────────────────────────────────

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)
}

function formatDate(dateStr: string) {
  return format(new Date(dateStr), 'dd/MM/yyyy', { locale: it })
}

function TrustBadge({ score }: { score: number }) {
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#eab308' : score >= 40 ? '#f97316' : '#ef4444'
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold"
      style={{ backgroundColor: `${color}20`, color }}
    >
      {score}
    </span>
  )
}

// ─── Action Dropdown ──────────────────────────────────────────────────────────

function ActionDropdown({ invoice, onAction }: { invoice: CollectionInvoice; onAction: () => void }) {
  const [open, setOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const { showToast } = useToast()

  const { data: actionsData } = useQuery<AvailableActionsResponse>({
    queryKey: ['collection-actions', invoice.id],
    queryFn: async () => {
      const response = await api.get('/api/v1/admin/actions/available', {
        params: { invoice_id: invoice.id },
      })
      return response.data
    },
    enabled: open,
  })

  const executeMutation = useMutation({
    mutationFn: async (action: string) => {
      const response = await api.post('/api/v1/admin/actions/execute', {
        action,
        invoice_id: invoice.id,
      })
      return response.data
    },
    onSuccess: (data) => {
      showToast(data.message, 'success')
      setOpen(false)
      onAction()
    },
    onError: () => {
      showToast('Errore durante lesecuzione dellazione', 'error')
    },
  })

  const getActionIcon = (action: string) => {
    if (action === 'mark_paid') return <Check className="w-3 h-3 text-green-600" />
    if (action.includes('reminder') || action === 'send_diffida') return <Mail className="w-3 h-3 text-blue-600" />
    if (action === 'apply_penalty') return <Euro className="w-3 h-3 text-orange-600" />
    if (action === 'prepare_legal' || action === 'mark_uncollectible') return <Gavel className="w-3 h-3 text-red-600" />
    return <Bell className="w-3 h-3" />
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        size="sm"
        variant="outline"
        onClick={() => setOpen(!open)}
        className="h-7 text-xs gap-1"
      >
        Azione
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </Button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-gray-200 rounded-lg shadow-lg w-64 py-1">
            {/* Escalation info */}
            <div className="px-3 py-2 border-b border-gray-100">
              <EscalationBadge
                stage={invoice.escalation_stage}
                label={invoice.escalation_label}
                color={invoice.escalation_color}
                size="sm"
              />
              <p className="text-[10px] text-gray-500 mt-1">
                {invoice.days_overdue} giorni di ritardo
              </p>
            </div>

            {/* Actions */}
            {!actionsData ? (
              <div className="p-3 flex justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
              </div>
            ) : (
              actionsData.actions.map((a) => (
                <button
                  key={a.action}
                  disabled={!a.available || executeMutation.isPending}
                  onClick={() => executeMutation.mutate(a.action)}
                  className="w-full px-3 py-2 flex items-center gap-2 text-left hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {getActionIcon(a.action)}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900">{a.action_label}</p>
                    <p className="text-[10px] text-gray-500 truncate">{a.action_description}</p>
                  </div>
                  {executeMutation.isPending && executeMutation.variables === a.action && (
                    <Loader2 className="w-3 h-3 animate-spin text-gray-400" />
                  )}
                </button>
              ))
            )}

            <div className="border-t border-gray-100 mt-1 pt-1">
              <Link
                to={`/invoices/${invoice.id}`}
                onClick={() => setOpen(false)}
                className="px-3 py-2 flex items-center gap-2 text-xs text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <FileText className="w-3 h-3" />
                Vedi dettaglio fattura
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KPICard({
  icon: Icon,
  label,
  value,
  subValue,
  color,
  bgColor,
}: {
  icon: React.ElementType
  label: string
  value: string
  subValue?: string
  color: string
  bgColor: string
}) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg shrink-0" style={{ backgroundColor: bgColor }}>
            <Icon className="w-5 h-5" style={{ color }} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500">{label}</p>
            {subValue && <p className="text-[10px] text-gray-400">{subValue}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Stage Bar ───────────────────────────────────────────────────────────────

function StageBar({ stages }: { stages: StageSummary[] }) {
  const total = stages.reduce((sum, s) => sum + s.invoice_count, 0)
  if (total === 0) return null

  return (
    <div className="flex items-center gap-1 h-8 rounded-full overflow-hidden">
      {stages.map((s) => {
        const pct = (s.invoice_count / total) * 100
        if (pct === 0) return null
        return (
          <div
            key={s.stage}
            className="h-full flex items-center justify-center group relative"
            style={{ width: `${pct}%`, backgroundColor: s.stage_color }}
            title={`${s.stage_label}: ${s.invoice_count} fatture (${formatCurrency(s.total_amount)})`}
          >
            <span className="text-[10px] font-semibold text-white">{s.invoice_count}</span>
            {/* Tooltip */}
            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-[10px] rounded px-2 py-1 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
              {s.stage_label}: {formatCurrency(s.total_amount)}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function AdminCollectionPage() {
  const queryClient = useQueryClient()

  const [stageFilter, setStageFilter] = useState('')
  const [clientFilter, setClientFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState<'due_date' | 'days_overdue' | 'total_amount'>('days_overdue')

  const { data: summary, isLoading: summaryLoading } = useQuery<CollectionSummary>({
    queryKey: ['collection-summary'],
    queryFn: async () => {
      const response = await api.get('/api/v1/admin/collection-summary')
      return response.data
    },
  })

  const { data: invoicesData, isLoading: invoicesLoading, refetch } = useQuery({
    queryKey: ['collection-invoices', { stage: stageFilter, client: clientFilter, dateFrom, dateTo, page, sortBy }],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, page_size: 50 }
      if (stageFilter) params.stage = stageFilter
      if (clientFilter) params.client_name = clientFilter
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      const response = await api.get('/api/v1/admin/collection-invoices', { params })
      let items: CollectionInvoice[] = response.data.items
      
      // Sort
      items = [...items].sort((a, b) => {
        if (sortBy === 'days_overdue') return b.days_overdue - a.days_overdue
        if (sortBy === 'total_amount') return b.total_amount - a.total_amount
        return new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
      })
      
      return { ...response.data, items }
    },
  })

  const handleRefresh = () => {
    refetch()
    queryClient.invalidateQueries({ queryKey: ['collection-summary'] })
  }

  const clearFilters = () => {
    setStageFilter('')
    setClientFilter('')
    setDateFrom('')
    setDateTo('')
    setPage(1)
  }

  const hasFilters = stageFilter || clientFilter || dateFrom || dateTo

  const STAGE_OPTIONS = [
    { value: '', label: 'Tutti gli stadi' },
    { value: 'stage_1', label: '1° Sollecito (verde)' },
    { value: 'stage_2', label: '2° Sollecito (giallo)' },
    { value: 'stage_3', label: 'Diffida (arancione)' },
    { value: 'stage_4', label: 'Presidio Legale (rosso)' },
    { value: 'stage_5', label: 'Recupero Legale (nero)' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestione Recovery</h1>
          <p className="text-sm text-gray-500">Monitoraggio escalation e azioni di recupero credito</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} className="gap-2">
          <RefreshCw className="w-3 h-3" />
          Aggiorna
        </Button>
      </div>

      {/* Escalation Timeline */}
      <Card>
        <CardContent className="p-4">
          <p className="text-xs font-medium text-gray-500 mb-3 uppercase tracking-wide">Stato Escalation</p>
          <EscalationTimeline currentStage={summary?.stages.find(s => s.invoice_count > 0)?.stage || 'none'} />
          {summary?.stages && <StageBar stages={summary.stages} />}
        </CardContent>
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4 animate-pulse">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gray-200 rounded-lg" />
                  <div className="flex-1">
                    <div className="h-6 bg-gray-200 rounded w-20 mb-1" />
                    <div className="h-3 bg-gray-200 rounded w-16" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <KPICard
              icon={Euro}
              label="Totale Insoluto"
              value={formatCurrency(summary?.total_insoluto || 0)}
              subValue={`${summary?.total_overdue_count || 0} fatture`}
              color="#ef4444"
              bgColor="#fee2e2"
            />
            <KPICard
              icon={AlertTriangle}
              label="Fatture Scadute"
              value={String(summary?.total_overdue_count || 0)}
              subValue={`${summary?.avg_days_overdue || 0}gg media ritardo`}
              color="#f97316"
              bgColor="#ffedd5"
            />
            <KPICard
              icon={Users}
              label="Clienti a Rischio"
              value={String(summary?.risk_client_count || 0)}
              subValue="top 10 per esposizione"
              color="#eab308"
              bgColor="#fef9c3"
            />
            <KPICard
              icon={Clock}
              label="Media Ritardo"
              value={`${summary?.avg_days_overdue || 0}gg`}
              subValue="giorni scadenza superata"
              color="#6b7280"
              bgColor="#f3f4f6"
            />
          </>
        )}
      </div>

      {/* Top Risk Clients */}
      {summary?.top_risk_clients && summary.top_risk_clients.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-500" />
              Top 10 Clienti a Rischio
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-2">
              {summary.top_risk_clients.slice(0, 10).map((client) => (
                <Link
                  key={client.client_id}
                  to={`/clients/${client.client_id}`}
                  className="p-3 rounded-lg border border-gray-100 hover:border-orange-200 hover:bg-orange-50/50 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-900 truncate">
                      {client.client_name}
                    </span>
                    <TrustBadge score={client.trust_score} />
                  </div>
                  <p className="text-sm font-bold text-red-600">
                    {formatCurrency(client.total_insoluto)}
                  </p>
                  <p className="text-[10px] text-gray-500">
                    {client.overdue_invoice_count}fatt. · {client.days_avg_overdue}gg avg
                  </p>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col lg:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Cerca cliente..."
                value={clientFilter}
                onChange={(e) => { setClientFilter(e.target.value); setPage(1) }}
                className="pl-10"
              />
            </div>
            <select
              value={stageFilter}
              onChange={(e) => { setStageFilter(e.target.value); setPage(1) }}
              className="px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {STAGE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Da:</span>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
                className="w-auto"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">A:</span>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
                className="w-auto"
              />
            </div>
            {hasFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters} className="gap-1">
                <X className="w-3 h-3" />
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Invoices Table */}
      <Card>
        <CardHeader className="pb-0">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">
              Fatture Scadute
              {invoicesData?.items && (
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({invoicesData.total})
                </span>
              )}
            </CardTitle>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-500">Ordina:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="text-xs border border-gray-200 rounded px-2 py-1 bg-white"
              >
                <option value="days_overdue">Ritardo</option>
                <option value="due_date">Scadenza</option>
                <option value="total_amount">Importo</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {invoicesLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
          ) : invoicesData?.items?.length === 0 ? (
            <div className="text-center py-16">
              <Check className="w-12 h-12 mx-auto mb-3 text-green-400" />
              <h3 className="text-lg font-medium text-gray-900">Nessuna fattura scaduta</h3>
              <p className="text-gray-500 text-sm mt-1">Tutto in regola!</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/50">
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Fattura</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Cliente</th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Importo</th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Scadenza</th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Ritardo</th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Stadio</th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Score</th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Solleciti</th>
                    <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Azioni</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {invoicesData?.items?.map((invoice: CollectionInvoice) => (
                    <tr
                      key={invoice.id}
                      className="hover:bg-gray-50/80 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <Link
                          to={`/invoices/${invoice.id}`}
                          className="font-medium text-gray-900 hover:text-blue-600 transition-colors"
                        >
                          {invoice.invoice_number}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/clients/${invoice.id}`}
                          className="text-gray-700 hover:text-blue-600 transition-colors"
                        >
                          {invoice.customer_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-gray-900">
                        {formatCurrency(invoice.total_amount)}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-500 text-xs">
                        {formatDate(invoice.due_date)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold"
                          style={{
                            backgroundColor: invoice.days_overdue > 30 ? '#fee2e2' : invoice.days_overdue > 15 ? '#ffedd5' : invoice.days_overdue > 7 ? '#fef9c3' : '#f0fdf4',
                            color: invoice.days_overdue > 30 ? '#991b1b' : invoice.days_overdue > 15 ? '#c2410c' : invoice.days_overdue > 7 ? '#a16207' : '#166534',
                          }}
                        >
                          +{invoice.days_overdue}gg
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <EscalationBadge
                          stage={invoice.escalation_stage}
                          label={invoice.escalation_label}
                          color={invoice.escalation_color}
                          size="sm"
                        />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <TrustBadge score={invoice.trust_score} />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-xs text-gray-500">
                          {invoice.reminder_count > 0 ? `${invoice.reminder_count}✉` : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <ActionDropdown
                          invoice={invoice}
                          onAction={() => {
                            refetch()
                            queryClient.invalidateQueries({ queryKey: ['collection-summary'] })
                          }}
                        />
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
