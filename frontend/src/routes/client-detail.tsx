import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Building2, Mail, Phone, MapPin, CreditCard, RefreshCw, Loader2, FileText, AlertTriangle, Clock, AlertCircle } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { TrustScoreBadge } from '../components/TrustScoreBadge'
import { SollecitoModal } from '../components/SollecitoModal'
import { api } from '../lib/api'
import { Client, PaymentHistory } from '../lib/types'
import { formatCurrency, formatDate } from '../lib/utils'
import { format, differenceInDays, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'

interface Invoice {
  id: number
  invoice_number: string
  invoice_date: string
  due_date: string
  customer_name: string
  total_amount: number
  status: 'paid' | 'pending' | 'overdue' | 'cancelled'
  customer_email?: string
  customer_pec?: string
  trust_score?: number
}

interface InvoiceList {
  items: Invoice[]
}

export function ClientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [client, setClient] = useState<Client | null>(null)
  const [history, setHistory] = useState<PaymentHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [recalculating, setRecalculating] = useState(false)
  const [sollecitoInvoice, setSollecitoInvoice] = useState<Invoice | null>(null)

  useEffect(() => {
    if (id) {
      fetchClient()
      fetchHistory()
    }
  }, [id])

  async function fetchClient() {
    try {
      setLoading(true)
      const response = await api.get<Client>(`/api/v1/clients/${id}`)
      setClient(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Cliente non trovato')
    } finally {
      setLoading(false)
    }
  }

  async function fetchHistory() {
    try {
      const response = await api.get<PaymentHistory[]>(`/api/v1/clients/${id}/history`)
      setHistory(response.data)
    } catch (err: any) {
      // Error fetching history silently ignored
    }
  }

  const { data: clientInvoicesData } = useQuery<InvoiceList>({
    queryKey: ['client-invoices', id],
    queryFn: async () => {
      const response = await api.get<InvoiceList>('/api/v1/invoices', {
        params: { page: 1, page_size: 50 },
      })
      return response.data
    },
    enabled: !!id,
  })

  const pendingInvoices = clientInvoicesData?.items?.filter(
    (inv) => inv.status === 'pending' || inv.status === 'overdue'
  ) ?? []

  async function recalculateScore() {
    try {
      setRecalculating(true)
      const response = await api.post<Client>(`/api/v1/clients/${id}/recalculate-score`)
      setClient(response.data)
    } catch (err: any) {
      // Error recalculating score silently ignored
    } finally {
      setRecalculating(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (error || !client) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" asChild>
          <Link to="/clients">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Torna ai clienti
          </Link>
        </Button>
        <Card className="p-8 text-center">
          <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-red-50 flex items-center justify-center">
            <AlertCircle className="w-7 h-7 text-red-400" />
          </div>
          <p className="font-semibold text-gray-900 text-lg mb-1">{(error as any)?.response?.data?.detail || error || 'Cliente non trovato'}</p>
          <p className="text-sm text-gray-500 mt-1">Riprova o contatta il supporto se il problema persiste</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-0">
      <div className="space-y-6">
      {/* Sollecito Modal */}
      {sollecitoInvoice && (
        <SollecitoModal
          invoice={sollecitoInvoice}
          open={!!sollecitoInvoice}
          onClose={() => setSollecitoInvoice(null)}
          onSent={() => {}}
        />
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <Button variant="ghost" asChild className="w-fit">
          <Link to="/clients">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Clienti
          </Link>
        </Button>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={recalculateScore} disabled={recalculating}>
            <RefreshCw className={`w-4 h-4 mr-2 ${recalculating ? 'animate-spin' : ''}`} />
            Ricalcola score
          </Button>
          {pendingInvoices.length > 0 && (
            <Button variant="outline" asChild className="border-orange-300 text-orange-700 hover:text-orange-800">
              <Link to={`/clients/${id}/status`}>
                <AlertCircle className="w-4 h-4 mr-2" />
                Stato Escalation
              </Link>
            </Button>
          )}
          <Button asChild>
            <Link to={`/clients/${id}/edit`}>Modifica</Link>
          </Button>
        </div>
      </div>

      {/* Client Info Card */}
      <Card className="p-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center">
              <Building2 className="w-7 h-7 text-primary-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{client.name}</h1>
              {client.vat && <p className="text-gray-500">P.IVA: {client.vat}</p>}
              {client.fiscal_code && <p className="text-gray-500">CF: {client.fiscal_code}</p>}
            </div>
          </div>
          <div className="flex flex-col items-start sm:items-end gap-2">
            <TrustScoreBadge score={client.trust_score} size="lg" />
            {client.is_new && <Badge variant="secondary">Nuovo</Badge>}
            {client.payment_pattern && (
              <p className="text-sm text-gray-500 capitalize">
                Pattern: {client.payment_pattern.replace('_', ' ')}
              </p>
            )}
          </div>
        </div>

        {/* Trust Score Progress Bar */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-700">Trust Score</span>
            <span className="text-sm font-bold text-gray-900">{client.trust_score}/100</span>
          </div>
          <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                client.trust_score >= 80 ? 'bg-green-500' :
                client.trust_score >= 60 ? 'bg-blue-500' :
                client.trust_score >= 40 ? 'bg-yellow-500' :
                client.trust_score >= 20 ? 'bg-orange-500' :
                'bg-red-500'
              }`}
              style={{ width: `${client.trust_score}%` }}
            />
          </div>
          <div className="flex justify-between mt-0.5 text-xs text-gray-400">
            <span>0</span>
            <span>20</span>
            <span>40</span>
            <span>60</span>
            <span>80</span>
            <span>100</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {client.email && (
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500">Email</p>
                <p className="font-medium">{client.email}</p>
              </div>
            </div>
          )}
          {client.phone && (
            <div className="flex items-center gap-3">
              <Phone className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500">Telefono</p>
                <p className="font-medium">{client.phone}</p>
              </div>
            </div>
          )}
          {client.address && (
            <div className="flex items-center gap-3">
              <MapPin className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500">Indirizzo</p>
                <p className="font-medium">{client.address}</p>
              </div>
            </div>
          )}
          {client.pec && (
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500">PEC</p>
                <p className="font-medium">{client.pec}</p>
              </div>
            </div>
          )}
          {client.sdi && (
            <div className="flex items-center gap-3">
              <CreditCard className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500">SDI</p>
                <p className="font-medium">{client.sdi}</p>
              </div>
            </div>
          )}
          {client.iban && (
            <div className="flex items-center gap-3">
              <CreditCard className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm text-gray-500">IBAN</p>
                <p className="font-medium">{client.iban}</p>
              </div>
            </div>
          )}
        </div>

        {client.notes && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-500 mb-1">Note</p>
            <p className="font-medium">{client.notes}</p>
          </div>
        )}
      </Card>

      {/* Pending / Overdue Invoices for this client */}
      {pendingInvoices.length > 0 && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            Fatture in sospeso ({pendingInvoices.length})
          </h2>
          <div className="space-y-3">
            {pendingInvoices.map((inv) => {
              const isOverdue = inv.status === 'overdue'
              const daysLeft = differenceInDays(parseISO(inv.due_date), new Date())
              const daysOverdue = Math.abs(daysLeft)
              return (
                <div key={inv.id} className="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${isOverdue ? 'bg-red-100' : 'bg-yellow-100'}`}>
                      <FileText className={`w-4 h-4 ${isOverdue ? 'text-red-600' : 'text-yellow-600'}`} />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{inv.invoice_number}</p>
                      <p className="text-xs text-gray-500">
                        {isOverdue
                          ? `Scaduta da ${daysOverdue} giorni`
                          : `Scade tra ${daysLeft} giorni`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="font-medium text-gray-900">{formatCurrency(inv.total_amount)}</p>
                      <p className="text-xs text-gray-500">{format(parseISO(inv.due_date), 'dd/MM/yyyy', { locale: it })}</p>
                    </div>
                    <Badge variant={isOverdue ? 'destructive' : 'warning'}>
                      {isOverdue ? 'Scaduta' : 'In attesa'}
                    </Badge>
                    {client.pec || client.email ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setSollecitoInvoice(inv)}
                        title="Invia sollecito"
                      >
                        <Clock className="w-4 h-4" />
                      </Button>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Payment History */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Storico pagamenti</h2>
        
        {history.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-gray-100 flex items-center justify-center">
              <Clock className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm font-medium text-gray-500">Nessuno storico pagamento disponibile</p>
            <p className="text-xs text-gray-400 mt-1">I pagamenti appariranno qui quando verranno registrati</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-2 font-medium text-gray-600">Data fattura</th>
                  <th className="text-left py-3 px-2 font-medium text-gray-600">Scadenza</th>
                  <th className="text-left py-3 px-2 font-medium text-gray-600">Pagamento</th>
                  <th className="text-right py-3 px-2 font-medium text-gray-600">Importo</th>
                  <th className="text-right py-3 px-2 font-medium text-gray-600">Ritardo</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id} className="border-b border-gray-100">
                    <td className="py-3 px-2">{formatDate(item.invoice_date)}</td>
                    <td className="py-3 px-2">{formatDate(item.due_date)}</td>
                    <td className="py-3 px-2">
                      {item.paid_date ? (
                        formatDate(item.paid_date)
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="py-3 px-2 text-right font-medium">
                      {formatCurrency(item.invoice_amount)}
                    </td>
                    <td className="py-3 px-2 text-right">
                      {item.was_on_time ? (
                        <Badge variant="success" className="text-xs">In tempo</Badge>
                      ) : (
                        <Badge variant="destructive" className="text-xs">
                          +{item.days_late} giorni
                        </Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
        </div>
  </div>
  )
}
