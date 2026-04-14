/**
 * PdfPreview - Componente per visualizzare PDF inline nella pagina fattura.
 * 
 * Funzionalità:
 * - Mostra PDF inline usando iframe con blob URL
 * - Loading state durante il caricamento
 * - Fallback se il PDF non è disponibile
 * - Bottone download per scaricare il PDF
 */
import { useState, useEffect, useRef } from 'react'
import { api } from '../lib/api'
import { Button } from './ui'
import { Download, FileX, Loader2, ExternalLink } from 'lucide-react'

interface PdfPreviewProps {
  invoiceId: number
  invoiceNumber?: string
  className?: string
}

export function PdfPreview({ invoiceId, invoiceNumber, className = '' }: PdfPreviewProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    let revoked = false

    const fetchPdf = async () => {
      setLoading(true)
      setError(null)

      try {
        const response = await api.get(`/api/v1/invoices/${invoiceId}/pdf`, {
          responseType: 'blob',
        })

        if (revoked) return

        const blob = new Blob([response.data], { type: 'application/pdf' })
        setPdfBlob(blob)
        objectUrl = URL.createObjectURL(blob)
        setPdfUrl(objectUrl)
      } catch (err: unknown) {
        if (revoked) return
        const error = err as { response?: { status?: number } }
        if (error.response?.status === 404) {
          setError('PDF non disponibile per questa fattura.')
        } else {
          setError('Errore durante il caricamento del PDF.')
        }
        // PDF fetch error silently handled
      } finally {
        if (!revoked) {
          setLoading(false)
        }
      }
    }

    fetchPdf()

    return () => {
      revoked = true
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [invoiceId])

  const handleDownload = () => {
    if (!pdfBlob) return

    const url = URL.createObjectURL(pdfBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `fattura_${(invoiceNumber || String(invoiceId)).replace(/\//g, '_')}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const handleOpenNewTab = () => {
    if (!pdfUrl) return
    const newWindow = window.open(pdfUrl, '_blank')
    if (newWindow) {
      newWindow.focus()
    }
  }

  if (loading) {
    return (
      <div className={`flex flex-col items-center justify-center py-16 bg-gray-50 rounded-xl border border-gray-200 ${className}`}>
        <Loader2 className="w-10 h-10 text-primary-600 animate-spin mb-4" />
        <p className="text-sm text-gray-500">Caricamento PDF in corso...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`flex flex-col items-center justify-center py-16 bg-red-50 rounded-xl border border-red-200 ${className}`}>
        <FileX className="w-12 h-12 text-red-400 mb-4" />
        <p className="text-sm text-red-600 font-medium mb-2">PDF non disponibile</p>
        <p className="text-xs text-red-400 text-center max-w-xs">{error}</p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => window.location.reload()}
          className="mt-4"
        >
          Riprova
        </Button>
      </div>
    )
  }

  if (!pdfUrl) {
    return (
      <div className={`flex flex-col items-center justify-center py-16 bg-gray-50 rounded-xl border border-gray-200 ${className}`}>
        <FileX className="w-12 h-12 text-gray-300 mb-4" />
        <p className="text-sm text-gray-500">Impossibile visualizzare il PDF</p>
      </div>
    )
  }

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 rounded-t-xl border border-b-0 border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 font-medium uppercase tracking-wide">
            Anteprima PDF
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleOpenNewTab}
            title="Apri in nuova scheda"
            className="h-7 px-2 text-gray-500 hover:text-gray-700"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDownload}
            title="Scarica PDF"
            className="h-7 px-2 text-gray-500 hover:text-gray-700"
          >
            <Download className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* PDF iframe */}
      <div className="flex-1 bg-gray-200 rounded-b-xl overflow-hidden border border-gray-200"
        style={{ minHeight: '600px' }}>
        <iframe
          ref={iframeRef}
          src={pdfUrl}
          title={`PDF Fattura ${invoiceNumber || invoiceId}`}
          className="w-full h-full"
          style={{ minHeight: '600px' }}
        />
      </div>

      {/* Download button (mobile fallback) */}
      <div className="mt-3 flex justify-center">
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownload}
          className="flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Scarica PDF
        </Button>
      </div>
    </div>
  )
}
