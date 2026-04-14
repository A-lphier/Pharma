import { useSearchParams, Link } from 'react-router-dom'
import { XCircle, Home, FileText, RefreshCw } from 'lucide-react'
import { Card, CardContent, Button } from '../components/ui'

export function PaymentCancelPage() {
  const [searchParams] = useSearchParams()
  const invoiceId = searchParams.get('invoice_id')

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardContent className="p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
            <XCircle className="w-8 h-8 text-red-500" />
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Pagamento annullato
          </h1>

          <p className="text-gray-500 mb-6">
            Il pagamento è stato annullato. La fattura non è stata modificata.
            Puoi ritentare il pagamento in qualsiasi momento.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {invoiceId && (
              <Link to={`/invoices/${invoiceId}`}>
                <Button variant="outline">
                  <FileText className="w-4 h-4 mr-2" />
                  Vedi fattura
                </Button>
              </Link>
            )}
            <Link to="/invoices">
              <Button variant="outline">
                <RefreshCw className="w-4 h-4 mr-2" />
                Ritenta pagamento
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
