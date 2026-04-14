import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Card, Button, Input } from '../components/ui'
import { FileText, Search, Upload, Check, Bell, Trash2, X, Copy, Download, CreditCard, AlertTriangle } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { format, differenceInDays } from 'date-fns'
import { it } from 'date-fns/locale'
import type { InvoiceStatus, EscalationStage } from '../lib/types'
import { EscalationBadge } from '../components/EscalationTimeline'
import { SollecitoModal } from '../components/SollecitoModal'
import { TrustScoreBadge } from '../components/TrustScoreBadge'
import { DeductibilityBadge } from '../components/DeductibilityBadge'
import { t } from '../lib/i18n'
import { useToast } from '../components/ui/toast'
import { InvoiceListSkeleton } from '../components/ui/skeleton'

interface Invoice {
  id: number
  invoice_number: string
  invoice_date: string
  due_date: string
  customer_name: string
  supplier_name: string
  total_amount: number
  vat_amount: number
  status: InvoiceStatus
  customer_pec?: string
  customer_sdi?: string
  customer_email?: string
  trust_score?: number
  payment_pattern?: string
  escalation_stage?: EscalationStage
  description?: string
}

const STATUS_COLORS: Record<string, string> = {
  paid: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  pending: 'bg-amber-50 text-amber-800 border-amber-200',
  overdue: 'bg-red-50 text-red-800 border-red-200',
  cancelled: 'bg-gray-100 text-gray-800 border-gray-200',
}

const STATUS_DOT: Record<string, string> = {
  paid: 'bg-emerald-500',
  pending: 'bg-amber-500',
  overdue: 'bg-red-500',
  cancelled: 'bg-gray-400',
}

export function InvoicesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { showToast } = useToast()

  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | ''>(
    (searchParams.get('status') as InvoiceStatus) || ''
  )
  const [selectedInvoices, setSelectedInvoices] = useState<Set<number>>(new Set())
  const [sollecitoInvoice, setSollecitoInvoice] = useState<Invoice | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const [pendingActions, setPendingActions] = useState<Set<number>>(new Set())

  const uploadTriggered = useRef(false)
  useEffect(() => {
    if (searchParams.get('upload') === 'true' && !uploadTriggered.current) {
      uploadTriggered.current = true
      fileInputRef.current?.click()
      setTimeout(() => {
        setSearchParams((prev) => {
          const next = new URLSearchParams(prev)
          next.delete('upload')
          return next
        })
      }, 100)
    }
  }, [])

  useEffect(() => {
    const urlStatus = searchParams.get('status') as InvoiceStatus | ''
    if (urlStatus !== statusFilter) {
      setStatusFilter(urlStatus || '')
    }
  }, [searchParams.get('status')])

  const { data, isLoading, isError, refetch, error: queryError } = useQuery({
    queryKey: ['invoices', { search, status: statusFilter }],
    queryFn: async () => {
      const params: Record<string, string | number> = { page: 1, page_size: 50 }
      if (search) params.search = search
      if (statusFilter) params.status = statusFilter
      const response = await api.get('/api/v1/invoices', { params })
      return response.data
    },
  })

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const response = await api.post('/api/v1/invoices', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setSearchParams({})
      showToast('Fattura caricata con successo', 'success')
    },
    onError: (err) => {
      const msg = err && typeof err === 'object' && 'response' in err
        ? ((err as { response?: { data?: { detail?: string } } }).response?.data?.detail || "Errore sconosciuto")
        : 'Errore durante il caricamento della fattura'
      showToast(msg, 'error')
    },
  })

  const markPaidMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post(`/api/v1/invoices/${id}/paid`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      showToast('Fattura segnata come pagata', 'success')
    },
    onSettled: (_data, _err, id) => {
      setPendingActions(prev => { const s = new Set(prev); s.delete(id); return s })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/v1/invoices/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      showToast('Fattura eliminata', 'success')
    },
    onSettled: (_data, _err, id) => {
      setPendingActions(prev => { const s = new Set(prev); s.delete(id); return s })
    },
  })

  const bulkPayMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      const response = await api.post('/api/v1/invoices/bulk/pay', { invoice_ids: ids })
      return response.data
    },
    onSuccess: () => {
      setSelectedInvoices(new Set())
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      showToast('Fatture segnate come pagate', 'success')
    },
  })

  const createCheckoutMutation = useMutation({
    mutationFn: async (invoiceId: number) => {
      const response = await api.post('/api/v1/payments/create-checkout', { invoice_id: invoiceId })
      return response.data
    },
    onSuccess: (data) => {
      window.open(data.checkout_url, '_blank', 'noopener,noreferrer')
    },
    onError: () => {
      showToast('Errore creazione link di pagamento', 'error')
    },
    onSettled: (_data, _err, invoiceId) => {
      setPendingActions(prev => { const s = new Set(prev); s.delete(invoiceId); return s })
    },
  })

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadMutation.mutate(file)
    }
  }

  const handleExportCSV = () => {
    if (!data?.items) return
    const headers = ['Numero', 'Cliente', 'Data Fattura', 'Scadenza', 'Importo', 'IVA', 'Totale', 'Stato']
    const rows = data.items.map((inv: Invoice) => [
      inv.invoice_number, inv.customer_name, inv.invoice_date, inv.due_date,
      (inv.total_amount - (inv.vat_amount || 0)).toFixed(2),
      (inv.vat_amount || 0).toFixed(2), inv.total_amount.toFixed(2), inv.status,
    ])
    const csv = [headers, ...rows].map((r) => r.map((c: string | number) => `"${c}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `fatture_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  const toggleSelect = (id: number) => {
    const newSelected = new Set(selectedInvoices)
    newSelected.has(id) ? newSelected.delete(id) : newSelected.add(id)
    setSelectedInvoices(newSelected)
  }

  const copyToClipboard = async (text: string, id: number) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(id)
      showToast('Numero fattura copiato!', 'success')
      setTimeout(() => setCopiedId(null), 2000)
    } catch {
      showToast('Impossibile copiare', 'error')
    }
  }

  const fc = (n: number) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(n)
  const fd = (d: string) => format(new Date(d), 'dd/MM/yyyy', { locale: it })

  const overdueCount = data?.items?.filter((i: Invoice) => i.status === 'overdue').length || 0
  const pendingCount = data?.items?.filter((i: Invoice) => i.status === 'pending').length || 0
  const totalAmount = data?.items?.reduce((s: number, i: Invoice) => s + i.total_amount, 0) || 0

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-5">
      {sollecitoInvoice && (
        <SollecitoModal
          invoice={sollecitoInvoice}
          open={!!sollecitoInvoice}
          onClose={() => setSollecitoInvoice(null)}
          onSent={() => {
            queryClient.invalidateQueries({ queryKey: ['invoices'] })
            queryClient.invalidateQueries({ queryKey: ['stats'] })
          }}
        />
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fatture</h1>
          {data?.items?.length > 0 && (
            <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
              {overdueCount > 0 && (
                <span className="text-red-600 font-medium">{overdueCount} scadute</span>
              )}
              {pendingCount > 0 && (
                <span className="text-amber-600 font-medium">{pendingCount} in attesa</span>
              )}
              <span>Totale: <strong className="text-gray-900">{fc(totalAmount)}</strong></span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={handleExportCSV} disabled={!data?.items?.length}>
            <Download className="w-4 h-4 mr-1.5" />Esporta CSV
          </Button>
          <Button size="sm" onClick={() => fileInputRef.current?.click()} title="Carica fattura in formato FatturaPA XML (SDI)">
            <Upload className="w-4 h-4 mr-1.5" />Carica XML
          </Button>
        </div>
        <input ref={fileInputRef} type="file" accept=".xml" className="hidden" onChange={handleFileUpload} />
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 min-h-12">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <Input
            placeholder="Cerca fattura, cliente..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-11 h-12 text-base"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as InvoiceStatus | '')}
          className="px-4 py-3 h-12 min-h-12 rounded-lg border border-gray-300 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-violet-500 touch-manipulation"
        >
          <option value="">Tutti gli stati</option>
          <option value="pending">In attesa</option>
          <option value="paid">Pagate</option>
          <option value="overdue">Scadute</option>
        </select>
      </div>

      {/* Bulk actions */}
      {selectedInvoices.size > 0 && (
        <div className="flex items-center gap-3 p-3 bg-violet-50 rounded-xl border border-violet-100">
          <span className="text-sm font-medium text-violet-700">{selectedInvoices.size} selezionate</span>
          <Button size="sm" className="bg-violet-600 hover:bg-violet-700" onClick={() => bulkPayMutation.mutate(Array.from(selectedInvoices))}>
            <Check className="w-3.5 h-3.5 mr-1" />Segna pagate
          </Button>
          <button onClick={() => setSelectedInvoices(new Set())} className="text-violet-500 hover:text-violet-700 p-1">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Invoice table */}
      <Card className="overflow-x-auto">
        {isLoading ? (
          <InvoiceListSkeleton />
        ) : isError ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 shadow-sm">
            <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-red-50 flex items-center justify-center">
              <AlertTriangle className="w-7 h-7 text-red-500" />
            </div>
            <p className="font-medium text-gray-900">Errore di caricamento</p>
            <p className="text-sm text-gray-600 mt-1 max-w-xs mx-auto">
              {queryError && (typeof queryError === 'object' && 'response' in queryError)
                ? ((queryError as { response?: { data?: { detail?: string } } }).response?.data?.detail || "Impossibile connettersi al server. Riprova.")
                : "Impossibile connettersi al server. Riprova."}
            </p>
            <Button onClick={() => refetch()} className="mt-4">
              Riprova
            </Button>
          </div>
        ) : !data?.items?.length ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 shadow-sm">
            <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
              <FileText className="w-10 h-10 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">
              {statusFilter && search
                ? `Nessun risultato`
                : statusFilter
                ? `Nessuna fattura ${t(`status.${statusFilter}`).toLowerCase()}`
                : search
                ? `Nessun risultato per "${search}"`
                : 'Nessuna fattura'}
            </h3>
            <p className="text-sm text-gray-500 mb-6">
              {statusFilter && search
                ? `Nessuna fattura "${search}" con stato "${t(`status.${statusFilter}`)}". Prova a modificare i filtri.`
                : statusFilter
                ? `Non ci sono fatture con stato "${t(`status.${statusFilter}`)}". Cambia il filtro per vedere altre fatture.`
                : search
                ? `Prova a cercare con parole diverse, oppure carica un nuovo file XML`
                : 'Carica un file FatturaPA XML (formato SDI) per visualizzare le tue fatture qui'}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              {search && <Button variant="outline" size="sm" onClick={() => setSearch('')}>Cancella ricerca</Button>}
              {statusFilter && <Button variant="outline" size="sm" onClick={() => setStatusFilter('')}>Mostra tutte</Button>}
              {!search && !statusFilter && (
                <>
                  <Button size="sm" onClick={() => fileInputRef.current?.click()}>
                    <Upload className="w-4 h-4 mr-1.5" />Carica XML
                  </Button>
                  <Button variant="outline" size="sm" asChild>
                    <Link to="/scadenziario">Vai a Scadenziario</Link>
                  </Button>
                </>
              )}
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/60">
                  <th className="w-10 px-4 py-4"></th>
                  <th className="text-left px-4 py-4 text-xs font-semibold text-gray-600 uppercase tracking-wider">Fattura</th>
                  <th className="text-left px-4 py-4 text-xs font-semibold text-gray-600 uppercase tracking-wider hidden md:table-cell">Cliente</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-600 uppercase tracking-wider">Importo</th>
                  <th className="text-center px-4 py-4 text-xs font-semibold text-gray-600 uppercase tracking-wider hidden sm:table-cell">Stato</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-600 uppercase tracking-wider hidden lg:table-cell">Scadenza</th>
                  <th className="text-right px-4 py-4 text-xs font-semibold text-gray-600 uppercase tracking-wider">Azioni</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.items.map((invoice: Invoice) => {
                  const overdueDays = invoice.status === 'overdue'
                    ? differenceInDays(new Date(), new Date(invoice.due_date))
                    : invoice.status === 'pending'
                    ? differenceInDays(new Date(invoice.due_date), new Date())
                    : null

                  return (
                    <tr key={invoice.id} className="hover:bg-gray-50/80 transition-colors group">
                      {/* Checkbox */}
                      <td className="px-4 py-4">
                        <div className="w-5 h-5 min-w-[44px] min-h-[44px] flex items-center justify-center -ml-1">
                          <input
                            type="checkbox"
                            checked={selectedInvoices.has(invoice.id)}
                            onChange={() => toggleSelect(invoice.id)}
                            className="w-5 h-5 rounded border-gray-300 text-violet-600 cursor-pointer"
                          />
                        </div>
                      </td>

                      {/* Invoice number + badges */}
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2 flex-wrap min-w-0">
                          <button
                            onClick={() => copyToClipboard(invoice.invoice_number, invoice.id)}
                            className="flex items-center gap-1 font-semibold text-gray-900 hover:text-violet-600 transition-colors min-h-[44px] min-w-[44px] -ml-2 pl-2 justify-center rounded-lg hover:bg-gray-100"
                            title="Copia numero fattura"
                          >
                            <span>{invoice.invoice_number}</span>
                            <Copy className={`w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity ${copiedId === invoice.id ? '!opacity-100 text-green-500' : 'text-gray-400'}`} />
                          </button>
                          {/* Status badge */}
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${STATUS_COLORS[invoice.status] || STATUS_COLORS.cancelled}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[invoice.status] || STATUS_DOT.cancelled}`} />
                            {t(`status.${invoice.status}`)}
                          </span>
                          {/* Trust score */}
                          {invoice.trust_score !== undefined && invoice.trust_score !== null && (
                            <TrustScoreBadge score={invoice.trust_score} size="sm" />
                          )}
                          {/* Deductibility */}
                          {invoice.description && (
                            <DeductibilityBadge description={invoice.description} inline size="sm" />
                          )}
                        </div>
                        {/* Mobile: client name */}
                        <p className="text-xs text-gray-500 mt-0.5 md:hidden">{invoice.customer_name}</p>
                      </td>

                      {/* Client name */}
                      <td className="px-4 py-4 hidden md:table-cell">
                        <p className="text-gray-700 font-medium truncate max-w-[160px]">{invoice.customer_name}</p>
                        {invoice.description && (
                          <p className="text-xs text-gray-500 truncate max-w-[160px]">{invoice.description}</p>
                        )}
                      </td>

                      {/* Amount */}
                      <td className="px-4 py-4 text-right">
                        <p className="font-bold text-gray-900">{fc(invoice.total_amount)}</p>
                        <p className="text-xs text-gray-600">+{fc(invoice.vat_amount || 0)} IVA</p>
                      </td>

                      {/* Status (tablet+) */}
                      <td className="px-4 py-4 text-center hidden sm:table-cell">
                        {invoice.escalation_stage && invoice.escalation_stage !== 'none' ? (
                          <EscalationBadge stage={invoice.escalation_stage} />
                        ) : (
                          <span className="text-xs text-gray-500">—</span>
                        )}
                      </td>

                      {/* Due date */}
                      <td className="px-4 py-4 text-right hidden lg:table-cell">
                        <p className="text-gray-700">{fd(invoice.due_date)}</p>
                        {overdueDays !== null && overdueDays > 0 && (
                          <p className="text-xs text-red-600 font-semibold">
                            {invoice.status === 'pending' ? `-${overdueDays}g` : `+${overdueDays}g`}
                          </p>
                        )}
                        {overdueDays !== null && overdueDays < 0 && overdueDays >= -7 && (
                          <p className="text-xs text-amber-600 font-semibold">{Math.abs(overdueDays)}g</p>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-4 align-middle">
                        <div className="flex items-center justify-end gap-2 min-h-[44px]">
                          {invoice.status !== 'paid' ? (
                            <>
                              <button
                                onClick={() => { setPendingActions(prev => new Set([...prev, invoice.id])); createCheckoutMutation.mutate(invoice.id) }}
                                disabled={pendingActions.has(invoice.id)}
                                className="inline-flex items-center gap-1 px-3 py-2 min-h-11 bg-gray-900 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-lg transition-colors"
                                title="Link pagamento"
                              >
                                <CreditCard className="w-3 h-3" />Paga
                              </button>
                              <button
                                onClick={() => { setPendingActions(prev => new Set([...prev, invoice.id])); markPaidMutation.mutate(invoice.id) }}
                                disabled={pendingActions.has(invoice.id)}
                                className="p-2 min-h-11 min-w-11 text-green-600 hover:bg-green-50 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center justify-center"
                                title="Segna pagata"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => setSollecitoInvoice(invoice)}
                                disabled={pendingActions.has(invoice.id)}
                                className="p-2 min-h-11 min-w-11 text-violet-600 hover:bg-violet-50 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center justify-center"
                                title="Invia sollecito"
                              >
                                <Bell className="w-3.5 h-3.5" />
                              </button>
                            </>
                          ) : null}
                          <button
                            onClick={() => { setPendingActions(prev => new Set([...prev, invoice.id])); deleteMutation.mutate(invoice.id) }}
                            disabled={pendingActions.has(invoice.id)}
                            className="p-2 min-h-11 min-w-11 text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center justify-center"
                            title="Elimina"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
