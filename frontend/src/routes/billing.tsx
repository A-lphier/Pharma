import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Button } from '../components/ui'
import { useAuthStore } from '../lib/auth'
import { TIERS, Tier } from '../lib/constants'
import {
  CreditCard,
  Check,
  ArrowLeft,
  ExternalLink,
  Loader2,
  Shield,
  Zap,
  X,
} from 'lucide-react'

// ─── Tiers array (costruito da TIERS constants) ─────────────────────────────

const tiersList = [
  TIERS.free,
  TIERS.starter,
  TIERS.professional,
  TIERS.studio,
]

// ─── Current plan badge ──────────────────────────────────────────────────────

function CurrentPlanBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 bg-green-100 text-green-700 text-xs font-semibold px-3 py-1 rounded-full">
      <Check className="h-3.5 w-3.5" />
      Piano attuale
    </span>
  )
}

// ─── Tier card ──────────────────────────────────────────────────────────────

function TierCard({
  tier,
  currentTierId,
  onSelect,
  loading,
}: {
  tier: Tier
  currentTierId: string
  onSelect: (tierId: string) => void
  loading: string | null
}) {
  const isCurrent = currentTierId === tier.id
  const isFree = tier.id === 'free'

  return (
    <div
      className={`relative rounded-2xl p-6 flex flex-col ${
        tier.highlighted
          ? 'bg-primary-600 text-white shadow-xl'
          : isCurrent
          ? 'bg-green-50 border-2 border-green-300'
          : 'bg-white border border-gray-200 shadow-sm'
      }`}
    >
      {tier.highlighted && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-yellow-400 text-yellow-900 text-xs font-bold px-3 py-1 rounded-full">
          PIU&apos; POPOLARE
        </div>
      )}

      <div className="mb-1">
        <h3 className={`text-lg font-bold ${tier.highlighted ? 'text-white' : 'text-gray-900'}`}>
          {tier.name}
        </h3>
        <p className={`text-sm ${tier.highlighted ? 'text-blue-200' : 'text-gray-500'}`}>
          {tier.price === 0 ? 'Gratis' : `€${tier.price}/mese`}
        </p>
      </div>

      <ul className="flex flex-col gap-2 mb-6 flex-1 mt-4">
        {tier.features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm">
            <Check
              className={`h-4 w-4 flex-shrink-0 mt-0.5 ${
                tier.highlighted ? 'text-blue-200' : 'text-green-500'
              }`}
            />
            <span className={tier.highlighted ? 'text-blue-100' : 'text-gray-600'}>{f}</span>
          </li>
        ))}
      </ul>

      {isCurrent ? (
        <div className="mt-auto">
          <CurrentPlanBadge />
        </div>
      ) : isFree ? (
        <div className="mt-auto text-sm text-gray-400">Piano gratuito</div>
      ) : (
        <Button
          onClick={() => onSelect(tier.id)}
          disabled={!!loading}
          variant={tier.highlighted ? 'secondary' : 'outline'}
          className={`mt-auto w-full ${
            tier.highlighted
              ? 'bg-white text-primary-700 hover:bg-blue-50'
              : 'border-primary-600 text-primary-600 hover:bg-blue-50'
          }`}
        >
          {loading === tier.id ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            'Upgrade'
          )}
        </Button>
      )}
    </div>
  )
}

// ─── Confirm cancel modal ───────────────────────────────────────────────────

function CancelModal({
  onConfirm,
  onCancel,
  loading,
}: {
  onConfirm: () => void
  onCancel: () => void
  loading: boolean
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="bg-red-100 p-2 rounded-full">
            <X className="h-5 w-5 text-red-600" />
          </div>
          <h3 className="text-lg font-bold text-gray-900">Annulla sottoscrizione</h3>
        </div>
        <p className="text-sm text-gray-600 mb-6">
          Sei sicuro di voler annullare la tua sottoscrizione? Riceverai un&apos;email di
          conferma e il tuo piano <strong>sarà</strong> degradato a <strong>Free</strong> alla fine del
          periodo di fatturazione corrente.
        </p>
        <div className="flex gap-3 justify-end">
          <Button variant="outline" onClick={onCancel} disabled={loading}>
            Torna indietro
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Annulla ora'}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Main Billing Page ──────────────────────────────────────────────────────

export function BillingPage() {
  const [searchParams] = useSearchParams()
  const { user } = useAuthStore()
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showCancelModal, setShowCancelModal] = useState(false)

  // Tier corrente (dal backend o da user meta)
  const currentTierId = user?.subscription_tier || 'starter'

  // Fetch stato reale dal backend
  const [billingStatus, setBillingStatus] = useState<{
    tier: string
    status: string
    next_billing_date?: string | null
    price: number
  } | null>(null)

  // Carica stato billing all mount
  useEffect(() => {
    api.get('/api/v1/billing/status')
      .then(res => setBillingStatus(res.data))
      .catch(() => {})
  }, [])

  const currentTier = TIERS[currentTierId as keyof typeof TIERS] ?? TIERS.free
  const isFree = currentTierId === 'free'
  const isPaidTier = !isFree

  // ─── Upgrade ──────────────────────────────────────────────────────────────

  const handleUpgrade = async (tierId: string) => {
    setLoading(tierId)
    setError(null)
    setSuccess(null)

    try {
      const res = await api.post('/api/v1/billing/checkout', {
        tier: tierId,
        success_url: `${window.location.origin}/billing?success=true`,
        cancel_url: `${window.location.origin}/billing?canceled=true`,
      })

      const { checkout_url } = res.data
      if (checkout_url && !checkout_url.includes('mock')) {
        window.location.href = checkout_url
      } else {
        // Demo mode
        setSuccess(`Hai selezionato il piano ${tierId}. In produzione verrai reindirizzato a Stripe.`)
      }
    } catch (err: unknown) {
      const errMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || 'Si e verificato un errore. Riprova.'
      setError(errMsg)
    } finally {
      setLoading(null)
    }
  }

  // ─── Customer portal ──────────────────────────────────────────────────────

  const handleManageSubscription = async () => {
    setLoading('portal')
    setError(null)
    try {
      const res = await api.post('/api/v1/billing/portal', {
        return_url: `${window.location.origin}/billing`,
      })
      const { portal_url } = res.data
      if (portal_url && !portal_url.includes('mock')) {
        window.location.href = portal_url
      } else {
        setSuccess('Portal: in produzione verrai reindirizzato al portale Stripe.')
      }
    } catch (err: unknown) {
      const errMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || 'Si e verificato un errore.'
      setError(errMsg)
    } finally {
      setLoading(null)
    }
  }

  // ─── Cancel subscription ───────────────────────────────────────────────────

  const handleCancelConfirm = async () => {
    setLoading('cancel')
    setError(null)
    try {
      const res = await api.post('/api/v1/billing/cancel')
      if (res.data.success) {
        setSuccess('Sottoscrizione annullata. Verrai degradato a Free alla fine del periodo.')
        setShowCancelModal(false)
      } else {
        setError(res.data.message || 'Impossibile annullare.')
      }
    } catch (err: unknown) {
      const errMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || 'Si e verificato un errore.'
      setError(errMsg)
    } finally {
      setLoading(null)
    }
  }

  const successMsg = searchParams.get('success')
  const canceledMsg = searchParams.get('canceled')

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      {showCancelModal && (
        <CancelModal
          onConfirm={handleCancelConfirm}
          onCancel={() => setShowCancelModal(false)}
          loading={loading === 'cancel'}
        />
      )}

      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6"
          >
            <ArrowLeft className="h-4 w-4" />
            Torna alla dashboard
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Piano e Fatturazione</h1>
          <p className="text-gray-600 mt-1">
            Gestisci il tuo piano e le impostazioni di fatturazione.
          </p>
        </div>

        {/* Alerts */}
        {successMsg && (
          <div className="mb-6 bg-green-50 border border-green-200 text-green-800 rounded-xl p-4 text-sm flex items-center gap-2">
            <Check className="h-4 w-4 text-green-600" />
            Pagamento riuscito! Il tuo piano e stato aggiornato.
          </div>
        )}
        {canceledMsg && (
          <div className="mb-6 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-xl p-4 text-sm">
            Pagamento annullato. Nessun addebito e stato effettuato.
          </div>
        )}
        {success && (
          <div className="mb-6 bg-green-50 border border-green-200 text-green-800 rounded-xl p-4 text-sm flex items-center gap-2">
            <Check className="h-4 w-4 text-green-600" />
            {success}
          </div>
        )}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
            {error}
          </div>
        )}

        {/* Current plan summary */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-lg font-semibold text-gray-900">
                  Piano {currentTier.name}
                </h2>
                {isFree ? (
                  <span className="inline-flex items-center gap-1 bg-gray-100 text-gray-600 text-xs font-semibold px-3 py-1 rounded-full">
                    Free
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 bg-primary-100 text-primary-700 text-xs font-semibold px-3 py-1 rounded-full">
                    <Check className="h-3.5 w-3.5" />
                    Attivo
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-500">
                {currentTier.price === 0
                  ? 'Piano gratuito'
                  : `€${currentTier.price}/mese`}
                {billingStatus?.next_billing_date && (
                  <> &middot; Prossima fattura: {billingStatus.next_billing_date}</>
                )}
              </p>

              {/* Feature summary */}
              <div className="flex flex-wrap gap-4 mt-3 text-xs text-gray-500">
                <span>
                  <strong className="text-gray-700">
                    {currentTier.limits.maxInvoices === -1
                      ? 'Illimitate'
                      : currentTier.limits.maxInvoices}
                  </strong>{' '}
                  fatture
                </span>
                <span>
                  <strong className="text-gray-700">{currentTier.limits.maxUsers}</strong>{' '}
                  utenti
                </span>
                <span>
                  <strong className="text-gray-700">
                    {currentTier.limits.aiReminders === -1
                      ? 'Illimitati'
                      : currentTier.limits.aiReminders}
                  </strong>{' '}
                  solleciti AI
                </span>
                <span>
                  SDI{' '}
                  <strong className="text-gray-700">
                    {currentTier.limits.sdi ? 'Attivo' : 'No'}
                  </strong>
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Shield className="h-4 w-4" />
                Pagamenti sicuri con Stripe
              </div>
              {isPaidTier && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleManageSubscription}
                  disabled={loading === 'portal'}
                >
                  {loading === 'portal' ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      Gestisci <ExternalLink className="h-3.5 w-3.5 ml-1" />
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>

          {/* Cancel subscription */}
          {isPaidTier && (
            <div className="mt-4 pt-4 border-t border-gray-100 flex justify-end">
              <button
                className="text-xs text-red-500 hover:text-red-700 hover:underline"
                onClick={() => setShowCancelModal(true)}
                disabled={!!loading}
              >
                Annulla sottoscrizione
              </button>
            </div>
          )}
        </div>

        {/* Upgrade tiers */}
        <div className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            {isFree ? 'Scegli il tuo piano' : 'Cambia piano'}
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {tiersList
              .filter(t => t.id !== 'free')
              .map((tier) => (
                <TierCard
                  key={tier.id}
                  tier={tier}
                  currentTierId={currentTierId}
                  onSelect={handleUpgrade}
                  loading={loading}
                />
              ))}
          </div>
        </div>

        {/* Stripe info */}
        <div className="bg-gray-100 rounded-xl p-4 flex items-start gap-3">
          <CreditCard className="h-5 w-5 text-gray-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-gray-700">
              Pagamenti gestiti tramite Stripe
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              Accedi al portale Stripe per visualizzare ricevute, aggiornare la carta
              di credito o cancellare la sottoscrizione in qualsiasi momento.
            </p>
          </div>
        </div>

        {/* Feature comparison note */}
        <div className="mt-8 border-t border-gray-200 pt-8">
          <h3 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary-600" />
            Tutti i piani includono
          </h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {[
              'Prova gratuita 30 giorni',
              'Setup in 5 minuti',
              'Supporto via email',
              'Dashboard analytics',
              'Integrazione SDI (Professional+)',
              'Nessuna carta di credito richiesta per la prova',
              'Cancel anytime',
              'Dati crittografati e GDPR compliant',
            ].map((f) => (
              <div key={f} className="flex items-center gap-2 text-sm text-gray-600">
                <Check className="h-4 w-4 text-green-500 flex-shrink-0" />
                {f}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
