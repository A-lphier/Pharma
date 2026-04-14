import { useState, useEffect } from 'react'
import { Settings, Save, Loader2 } from 'lucide-react'
import { Button } from './ui/button'
import { Card } from './ui/card'
import { Input } from './ui/input'
import { api } from '../lib/api'
import { BusinessConfig } from '../lib/types'

const STYLE_OPTIONS = [
  { value: 'gentile', label: 'Gentile', description: 'Messaggi cordiali e non invasivi' },
  { value: 'equilibrato', label: 'Equilibrato', description: 'Tono professionale e moderato' },
  { value: 'fermo', label: 'Fermo', description: 'Messaggi decisi e diretti' },
]

interface ConfigPanelProps {
  config?: BusinessConfig
  onSave?: (config: BusinessConfig) => void
  readonly?: boolean
}

export function ConfigPanel({ config, onSave, readonly = false }: ConfigPanelProps) {
  const [formData, setFormData] = useState<Partial<BusinessConfig>>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (config) {
      setFormData(config)
    } else {
      fetchConfig()
    }
  }, [config])

  async function fetchConfig() {
    try {
      setLoading(true)
      const response = await api.get<BusinessConfig>('/api/v1/config')
      setFormData(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore nel caricamento')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      setSaving(true)
      setError(null)
      const response = await api.put<BusinessConfig>('/api/v1/config', formData)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
      onSave?.(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore nel salvataggio')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <Card className="p-6 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
      </Card>
    )
  }

  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
          <Settings className="w-5 h-5 text-primary-600" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Configurazione Sistema Sollecito</h2>
          <p className="text-sm text-gray-500">Imposta le regole per la gestione dei solleciti</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
          Configurazione salvata con successo!
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Style Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Stile dei solleciti
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {STYLE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => !readonly && setFormData({ ...formData, style: option.value as any })}
                disabled={readonly}
                className={`p-3 rounded-lg border-2 text-left transition-all ${
                  formData.style === option.value
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                } ${readonly ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
              >
                <span className="font-medium text-gray-900">{option.label}</span>
                <p className="text-xs text-gray-500 mt-1">{option.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Threshold Fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Soglia legale (€)
            </label>
            <Input
              type="number"
              value={formData.legal_threshold || 0}
              onChange={(e) => setFormData({ ...formData, legal_threshold: Number(e.target.value) })}
              disabled={readonly}
              min={0}
              step={100}
            />
            <p className="text-xs text-gray-500 mt-1">
              Sotto questo importo non conviene agire legalmente
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Score cliente nuovo
            </label>
            <Input
              type="number"
              value={formData.new_client_score || 60}
              onChange={(e) => setFormData({ ...formData, new_client_score: Number(e.target.value) })}
              disabled={readonly}
              min={0}
              max={100}
            />
            <p className="text-xs text-gray-500 mt-1">
              Score iniziale per nuovi clienti (0-100)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Primo sollecito (giorni)
            </label>
            <Input
              type="number"
              value={formData.first_reminder_days || 7}
              onChange={(e) => setFormData({ ...formData, first_reminder_days: Number(e.target.value) })}
              disabled={readonly}
              min={1}
            />
            <p className="text-xs text-gray-500 mt-1">
              Giorni dopo la scadenza per il primo sollecito
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Soglia allarme (giorni)
            </label>
            <Input
              type="number"
              value={formData.warning_threshold_days || 15}
              onChange={(e) => setFormData({ ...formData, warning_threshold_days: Number(e.target.value) })}
              disabled={readonly}
              min={1}
            />
            <p className="text-xs text-gray-500 mt-1">
              Ritardo che attiva il livello di allarme
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Giorni escalation (giorni)
            </label>
            <Input
              type="number"
              value={formData.escalation_days || 30}
              onChange={(e) => setFormData({ ...formData, escalation_days: Number(e.target.value) })}
              disabled={readonly}
              min={1}
            />
            <p className="text-xs text-gray-500 mt-1">
              Ritardo per escalation estrema
            </p>
          </div>
        </div>

        {!readonly && (
          <div className="flex justify-end">
            <Button type="submit" disabled={saving}>
              {saving ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Salva configurazione
            </Button>
          </div>
        )}
      </form>
    </Card>
  )
}
