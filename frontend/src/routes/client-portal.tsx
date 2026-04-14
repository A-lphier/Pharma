import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { CheckCircle2, Download, CreditCard, AlertTriangle, Euro, Shield, X } from 'lucide-react'
import { formatCurrency } from '../lib/utils'

interface PortalInvoice {
  id: number
  invoice_number: string
  total_amount: number
  due_date: string
  status: 'paid' | 'pending' | 'overdue'
  invoice_date: string
}

const MOCK_PORTAL: Record<string, { customer_name: string; customer_email: string; invoices: PortalInvoice[] }> = {
  'demo-portal-techsolutions-2026': {
    customer_name: 'Tech Solutions S.r.l.',
    customer_email: 'amministrazione@techsolutions.it',
    invoices: [
      { id: 3, invoice_number: 'FT/2026/0003', total_amount: 8900, due_date: '2026-01-15', status: 'overdue', invoice_date: '2026-01-01' },
      { id: 1, invoice_number: 'FT/2026/0001', total_amount: 5200, due_date: '2026-02-01', status: 'paid', invoice_date: '2026-01-15' },
      { id: 2, invoice_number: 'FT/2026/0002', total_amount: 3150, due_date: '2026-02-15', status: 'paid', invoice_date: '2026-01-20' },
    ],
  },
}

function StripeModal({ amount, invoiceNumber, onClose }: { amount: number; invoiceNumber: string; onClose: () => void }) {
  const [step, setStep] = useState<'idle' | 'processing' | 'done'>('idle')
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-white" />
            <span className="font-semibold text-white">Pagamento sicuro</span>
          </div>
          <button onClick={onClose} className="text-white/70 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6">
          {step === 'idle' && (
            <>
              <div className="text-center mb-6">
                <p className="text-3xl font-bold text-gray-900 mt-1">{formatCurrency(amount)}</p>
                <p className="text-xs text-gray-400 mt-1">Fattura {invoiceNumber}</p>
              </div>
              <div className="space-y-3 mb-6">
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Numero carta</label>
                  <input type="text" placeholder="4242 4242 4242 4242" className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Scadenza</label>
                    <input type="text" placeholder="12/28" className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">CVC</label>
                    <input type="text" placeholder="123" className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                  </div>
                </div>
              </div>
              <button
                onClick={() => setStep('processing')}
                className="w-full bg-violet-600 hover:bg-violet-700 text-white py-3 rounded-xl font-semibold transition-colors"
              >
                Paga {formatCurrency(amount)}
              </button>
              <div className="flex items-center justify-center gap-1 mt-3 text-xs text-gray-400">
                <Shield className="w-3.5 h-3.5" />
                Pagamento elaborato da Stripe — crittografato end-to-end
              </div>
            </>
          )}
          {step === 'processing' && (
            <div className="text-center py-8" onClick={() => setStep('done')}>
              <div className="w-12 h-12 rounded-full border-4 border-violet-200 border-t-violet-600 animate-spin mx-auto mb-4" />
              <p className="text-sm font-medium text-gray-700">Elaborazione...</p>
              <p className="text-xs text-gray-400 mt-1">(click to simulate done)</p>
            </div>
          )}
          {step === 'done' && (
            <div className="text-center py-8">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
              <p className="text-lg font-bold text-gray-900">Pagamento riuscito!</p>
              <p className="text-sm text-gray-500 mt-1">La fattura è stata saldata</p>
              <button onClick={onClose} className="mt-6 w-full bg-gray-900 text-white py-2.5 rounded-xl font-semibold">
                Chiudi
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function ClientPortalPage() {
  const { token } = useParams<{ token: string }>()
  const [payTarget, setPayTarget] = useState<{ id: number; amount: number; number: string } | null>(null)
  const data = token ? MOCK_PORTAL[token] : null
  const pending = data?.invoices.filter(i => i.status !== 'paid') || []
  const paid = data?.invoices.filter(i => i.status === 'paid') || []

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-gray-900 mb-2">Link non valido</h1>
          <p className="text-sm text-gray-500">Questo link non è attivo o è già stato utilizzato.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {payTarget && (
        <StripeModal
          amount={payTarget.amount}
          invoiceNumber={payTarget.number}
          onClose={() => setPayTarget(null)}
        />
      )}

      <div className="bg-white border-b border-gray-200">
        <div className="max-w-xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gray-900 rounded-xl flex items-center justify-center">
                <Euro className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-xs text-gray-500">PORTALE PAGAMENTI</p>
                <h1 className="font-bold text-gray-900">{data.customer_name}</h1>
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <Shield className="w-3.5 h-3.5" />
              FatturaMVP
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-xl mx-auto px-4 py-8 space-y-6">
        {pending.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Da pagare</h2>
            <div className="space-y-3">
              {pending.map(inv => (
                <div key={inv.id} className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                  {inv.status === 'overdue' && (
                    <div className="bg-red-50 border-b border-red-100 px-4 py-2.5 flex items-center gap-2">
                      <AlertTriangle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                      <p className="text-xs font-medium text-red-700">Questa fattura è scaduta — paga ora per evitare solleciti</p>
                    </div>
                  )}
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-gray-900">{inv.invoice_number}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          Emessa {new Date(inv.invoice_date).toLocaleDateString('it-IT')}
                        </p>
                        <p className="text-xs text-gray-400">
                          Scade {new Date(inv.due_date).toLocaleDateString('it-IT')}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-bold text-gray-900">{formatCurrency(inv.total_amount)}</p>
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold mt-1 ${
                          inv.status === 'overdue' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                        }`}>
                          {inv.status === 'overdue' ? 'Scaduta' : 'In scadenza'}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-4">
                      <button
                        onClick={() => setPayTarget({ id: inv.id, amount: inv.total_amount, number: inv.invoice_number })}
                        className="flex-1 inline-flex items-center justify-center gap-2 py-2.5 bg-gray-900 hover:bg-gray-800 text-white text-sm font-semibold rounded-xl transition-colors"
                      >
                        <CreditCard className="w-4 h-4" /> Paga ora
                      </button>
                      <button className="px-3 py-2.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-xl hover:bg-gray-50 transition-colors">
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {paid.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Pagate</h2>
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm divide-y divide-gray-100">
              {paid.map(inv => (
                <div key={inv.id} className="px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-gray-700">{inv.invoice_number}</p>
                      <p className="text-xs text-gray-400">{formatCurrency(inv.total_amount)} · Pagata</p>
                    </div>
                  </div>
                  <button className="text-gray-400 hover:text-gray-600">
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="text-center pt-4">
          <p className="text-xs text-gray-400">
            Powered by <span className="font-semibold text-gray-600">FatturaMVP</span>
          </p>
        </div>
      </div>
    </div>
  )
}
