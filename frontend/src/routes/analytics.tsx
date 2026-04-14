import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Card, CardContent, CardHeader, CardTitle, Button } from '../components/ui'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import {
  FileText, CheckCircle2, AlertTriangle, Euro, Clock,
  TrendingUp, Users, Upload,
} from 'lucide-react'
import { parseISO, subMonths, startOfMonth, endOfMonth } from 'date-fns'
import { useI18n } from '../lib/I18nContext'
import { useEffect } from 'react'

interface InvoiceStats {
  total: number
  paid: number
  pending: number
  overdue: number
  due_soon: number
  total_amount: number
  paid_amount: number
  pending_amount: number
  overdue_amount: number
}

interface Invoice {
  id: number
  invoice_number: string
  customer_name: string
  total_amount: number
  due_date: string
  status: 'paid' | 'pending' | 'overdue' | 'cancelled'
  invoice_date: string
}

interface InvoiceList {
  items: Invoice[]
  total: number
  page: number
  page_size: number
  pages: number
}

const STATUS_COLORS = {
  paid: '#16a34a',    // green
  pending: '#d97706', // amber
  overdue: '#dc2626', // red
  cancelled: '#9ca3af', // gray
}

const MONTH_NAMES = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)
}

export function AnalyticsPage() {
  const { t } = useI18n()
  useEffect(() => { document.title = `Analytics — FatturaMVP` }, [t])

  // Fetch stats from API
  const { data: stats, isLoading: statsLoading } = useQuery<InvoiceStats>({
    queryKey: ['analytics-stats'],
    queryFn: async () => {
      const response = await api.get('/api/v1/invoices/stats')
      return response.data
    },
  })

  // Fetch all invoices for monthly breakdown + top clients (fetch enough pages)
  const { data: invoicesData, isLoading: invoicesLoading } = useQuery<InvoiceList>({
    queryKey: ['analytics-invoices'],
    queryFn: async () => {
      const response = await api.get('/api/v1/invoices', { params: { page: 1, page_size: 200 } })
      return response.data
    },
  })

  // Compute monthly bar chart data (last 6 months)
  const monthlyData = (() => {
    if (!invoicesData?.items) return []
    const now = new Date()
    return Array.from({ length: 6 }, (_, i) => {
      const d = subMonths(now, 5 - i)
      const mStart = startOfMonth(d)
      const mEnd = endOfMonth(d)
      const mInvoices = invoicesData.items.filter(inv => {
        const date = parseISO(inv.invoice_date)
        return date >= mStart && date <= mEnd
      })
      return {
        month: MONTH_NAMES[d.getMonth()],
        fatture: mInvoices.length,
        ammontare: mInvoices.reduce((s, inv) => s + inv.total_amount, 0),
        pagate: mInvoices.filter(inv => inv.status === 'paid').length,
        insolute: mInvoices.filter(inv => inv.status === 'overdue').length,
      }
    })
  })()

  // Compute pie chart data
  const pieData = (() => {
    if (!stats) return []
    return [
      { name: t('analytics.paid') || 'Pagate', value: stats.paid, color: STATUS_COLORS.paid },
      { name: t('analytics.pending') || 'In attesa', value: stats.pending, color: STATUS_COLORS.pending },
      { name: t('analytics.overdue') || 'Insolute', value: stats.overdue, color: STATUS_COLORS.overdue },
    ].filter(d => d.value > 0)
  })()

  // Top 5 clients by amount
  const topClients = (() => {
    if (!invoicesData?.items) return []
    const map: Record<string, { name: string; total: number; count: number }> = {}
    invoicesData.items.forEach(inv => {
      if (!map[inv.customer_name]) map[inv.customer_name] = { name: inv.customer_name, total: 0, count: 0 }
      map[inv.customer_name].total += inv.total_amount
      map[inv.customer_name].count++
    })
    return Object.values(map).sort((a, b) => b.total - a.total).slice(0, 5)
  })()

  // Average collection time (days between invoice_date and due_date for paid invoices)
  const avgCollectionDays = (() => {
    if (!invoicesData?.items) return 0
    const paid = invoicesData.items.filter(inv => inv.status === 'paid')
    if (paid.length === 0) return 0
    const total = paid.reduce((sum, inv) => {
      const issued = parseISO(inv.invoice_date)
      const due = parseISO(inv.due_date)
      const days = Math.round((due.getTime() - issued.getTime()) / (1000 * 60 * 60 * 24))
      return sum + Math.max(days, 0)
    }, 0)
    return Math.round(total / paid.length)
  })()

  const isLoading = statsLoading || invoicesLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!stats?.total && !invoicesData?.items?.length) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('analytics.title')}
          </h1>
        </div>
        <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm">
          <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
            <FileText className="w-10 h-10 text-gray-400 dark:text-gray-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Nessun dato disponibile</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Importa le tue fatture per visualizzare le analisi</p>
          <div className="flex gap-3 justify-center">
            <Button asChild className="bg-gray-900 hover:bg-gray-800 dark:bg-primary-600 dark:hover:bg-primary-700">
              <Link to="/import"><Upload className="w-4 h-4 mr-2" />Importa fatture</Link>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t('analytics.title')}
        </h1>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="border-blue-100 dark:border-blue-900">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-blue-100 dark:bg-blue-900/40">
                <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total ?? 0}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('analytics.totalInvoices')}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-green-100 dark:border-green-900">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-green-100 dark:bg-green-900/40">
                <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.paid ?? 0}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('analytics.paid')}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-red-100 dark:border-red-900">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-red-100 dark:bg-red-900/40">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.overdue ?? 0}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('analytics.overdue')}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-amber-100 dark:border-amber-900">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-amber-100 dark:bg-amber-900/40">
                <Euro className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatCurrency(stats?.total_amount ?? 0)}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('analytics.totalAmount')}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-purple-100 dark:border-purple-900">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-purple-100 dark:bg-purple-900/40">
                <Clock className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{avgCollectionDays}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{t('analytics.avgCollectionTime')}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Bar Chart - Monthly Invoices */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary-600" />
              {t('analytics.monthlyInvoices')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={monthlyData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value, name) => [
                    (name as string) === 'ammontare' ? formatCurrency(value as number) : value,
                    (name as string) === 'ammontare' ? 'Importo' : 'Fatture'
                  ]}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
                <Bar dataKey="fatture" fill="#3b82f6" name="Fatture" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Pie Chart - Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary-600" />
              {t('analytics.statusDistribution')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pieData.length === 0 ? (
              <div className="flex items-center justify-center h-[260px] text-gray-400 text-sm">
                {t('analytics.noData')}
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => [value, '']}
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  />
                  <Legend
                    formatter={(value) => <span style={{ fontSize: 12 }}>{value}</span>}
                    iconSize={10}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top Clients */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-gray-900 flex items-center gap-2">
            <Users className="w-4 h-4 text-primary-600" />
            {t('analytics.topClients')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {topClients.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <Users className="w-12 h-12 mb-3" />
              <p className="text-sm">{t('analytics.noClients')}</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {topClients.map((client, idx) => (
                <div key={client.name} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 ${
                      idx === 0 ? 'bg-amber-500' : idx === 1 ? 'bg-slate-400' : idx === 2 ? 'bg-orange-400' : 'bg-blue-400'
                    }`}>
                      {idx + 1}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900">{client.name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{client.count} {client.count === 1 ? 'fattura' : 'fatture'}</p>
                    </div>
                  </div>
                  <span className="text-sm font-bold text-gray-900 tabular-nums ml-4">
                    {formatCurrency(client.total)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Amount Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card className="border-green-200 bg-green-50/50">
          <CardContent className="p-5 text-center">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{t('analytics.collected')}</p>
            <p className="text-xl font-bold text-green-700 tabular-nums">{formatCurrency(stats?.paid_amount ?? 0)}</p>
          </CardContent>
        </Card>
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="p-5 text-center">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{t('analytics.pendingAmount')}</p>
            <p className="text-xl font-bold text-amber-700 tabular-nums">{formatCurrency(stats?.pending_amount ?? 0)}</p>
          </CardContent>
        </Card>
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="p-5 text-center">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{t('analytics.overdueAmount')}</p>
            <p className="text-xl font-bold text-red-700 tabular-nums">{formatCurrency(stats?.overdue_amount ?? 0)}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
