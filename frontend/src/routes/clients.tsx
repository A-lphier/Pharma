import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, Users, TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { ClientGridSkeleton, StatsSkeleton } from '../components/ui/skeleton'

import { ClientCard } from '../components/ClientCard'
import { api } from '../lib/api'
import { t } from '../lib/i18n'
import { Client, ClientListResponse } from '../lib/types'
import { useToast } from '../components/ui/toast'

const MOCK_STATS = {
  total: 8,
  with_overdue: 3,
  reliable: 5,
  new_this_month: 1,
}

export function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const { showToast } = useToast()

  useEffect(() => {
    fetchClients()
  }, [page, search])

  async function fetchClients() {
    try {
      setLoading(true)
      const params = new URLSearchParams({ page: String(page), page_size: '20' })
      if (search) params.append('search', search)
      const response = await api.get<ClientListResponse>(`/api/v1/clients?${params}`)
      setClients(response.data.items)
      setTotalPages(response.data.pages)
      setTotal(response.data.total)
    } catch (err) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? ((err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('clients.error_loading'))
        : t('clients.error_loading')
      setError(msg)
      showToast(msg, 'error')
    } finally {
      setLoading(false)
    }
  }

  const statsCards = [
    { label: 'Clienti totali', value: total, icon: Users, color: 'text-violet-600', bg: 'bg-violet-50' },
    { label: 'Con scadenze', value: MOCK_STATS.with_overdue, icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50' },
    { label: 'Affidabili', value: MOCK_STATS.reliable, icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Nuovi questo mese', value: MOCK_STATS.new_this_month, icon: TrendingUp, color: 'text-blue-600', bg: 'bg-blue-50' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clienti</h1>
          <p className="text-sm text-gray-500">{total} clienti totali</p>
        </div>
        <Button asChild className="bg-gray-900 hover:bg-gray-800">
          <Link to="/clients/new">
            <Plus className="w-4 h-4 mr-2" />Nuovo cliente
          </Link>
        </Button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {statsCards.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-500">{label}</span>
              <div className={`w-8 h-8 rounded-xl ${bg} flex items-center justify-center`}>
                <Icon className={`w-4 h-4 ${color}`} />
              </div>
            </div>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="relative min-h-12">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
        <Input
          type="search"
          placeholder="Cerca per nome, P.IVA o email..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          className="pl-11 h-12 text-base touch-manipulation"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="text-center py-12 bg-white rounded-2xl border border-gray-100 shadow-sm">
          <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-red-50 flex items-center justify-center">
            <AlertCircle className="w-7 h-7 text-red-400" />
          </div>
          <p className="font-medium text-gray-900">Errore di caricamento</p>
          <p className="text-sm text-gray-500 mt-1">{error}</p>
          <Button onClick={() => { setError(null); fetchClients() }} className="mt-4">
            Riprova
          </Button>
        </div>
      )}

      {/* Loading skeletons */}
      {loading && !clients.length && (
        <>
          <StatsSkeleton />
          <ClientGridSkeleton />
        </>
      )}

      {/* Empty */}
      {!loading && !error && clients.length === 0 && (
        <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 shadow-sm">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
            <Users className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            {search ? `Nessun risultato per "${search}"` : 'Nessun cliente'}
          </h3>
          <p className="text-sm text-gray-500 mb-6">
            {search ? 'Nessun cliente trovato per la ricerca effettuata' : 'Inizia aggiungendo il tuo primo cliente'}
          </p>
          <div className="flex gap-3 justify-center">
            {search ? (
              <Button variant="outline" size="sm" onClick={() => { setSearch(''); setPage(1) }}>
                Cancella ricerca
              </Button>
            ) : (
              <Button asChild className="bg-gray-900 hover:bg-gray-800">
                <Link to="/clients/new"><Plus className="w-4 h-4 mr-2" />Aggiungi cliente</Link>
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Grid */}
      {!loading && clients.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {clients.map((client) => (
              <ClientCard key={client.id} client={client} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3">
              <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                Precedente
              </Button>
              <span className="text-sm text-gray-600 px-2">Pagina {page} di {totalPages}</span>
              <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                Successivo
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
