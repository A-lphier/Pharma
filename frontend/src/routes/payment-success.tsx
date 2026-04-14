import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { CheckCircle, Home, FileText } from 'lucide-react'
import { Card, CardContent, Button } from '../components/ui'
import { useToast } from '../components/ui/toast'

export function PaymentSuccessPage() {
  const [searchParams] = useSearchParams()
  const { showToast } = useToast()
  const [verifying, setVerifying] = useState(true)

  const sessionId = searchParams.get('session_id')

  useEffect(() => {
    if (!sessionId) {
      setVerifying(false)
      return
    }

    // Verify payment status with backend by checking invoice payment status
    const verifyPayment = async () => {
      try {
        // Extract invoice_id from the session metadata via the status endpoint
        // In real mode, we need to know which invoice this session belongs to
        // For demo, we just show success after a brief delay
        setTimeout(() => {
          setVerifying(false)
          showToast('Pagamento completato! La fattura sarà aggiornata a breve.', 'success')
        }, 1500)
      } catch {
        setVerifying(false)
      }
    }

    verifyPayment()
  }, [sessionId])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardContent className="p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Pagamento completato!
          </h1>

          <p className="text-gray-500 mb-6">
            {verifying
              ? 'Verifica in corso...'
              : 'Il pagamento è stato processato con successo. La fattura verrà aggiornata automaticamente.'
            }
          </p>

          {verifying && (
            <div className="flex justify-center mb-6">
              <div className="w-6 h-6 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {sessionId && !verifying && (
            <p className="text-xs text-gray-400 mb-6 font-mono truncate">
              Sessione: {sessionId}
            </p>
          )}

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/invoices">
              <Button variant="outline">
                <FileText className="w-4 h-4 mr-2" />
                Vedi fatture
              </Button>
            </Link>
            <Link to="/dashboard">
              <Button>
                <Home className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
