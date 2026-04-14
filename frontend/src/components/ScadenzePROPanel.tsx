import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui'
import { CalendarDays, TrendingUp } from 'lucide-react'
import { getUpcomingEvents } from '../lib/fiscalCalendar'
import { format, parseISO, differenceInDays } from 'date-fns'
import { it } from 'date-fns/locale'

interface ScadenzePROPanelProps {
  invoicesDue?: Array<{ due_date: string; total_amount: number; status: string }>
}

export function ScadenzePROPanel({ invoicesDue }: ScadenzePROPanelProps) {
  const [daysFilter, setDaysFilter] = useState(30)
  const today = new Date()

  const fiscalEvents = useMemo(() => getUpcomingEvents(daysFilter), [daysFilter])

  const cashflowImpact = useMemo(() => {
    if (!invoicesDue) return 0
    return invoicesDue
      .filter(inv => inv.status !== 'paid')
      .reduce((sum, inv) => sum + inv.total_amount, 0)
  }, [invoicesDue])

  const daysLeft = (dateStr: string) => differenceInDays(parseISO(dateStr), today)
  const formatDate = (d: string) => format(parseISO(d), 'dd MMM', { locale: it })
  const isUrgent = (d: string) => daysLeft(d) <= 3
  const isSoon = (d: string) => daysLeft(d) <= 7

  const tipoColors: Record<string, string> = {
    IVA: 'bg-red-50 text-red-700 border-red-100',
    ACCONTO: 'bg-blue-50 text-blue-700 border-blue-100',
    COMUNICAZIONE: 'bg-violet-50 text-violet-700 border-violet-100',
  }

  return (
    <div className="space-y-3">
      {/* ── Header Stats ── */}
      <div className="grid grid-cols-2 gap-2">
        <Card className="border border-gray-200 shadow-sm">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-gray-400 mb-1">Prossime scadenze</p>
            <p className="text-2xl font-bold text-gray-900">{fiscalEvents.length}</p>
            <p className="text-xs text-gray-400">in {daysFilter}gg</p>
          </CardContent>
        </Card>
        <Card className="border border-gray-200 shadow-sm">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-gray-400 mb-1">Fatture in scadenza</p>
            <p className="text-2xl font-bold text-gray-900">{invoicesDue?.filter(i => i.status !== 'paid').length || 0}</p>
            <p className="text-xs text-gray-400">
              {invoicesDue ? `€${(cashflowImpact / 1000).toFixed(0)}K` : '—'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* ── Filter ── */}
      <div className="flex gap-1">
        {[7, 14, 30, 60].map(d => (
          <button
            key={d}
            onClick={() => setDaysFilter(d)}
            className={`flex-1 py-1.5 text-xs rounded-lg border font-medium transition-all duration-150 ${
              daysFilter === d
                ? 'bg-gray-900 text-white border-gray-900'
                : 'bg-white text-gray-500 border-gray-200 hover:bg-gray-50'
            }`}
          >
            {d}gg
          </button>
        ))}
      </div>

      {/* ── Fiscal Events ── */}
      <Card className="border border-gray-200 shadow-sm">
        <CardHeader className="pb-2 px-4 pt-4">
          <CardTitle className="text-sm flex items-center gap-2">
            <CalendarDays className="w-4 h-4 text-gray-500" />
            Calendario Fiscale
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-1.5">
          {fiscalEvents.length === 0 && (
            <p className="text-sm text-gray-400 py-4 text-center">
              Nessuna scadenza nei prossimi {daysFilter} giorni
            </p>
          )}
          {fiscalEvents.slice(0, 8).map((event) => {
            const urgent = isUrgent(event.date)
            const soon = isSoon(event.date)
            const dl = daysLeft(event.date)

            return (
              <div
                key={event.id}
                className={`flex items-start gap-2.5 p-2.5 rounded-lg border transition-colors ${
                  urgent
                    ? 'bg-red-50/70 border-red-100'
                    : soon
                    ? 'bg-amber-50/70 border-amber-100'
                    : 'hover:bg-gray-50 border-transparent'
                }`}
              >
                {/* Date badge */}
                <div className={`shrink-0 w-9 h-9 rounded-lg flex flex-col items-center justify-center text-xs font-bold border ${
                  urgent
                    ? 'bg-red-100 text-red-700 border-red-200'
                    : soon
                    ? 'bg-amber-100 text-amber-700 border-amber-200'
                    : 'bg-gray-100 text-gray-600 border-gray-200'
                }`}>
                  <span className="leading-none text-[10px] uppercase">{formatDate(event.date).split(' ')[1]}</span>
                  <span className="leading-none font-bold">{formatDate(event.date).split(' ')[0]}</span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
                    <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border ${tipoColors[event.tipo] || 'bg-gray-50 text-gray-600 border-gray-100'}`}>
                      {event.tipo}
                    </span>
                    {urgent && (
                      <span className="text-xs bg-red-100 text-red-600 rounded px-1.5 py-0.5 font-semibold">Urgenza</span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-gray-800 leading-tight">{event.label}</p>
                  <p className="text-xs text-gray-500 mt-0.5 leading-tight">{event.description}</p>
                </div>

                {/* Days badge */}
                <div className="text-right shrink-0">
                  {dl >= 0 ? (
                    <span className={`text-xs font-bold tabular-nums ${
                      urgent ? 'text-red-600' : soon ? 'text-amber-600' : 'text-gray-400'
                    }`}>
                      {dl === 0 ? 'Oggi' : `${dl}g`}
                    </span>
                  ) : (
                    <span className="text-xs font-bold text-red-500 tabular-nums">
                      -{Math.abs(dl)}g fa
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>

      {/* ── Cashflow Alert ── */}
      {cashflowImpact > 0 && (
        <Card className="border border-blue-200 shadow-sm bg-gradient-to-r from-blue-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-600 shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-blue-800">
                  Uscite previste ({daysFilter}gg):
                </p>
                <p className="text-xs text-blue-600">
                  {invoicesDue?.filter(i => i.status !== 'paid').length} fatture
                </p>
              </div>
              <p className="text-lg font-bold text-blue-700 tabular-nums">
                €{cashflowImpact.toLocaleString('it')}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
