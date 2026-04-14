import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, AlertTriangle, CheckCircle, Clock, Ban, Gavel, ShieldAlert, Loader2, ArrowRight } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { api } from '../lib/api'
import { EscalationStage } from '../lib/types'
import { formatCurrency } from '../lib/utils'
import { format, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'
import { useToast } from '../components/ui/toast'

// Stage configuration: labels, icons, colors, urgency level
const STAGE_CONFIG: Record<EscalationStage, {
  label: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  color: string        // Tailwind color classes
  bgColor: string      // Background color
  borderColor: string  // Border color
  urgency: 'ok' | 'warning' | 'critical'
}> = {
  none: {
    label: 'Regolare',
    description: 'Fattura in regola, nessuna azione necessaria',
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    urgency: 'ok',
  },
  sollecito_1: {
    label: '1° Sollecito',
    description: 'Primo sollecito di pagamento inviato',
    icon: Clock,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    urgency: 'warning',
  },
  sollecito_2: {
    label: '2° Sollecito',
    description: 'Secondo sollecito di pagamento - sollecito finale',
    icon: Clock,
    color: 'text-orange-500',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    urgency: 'warning',
  },
  penalty_applicata: {
    label: 'Penalty',
    description: 'Interessi di mora applicati per ritardo',
    icon: AlertTriangle,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-300',
    urgency: 'warning',
  },
  diffida: {
    label: 'Diffida',
    description: 'Diffida formale al pagamento',
    icon: ShieldAlert,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-300',
    urgency: 'critical',
  },
  stop_servizi: {
    label: 'Stop Servizi',
    description: 'Servizi sospesi - riattivazione solo dopo pagamento',
    icon: Ban,
    color: 'text-red-700',
    bgColor: 'bg-red-100',
    borderColor: 'border-red-400',
    urgency: 'critical',
  },
  legal_action: {
    label: 'Azione Legale',
    description: 'Avvio procedura legale per recupero credito',
    icon: Gavel,
    color: 'text-red-800',
    bgColor: 'bg-red-100',
    borderColor: 'border-red-600',
    urgency: 'critical',
  },
}

// Ordered list of all stages for the timeline
const STAGE_ORDER: EscalationStage[] = [
  'none',
  'sollecito_1',
  'sollecito_2',
  'penalty_applicata',
  'diffida',
  'stop_servizi',
  'legal_action',
]

function getStageIndex(stage: EscalationStage): number {
  return STAGE_ORDER.indexOf(stage)
}

function EscalationBadge({ stage }: { stage: EscalationStage }) {
  const config = STAGE_CONFIG[stage]
  if (!config) return null
  const Icon = config.icon
  return (
    <Badge className={`${config.bgColor} ${config.color} border ${config.borderColor} gap-1.5 text-xs font-medium`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </Badge>
  )
}

interface EscalationTimelineProps {
  currentStage: EscalationStage
}

function EscalationTimeline({ currentStage }: EscalationTimelineProps) {
  const currentIdx = getStageIndex(currentStage)
  // Filter out 'none' from display since it's just "OK" state
  const displayStages = STAGE_ORDER.filter(s => s !== 'none')

  return (
    <div className="w-full">
      <div className="flex items-center justify-between">
        {displayStages.map((stage, i) => {
          const config = STAGE_CONFIG[stage]
          const Icon = config.icon
          const stageIdx = getStageIndex(stage)
          const isCompleted = stageIdx < currentIdx
          const isCurrent = stageIdx === currentIdx

          let barColor = 'bg-gray-200'
          if (isCompleted) barColor = 'bg-green-500'
          else if (isCurrent) barColor = config.urgency === 'critical' ? 'bg-red-500' : config.urgency === 'warning' ? 'bg-yellow-400' : 'bg-green-400'

          return (
            <div key={stage} className="flex flex-col items-center flex-1">
              {/* Connector line */}
              {i > 0 && (
                <div className={`absolute h-1 ${barColor} w-full`} style={{
                  background: isCompleted ? undefined : isCurrent ? undefined : undefined
                }} />
              )}
              
              {/* Step circle */}
              <div className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all ${
                isCompleted ? `${config.borderColor} ${config.bgColor}` :
                isCurrent ? `${config.borderColor} ${config.bgColor} ring-4 ring-offset-2 ${config.urgency === 'critical' ? 'ring-red-200' : config.urgency === 'warning' ? 'ring-yellow-200' : 'ring-green-200'}` :
                'border-gray-200 bg-gray-50'
              }`}>
                {isCompleted ? (
                  <CheckCircle className={`w-5 h-5 ${config.color}`} />
                ) : (
                  <Icon className={`w-5 h-5 ${isCurrent ? config.color : 'text-gray-300'}`} />
                )}
              </div>

              {/* Stage label */}
              <p className={`mt-2 text-xs font-medium text-center ${
                isCurrent ? config.color : isCompleted ? 'text-gray-700' : 'text-gray-400'
              }`}>
                {config.label}
              </p>

              {/* Stage threshold (days) */}
              {STAGE_CONFIG[stage] && (
                <p className="text-xs text-gray-400 mt-0.5">
                  {stage === 'sollecito_1' ? '7gg' :
                   stage === 'sollecito_2' ? '30gg' :
                   stage === 'penalty_applicata' ? '60gg' :
                   stage === 'diffida' ? '90gg' :
                   stage === 'stop_servizi' || stage === 'legal_action' ? '120gg' : ''}
                </p>
              )}
            </div>
          )
        })}
      </div>
      {/* Progress bar underneath */}
      <div className="mt-4 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            currentStage === 'none' ? 'bg-green-500' :
            STAGE_CONFIG[currentStage]?.urgency === 'critical' ? 'bg-red-500' :
            STAGE_CONFIG[currentStage]?.urgency === 'warning' ? 'bg-yellow-400' : 'bg-green-400'
          }`}
          style={{ width: `${Math.max(((getStageIndex(currentStage)) / (displayStages.length - 1)) * 100, 8)}%` }}
        />
      </div>
    </div>
  )
}

interface ClientEscalationCardProps {
  invoice: {
    id: number
    invoice_number: string
    total_amount: number
    due_date: string
    escalation_stage: EscalationStage
    escalation_label: string
    days_overdue: number
    days_until_next_stage: number | null
    penalty_applied: number
    status: string
  }
  onAdvance: (invoiceId: number) => void
  isAdmin: boolean
}

function ClientEscalationCard({ invoice, onAdvance, isAdmin }: ClientEscalationCardProps) {
  const config = STAGE_CONFIG[invoice.escalation_stage]
  if (!config) return null
  const Icon = config.icon

  return (
    <Card className={`p-4 border-2 ${config.borderColor} ${config.bgColor}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${config.bgColor}`}>
            <Icon className={`w-6 h-6 ${config.color}`} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-gray-900">{invoice.invoice_number}</h3>
              <EscalationBadge stage={invoice.escalation_stage} />
            </div>
            <p className="text-sm text-gray-600 mt-0.5">{config.description}</p>
            <div className="flex items-center gap-4 mt-2 text-sm">
              <span className="font-medium text-gray-900">{formatCurrency(invoice.total_amount)}</span>
              {invoice.days_overdue > 0 && (
                <span className="text-red-600 font-medium">
                  {invoice.days_overdue} giorni di ritardo
                </span>
              )}
              {invoice.penalty_applied > 0 && (
                <span className="text-orange-600">
                  Penalty: {formatCurrency(invoice.penalty_applied)}
                </span>
              )}
              {invoice.days_until_next_stage !== null && invoice.days_until_next_stage > 0 && (
                <span className="text-gray-500">
                  Prossimo stadio tra {invoice.days_until_next_stage} giorni
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Scadenza: {format(parseISO(invoice.due_date), 'dd/MM/yyyy', { locale: it })}
            </p>
          </div>
        </div>
        {isAdmin && invoice.escalation_stage !== 'legal_action' && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onAdvance(invoice.id)}
            className="ml-4 shrink-0"
          >
            Avanza
            <ArrowRight className="w-3 h-3 ml-1" />
          </Button>
        )}
      </div>
    </Card>
  )
}

interface OverdueInvoice {
  id: number
  invoice_number: string
  due_date: string
  total_amount: number
  escalation_stage: EscalationStage
  days_overdue: number
  status: string
}

interface ClientStatusAPIResponse {
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

export function ClientStatusPage() {
  const { id } = useParams<{ id: string }>()
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const [isAdmin, setIsAdmin] = useState(false)

  // Check if user is admin
  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (userData) {
      try {
        const user = JSON.parse(userData)
        setIsAdmin(user.role === 'admin')
      } catch {
        // ignore
      }
    }
  }, [])

  // Fetch all invoices for this client to get their escalation status
  const { data: allInvoicesData, isLoading } = useQuery({
    queryKey: ['client-status-invoices', id],
    queryFn: async () => {
      const response = await api.get('/api/v1/invoices', {
        params: { page: 1, page_size: 100 },
      })
      return response.data
    },
    enabled: !!id,
  })

  // Filter to only overdue invoices and fetch escalation status for each
  const overdueInvoices: OverdueInvoice[] = allInvoicesData?.items?.filter(
    (inv: any) => inv.status === 'overdue' || inv.escalation_stage !== 'none'
  ) ?? []

  // Fetch escalation details for each overdue invoice
  const { data: escalationStatuses, isLoading: escalationLoading } = useQuery({
    queryKey: ['escalation-statuses', id],
    queryFn: async () => {
      const statuses: ClientStatusAPIResponse[] = []
      for (const inv of overdueInvoices) {
        try {
          const response = await api.get(`/api/v1/invoices/${inv.id}/escalation-status`)
          statuses.push(response.data)
        } catch {
          // Invoice may not have escalation data yet
        }
      }
      return statuses
    },
    enabled: overdueInvoices.length > 0,
    refetchInterval: 60000, // Refresh every minute
  })

  const advanceMutation = useMutation({
    mutationFn: async (invoiceId: number) => {
      const response = await api.post(`/api/v1/escalation/advance?invoice_id=${invoiceId}`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['escalation-statuses', id] })
      showToast('Stadio avanzato con successo', 'success')
    },
    onError: () => {
      showToast('Errore durante l\'avanzamento', 'error')
    },
  })

  const handleAdvance = (invoiceId: number) => {
    advanceMutation.mutate(invoiceId)
  }

  // Compute overall status for the client based on their worst invoice
  const worstStage = escalationStatuses?.reduce<EscalationStage>((worst, curr) => {
    const worstIdx = getStageIndex(worst)
    const currIdx = getStageIndex(curr.escalation_stage)
    return currIdx > worstIdx ? curr.escalation_stage : worst
  }, 'none')

  // Summary stats
  const totalOverdue = escalationStatuses?.length ?? 0
  const criticalCount = escalationStatuses?.filter(s =>
    s.escalation_stage === 'diffida' ||
    s.escalation_stage === 'stop_servizi' ||
    s.escalation_stage === 'legal_action'
  ).length ?? 0
  const warningCount = escalationStatuses?.filter(s =>
    s.escalation_stage === 'sollecito_1' ||
    s.escalation_stage === 'sollecito_2' ||
    s.escalation_stage === 'penalty_applicata'
  ).length ?? 0
  const totalPenalty = escalationStatuses?.reduce((sum, s) => sum + (s.penalty_applied || 0), 0) ?? 0

  if (isLoading || escalationLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <Button variant="ghost" asChild className="w-fit">
          <Link to={`/clients/${id}`}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Scheda Cliente
          </Link>
        </Button>
        <div className="flex items-center gap-2">
          <Link to={`/clients/${id}`}>
            <Button variant="outline" size="sm">Scheda Cliente</Button>
          </Link>
        </div>
      </div>

      {/* Page title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Stato Escalation</h1>
        <p className="text-gray-500 text-sm mt-1">
          Monitoraggio automatico dello stato di recupero crediti
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{totalOverdue}</p>
          <p className="text-xs text-gray-500">Fatture in escalation</p>
        </Card>
        <Card className={`p-4 text-center ${criticalCount > 0 ? 'border-red-300 bg-red-50' : ''}`}>
          <p className={`text-2xl font-bold ${criticalCount > 0 ? 'text-red-600' : 'text-gray-400'}`}>{criticalCount}</p>
          <p className="text-xs text-gray-500">Critiche</p>
        </Card>
        <Card className={`p-4 text-center ${warningCount > 0 ? 'border-yellow-300 bg-yellow-50' : ''}`}>
          <p className={`text-2xl font-bold ${warningCount > 0 ? 'text-yellow-600' : 'text-gray-400'}`}>{warningCount}</p>
          <p className="text-xs text-gray-500">Avvisi</p>
        </Card>
        <Card className={`p-4 text-center ${totalPenalty > 0 ? 'border-orange-300 bg-orange-50' : ''}`}>
          <p className={`text-2xl font-bold ${totalPenalty > 0 ? 'text-orange-600' : 'text-gray-400'}`}>
            {formatCurrency(totalPenalty)}
          </p>
          <p className="text-xs text-gray-500">Penalty applicate</p>
        </Card>
      </div>

      {/* Timeline */}
      {worstStage && worstStage !== 'none' && (
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-6">
            Timeline Escalation Attuale
          </h2>
          <EscalationTimeline
            currentStage={worstStage}
          />
        </Card>
      )}

      {/* Legend */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Guida stadi escalation</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {STAGE_ORDER.filter(s => s !== 'none').map((stage) => {
            const config = STAGE_CONFIG[stage]
            const Icon = config.icon
            return (
              <div key={stage} className="flex items-center gap-2 text-sm">
                <div className={`p-1 rounded ${config.bgColor}`}>
                  <Icon className={`w-3.5 h-3.5 ${config.color}`} />
                </div>
                <span className="text-gray-700">{config.label}</span>
                <span className="text-gray-400 text-xs ml-auto">
                  {stage === 'sollecito_1' ? '>7gg' :
                   stage === 'sollecito_2' ? '>30gg' :
                   stage === 'penalty_applicata' ? '>60gg' :
                   stage === 'diffida' ? '>90gg' : '>120gg'}
                </span>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Invoice escalation cards */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Fatture in Escalation
        </h2>
        {escalationStatuses && escalationStatuses.length > 0 ? (
          <div className="space-y-3">
            {escalationStatuses.map((status) => (
              <ClientEscalationCard
                key={status.invoice_id}
                invoice={{
                  id: status.invoice_id,
                  invoice_number: status.invoice_number,
                  total_amount: status.total_amount,
                  due_date: status.due_date,
                  escalation_stage: status.escalation_stage,
                  escalation_label: status.escalation_label,
                  days_overdue: status.days_overdue,
                  days_until_next_stage: status.days_until_next_stage,
                  penalty_applied: status.penalty_applied,
                  status: status.status,
                }}
                onAdvance={handleAdvance}
                isAdmin={isAdmin}
              />
            ))}
          </div>
        ) : (
          <Card className="p-8 text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-900 mb-1">Nessuna fattura in escalation</h3>
            <p className="text-gray-500 text-sm">
              Tutte le fatture sono regolari o sono già state pagate.
            </p>
          </Card>
        )}
      </div>
    </div>
  )
}
