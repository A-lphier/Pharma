import { useState, useMemo } from 'react'
import {
  format, parseISO, startOfMonth, endOfMonth, eachDayOfInterval,
  startOfWeek, endOfWeek, addMonths, subMonths, isSameDay, isToday
} from 'date-fns'
import { it } from 'date-fns/locale'
import { ChevronLeft, ChevronRight, AlertTriangle, Clock, CheckCircle2 } from 'lucide-react'
import { formatCurrency } from '../lib/utils'

interface Invoice {
  id: number
  invoice_number: string
  customer_name: string
  total_amount: number
  due_date: string
  status: 'paid' | 'pending' | 'overdue'
}

interface CalendarViewProps {
  invoices: Invoice[]
}

export function CalendarView({ invoices }: CalendarViewProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [selectedDay, setSelectedDay] = useState<Date | null>(null)

  // Build calendar grid
  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const calStart = startOfWeek(monthStart, { weekStartsOn: 1 })
  const calEnd = endOfWeek(monthEnd, { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: calStart, end: calEnd })

  // Group invoices by due date
  const invoicesByDate = useMemo(() => {
    const map: Record<string, Invoice[]> = {}
    invoices.forEach(inv => {
      const key = format(parseISO(inv.due_date), 'yyyy-MM-dd')
      if (!map[key]) map[key] = []
      map[key].push(inv)
    })
    return map
  }, [invoices])

  // Selected day's invoices
  const selectedInvoices = useMemo(() => {
    if (!selectedDay) return []
    const key = format(selectedDay, 'yyyy-MM-dd')
    return invoicesByDate[key] || []
  }, [selectedDay, invoicesByDate])

  const getInvoicesForDay = (day: Date) => {
    const key = format(day, 'yyyy-MM-dd')
    return invoicesByDate[key] || []
  }

  const getDayStatus = (dayInvoices: Invoice[]) => {
    if (!dayInvoices.length) return 'empty'
    const hasOverdue = dayInvoices.some(i => i.status === 'overdue')
    const hasPending = dayInvoices.some(i => i.status === 'pending')
    if (hasOverdue) return 'overdue'
    if (hasPending) return 'pending'
    return 'paid'
  }

  const WEEKDAYS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

  const totalDue = selectedInvoices.reduce((s, i) => s + i.total_amount, 0)
  const overdueCount = selectedInvoices.filter(i => i.status === 'overdue').length

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Calendar header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-gray-900 capitalize">
            {format(currentMonth, 'MMMM yyyy', { locale: it })}
          </h2>
          <div className="flex items-center gap-1">
            <button
              onClick={() => { setCurrentMonth(subMonths(currentMonth, 1)); setSelectedDay(null) }}
              className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center transition-colors"
            >
              <ChevronLeft className="w-4 h-4 text-gray-500" />
            </button>
            <button
              onClick={() => setCurrentMonth(new Date())}
              className="px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Oggi
            </button>
            <button
              onClick={() => { setCurrentMonth(addMonths(currentMonth, 1)); setSelectedDay(null) }}
              className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center transition-colors"
            >
              <ChevronRight className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-red-500" />
            <span className="text-gray-500">Scaduta</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="text-gray-500">In scadenza</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-gray-500">Pagata</span>
          </div>
        </div>
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7">
        {/* Weekday headers */}
        {WEEKDAYS.map(day => (
          <div key={day} className="py-2 text-center text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100">
            {day}
          </div>
        ))}

        {/* Day cells */}
        {days.map((day, idx) => {
          const dayInvoices = getInvoicesForDay(day)
          const status = getDayStatus(dayInvoices)
          const isCurrentMonth = day.getMonth() === currentMonth.getMonth()
          const isSelected = selectedDay && isSameDay(day, selectedDay)
          const isTodayDate = isToday(day)

          const bgClass = isSelected ? 'bg-violet-50 ring-2 ring-violet-500 ring-inset' : ''
          const opacityClass = isCurrentMonth ? '' : 'opacity-25'

          return (
            <button
              key={idx}
              onClick={() => setSelectedDay(dayInvoices.length ? day : null)}
              disabled={!dayInvoices.length}
              className={`
                relative min-h-[72px] p-2 border-b border-r border-gray-50 text-left transition-all
                hover:bg-gray-50
                ${bgClass}
                ${opacityClass}
                ${!dayInvoices.length ? 'cursor-default' : 'cursor-pointer'}
                ${isTodayDate && dayInvoices.length ? 'bg-blue-50/30' : ''}
              `}
            >
              {/* Day number */}
              <span className={`
                inline-flex items-center justify-center w-6 h-6 text-xs font-semibold rounded-full
                ${isTodayDate ? 'bg-blue-600 text-white' : 'text-gray-600'}
              `}>
                {format(day, 'd')}
              </span>

              {/* Invoice dots */}
              {dayInvoices.length > 0 && (
                <div className="mt-1.5 space-y-0.5">
                  {dayInvoices.slice(0, 3).map((inv, i) => (
                    <div key={i} className="flex items-center gap-1">
                      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                        inv.status === 'overdue' ? 'bg-red-500' :
                        inv.status === 'pending' ? 'bg-amber-400' : 'bg-emerald-500'
                      }`} />
                      <span className={`text-xs truncate font-medium ${
                        inv.status === 'overdue' ? 'text-red-700' :
                        inv.status === 'pending' ? 'text-amber-700' : 'text-emerald-700'
                      }`}>
                        {inv.customer_name.split(' ')[0]}
                      </span>
                    </div>
                  ))}
                  {dayInvoices.length > 3 && (
                    <p className="text-xs text-gray-400 pl-2">+{dayInvoices.length - 3}</p>
                  )}
                </div>
              )}

              {/* Overflow indicator */}
              {dayInvoices.length > 0 && (
                <div className="absolute bottom-1 right-1">
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                    status === 'overdue' ? 'bg-red-500' :
                    status === 'pending' ? 'bg-amber-400 text-amber-900' : 'bg-emerald-500'
                  }`}>
                    {dayInvoices.length}
                  </div>
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* Selected day detail */}
      {selectedDay && (
        <div className="border-t border-gray-100 p-4 bg-gray-50/50">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <p className="font-semibold text-gray-900">
                {isToday(selectedDay) ? 'Oggi' : format(selectedDay, 'EEEE d MMMM', { locale: it })}
              </p>
              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                overdueCount > 0 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
              }`}>
                {overdueCount > 0 ? `${overdueCount} scadute` : `${selectedInvoices.length} in scadenza`}
              </span>
            </div>
            <p className="text-sm font-bold text-gray-900">{formatCurrency(totalDue)}</p>
          </div>

          <div className="space-y-2">
            {selectedInvoices.map(inv => (
              <div key={inv.id} className="flex items-center justify-between p-3 bg-white rounded-xl border border-gray-100">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    inv.status === 'overdue' ? 'bg-red-50' :
                    inv.status === 'pending' ? 'bg-amber-50' : 'bg-emerald-50'
                  }`}>
                    {inv.status === 'overdue' ? <AlertTriangle className="w-4 h-4 text-red-500" /> :
                     inv.status === 'pending' ? <Clock className="w-4 h-4 text-amber-500" /> :
                     <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{inv.invoice_number}</p>
                    <p className="text-xs text-gray-500">{inv.customer_name}</p>
                  </div>
                </div>
                <p className={`text-sm font-bold ${
                  inv.status === 'overdue' ? 'text-red-600' : 'text-gray-900'
                }`}>
                  {formatCurrency(inv.total_amount)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
