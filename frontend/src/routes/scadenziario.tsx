import { useState, useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Card, Badge, Button } from '../components/ui'
import { FileText, AlertTriangle, Clock, RefreshCw, LayoutGrid, List, CheckCircle2 } from 'lucide-react'
import { format, parseISO, differenceInDays } from 'date-fns'
import { it } from 'date-fns/locale'
import { formatCurrency } from '../lib/utils'
import { Link } from 'react-router-dom'
import { useToast } from '../components/ui/toast'
import { CalendarView } from '../components/CalendarView'
import { Skeleton } from '../components/ui/skeleton'
import { t } from '../lib/i18n'

interface Invoice {
  id: number
  invoice_number: string
  customer_name: string
  total_amount?: number
  due_date: string
  status: string
}

interface InvoiceList {
  items: Invoice[]
  total: number
  page: number
  page_size: number
  pages: number
}

type FilterType = 'all' | 'due_soon' | 'overdue'

export function ScadenziarioPage() {
  const { showToast } = useToast()
  const [filter, setFilter] = useState<FilterType>('all')
  const [view, setView] = useState<'list' | 'calendar'>('list')
  const [pendingInvoice, setPendingInvoice] = useState<number | null>(null)

  const { data, isLoading, isError, refetch } = useQuery<InvoiceList>({
    queryKey: ['scadenziario-invoices'],
    queryFn: async () => {
      const response = await api.get('/api/v1/invoices', { params: { page: 1, page_size: 200 } })
      return response.data
    },
  })

  const markPaidMutation = useMutation({
    mutationFn: async (invoiceId: number) => {
      await api.post(`/api/v1/invoices/${invoiceId}/paid`)
    },
    onSuccess: () => {
      showToast('Fattura segnata come pagata', 'success')
      refetch()
    },
    onError: () => {
      showToast('Errore', 'error')
    },
    onSettled: () => {
      setPendingInvoice(null)
    },
  })

  const today = new Date()

  const allInvoices = useMemo(() => data?.items || [], [data])

  const unpaidInvoices = useMemo(() =>
    allInvoices.filter(inv => inv.status !== 'paid'), [allInvoices])

  const filteredInvoices = useMemo(() => {
    const filtered = unpaidInvoices.filter(inv => {
      if (filter === 'overdue')
        return inv.status === 'overdue' || (inv.status === 'pending' && differenceInDays(today, parseISO(inv.due_date)) > 0)
      if (filter === 'due_soon') {
        const diff = differenceInDays(parseISO(inv.due_date), today)
        return diff >= 0 && diff <= 7
      }
      return true
    })
    return filtered.sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime())
  }, [unpaidInvoices, filter])

  const stats = useMemo(() => {
    const overdue = unpaidInvoices.filter(inv =>
      inv.status === 'overdue' || differenceInDays(today, parseISO(inv.due_date)) > 0)
    const due_soon = unpaidInvoices.filter(inv => {
      const diff = differenceInDays(parseISO(inv.due_date), today)
      return diff >= 0 && diff <= 7
    })
    return {
      overdue: overdue.length,
      due_soon: due_soon.length,
      total_overdue: overdue.reduce((s, i) => s + (i.total_amount ?? 0), 0),
      total_due_soon: due_soon.reduce((s, i) => s + (i.total_amount ?? 0), 0),
    }
  }, [unpaidInvoices])

  const calendarInvoices = useMemo(() =>
    unpaidInvoices.map(inv => ({
      id: inv.id,
      invoice_number: inv.invoice_number,
      customer_name: inv.customer_name,
      total_amount: inv.total_amount || 0,
      due_date: inv.due_date,
      status: inv.status as 'paid' | 'pending' | 'overdue',
    })), [unpaidInvoices])

  const getDaysLabel = (dueDate: string) => {
    const diff = differenceInDays(parseISO(dueDate), today)
    if (diff < 0) return { label: `${Math.abs(diff)}g`, className: 'text-red-600 font-semibold' }
    if (diff === 0) return { label: 'Oggi', className: 'text-orange-600 font-semibold' }
    return { label: `${diff}g`, className: 'text-gray-600' }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Scadenziario</h1>
          <div className="flex items-center gap-2">
            {/* View toggle */}
            <div className="flex items-center bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setView('list')}
                className={`flex items-center gap-1.5 px-3 py-2 min-h-11 rounded-md text-sm font-medium transition-all touch-manipulation ${
                  view === 'list' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <List className="w-4 h-4" /> Lista
              </button>
              <button
                onClick={() => setView('calendar')}
                className={`flex items-center gap-1.5 px-3 py-2 min-h-11 rounded-md text-sm font-medium transition-all touch-manipulation ${
                  view === 'calendar' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <LayoutGrid className="w-4 h-4" /> Calendario
              </button>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            onClick={() => setFilter('overdue')}
            className={`text-left p-5 rounded-xl border transition-all min-h-[88px] flex flex-col justify-center ${filter === 'overdue' ? 'border-red-500 bg-red-50 ring-2 ring-red-200' : 'border-gray-200 bg-white hover:border-red-300 hover:bg-red-50'}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <span className="text-sm font-semibold text-red-700">Scadute</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.overdue}</p>
            <p className="text-xs text-red-600 mt-0.5">{formatCurrency(stats.total_overdue)}</p>
          </button>

          <button
            onClick={() => setFilter('due_soon')}
            className={`text-left p-5 rounded-xl border transition-all min-h-[88px] flex flex-col justify-center ${filter === 'due_soon' ? 'border-amber-500 bg-amber-50 ring-2 ring-amber-200' : 'border-gray-200 bg-white hover:border-amber-300 hover:bg-amber-50'}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-amber-600" />
              <span className="text-sm font-semibold text-amber-700">In scadenza (7gg)</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.due_soon}</p>
            <p className="text-xs text-amber-600 mt-0.5">{formatCurrency(stats.total_due_soon)}</p>
          </button>

          <button
            onClick={() => setFilter('all')}
            className={`text-left p-5 rounded-xl border transition-all min-h-[88px] flex flex-col justify-center ${filter === 'all' ? 'border-violet-500 bg-violet-50 ring-2 ring-violet-200' : 'border-gray-200 bg-white hover:border-violet-300 hover:bg-violet-50'}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-violet-600" />
              <span className="text-sm font-semibold text-violet-700">Tutte</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{unpaidInvoices.length}</p>
            <p className="text-xs text-gray-600 mt-0.5">Non pagate</p>
          </button>
        </div>

        {/* Calendar or List view */}
        {view === 'calendar' ? (
          <CalendarView invoices={calendarInvoices} />
        ) : (
          <Card className="overflow-x-auto">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-gray-900">
                  {filter === 'all' ? 'Tutte le fatture' : filter === 'overdue' ? 'Scadute' : 'In scadenza'}
                </h2>
                <Badge variant="secondary">{filteredInvoices.length}</Badge>
              </div>
              {filter !== 'all' && (
                <button onClick={() => setFilter('all')} className="text-xs min-h-11 px-3 py-2 -my-1 text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors touch-manipulation font-medium">
                  Mostra tutte
                </button>
              )}
            </div>

            {isLoading ? (
              <div className="divide-y divide-gray-50 min-w-[600px]">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center gap-4 px-5 py-4">
                    <Skeleton className="w-10 h-10 rounded-xl shrink-0" />
                    <div className="flex-1 min-w-0 space-y-2">
                      <Skeleton className="h-4 w-36" />
                      <Skeleton className="h-3 w-52" />
                    </div>
                    <div className="text-center shrink-0 space-y-2">
                      <Skeleton className="h-4 w-10 mx-auto" />
                      <Skeleton className="h-3 w-14 mx-auto" />
                    </div>
                    <div className="text-right shrink-0">
                      <Skeleton className="h-4 w-24" />
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Skeleton className="h-9 w-16 rounded-lg" />
                      <Skeleton className="h-9 w-20 rounded-lg" />
                    </div>
                  </div>
                ))}
              </div>
            ) : isError ? (
              <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 shadow-sm">
                <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-red-50 flex items-center justify-center">
                  <AlertTriangle className="w-7 h-7 text-red-500" />
                </div>
                <p className="font-medium text-gray-900">Errore di caricamento</p>
                <p className="text-sm text-gray-500 mt-1">Impossibile caricare lo scadenziario. Riprova.</p>
                <Button onClick={() => refetch()} className="mt-4">
                  Riprova
                </Button>
              </div>
            ) : filteredInvoices.length === 0 ? (
              <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 shadow-sm">
                {filter === 'all' ? (
                  allInvoices.length === 0 ? (
                    // No invoices imported yet — neutral/info state (NOT success green)
                    <>
                      <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-gray-100 flex items-center justify-center">
                        <FileText className="w-7 h-7 text-gray-400" />
                      </div>
                      <p className="font-medium text-gray-900">Nessuna fattura importata</p>
                      <p className="text-sm text-gray-500 mt-1">Vai su <Link to="/invoices" className="text-violet-600 hover:underline font-medium">Fatture</Link> per importare le tue fatture FatturaPA XML (formato SDI).</p>
                      <div className="flex gap-3 justify-center mt-5">
                        <Button asChild>
                          <Link to="/invoices">Importa fatture</Link>
                        </Button>
                      </div>
                    </>
                  ) : (
                    // All invoices paid — TRUE success state
                    <>
                      <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-emerald-50 flex items-center justify-center">
                        <CheckCircle2 className="w-7 h-7 text-emerald-500" />
                      </div>
                      <p className="font-medium text-emerald-700">Tutte pagate!</p>
                      <p className="text-sm text-gray-500 mt-1">Ottimo lavoro! Nessuna fattura in attesa.</p>
                      <div className="flex gap-3 justify-center mt-5">
                        <Button variant="outline" size="sm" asChild>
                          <Link to="/invoices">Vedi fatture</Link>
                        </Button>
                      </div>
                    </>
                  )
                ) : (
                  // Filtered view (overdue / week)
                  allInvoices.length === 0 ? (
                    // No invoices imported at all — neutral info, not success
                    <>
                      <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-gray-100 flex items-center justify-center">
                        <FileText className="w-7 h-7 text-gray-400" />
                      </div>
                      <p className="font-medium text-gray-900">Nessuna fattura importata</p>
                      <p className="text-sm text-gray-500 mt-1">Vai su <Link to="/invoices" className="text-violet-600 hover:underline font-medium">Fatture</Link> per importare le tue fatture FatturaPA XML (formato SDI).</p>
                      <div className="flex gap-3 justify-center mt-5">
                        <Button asChild>
                          <Link to="/invoices">Importa fatture</Link>
                        </Button>
                      </div>
                    </>
                  ) : (
                    // Invoices exist but none match this filter
                    <>
                      <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-emerald-50 flex items-center justify-center">
                        <CheckCircle2 className="w-7 h-7 text-emerald-500" />
                      </div>
                      <p className="font-medium text-emerald-700">
                        {filter === 'overdue' ? 'Nessuno scaduto' : filter === 'due_soon' ? t('scadenziario.noUpcoming') : 'Tutte pagate!'}
                      </p>
                      <p className="text-sm text-gray-500 mt-1">
                        {filter === 'overdue'
                          ? 'Tutte le fatture sono state pagate. Ottimo lavoro!'
                          : filter === 'due_soon'
                          ? unpaidInvoices.some(inv => inv.status === 'overdue')
                            ? 'Nessuna fattura in scadenza nei prossimi 7 giorni, ma ci sono fatture scadute da gestire.'
                            : 'Nessuna fattura in scadenza nei prossimi 7 giorni.'
                          : 'Non ci sono fatture in attesa.'}
                      </p>
                      <div className="flex gap-3 justify-center mt-5">
                        {filter === 'due_soon' ? (
                          <Button variant="outline" size="sm" onClick={() => setFilter('all')}>
                            Mostra tutte
                          </Button>
                        ) : null}
                        <Button asChild>
                          <Link to="/invoices">Vedi fatture</Link>
                        </Button>
                      </div>
                    </>
                  )
                )}
              </div>
            ) : (
              <div className="divide-y divide-gray-50 min-w-[600px]">
                {filteredInvoices.map((invoice) => {
                  const days = getDaysLabel(invoice.due_date)
                  const isOverdue = invoice.status === 'overdue' || differenceInDays(today, parseISO(invoice.due_date)) > 0
                  return (
                    <div key={invoice.id} className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50/60 transition-colors group min-w-0 overflow-x-auto">
                      {/* Status dot */}
                      <div className={`shrink-0 w-9 h-9 rounded-xl flex items-center justify-center ${
                        isOverdue ? 'bg-red-50' : 'bg-amber-50'
                      }`}>
                        {isOverdue
                          ? <AlertTriangle className="w-4 h-4 text-red-500" />
                          : <Clock className="w-4 h-4 text-amber-500" />}
                      </div>

                      {/* Main info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Link to={`/invoices/${invoice.id}`} className="font-semibold text-gray-900 hover:text-violet-600 transition-colors">
                            {invoice.invoice_number}
                          </Link>
                          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${
                            isOverdue ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                          }`}>
                            {isOverdue ? 'Scaduta' : 'In scadenza'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 mt-0.5 truncate">{invoice.customer_name}</p>
                      </div>

                      {/* Due date */}
                      <div className="text-center shrink-0">
                        <p className={`text-xs font-semibold ${days.className}`}>{days.label}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {format(parseISO(invoice.due_date), 'd MMM', { locale: it })}
                        </p>
                      </div>

                      {/* Amount */}
                      <div className="text-right shrink-0 min-w-[80px]">
                        <p className="text-sm font-bold text-gray-900 tabular-nums">
                          {formatCurrency(invoice.total_amount ?? 0)}
                        </p>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1 shrink-0 flex-nowrap">
                        <button
                          onClick={() => { setPendingInvoice(invoice.id); markPaidMutation.mutate(invoice.id) }}
                          disabled={pendingInvoice === invoice.id}
                          className="px-3 py-2 min-h-11 text-xs font-semibold bg-emerald-50 text-emerald-700 rounded-lg hover:bg-emerald-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors touch-manipulation"
                        >
                          {pendingInvoice === invoice.id ? '...' : 'Pagata'}
                        </button>
                        <Link
                          to={`/invoices/${invoice.id}`}
                          className="px-3 py-2 min-h-11 text-xs font-medium text-gray-600 rounded-lg hover:bg-gray-100 transition-colors touch-manipulation"
                        >
                          Dettagli
                        </Link>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  )
}
