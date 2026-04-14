import { useState, useEffect } from 'react'
import { CheckCircle, ArrowRight, Loader2 } from 'lucide-react'
import { Button } from './ui/button'
import { Card } from './ui/card'
import { api } from '../lib/api'
import {
  OnboardingStatus,
  OnboardingQuestion,
  OnboardingConfigProposal,
} from '../lib/types'

interface OnboardingChatProps {
  onComplete?: () => void
}

export function OnboardingChat({ onComplete }: OnboardingChatProps) {
  const [_status, setStatus] = useState<OnboardingStatus | null>(null)
  const [question, setQuestion] = useState<OnboardingQuestion | null>(null)
  const [proposal, setProposal] = useState<OnboardingConfigProposal | null>(null)
  const [answers, setAnswers] = useState<Record<number, string | number>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sliderValue, setSliderValue] = useState(2000)
  const [showProposal, setShowProposal] = useState(false)

  useEffect(() => {
    fetchStatus()
  }, [])

  async function fetchStatus() {
    try {
      setLoading(true)
      const response = await api.get<OnboardingStatus>('/api/v1/onboarding/status')
      setStatus(response.data)

      if (response.data.status === 'completed') {
        onComplete?.()
        return
      }

      if (response.data.status === 'not_started') {
        await startOnboarding()
      } else if (response.data.status === 'in_progress') {
        await fetchQuestion()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore durante il caricamento')
    } finally {
      setLoading(false)
    }
  }

  async function startOnboarding() {
    try {
      setLoading(true)
      const response = await api.post<OnboardingQuestion>('/api/v1/onboarding/start')
      setQuestion(response.data)
      if (response.data.slider_default) {
        setSliderValue(response.data.slider_default)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore')
    } finally {
      setLoading(false)
    }
  }

  async function fetchQuestion() {
    try {
      setLoading(true)
      const response = await api.post<OnboardingQuestion>('/api/v1/onboarding/start')
      setQuestion(response.data)
      if (response.data.slider_default) {
        setSliderValue(response.data.slider_default)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore')
    } finally {
      setLoading(false)
    }
  }

  async function submitAnswer(answer: string | number) {
    if (!question) return

    try {
      setLoading(true)
      const newAnswers = { ...answers, [question.step]: answer }
      setAnswers(newAnswers)

      const response = await api.post<
        OnboardingQuestion | OnboardingConfigProposal
      >('/api/v1/onboarding/answer', {
        step: question.step,
        answer,
      })

      if ('reasoning' in response.data) {
        setProposal(response.data as OnboardingConfigProposal)
        setShowProposal(true)
      } else {
        setQuestion(response.data as OnboardingQuestion)
        if ((response.data as OnboardingQuestion).slider_default) {
          setSliderValue((response.data as OnboardingQuestion).slider_default!)
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore')
    } finally {
      setLoading(false)
    }
  }

  async function approveConfig(approved: boolean) {
    try {
      setLoading(true)
      await api.post('/api/v1/onboarding/approve', { approved })
      if (approved) {
        onComplete?.()
      } else {
        setShowProposal(false)
        setProposal(null)
        setAnswers({})
        await startOnboarding()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Errore')
    } finally {
      setLoading(false)
    }
  }

  if (loading && !question && !showProposal) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (showProposal && proposal) {
    return (
      <Card className="p-6">
        <div className="text-center mb-6">
          <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-3" />
          <h2 className="text-xl font-semibold text-gray-900">
            Configurazione completata!
          </h2>
          <p className="text-gray-600 mt-2">Ecco la configurazione che ho preparato per te:</p>
        </div>

        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <p className="text-sm text-gray-700 mb-4">{proposal.reasoning}</p>
          
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Stile:</span>
              <span className="ml-2 font-medium capitalize">{proposal.style}</span>
            </div>
            <div>
              <span className="text-gray-500">Soglia legale:</span>
              <span className="ml-2 font-medium">€{proposal.legal_threshold.toLocaleString('it-IT')}</span>
            </div>
            <div>
              <span className="text-gray-500">Primo sollecito:</span>
              <span className="ml-2 font-medium">{proposal.first_reminder_days} giorni</span>
            </div>
            <div>
              <span className="text-gray-500">Allarme:</span>
              <span className="ml-2 font-medium">{proposal.warning_threshold_days} giorni</span>
            </div>
            <div>
              <span className="text-gray-500">Escalation:</span>
              <span className="ml-2 font-medium">{proposal.escalation_days} giorni</span>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => approveConfig(false)}
            disabled={loading}
          >
            Modifica
          </Button>
          <Button
            className="flex-1"
            onClick={() => approveConfig(true)}
            disabled={loading}
          >
            <CheckCircle className="w-4 h-4 mr-2" />
            Approva
          </Button>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <Button onClick={fetchStatus}>Riprova</Button>
      </Card>
    )
  }

  if (!question) {
    return null
  }

  return (
    <Card className="p-6">
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm text-gray-500 mb-2">
          <span>Passo {question.step} di 4</span>
          <span>{Math.round((question.step / 4) * 100)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-primary-600 h-2 rounded-full transition-all"
            style={{ width: `${(question.step / 4) * 100}%` }}
          />
        </div>
      </div>

      <h3 className="text-lg font-medium text-gray-900 mb-4">
        {question.question}
      </h3>

      {question.input_type === 'single_choice' && question.options && (
        <div className="space-y-2">
          {question.options.map((option) => (
            <button
              key={option.value}
              onClick={() => submitAnswer(option.value)}
              className="w-full text-left p-3 rounded-lg border border-gray-200 hover:border-primary-500 hover:bg-primary-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-gray-700">{option.label}</span>
                <ArrowRight className="w-4 h-4 text-gray-400" />
              </div>
            </button>
          ))}
        </div>
      )}

      {question.input_type === 'slider' && (
        <div className="space-y-4">
          <div className="text-center">
            <span className="text-3xl font-bold text-primary-600">
              €{sliderValue.toLocaleString('it-IT')}
            </span>
          </div>
          <input
            type="range"
            min={question.slider_min || 0}
            max={question.slider_max || 10000}
            step={100}
            value={sliderValue}
            onChange={(e) => setSliderValue(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-sm text-gray-500">
            <span>€{question.slider_min?.toLocaleString('it-IT') || 0}</span>
            <span>€{question.slider_max?.toLocaleString('it-IT') || 10000}</span>
          </div>
          <Button
            className="w-full"
            onClick={() => submitAnswer(sliderValue)}
            disabled={loading}
          >
            Continua
          </Button>
        </div>
      )}
    </Card>
  )
}
