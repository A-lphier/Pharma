import { FileText, Download, CreditCard, CheckCircle, Clock, AlertTriangle } from 'lucide-react'
import { format, differenceInDays } from 'date-fns'
import { it } from 'date-fns/locale'


export interface PortalInvoice {
  id: number
  invoice_number: string
  invoice_date: string
  due_date: string
  total_amount: number
  status: 'paid' | 'pending' | 'overdue'
  description?: string
  paid_date?: string
}

interface PortalInvoiceCardProps {
  invoice: PortalInvoice
  onPay: (invoice: PortalInvoice) => void
  loading?: boolean
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)

const formatDate = (dateStr: string) =>
  format(new Date(dateStr), 'dd MMM yyyy', { locale: it })

const formatDateShort = (dateStr: string) =>
  format(new Date(dateStr), 'dd/MM/yyyy', { locale: it })

function getDaysUntilDue(dueDate: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(dueDate)
  due.setHours(0, 0, 0, 0)
  return differenceInDays(due, today)
}

export function PortalInvoiceCard({ invoice, onPay, loading }: PortalInvoiceCardProps) {
  const isPaid = invoice.status === 'paid'
  const isOverdue = invoice.status === 'overdue'
  const daysUntil = getDaysUntilDue(invoice.due_date)
  const isDueSoon = !isPaid && !isOverdue && daysUntil >= 0 && daysUntil <= 7

  const statusBadge = () => {
    if (isPaid) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700">
          <CheckCircle className="w-3.5 h-3.5" />
          Pagata
        </span>
      )
    }
    if (isOverdue) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700">
          <AlertTriangle className="w-3.5 h-3.5" />
          Scaduta
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">
        <Clock className="w-3.5 h-3.5" />
        In corso
      </span>
    )
  }

  return (
    <div
      className={`bg-white rounded-2xl border transition-all duration-200 hover:shadow-md ${
        isOverdue
          ? 'border-red-200'
          : isPaid
          ? 'border-gray-200'
          : 'border-gray-200'
      }`}
    >
      {/* Overdue warning banner */}
      {isOverdue && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-100 rounded-t-2xl">
          <p className="text-xs text-red-700 flex items-center gap-1.5 font-medium">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            Questa fattura è scaduta — paga ora per evitare solleciti
          </p>
        </div>
      )}

      <div className="p-5">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-gray-400 shrink-0" />
              <span className="font-semibold text-gray-900 text-base truncate">
                {invoice.invoice_number}
              </span>
            </div>
            <p className="text-sm text-gray-500">{formatDate(invoice.invoice_date)}</p>
            {invoice.description && (
              <p className="text-xs text-gray-400 mt-0.5 truncate max-w-[200px]">
                {invoice.description}
              </p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-xl font-bold text-gray-900">
              {formatCurrency(invoice.total_amount)}
            </p>
            {statusBadge()}
          </div>
        </div>

        {/* Due date info */}
        <div className="mb-4">
          {isPaid ? (
            <p className="text-sm text-green-700 font-medium flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 shrink-0" />
              Pagata il {invoice.paid_date ? formatDate(invoice.paid_date) : '—'}
            </p>
          ) : isOverdue ? (
            <p className="text-sm text-red-600 font-medium flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              Scaduta da {Math.abs(daysUntil)} {Math.abs(daysUntil) === 1 ? 'giorno' : 'giorni'} — scadenza {formatDateShort(invoice.due_date)}
            </p>
          ) : isDueSoon ? (
            <p className="text-sm text-amber-600 font-medium flex items-center gap-1.5">
              <Clock className="w-4 h-4 shrink-0" />
              Scade tra {daysUntil} {daysUntil === 1 ? 'giorno' : 'giorni'} — {formatDateShort(invoice.due_date)}
            </p>
          ) : (
            <p className="text-sm text-gray-500">
              Scadenza: <span className="font-medium text-gray-700">{formatDateShort(invoice.due_date)}</span>
              <span className="text-gray-400 ml-1">(tra {daysUntil} giorni)</span>
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {!isPaid && (
            <button
              onClick={() => onPay(invoice)}
              disabled={loading}
              className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-900 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl transition-colors"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Elaborazione...
                </>
              ) : (
                <>
                  <CreditCard className="w-4 h-4" />
                  Paga {formatCurrency(invoice.total_amount)}
                </>
              )}
            </button>
          )}

          <a
            href={`/api/v1/portal/invoice/${invoice.id}/pdf`}
            download={`${invoice.invoice_number}.pdf`}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-xl transition-colors"
          >
            <Download className="w-4 h-4" />
            PDF
          </a>
        </div>

        {/* Paid confirmation */}
        {isPaid && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-sm text-green-700 font-medium flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              Pagamento confermato
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
