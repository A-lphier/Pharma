import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OnboardingChat } from '../components/OnboardingChat'
import { Card } from '../components/ui/card'
import { api } from '../lib/api'
import { OnboardingStatus } from '../lib/types'

export function OnboardingPage() {
  const navigate = useNavigate()
  const [_status, setStatus] = useState<OnboardingStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkStatus()
  }, [])

  async function checkStatus() {
    try {
      const response = await api.get<OnboardingStatus>('/api/v1/onboarding/status')
      setStatus(response.data)
      
      if (response.data.status === 'completed') {
        navigate('/')
      }
    } catch (err) {
      // Error checking onboarding status silently ignored
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-lg mx-auto">
        <Card className="p-6 text-center">
          <p className="text-gray-500">Caricamento...</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Benvenuto in FatturaMVP
        </h1>
        <p className="text-gray-600">
          Configura il sistema di sollecito intelligente in pochi semplici passi.
          Ti faremo qualche domanda per capire come gestisci i pagamenti.
        </p>
      </div>

      <OnboardingChat onComplete={() => navigate('/')} />
    </div>
  )
}
