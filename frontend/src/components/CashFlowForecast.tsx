import { useMemo } from 'react'
import { Card, CardContent } from '../components/ui'
import { formatCurrency } from '../lib/utils'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer
} from 'recharts'
import { Calendar } from 'lucide-react'
import { parseISO, addDays, startOfWeek, isSameWeek } from 'date-fns'


interface Invoice {
  id: number
  total_amount: number
  due_date: string
  status: 'paid' | 'pending' | 'overdue'
}

export function CashFlowForecast({ invoices }: { invoices: Invoice[] }) {
  const chartData = useMemo(() => {
    const today = new Date()
    const weeks: { label: string; incassi: number; previsti: number; scaduti: number }[] = []

    for (let w = 0; w < 5; w++) {
      const weekStart = startOfWeek(addDays(today, w * 7), { weekStartsOn: 1 })
      
      const weekInvoices = invoices.filter(inv => {
        const due = parseISO(inv.due_date)
        return isSameWeek(due, weekStart, { weekStartsOn: 1 })
      })

      const incassi = weekInvoices
        .filter(i => i.status === 'paid')
        .reduce((s, i) => s + i.total_amount, 0)

      const previsti = weekInvoices
        .filter(i => i.status === 'pending')
        .reduce((s, i) => s + i.total_amount, 0)

      const scaduti = weekInvoices
        .filter(i => i.status === 'overdue')
        .reduce((s, i) => s + i.total_amount, 0)

      const label = w === 0 ? 'Questa sett.' : w === 1 ? 'Sett. prossima' : `+${w} sett.`

      weeks.push({ label, incassi, previsti, scaduti })
    }

    return weeks
  }, [invoices])

  const totalIncoming = chartData.reduce((s, w) => s + w.incassi + w.previsti, 0)
    
  return (
    <Card className="border border-gray-200 shadow-sm">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">Flusso di cassa</h3>
          <p className="text-xs text-gray-400 mt-0.5">Proiezione settimanale</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-400">Prossime 5 settimane</p>
          <p className="text-lg font-bold text-gray-900">{formatCurrency(totalIncoming)}</p>
        </div>
      </div>
      <CardContent className="p-5">
        {/* Summary chips */}
        <div className="flex gap-2 mb-5">
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 rounded-lg">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-xs font-medium text-emerald-700">Incassati</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 rounded-lg">
            <div className="w-2 h-2 rounded-full bg-blue-400" />
            <span className="text-xs font-medium text-blue-700">Previsti</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-red-50 rounded-lg">
            <div className="w-2 h-2 rounded-full bg-red-400" />
            <span className="text-xs font-medium text-red-700">Scaduti</span>
          </div>
        </div>

        {/* Chart */}
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} barGap={2} barCategoryGap="30%" margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: '#6b7280' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#6b7280' }}
                axisLine={false}
                tickLine={false}
                tickFormatter={v => `€${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                formatter={(value: unknown, name: unknown) => [formatCurrency(value as number), name === 'incassi' ? 'Incassati' : name === 'previsti' ? 'Previsti' : 'Scaduti']}
                contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                labelStyle={{ fontWeight: 600 }}
              />
              <Bar dataKey="incassi" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} />
              <Bar dataKey="previsti" stackId="a" fill="#60a5fa" radius={[0, 0, 0, 0]} />
              <Bar dataKey="scaduti" stackId="a" fill="#f87171" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* This week highlight */}
        <div className="mt-4 p-3 bg-gray-50 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500">Questa settimana</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-emerald-600">
              +{formatCurrency(chartData[0]?.incassi || 0)} incassati
            </span>
            <span className="text-sm font-semibold text-blue-600">
              +{formatCurrency(chartData[0]?.previsti || 0)} previsti
            </span>
            <span className={`text-sm font-bold ${(chartData[0]?.scaduti || 0) > 0 ? 'text-red-600' : 'text-gray-400'}`}>
              {(chartData[0]?.scaduti || 0) > 0 ? `${formatCurrency(chartData[0]?.scaduti || 0)} scaduti` : 'Nessuno scaduto'}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
