import { useState, useRef, useEffect } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, Download } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { api } from '../lib/api'
import { ImportResult, ImportHistory } from '../lib/types'
import { formatDateTime } from '../lib/utils'

export function ImportPage() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [history, setHistory] = useState<ImportHistory[]>([])
  const [error, setError] = useState<string | null>(null)

  const loadHistory = async () => {
    try {
      const response = await api.get<ImportHistory[]>('/api/v1/import/history')
      setHistory(response.data)
    } catch (err) {
      // Error loading history silently ignored
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  async function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.csv')) {
      setError('Solo file CSV sono supportati')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    try {
      setUploading(true)
      setError(null)
      const response = await api.post<ImportResult>('/api/v1/import/csv', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      setResult(response.data)
      loadHistory()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore durante l\'importazione')
    } finally {
      setUploading(false)
    }
  }

  function downloadTemplate() {
    const template = 'cliente,data_fattura,data_pagamento,importo\nAcme S.p.A.,2025-01-15,2025-01-20,1500'
    const blob = new Blob([template], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'template_importazione.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Importa dati</h1>
        <p className="text-sm text-gray-500">
          Importa lo storico clienti e pagamenti da un file CSV
        </p>
      </div>

      {/* Upload Card */}
      <Card className="p-6">
        <div className="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg p-8">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            className="hidden"
          />
          
          {uploading ? (
            <Loader2 className="w-12 h-12 animate-spin text-primary-600 mb-4" />
          ) : (
            <Upload className="w-12 h-12 text-gray-400 mb-4" />
          )}
          
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {uploading ? 'Elaborazione in corso...' : 'Carica file CSV'}
          </h3>
          <p className="text-sm text-gray-500 mb-4 text-center">
            Trascina un file qui oppure clicca per selezionarlo
          </p>
          
          <Button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            Seleziona file
          </Button>
          
          <Button
            variant="ghost"
            className="mt-4"
            onClick={downloadTemplate}
          >
            <Download className="w-4 h-4 mr-2" />
            Scarica template CSV
          </Button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </Card>

      {/* Result Card */}
      {result && (
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            {result.success ? (
              <CheckCircle className="w-6 h-6 text-green-500" />
            ) : (
              <AlertCircle className="w-6 h-6 text-red-500" />
            )}
            <h3 className="text-lg font-semibold text-gray-900">
              {result.success ? 'Importazione completata' : 'Importazione fallita'}
            </h3>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">{result.rows_imported}</p>
              <p className="text-sm text-gray-500">Righe</p>
            </div>
            <div className="text-center p-3 bg-green-50 rounded-lg">
              <p className="text-2xl font-bold text-green-600">{result.clients_created}</p>
              <p className="text-sm text-gray-500">Clienti creati</p>
            </div>
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <p className="text-2xl font-bold text-blue-600">{result.clients_updated}</p>
              <p className="text-sm text-gray-500">Clienti aggiornati</p>
            </div>
            <div className="text-center p-3 bg-purple-50 rounded-lg">
              <p className="text-2xl font-bold text-purple-600">{result.invoices_created}</p>
              <p className="text-sm text-gray-500">Fatture importate</p>
            </div>
          </div>

          {result.errors.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Errori riscontrati:</p>
              <ul className="text-sm text-red-600 space-y-1 max-h-32 overflow-y-auto">
                {result.errors.map((err, idx) => (
                  <li key={idx}>• {err}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Format Info */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Formato CSV accettato</h3>
        <div className="bg-gray-50 rounded-lg p-4 overflow-x-auto">
          <code className="text-sm text-gray-700 whitespace-pre">
cliente,data_fattura,data_pagamento,importo
Acme S.p.A.,2025-01-15,2025-01-20,1500
            {'\n'}Mario Rossi,2025-02-01,2025-02-10,2500
          </code>
        </div>
        <div className="mt-4 space-y-2 text-sm text-gray-600">
          <p>• <strong>cliente:</strong> Nome del cliente (obbligatorio)</p>
          <p>• <strong>data_fattura:</strong> Data emissione fattura (YYYY-MM-DD)</p>
          <p>• <strong>data_pagamento:</strong> Data pagamento (YYYY-MM-DD, vuoto se non pagata)</p>
          <p>• <strong>importo:</strong> Importo della fattura (numero, virgola per decimali)</p>
        </div>
      </Card>

      {/* History */}
      {history.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Storico importazioni</h3>
          <div className="space-y-3">
            {history.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-gray-400" />
                  <div>
                    <p className="font-medium text-gray-900">{item.filename}</p>
                    <p className="text-sm text-gray-500">
                      {item.rows_imported} righe • {item.clients_created} clienti • {item.invoices_created} fatture
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">{formatDateTime(item.imported_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
