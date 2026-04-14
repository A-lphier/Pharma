import { Link } from 'react-router-dom'
import { Building2, Mail, Phone, MapPin } from 'lucide-react'
import { TrustScoreBadge } from './TrustScoreBadge'
import { Card } from './ui/card'
import { Client } from '../lib/types'

interface ClientCardProps {
  client: Client
}

export function ClientCard({ client }: ClientCardProps) {
  return (
    <Link to={`/clients/${client.id}`}>
      <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
              <Building2 className="w-5 h-5 text-primary-600" />
            </div>
            <div className="min-w-0">
              <h3 className="font-medium text-gray-900 truncate">{client.name}</h3>
              {client.vat && (
                <p className="text-sm text-gray-500">P.IVA: {client.vat}</p>
              )}
            </div>
          </div>
          <TrustScoreBadge score={client.trust_score} size="sm" />
        </div>

        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-500">
          {client.email && (
            <div className="flex items-center gap-2 truncate">
              <Mail className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">{client.email}</span>
            </div>
          )}
          {client.phone && (
            <div className="flex items-center gap-2 truncate">
              <Phone className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">{client.phone}</span>
            </div>
          )}
          {client.address && (
            <div className="flex items-center gap-2 truncate col-span-2">
              <MapPin className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">{client.address}</span>
            </div>
          )}
        </div>

        {client.payment_pattern && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">
              Pattern: <span className="font-medium capitalize">{client.payment_pattern.replace('_', ' ')}</span>
            </p>
          </div>
        )}
      </Card>
    </Link>
  )
}
