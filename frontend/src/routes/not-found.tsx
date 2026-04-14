import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, Button } from '../components/ui'
import { FileQuestion, Home } from 'lucide-react'

export function NotFoundPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <div className="mx-auto mb-4">
            <FileQuestion className="w-16 h-16 text-gray-300" />
          </div>
          <CardTitle className="text-3xl">404</CardTitle>
          <p className="text-gray-500 mt-2">Pagina non trovata</p>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-400 mb-6">
            La pagina che stai cercando non esiste o è stata spostata.
          </p>
          <Link to="/">
            <Button variant="default" size="lg" className="w-full">
              <Home className="w-4 h-4 mr-2" />
              Torna alla Dashboard
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
