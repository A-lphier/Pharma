import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card } from '../components/ui/card'
import { api } from '../lib/api'
import { Client } from '../lib/types'

export function ClientFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEditing = Boolean(id)

  const [loading, setLoading] = useState(isEditing)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    name: '',
    vat: '',
    fiscal_code: '',
    email: '',
    phone: '',
    pec: '',
    sdi: '',
    iban: '',
    address: '',
    notes: '',
  })

  useEffect(() => {
    if (isEditing && id) {
      fetchClient(id)
    }
  }, [id])

  async function fetchClient(clientId: string) {
    try {
      setLoading(true)
      const response = await api.get<Client>(`/api/v1/clients/${clientId}`)
      const client = response.data
      setFormData({
        name: client.name || '',
        vat: client.vat || '',
        fiscal_code: client.fiscal_code || '',
        email: client.email || '',
        phone: client.phone || '',
        pec: client.pec || '',
        sdi: client.sdi || '',
        iban: client.iban || '',
        address: client.address || '',
        notes: client.notes || '',
      })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore nel caricamento del cliente')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      setSaving(true)
      setError(null)
      if (isEditing && id) {
        await api.put(`/api/v1/clients/${id}`, formData)
      } else {
        await api.post('/api/v1/clients', formData)
      }
      navigate('/clients')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore nel salvataggio')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" asChild>
          <Link to="/clients">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Clienti
          </Link>
        </Button>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEditing ? 'Modifica cliente' : 'Nuovo cliente'}
        </h1>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm">
          {error}
        </div>
      )}

      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Ragione sociale / Nome *
              </label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Acme S.p.A."
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Partita IVA
              </label>
              <Input
                value={formData.vat}
                onChange={(e) => setFormData({ ...formData, vat: e.target.value })}
                placeholder="IT12345678901"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Codice Fiscale
              </label>
              <Input
                value={formData.fiscal_code}
                onChange={(e) => setFormData({ ...formData, fiscal_code: e.target.value })}
                placeholder="ABCDEF12G34H567I"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="cliente@esempio.it"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Telefono
              </label>
              <Input
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+39 02 1234567"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                PEC
              </label>
              <Input
                value={formData.pec}
                onChange={(e) => setFormData({ ...formData, pec: e.target.value })}
                placeholder="cliente@pec.esempio.it"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SDI
              </label>
              <Input
                value={formData.sdi}
                onChange={(e) => setFormData({ ...formData, sdi: e.target.value })}
                placeholder="M5UXCR1"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                IBAN
              </label>
              <Input
                value={formData.iban}
                onChange={(e) => setFormData({ ...formData, iban: e.target.value })}
                placeholder="IT60 X054 2811 1010 0000 0123 456"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Indirizzo
              </label>
              <Input
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Via Roma 123, 20100 Milano"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Note
              </label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Note sul cliente..."
                rows={3}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => navigate('/clients')}>
              Annulla
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : null}
              {isEditing ? 'Salva modifiche' : 'Crea cliente'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
