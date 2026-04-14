import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../lib/auth'
import { Button, Input } from '../components/ui'
import { t, getLocale, setLocale, Locale } from '../lib/i18n'
import { Globe, ArrowRight, Lock, Mail, AlertCircle } from 'lucide-react'

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuthStore()
  const navigate = useNavigate()
  const currentLocale = getLocale()

  function toggleLocale(locale: Locale) {
    setLocale(locale)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || t('login.error'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left panel — dark hero */}
      <div className="hidden lg:flex lg:w-1/2 bg-gray-950 flex-col justify-between p-12 relative overflow-hidden">
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.5) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />
        {/* Glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl" />

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
            <span className="text-white font-bold text-lg">F</span>
          </div>
          <span className="text-white font-bold text-xl tracking-tight">FatturaMVP</span>
        </div>

        {/* Hero text */}
        <div className="relative">
          <div className="absolute -left-4 top-0 w-1 h-12 bg-gradient-to-b from-violet-500 to-transparent rounded-full" />
          <h1 className="text-4xl font-bold text-white leading-tight mb-4">
            La gestione fatture<br />
            <span className="text-violet-400">che funziona davvero</span>
          </h1>
          <p className="text-gray-400 text-base leading-relaxed max-w-sm">
            Scadenziario automatico, solleciti intelligenti, portale clienti.
            Tutto quello che serve per incassare di più.
          </p>
        </div>

        {/* Features */}
        <div className="relative space-y-3">
          {[
            ['SDI in tempo reale', 'Ricevi fatture automaticamente'],
            ['Sollecito automatico', 'Non perdere più un pagamento'],
            ['Portale pagamenti', 'I tuoi clienti pagano in un click'],
          ].map(([title, desc]) => (
            <div key={title} className="flex items-start gap-3">
              <div className="w-5 h-5 rounded-md bg-violet-500/20 flex items-center justify-center mt-0.5 shrink-0">
                <div className="w-1.5 h-1.5 rounded-full bg-violet-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">{title}</p>
                <p className="text-xs text-gray-500">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6 bg-gray-50">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-2 mb-8">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
              <span className="text-white font-bold">F</span>
            </div>
            <span className="font-bold text-gray-900 text-lg tracking-tight">FatturaMVP</span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900">{t('login.title')}</h2>
            <p className="text-sm text-gray-500 mt-1">{t('login.subtitle')}</p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
              {error}
            </div>
          )}

          {/* Demo button */}
          <button
            onClick={() => {
              setUsername('admin')
              setPassword('admin123')
              handleSubmit({ preventDefault: () => {} } as any)
            }}
            className="w-full mb-4 h-10 py-3 bg-gray-900 hover:bg-gray-800 text-white rounded-xl font-semibold text-sm transition-colors flex items-center justify-center gap-2"
          >
            🚀 Entra in demo
            <ArrowRight className="w-4 h-4" />
          </button>

          <div className="relative mb-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-3 text-xs text-gray-500 bg-gray-50">oppure accedi</span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">{t('login.email')}</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  required
                  autoComplete="username"
                  className="pl-10"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">{t('login.password')}</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                  className="pl-10"
                />
              </div>
            </div>

            <Button type="submit" className="w-full bg-violet-600 hover:bg-violet-700" disabled={isLoading}>
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {t('common.loading')}
                </span>
              ) : t('login.signIn')}
            </Button>
          </form>

          {/* Language switcher */}
          <div className="flex items-center justify-center gap-1 mt-8">
            <button onClick={() => toggleLocale('it')} className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-colors ${currentLocale === 'it' ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-700'}`}>IT</button>
            <button onClick={() => toggleLocale('en')} className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-colors ${currentLocale === 'en' ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-700'}`}>EN</button>
            <Globe className="w-3.5 h-3.5 text-gray-500 ml-1" />
          </div>
        </div>
      </div>
    </div>
  )
}
