import { Link } from 'react-router-dom'
import { format, parseISO, subMonths, startOfMonth, endOfMonth } from 'date-fns'
import { it } from 'date-fns/locale'
import { formatCurrency } from '../lib/utils'
import { DSOForecast } from '../components/DSOForecast'
import { TrustScoreBadge } from '../components/TrustScoreBadge'
import { DeductibilityBadge } from '../components/DeductibilityBadge'
import { AIRecoverer } from '../components/AIRecoverer'
import { CollectionFunnel } from '../components/CollectionFunnel'
import { CashFlowForecast } from '../components/CashFlowForecast'
import { ActivityFeed } from '../components/ActivityFeed'
import {
  FileText, Users, CalendarDays,
  Upload, AlertTriangle, Clock, TrendingUp,
  ChevronRight,
} from 'lucide-react'
import { Card, CardContent, Button } from '../components/ui'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

interface Stats { total: number; paid_amount: number; pending_amount: number; overdue_amount: number; overdue: number; due_soon: number; total_amount: number; paid: number; pending: number }
interface Invoice { id: number; invoice_number: string; customer_name: string; total_amount: number; due_date: string; status: string; invoice_date: string; trust_score?: number; description?: string; updated_at?: string }
interface InvoicesResponse { items: Invoice[]; total: number; page: number; page_size: number }
interface StatsResponse { items: Stats[] }

export function DashboardPage() {
  const { data: statsData, isLoading: statsLoading } = useQuery<StatsResponse>({
    queryKey: ['stats'],
    queryFn: () => api.get('/api/v1/invoices/stats').then((r: { data: StatsResponse }) => r.data),
  })
  const stats = statsData?.items?.[0]

  const { data: allInvoices } = useQuery<InvoicesResponse>({
    queryKey: ['invoices', 'all'],
    queryFn: () => api.get('/api/v1/invoices?page_size=100').then((r: { data: InvoicesResponse }) => r.data),
  })

  const paymentForecast = (() => {
    if (!allInvoices?.items) return { next30: 0, next60: 0, next90: 0 }
    const now = new Date()
    const in30 = new Date(now); in30.setDate(now.getDate() + 30)
    const in60 = new Date(now); in60.setDate(now.getDate() + 60)
    const in90 = new Date(now); in90.setDate(now.getDate() + 90)
    return {
      next30: allInvoices.items.filter(inv => inv.status === 'pending' && new Date(inv.due_date) <= in30).reduce((sum, inv) => sum + inv.total_amount, 0),
      next60: allInvoices.items.filter(inv => inv.status === 'pending' && new Date(inv.due_date) <= in60).reduce((sum, inv) => sum + inv.total_amount, 0),
      next90: allInvoices.items.filter(inv => inv.status === 'pending' && new Date(inv.due_date) <= in90).reduce((sum, inv) => sum + inv.total_amount, 0),
    }
  })()

  const chartData = (() => {
    const months = []
    for (let i = 5; i >= 0; i--) {
      const start = startOfMonth(subMonths(new Date(), i))
      const end = endOfMonth(subMonths(new Date(), i))
      const monthInvoices = allInvoices?.items?.filter(inv => {
        const d = parseISO(inv.invoice_date)
        return d >= start && d <= end
      }) || []
      months.push({
        month: format(start, 'MMM', { locale: it }),
        incassati: monthInvoices.filter(i => i.status === 'paid').reduce((s, i) => s + i.total_amount, 0),
        inScadenza: monthInvoices.filter(i => i.status === 'pending').reduce((s, i) => s + i.total_amount, 0),
      })
    }
    return months
  })()

  const recentInvoices = allInvoices?.items?.slice().sort((a, b) => new Date(b.invoice_date).getTime() - new Date(a.invoice_date).getTime()).slice(0, 7) || []
  const overdueCount = allInvoices?.items?.filter(i => i.status === 'overdue').length || 0
  const overdueAmount = allInvoices?.items?.filter(i => i.status === 'overdue').reduce((s, i) => s + i.total_amount, 0) || 0
  const pendingAmount = allInvoices?.items?.filter(i => i.status === 'pending').reduce((s, i) => s + i.total_amount, 0) || 0
  const totalOutstanding = pendingAmount + overdueAmount
  const hasOverdue = overdueCount > 0

  return (
    <div className="min-h-screen bg-gray-50">

      {/* ── HERO: Full-width dark strip ─────────────────────────────── */}
      <div className="bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 relative overflow-hidden">
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)', backgroundSize: '28px 28px' }} />
        {/* Glow */}
        <div className="absolute -top-32 -right-32 w-96 h-96 bg-blue-600 rounded-full opacity-10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -left-20 w-64 h-64 bg-indigo-600 rounded-full opacity-10 blur-3xl pointer-events-none" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-8">
          {(statsLoading && !stats) ? (
            <div className="flex items-start justify-between">
              <div>
                <div className="h-3 w-48 bg-white/10 rounded mb-3 animate-pulse" />
                <div className="h-3 w-32 bg-white/10 rounded mb-1 animate-pulse" />
                <div className="h-14 w-56 bg-white/10 rounded animate-pulse" />
              </div>
            </div>
          ) : (
            <>
            <div className="flex items-start justify-between">
              {/* Left: Big number */}
              <div>
                <p className="text-xs font-medium text-gray-300 uppercase tracking-widest mb-3">
                  {format(new Date(), 'EEEE, d MMMM yyyy', { locale: it })}
                </p>
                <p className="text-xs text-gray-300 mb-1">Totale da incassare</p>
                <p className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight tabular-nums leading-none">
                  {formatCurrency(totalOutstanding)}
                </p>
                <div className="flex items-center gap-2 mt-3">
                  {hasOverdue ? (
                    <>
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-500/20 border border-red-500/30 rounded-full text-xs font-semibold text-red-400">
                        <AlertTriangle className="w-3 h-3" />
                        {overdueCount === 1 ? '1 fattura scaduta' : `${overdueCount} fatture scadute`}
                      </span>
                      <span className="text-red-500 text-sm font-medium">{formatCurrency(overdueAmount)}</span>
                    </>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-500/20 border border-emerald-500/30 rounded-full text-xs font-semibold text-emerald-400">
                      Tutto in regola
                    </span>
                  )}
                </div>
              </div>

              {/* Right: CTAs */}
              <div className="flex flex-col sm:flex-row gap-3">
                <Link to="/invoices?upload=true" className="inline-flex items-center justify-center gap-2 px-5 py-2.5 min-h-11 bg-white text-gray-900 text-sm font-semibold rounded-xl hover:bg-gray-100 transition-colors shadow-lg shadow-black/20">
                  <Upload className="w-4 h-4" /> Carica fattura
                </Link>
                <Link to="/scadenziario" className="inline-flex items-center justify-center gap-2 px-5 py-2.5 min-h-11 bg-white/10 text-gray-200 text-sm font-medium rounded-xl hover:bg-white/20 transition-colors border border-white/20">
                  <CalendarDays className="w-4 h-4" /> Scadenziario
                </Link>
              </div>
            </div>

            {/* 30/60/90 forecast row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-8 pt-8 border-t border-white/10">
              {[
                { label: 'Incassi 30gg', value: paymentForecast.next30, color: 'text-white', sub: 'Prossimi 30 giorni' },
                { label: 'Incassi 60gg', value: paymentForecast.next60, color: 'text-gray-300', sub: 'Prossimi 60 giorni' },
                { label: 'Incassi 90gg', value: paymentForecast.next90, color: 'text-gray-300', sub: 'Prossimi 90 giorni' },
              ].map(({ label, value, color, sub }) => (
                <div key={label} className="flex flex-col items-center text-center p-3 rounded-xl bg-white/5 border border-white/10">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">{label}</p>
                  <p className={`text-xl sm:text-2xl font-bold tabular-nums ${color}`}>{formatCurrency(value)}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{sub}</p>
                </div>
              ))}
            </div>
            </>
          )}
        </div>
      </div>

      {/* ── STATS ROW — 4 cards ─────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 mt-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Fatture totali', value: stats?.total || 0, icon: FileText, color: 'text-blue-600', bg: 'bg-blue-50', to: '/invoices', sub: `${stats?.paid || 0} pagate · ${stats?.pending || 0} in corso` },
            { label: 'Incassato', value: stats?.paid_amount || 0, icon: TrendingUp, color: 'text-emerald-600', bg: 'bg-emerald-50', to: '/invoices?status=paid', sub: 'Totale riscosso', highlight: true },
            { label: 'Scadute', value: overdueCount, icon: AlertTriangle, color: hasOverdue ? 'text-red-600' : 'text-emerald-600', bg: hasOverdue ? 'bg-red-50' : 'bg-emerald-50', to: '/invoices?status=overdue', sub: overdueCount > 0 ? formatCurrency(overdueAmount) : 'Nessuna' },
            { label: 'Clienti attivi', value: allInvoices ? new Set(allInvoices.items.map(i => i.customer_name)).size : 0, icon: Users, color: 'text-violet-600', bg: 'bg-violet-50', to: '/clients', sub: 'Registrati' },
          ].map(({ label, value, icon: Icon, color, bg, to, sub, highlight }) => (
            <Link key={label} to={to} className="block group">
              <Card className={`border-0 shadow-sm hover:shadow-md transition-all duration-200 ${highlight ? 'bg-gradient-to-br from-emerald-50 to-white border border-emerald-100' : 'bg-white'}`}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-2">
                    <span className={`text-xs font-medium text-gray-600 uppercase tracking-wide`}>{label}</span>
                    <div className={`p-1.5 rounded-lg ${bg}`}>
                      <Icon className={`w-4 h-4 ${color}`} />
                    </div>
                  </div>
                  <p className={`text-2xl font-bold tabular-nums ${highlight ? 'text-emerald-700' : 'text-gray-900'}`}>{label === 'Incassato' ? formatCurrency(value) : value}</p>
                  <p className="text-xs text-gray-600 mt-0.5">{sub}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {/* ── MAIN CONTENT ───────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

        {/* Funnel + Forecast + Activity */}
        <div className="grid lg:grid-cols-3 gap-6">
          <CollectionFunnel
            invoices={(allInvoices?.items || []).map(inv => ({
              id: inv.id,
              invoice_number: inv.invoice_number,
              customer_name: inv.customer_name,
              total_amount: inv.total_amount,
              due_date: inv.due_date,
              status: inv.status as 'paid' | 'pending' | 'overdue',
              escalation_stage: (inv as { escalation_stage?: string }).escalation_stage,
            }))}
          />
          <CashFlowForecast
            invoices={(allInvoices?.items || []).map(inv => ({
              id: inv.id,
              total_amount: inv.total_amount,
              due_date: inv.due_date,
              status: inv.status as 'paid' | 'pending' | 'overdue',
            }))}
          />
          <ActivityFeed />
        </div>

        {/* DSO + AI Recoverer */}
        <div className="grid lg:grid-cols-3 gap-6">
          <DSOForecast
            invoices={(allInvoices?.items || []).map(inv => ({
              id: inv.id, customer_name: inv.customer_name, total_amount: inv.total_amount,
              due_date: inv.due_date, status: inv.status as 'paid' | 'pending' | 'overdue',
              paid_date: inv.status === 'paid' ? inv.updated_at : undefined,
            }))}
          />
          <div className="lg:col-span-2">
            <AIRecoverer
              invoices={(allInvoices?.items || [])
                .filter(inv => inv.status === 'overdue' || inv.status === 'pending')
                .slice(0, 4)
                .map(inv => ({
                  id: inv.id, customer_name: inv.customer_name, total_amount: inv.total_amount,
                  days_overdue: Math.max(0, Math.floor((Date.now() - new Date(inv.due_date).getTime()) / (1000 * 60 * 60 * 24))),
                  status: 'negotiating' as const, probability: Math.floor(Math.random() * 60 + 20),
                }))}
            />
          </div>
        </div>

        {/* ── CHART + INVOICES ROW ────────────────────────────────────── */}
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Chart — 2 cols */}
          <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-gray-900">Andamento</h2>
                <p className="text-xs text-gray-500 mt-0.5">Ultimi 6 mesi</p>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="text-gray-600">Incassati</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-amber-400" />
                  <span className="text-gray-600">In scadenza</span>
                </div>
              </div>
            </div>
            <div className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorInc" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.15}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorScad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.15}/>
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#6b7280' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} axisLine={false} tickLine={false} tickFormatter={v => `€${(v/1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value) => [formatCurrency(Number(value)), '']} contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }} />
                  <Area type="monotone" dataKey="incassati" stroke="#10b981" strokeWidth={2} fill="url(#colorInc)" />
                  <Area type="monotone" dataKey="inScadenza" stroke="#f59e0b" strokeWidth={2} fill="url(#colorScad)" strokeDasharray="4 4" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recent invoices — 3 cols */}
          <div className="lg:col-span-3 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">Ultime fatture</h2>
              <Link to="/invoices" className="text-xs text-gray-500 hover:text-gray-900 flex items-center gap-1 transition-colors">
                Vedi tutte <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
            {recentInvoices.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-center px-6">
                <div className="w-14 h-14 rounded-2xl bg-violet-50 flex items-center justify-center mb-3">
                  <FileText className="w-7 h-7 text-violet-400" />
                </div>
                <p className="text-sm font-semibold text-gray-900">Nessuna fattura ancora</p>
                <p className="text-xs text-gray-500 mt-1 mb-5">Carica il tuo primo file FatturaPA XML (formato SDI) per iniziare a tracciare le tue fatture</p>
                <div className="flex flex-col sm:flex-row gap-2">
                  <Button size="sm" asChild className="bg-gray-900 hover:bg-gray-800">
                    <Link to="/invoices?upload=true">
                      <Upload className="w-4 h-4 mr-1.5" />Carica fattura
                    </Link>
                  </Button>
                  <Button size="sm" variant="outline" asChild>
                    <Link to="/import">Come funziona</Link>
                  </Button>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {recentInvoices.map((invoice) => {
                  const isOverdue = invoice.status === 'overdue'
                  const isPaid = invoice.status === 'paid'
                  const hasScore = invoice.trust_score != null && invoice.trust_score > 0
                  const hasDeduct = !!invoice.description
                  return (
                    <Link
                      key={invoice.id}
                      to={`/invoices/${invoice.id}`}
                      className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50/60 transition-colors group"
                    >
                      <div className={`shrink-0 w-9 h-9 rounded-xl flex items-center justify-center ${
                        isPaid ? 'bg-emerald-50' : isOverdue ? 'bg-red-50' : 'bg-gray-100'
                      }`}>
                        {isPaid ? <TrendingUp className="w-4 h-4 text-emerald-600" />
                         : isOverdue ? <AlertTriangle className="w-4 h-4 text-red-500" />
                         : <Clock className="w-4 h-4 text-gray-500" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate leading-tight">{invoice.customer_name}</p>
                        <p className="text-xs text-gray-500 mt-0.5 leading-tight">
                          {invoice.invoice_number} · {format(parseISO(invoice.due_date), 'd MMM', { locale: it })}
                        </p>
                      </div>
                      <div className="text-right shrink-0 ml-auto">
                        <p className={`text-sm font-semibold tabular-nums ${
                          isPaid ? 'text-emerald-600' : isOverdue ? 'text-red-600' : 'text-gray-900'
                        }`}>{formatCurrency(invoice.total_amount)}</p>
                        <p className={`text-xs mt-0.5 ${
                          isPaid ? 'text-emerald-600' : isOverdue ? 'text-red-600' : 'text-gray-600'
                        }`}>{isPaid ? 'Pagata' : isOverdue ? 'Scaduta' : 'In corso'}</p>
                      </div>
                      {(hasScore || hasDeduct) && (
                        <div className="flex items-center gap-1 shrink-0">
                          {hasScore && <TrustScoreBadge score={invoice.trust_score!} size="sm" showLabel={false} />}
                          {hasDeduct && <DeductibilityBadge description={invoice.description!} inline size="sm" />}
                        </div>
                      )}
                      <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors shrink-0" />
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
