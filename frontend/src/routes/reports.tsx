import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from '../components/ui'
import { TrendingUp, Users, Calendar, Award, AlertTriangle, Download, FileText, Upload } from 'lucide-react'
import { format, parseISO, subMonths, startOfMonth, endOfMonth } from 'date-fns'
import { it } from 'date-fns/locale'
import { useI18n } from '../lib/I18nContext'

interface Invoice {
  id: number
  invoice_number: string
  customer_name: string
  total_amount: number
  due_date: string
  status: 'paid' | 'pending' | 'overdue' | 'cancelled'
  invoice_date: string
}

interface Client {
  id: number
  name: string
  trust_score: number
  payment_pattern: string
}

interface InvoiceList {
  items: Invoice[]
}

interface ClientList {
  items: Client[]
}

interface PeriodStats {
  total: number
  amount: number
  paid: number
  pending: number
  overdue: number
}

interface MonthlyTrend {
  month: string
  amount: number
  paid: number
  pending: number
  overdue: number
}

interface ReportData {
  monthly: PeriodStats
  yearly: PeriodStats
  monthlyTrend: MonthlyTrend[]
  topDelayedClients: { name: string; delays: number; total: number }[]
  topClientsByAmount: { name: string; totalAmount: number; count: number }[]
  avgTrustScore: number
  totalClients: number
  clientsByScore: { excellent: number; good: number; medium: number; low: number }
  avgPaymentDays: number
  periodStart: string
  periodEnd: string
  periodKey: 'month' | 'year'
}

export function ReportsPage() {
  const [period, setPeriod] = useState<'month' | 'year'>('month')
  const { t } = useI18n()
  useEffect(() => { document.title = `${t('reports.title')} — FatturaMVP` }, [t])

  const { data: invoicesData, isLoading: invoicesLoading } = useQuery<InvoiceList>({
    queryKey: ['invoices', { page: 1, page_size: 100 }],
    queryFn: async () => {
      const response = await api.get('/api/v1/invoices', {
        params: { page: 1, page_size: 100 },
      })
      return response.data
    },
  })

  const { data: clientsData, isLoading: clientsLoading } = useQuery<ClientList>({
    queryKey: ['clients', { page: 1, page_size: 100 }],
    queryFn: async () => {
      const response = await api.get('/api/v1/clients', {
        params: { page: 1, page_size: 100 },
      })
      return response.data
    },
  })

  const reportData = useMemo<ReportData | null>(() => {
    if (!invoicesData?.items) return null

    const invoices = invoicesData.items
    const now = new Date()
    const thisMonth = startOfMonth(now)
    const thisMonthEnd = endOfMonth(now)
    const yearStart = new Date(now.getFullYear(), 0, 1)

    const monthlyInvoices = invoices.filter(inv => {
      const date = parseISO(inv.invoice_date)
      return date >= thisMonth && date <= thisMonthEnd
    })

    const yearlyInvoices = invoices.filter(inv => {
      const date = parseISO(inv.invoice_date)
      return date >= yearStart
    })

    const monthly: PeriodStats = {
      total: monthlyInvoices.length,
      amount: monthlyInvoices.reduce((sum, inv) => sum + inv.total_amount, 0),
      paid: monthlyInvoices.filter(inv => inv.status === 'paid').length,
      pending: monthlyInvoices.filter(inv => inv.status === 'pending').length,
      overdue: monthlyInvoices.filter(inv => inv.status === 'overdue').length,
    }

    const yearly: PeriodStats = {
      total: yearlyInvoices.length,
      amount: yearlyInvoices.reduce((sum, inv) => sum + inv.total_amount, 0),
      paid: yearlyInvoices.filter(inv => inv.status === 'paid').length,
      pending: yearlyInvoices.filter(inv => inv.status === 'pending').length,
      overdue: yearlyInvoices.filter(inv => inv.status === 'overdue').length,
    }

    const monthlyTrend: MonthlyTrend[] = []
    for (let i = 5; i >= 0; i--) {
      const d = subMonths(now, i)
      const mStart = startOfMonth(d)
      const mEnd = endOfMonth(d)
      const mInvoices = invoices.filter(inv => {
        const date = parseISO(inv.invoice_date)
        return date >= mStart && date <= mEnd
      })
      monthlyTrend.push({
        month: format(d, 'MMM', { locale: it }),
        amount: mInvoices.reduce((sum, inv) => sum + inv.total_amount, 0),
        paid: mInvoices.filter(inv => inv.status === 'paid').length,
        pending: mInvoices.filter(inv => inv.status === 'pending').length,
        overdue: mInvoices.filter(inv => inv.status === 'overdue').length,
      })
    }

    const clientDelayCount: Record<string, { name: string; delays: number; total: number }> = {}
    invoices.forEach(inv => {
      if (!clientDelayCount[inv.customer_name]) {
        clientDelayCount[inv.customer_name] = { name: inv.customer_name, delays: 0, total: 0 }
      }
      clientDelayCount[inv.customer_name].total++
      if (inv.status === 'overdue') {
        clientDelayCount[inv.customer_name].delays++
      }
    })
    const topDelayedClients = Object.values(clientDelayCount)
      .filter(c => c.delays > 0)
      .sort((a, b) => b.delays - a.delays)
      .slice(0, 5)

    const clientAmountMap: Record<string, { name: string; totalAmount: number; count: number }> = {}
    invoices.forEach(inv => {
      if (!clientAmountMap[inv.customer_name]) {
        clientAmountMap[inv.customer_name] = { name: inv.customer_name, totalAmount: 0, count: 0 }
      }
      clientAmountMap[inv.customer_name].totalAmount += inv.total_amount
      clientAmountMap[inv.customer_name].count++
    })
    const topClientsByAmount = Object.values(clientAmountMap)
      .sort((a, b) => b.totalAmount - a.totalAmount)
      .slice(0, 5)

    const paidInvoices = invoices.filter(inv => inv.status === 'paid')
    const avgPaymentDays = paidInvoices.length > 0
      ? paidInvoices.reduce((sum, inv) => {
          const invDate = parseISO(inv.invoice_date)
          const dueDate = parseISO(inv.due_date)
          // days from invoice issue to due date = standard payment term
          const daysToPay = Math.round(Math.abs(dueDate.getTime() - invDate.getTime()) / (1000 * 60 * 60 * 24))
          return sum + daysToPay
        }, 0) / paidInvoices.length
      : 0

    const avgTrustScore = clientsData?.items?.length
      ? clientsData.items.reduce((sum, c) => sum + c.trust_score, 0) / clientsData.items.length
      : 0

    const periodStart = period === 'month'
      ? format(startOfMonth(new Date()), 'dd MMM yyyy', { locale: it })
      : format(new Date(new Date().getFullYear(), 0, 1), 'dd MMM yyyy', { locale: it })
    const periodEnd = format(new Date(), 'dd MMM yyyy', { locale: it })
    const periodKey = period

    return {
      monthly,
      yearly,
      monthlyTrend,
      topDelayedClients,
      avgTrustScore,
      totalClients: clientsData?.items?.length || 0,
      clientsByScore: {
        excellent: clientsData?.items?.filter(c => c.trust_score >= 80).length || 0,
        good: clientsData?.items?.filter(c => c.trust_score >= 60 && c.trust_score < 80).length || 0,
        medium: clientsData?.items?.filter(c => c.trust_score >= 40 && c.trust_score < 60).length || 0,
        low: clientsData?.items?.filter(c => c.trust_score < 40).length || 0,
      },
      avgPaymentDays,
      topClientsByAmount,
      periodStart,
      periodEnd,
      periodKey,
    }
  }, [invoicesData, clientsData, period])

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)

  const exportInvoicesCSV = () => {
    if (!invoicesData?.items) return
    const headers = ['Numero Fattura', 'Cliente', 'Data Fattura', 'Scadenza', 'Importo', 'Stato']
    const rows = invoicesData.items.map(inv => [
      inv.invoice_number,
      `"${inv.customer_name}"`,
      format(parseISO(inv.invoice_date), 'yyyy-MM-dd'),
      format(parseISO(inv.due_date), 'yyyy-MM-dd'),
      inv.total_amount.toFixed(2),
      inv.status,
    ])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `fatture_${format(new Date(), 'yyyy-MM-dd')}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  if (invoicesLoading || clientsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!invoicesData?.items?.length) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-0">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">{t('reports.title')}</h1>
          </div>
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 shadow-sm">
            <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
              <FileText className="w-10 h-10 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">Ancora nessuna fattura</h3>
            <p className="text-sm text-gray-500 mb-6">Importa le tue fatture XML per vedere statistiche e analisi qui</p>
            <div className="flex gap-3 justify-center">
              <Button asChild className="bg-gray-900 hover:bg-gray-800">
                <Link to="/import"><Upload className="w-4 h-4 mr-2" />Importa fatture</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const currentStats = period === 'month' ? reportData?.monthly : reportData?.yearly
  const maxTrendAmount = reportData?.monthlyTrend?.reduce((max, m) => Math.max(max, m.amount), 1) || 1

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-0">
      <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t('reports.title')}</h1>
        <div className="flex gap-2">
          <button
            onClick={exportInvoicesCSV}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            title="Esporta CSV"
          >
            <Download className="w-4 h-4" />
            CSV
          </button>
          <button
            onClick={() => setPeriod('month')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              period === 'month' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {t('reports.monthly')}
          </button>
          <button
            onClick={() => setPeriod('year')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              period === 'year' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {t('reports.yearly')}
          </button>
        </div>
      </div>

      {/* Summary text */}
      {reportData && (() => {
        const template = t('reports.summaryTemplate')
        const periodLabel = t(reportData.periodKey === 'month' ? 'reports.monthPeriod' : 'reports.yearPeriod')
        const summary = template
          .replace('{{period}}', periodLabel)
          .replace('{{startDate}}', reportData.periodStart)
          .replace('{{endDate}}', reportData.periodEnd)
          .replace('{{total}}', String(reportData.monthly.total))
          .replace('{{amount}}', formatCurrency(reportData.monthly.amount))
          .replace('{{paid}}', String(reportData.monthly.paid))
          .replace('{{pending}}', String(reportData.monthly.pending))
          .replace('{{overdue}}', String(reportData.monthly.overdue))
        return (
          <Card className="bg-primary-50 border-primary-100">
            <CardContent className="p-4">
              <p className="text-sm text-primary-800">{summary}</p>
            </CardContent>
          </Card>
        )
      })()}

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100">
                <Calendar className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{currentStats?.total || 0}</p>
                <p className="text-xs text-gray-500">{period === 'month' ? t('reports.thisMonth') : t('reports.thisYear')}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-100">
                <TrendingUp className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(currentStats?.amount || 0)}</p>
                <p className="text-xs text-gray-500">{t('reports.total')}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-100">
                <Award className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{reportData?.avgTrustScore?.toFixed(0) || 0}</p>
                <p className="text-xs text-gray-500">{t('reports.trustAverage')}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-100">
                <TrendingUp className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{reportData?.avgPaymentDays?.toFixed(0) || 0}</p>
                <p className="text-xs text-gray-500">{t('reports.avgPaymentDays')}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Monthly Revenue Trend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-600" />
            {t('reports.revenueTrend')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-48 flex items-end justify-around gap-2">
            {reportData?.monthlyTrend?.map((m, idx) => (
              <div key={idx} className="flex flex-col items-center flex-1 max-w-[80px]">
                <div className="w-full flex flex-col items-center gap-0.5">
                  <span className="text-xs text-gray-500 mb-1">{formatCurrency(m.amount)}</span>
                  <div className="w-full bg-green-500 rounded-t transition-all hover:bg-green-600" style={{ height: `${Math.max((m.amount / maxTrendAmount) * 140, 8)}px`, minHeight: '8px' }} />
                  <div className="w-full bg-yellow-400 rounded-t transition-all hover:bg-yellow-500" style={{ height: `${Math.max((m.pending / maxTrendAmount) * 80, 4)}px`, minHeight: '4px' }} />
                  <div className="w-full bg-red-400 rounded-t transition-all hover:bg-red-500" style={{ height: `${Math.max((m.overdue / maxTrendAmount) * 60, 4)}px`, minHeight: '4px' }} />
                </div>
                <span className="text-xs text-gray-600 mt-2 capitalize">{m.month}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-center gap-4 mt-2 text-xs">
            <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-green-500" /><span className="text-gray-500">{t('reports.paid')}</span></div>
            <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-yellow-400" /><span className="text-gray-500">{t('reports.pending')}</span></div>
            <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-red-400" /><span className="text-gray-500">{t('reports.expired')}</span></div>
          </div>
        </CardContent>
      </Card>

      {/* Two column layout */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Delayed Clients */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              {t('reports.delayedClients')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {reportData?.topDelayedClients?.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Users className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>{t('reports.noDelays')}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {reportData?.topDelayedClients?.map((client, idx) => (
                  <div key={client.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
                        <span className="text-sm font-medium text-red-600">{idx + 1}</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{client.name}</p>
                        <p className="text-xs text-gray-500">{client.delays} ritardo{client.delays > 1 ? 'i' : ''} su {client.total} fatture</p>
                      </div>
                    </div>
                    <Badge variant="destructive">{Math.round((client.delays / client.total) * 100)}%</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Clients by Amount */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary-600" />
              {t('reports.topClientsByAmount')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {reportData?.topClientsByAmount?.map((client, idx) => (
                <div key={client.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                      <span className="text-sm font-medium text-primary-600">{idx + 1}</span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{client.name}</p>
                      <p className="text-xs text-gray-500">{client.count} fatture</p>
                    </div>
                  </div>
                  <span className="text-sm font-bold text-gray-900">{formatCurrency(client.totalAmount)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Trust Score Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Users className="w-5 h-5 text-purple-600" />
            {t('reports.trustScoreDistribution')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { label: t('reports.excellent') + ' (80-100)', key: 'excellent', color: 'bg-green-500' },
              { label: t('reports.good') + ' (60-79)', key: 'good', color: 'bg-blue-500' },
              { label: t('reports.medium') + ' (40-59)', key: 'medium', color: 'bg-yellow-500' },
              { label: t('reports.low') + ' (0-39)', key: 'low', color: 'bg-red-500' },
            ].map(({ label, key, color }) => (
              <div key={key} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${color}`} />
                  <span className="text-sm text-gray-600">{label}</span>
                </div>
                <span className="text-sm font-medium">{reportData?.clientsByScore[key as keyof typeof reportData.clientsByScore] || 0}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 h-4 rounded-full bg-gray-100 flex overflow-hidden">
            {reportData && reportData.totalClients > 0 && [
              { key: 'excellent', color: 'bg-green-500' },
              { key: 'good', color: 'bg-blue-500' },
              { key: 'medium', color: 'bg-yellow-500' },
              { key: 'low', color: 'bg-red-500' },
            ].map(({ key, color }) => {
              const val = reportData.clientsByScore[key as keyof typeof reportData.clientsByScore]
              const width = (val / reportData.totalClients) * 100
              return width > 0 ? <div key={key} className={`${color} h-full`} style={{ width: `${width}%` }} /> : null
            })}
          </div>
        </CardContent>
      </Card>

      {/* Status Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('reports.invoiceStatus')} — {period === 'month' ? t('reports.thisMonth') : t('reports.thisYear')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-4 rounded-lg bg-green-50">
              <p className="text-2xl font-bold text-green-600">{currentStats?.paid || 0}</p>
              <p className="text-sm text-gray-600">{t('reports.paid')}</p>
              <p className="text-xs text-green-600 mt-1">{formatCurrency(invoicesData?.items?.filter(inv => inv.status === 'paid').reduce((sum, inv) => sum + inv.total_amount, 0) || 0)}</p>
            </div>
            <div className="p-4 rounded-lg bg-yellow-50">
              <p className="text-2xl font-bold text-yellow-600">{currentStats?.pending || 0}</p>
              <p className="text-sm text-gray-600">{t('reports.pending')}</p>
              <p className="text-xs text-yellow-600 mt-1">{formatCurrency(invoicesData?.items?.filter(inv => inv.status === 'pending').reduce((sum, inv) => sum + inv.total_amount, 0) || 0)}</p>
            </div>
            <div className="p-4 rounded-lg bg-red-50">
              <p className="text-2xl font-bold text-red-600">{currentStats?.overdue || 0}</p>
              <p className="text-sm text-gray-600">{t('reports.expired')}</p>
              <p className="text-xs text-red-600 mt-1">{formatCurrency(invoicesData?.items?.filter(inv => inv.status === 'overdue').reduce((sum, inv) => sum + inv.total_amount, 0) || 0)}</p>
            </div>
          </div>
        </CardContent>
      </Card>
        </div>
  </div>
  )
}
