import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui'
import { Button } from '../components/ui/button'
import { useToast } from '../components/ui/toast'
import { format, addDays } from 'date-fns'
import { ArrowLeft, Plus, Trash2, Send, Check } from 'lucide-react'

interface InvoiceLine {
  description: string
  quantity: number
  unit_price: number
  vat: number
  total?: number
}

interface Client {
  id?: number
  name: string
  vat?: string
  email?: string
  phone?: string
  address?: string
  sdi?: string
  pec?: string
  fiscal_code?: string
  iban?: string
}

interface InvoiceFormData {
  client_id: number | null
  invoice_number: string
  invoice_date: string
  due_date: string
  lines: InvoiceLine[]
  payment_method: string
  payment_terms: string
  iban: string
  notes: string
}

function makeLine(): InvoiceLine {
  return { description: '', quantity: 1, unit_price: 0, vat: 22 }
}

export function InvoiceNewPage() {
  const navigate = useNavigate()
  const { showToast } = useToast()

  const today = format(new Date(), 'yyyy-MM-dd')
  const defaultDue = format(addDays(new Date(), 30), 'yyyy-MM-dd')

  const [step, setStep] = useState(1)
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const [sendSuccess, setSendSuccess] = useState(false)
  const [client, setClient] = useState<Client | null>(null)
  const [clients, setClients] = useState<Client[]>([])
  const [newClientOpen, setNewClientOpen] = useState(false)
  const [newClientData, setNewClientData] = useState<Partial<Client>>({})

  const [formData, setFormData] = useState<InvoiceFormData>({
    client_id: null,
    invoice_number: 'FT/' + new Date().getFullYear() + '/001',
    invoice_date: today,
    due_date: defaultDue,
    lines: [makeLine()],
    payment_method: 'bank_transfer',
    payment_terms: '30gg',
    iban: '',
    notes: '',
  })

  useEffect(() => {
    api.get<{items: Client[]}>('/api/v1/clients').then(r => setClients(r.data.items || [])).catch(() => setClients([]))
  }, [])

  const subtotal = formData.lines.reduce((s, l) => s + l.quantity * l.unit_price, 0)
  const totalVat = formData.lines.reduce((s, l) => s + l.quantity * l.unit_price * l.vat / 100, 0)
  const total = subtotal + totalVat

  const handleAddLine = () => setFormData(f => ({ ...f, lines: [...f.lines, makeLine()] }))

  const handleRemoveLine = (i: number) => setFormData(f => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }))

  const handleLineChange = (i: number, field: keyof InvoiceLine, value: string | number) =>
    setFormData(f => ({ ...f, lines: f.lines.map((l, idx) => idx === i ? { ...l, [field]: value } : l) }))

  const handleClientSelect = (c: Client) => {
    setClient(c)
    setFormData(f => ({ ...f, client_id: c.id || null }))
  }

  const handleCreateClient = async () => {
    try {
      const r = await api.post<Client>('/api/v1/clients', newClientData)
      const created = r.data
      setClient(created)
      setFormData(f => ({ ...f, client_id: created.id || null }))
      setClients(cs => [...cs, created])
      setNewClientOpen(false)
      setNewClientData({})
      showToast('Cliente creato', 'success')
    } catch { showToast('Errore creazione cliente', 'error') }
  }

  const handleSubmit = async () => {
    if (!formData.client_id) { showToast('Seleziona un cliente', 'error'); return }
    setSending(true); setSendError(null)
    try {
      const payload = {
        ...formData,
        lines: formData.lines.map(l => ({ ...l, total: l.quantity * l.unit_price * (1 + l.vat / 100) })),
      }
      await api.post('/api/v1/invoices', payload)
      setSendSuccess(true)
      showToast('Fattura creata!', 'success')
      setTimeout(() => navigate('/invoices'), 1500)
    } catch (e: any) {
      setSendError(e.message || 'Errore')
      showToast('Errore invio', 'error')
    } finally { setSending(false) }
  }

  const stepLabels = ['Cliente', 'Dettagli', 'Pagamento', 'Conferma']

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4 mb-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}><ArrowLeft className="w-4 h-4 mr-1" /> Indietro</Button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Nuova Fattura</h1>
          <p className="text-gray-500 text-sm">Creazione guidata</p>
        </div>
      </div>

      {/* Progress */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center justify-between mb-2">
          {stepLabels.map((label, i) => (
            <div key={i} className="flex items-center">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${i + 1 <= step ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'}`}>{i + 1}</div>
              <span className={`ml-2 text-xs hidden sm:inline ${i + 1 <= step ? 'text-blue-600 font-medium' : 'text-gray-500'}`}>{label}</span>
              {i < 3 && <div className={`w-8 sm:w-16 h-0.5 mx-2 ${i + 1 < step ? 'bg-blue-600' : 'bg-gray-200'}`} />}
            </div>
          ))}
        </div>
        <div className="h-1.5 bg-gray-100 rounded-full"><div className="h-1.5 bg-blue-600 rounded-full transition-all" style={{ width: `${((step - 1) / 3) * 100}%` }} /></div>
      </div>

      {/* Step 1 - Client */}
      {step === 1 && (
        <Card>
          <CardHeader><CardTitle>Seleziona Cliente</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {clients.map(c => (
              <button key={c.id} onClick={() => handleClientSelect(c)}
                className={`w-full p-4 border rounded-lg text-left transition-colors ${formData.client_id === c.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300'}`}>
                <div className="font-medium text-gray-900">{c.name}</div>
                <div className="text-sm text-gray-500">P.IVA: {c.vat || '—'}</div>
              </button>
            ))}
            <button onClick={() => setNewClientOpen(true)}
              className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-blue-400 hover:text-blue-600 transition-colors">
              + Nuovo cliente
            </button>
          </CardContent>
        </Card>
      )}

      {/* Step 2 - Details */}
      {step === 2 && (
        <Card>
          <CardHeader><CardTitle>Dettagli Fattura</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Numero</label>
                <input value={formData.invoice_number} onChange={e => setFormData(f => ({ ...f, invoice_number: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data</label>
                <input type="date" value={formData.invoice_date} onChange={e => setFormData(f => ({ ...f, invoice_date: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Scadenza</label>
                <input type="date" value={formData.due_date} onChange={e => setFormData(f => ({ ...f, due_date: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
              </div>
            </div>
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm font-medium text-gray-700">Beni/Servizi</label>
                <button onClick={handleAddLine} className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"><Plus className="w-4 h-4" /> Aggiungi</button>
              </div>
              <div className="space-y-2">
                {formData.lines.map((line, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 items-end">
                    <input placeholder="Descrizione" value={line.description} onChange={e => handleLineChange(i, 'description', e.target.value)}
                      className="col-span-5 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                    <input type="number" placeholder="Q.ta" value={line.quantity} onChange={e => handleLineChange(i, 'quantity', Number(e.target.value))}
                      className="col-span-2 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                    <input type="number" placeholder="Prezzo" value={line.unit_price} onChange={e => handleLineChange(i, 'unit_price', Number(e.target.value))}
                      className="col-span-2 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                    <input type="number" placeholder="IVA%" value={line.vat} onChange={e => handleLineChange(i, 'vat', Number(e.target.value))}
                      className="col-span-2 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                    <button onClick={() => handleRemoveLine(i)} className="col-span-1 p-2 text-red-500 hover:bg-red-50 rounded"><Trash2 className="w-4 h-4" /></button>
                  </div>
                ))}
              </div>
            </div>
            <div className="text-right space-y-1 pt-2 border-t">
              <div className="text-sm text-gray-500">Imponibile: <span className="text-gray-900">€{subtotal.toFixed(2)}</span></div>
              <div className="text-sm text-gray-500">IVA: <span className="text-gray-900">€{totalVat.toFixed(2)}</span></div>
              <div className="text-lg font-bold text-gray-900">Totale: €{total.toFixed(2)}</div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3 - Payment */}
      {step === 3 && (
        <Card>
          <CardHeader><CardTitle>Dati Pagamento</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">IBAN</label>
              <input placeholder="IT00X0000000000000000000000" value={formData.iban} onChange={e => setFormData(f => ({ ...f, iban: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Modalita</label>
                <select value={formData.payment_method} onChange={e => setFormData(f => ({ ...f, payment_method: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                  <option value="bank_transfer">Bonifico</option><option value="rid">RID</option><option value="cash">Contanti</option><option value="other">Altro</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Termini</label>
                <select value={formData.payment_terms} onChange={e => setFormData(f => ({ ...f, payment_terms: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                  <option value="30gg">30 gg</option><option value="60gg">60 gg</option><option value="90gg">90 gg</option><option value="immediate">Immediato</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Note</label>
              <textarea placeholder="Note..." value={formData.notes} onChange={e => setFormData(f => ({ ...f, notes: e.target.value }))}
                rows={3} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4 - Confirm */}
      {step === 4 && (
        <Card>
          <CardHeader><CardTitle>Conferma e Invia</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <div className="flex justify-between"><span className="text-gray-500">Cliente:</span><span className="font-medium">{client?.name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Numero:</span><span className="font-medium">{formData.invoice_number}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Data:</span><span className="font-medium">{formData.invoice_date}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Scadenza:</span><span className="font-medium">{formData.due_date}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Righe:</span><span className="font-medium">{formData.lines.length}</span></div>
              <div className="border-t pt-2 flex justify-between"><span className="text-gray-500">Totale:</span><span className="font-bold text-lg">€{total.toFixed(2)}</span></div>
            </div>
            {sendError && <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{sendError}</div>}
            {sendSuccess && <div className="p-3 bg-green-50 text-green-700 rounded-lg text-sm flex items-center gap-2"><Check className="w-4 h-4" /> Fattura creata! Reindirizzamento...</div>}
          </CardContent>
        </Card>
      )}

      {/* New Client Modal */}
      {newClientOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md space-y-4">
            <h3 className="text-lg font-semibold">Nuovo Cliente</h3>
            <input placeholder="Nome/Ragione sociale *" value={newClientData.name || ''} onChange={e => setNewClientData(d => ({ ...d, name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            <input placeholder="P.IVA" value={newClientData.vat || ''} onChange={e => setNewClientData(d => ({ ...d, vat: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            <input placeholder="Email" type="email" value={newClientData.email || ''} onChange={e => setNewClientData(d => ({ ...d, email: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setNewClientOpen(false)}>Annulla</Button>
              <Button onClick={handleCreateClient}>Crea</Button>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Button variant="outline" onClick={() => setStep(s => Math.max(1, s - 1))} disabled={step === 1}>Indietro</Button>
        {step < 4 ? (
          <Button onClick={() => setStep(s => s + 1)}>Avanti</Button>
        ) : (
          <Button onClick={handleSubmit} disabled={sending || sendSuccess}>
            {sending ? 'Invio...' : <><Send className="w-4 h-4 mr-1" /> Crea Fattura</>}
          </Button>
        )}
      </div>
    </div>
  )
}
