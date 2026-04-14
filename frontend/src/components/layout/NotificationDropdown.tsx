import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { Link } from 'react-router-dom'
import { parseISO, isToday, isTomorrow, isPast, differenceInDays } from 'date-fns'
import { Bell, FileText, AlertTriangle, Clock, X, ChevronRight } from 'lucide-react'

interface Invoice {
  id: number
  invoice_number: string
  customer_name: string
  total_amount: number
  due_date: string
  status: 'paid' | 'pending' | 'overdue' | 'cancelled'
}

interface InvoiceList {
  items: Invoice[]
}

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)
}

function getDueLabel(dueDate: string): string {
  const due = parseISO(dueDate)
  if (isToday(due)) return 'Oggi'
  if (isTomorrow(due)) return 'Domani'
  const days = differenceInDays(due, new Date())
  if (days < 0) return `${Math.abs(days)} gg fa`
  return `Tra ${days} gg`
}

export function NotificationDropdown() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const { data, isLoading } = useQuery<InvoiceList>({
    queryKey: ['invoices', { page: 1, page_size: 100 }],
    queryFn: async () => {
      const response = await api.get('/api/v1/invoices', { params: { page: 1, page_size: 100 } })
      return response.data
    },
  })

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const pendingInvoices = data?.items?.filter(inv => inv.status === 'pending' || inv.status === 'overdue') ?? []
  const overdue = pendingInvoices.filter(inv => isPast(parseISO(inv.due_date)) && inv.status !== 'paid')
  const dueSoon = pendingInvoices.filter(inv => {
    const d = parseISO(inv.due_date)
    return !isPast(d) && differenceInDays(d, new Date()) <= 7
  })
  const urgent = [...overdue, ...dueSoon].slice(0, 5)

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
        title="Notifiche"
      >
        <Bell className="w-5 h-5" />
        {urgent.length > 0 && (
          <span className="absolute top-0.5 right-0.5 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {urgent.length > 9 ? '9+' : urgent.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-gray-100 z-[100] overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-gray-600" />
              <span className="text-sm font-semibold text-gray-800">Notifiche</span>
              {urgent.length > 0 && (
                <span className="px-1.5 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                  {urgent.length}
                </span>
              )}
            </div>
            <button onClick={() => setOpen(false)} className="p-1 hover:bg-gray-200 rounded">
              <X className="w-3.5 h-3.5 text-gray-400" />
            </button>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {isLoading ? (
              <div className="flex justify-center py-6">
                <div className="w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : urgent.length === 0 ? (
              <div className="py-8 text-center text-gray-400">
                <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">Nessuna scadenza imminente</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50">
                {urgent.map(inv => {
                  const due = parseISO(inv.due_date)
                  const isOverdue = isPast(due) && inv.status !== 'paid'
                  return (
                    <Link
                      key={inv.id}
                      to={`/invoices/${inv.id}`}
                      onClick={() => setOpen(false)}
                      className="flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors"
                    >
                      <div className={`mt-0.5 rounded-full p-1.5 shrink-0 ${
                        isOverdue ? 'bg-red-100 text-red-600' : 'bg-yellow-100 text-yellow-600'
                      }`}>
                        {isOverdue
                          ? <AlertTriangle className="w-3.5 h-3.5" />
                          : <Clock className="w-3.5 h-3.5" />
                        }
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <p className="text-sm font-medium text-gray-900 truncate">{inv.invoice_number}</p>
                          <span className={`text-xs font-medium shrink-0 ${
                            isOverdue ? 'text-red-600' : 'text-yellow-600'
                          }`}>
                            {getDueLabel(inv.due_date)}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 truncate">{inv.customer_name}</p>
                        <p className="text-sm font-semibold text-gray-800 mt-0.5">
                          {formatCurrency(inv.total_amount)}
                        </p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-gray-300 shrink-0 mt-1" />
                    </Link>
                  )
                })}
              </div>
            )}
          </div>

          {urgent.length > 0 && (
            <div className="px-4 py-2.5 border-t border-gray-100 bg-gray-50">
              <Link
                to="/scadenziario"
                onClick={() => setOpen(false)}
                className="flex items-center justify-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700"
              >
                <FileText className="w-3.5 h-3.5" />
                Vai allo scadenziario
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
