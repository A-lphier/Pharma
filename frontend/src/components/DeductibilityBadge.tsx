import { useState } from 'react'
import { cn } from '../lib/utils'
import { analyzeDeductibility, DEDUCT_ICONS } from '../lib/deductibility'

interface DeductibilityBadgeProps {
  description: string
  inline?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function DeductibilityBadge({ description, inline = false, size = 'md', className }: DeductibilityBadgeProps) {
  const [open, setOpen] = useState(false)
  const result = analyzeDeductibility(description)

  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-xs',
    md: 'px-2 py-0.5 text-xs',
    lg: 'px-2.5 py-1 text-sm',
  }

  const color = result.status === 'full' ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
    : result.status === 'partial' ? 'bg-amber-50 text-amber-700 border-amber-200'
    : result.status === 'none' ? 'bg-red-50 text-red-700 border-red-200'
    : 'bg-gray-100 text-gray-600 border-gray-200'

  const icon = DEDUCT_ICONS[result.status]

  if (inline) {
    return (
      <span
        className={cn('inline-flex items-center gap-1 rounded-full border font-medium', color, sizeClasses[size], className)}
        title={result.message}
      >
        <span>{icon}</span>
        <span>{result.status === 'full' ? 'Ded.' : result.status === 'partial' ? `${result.irpefDeduzionePct}%` : null}</span>
      </span>
    )
  }

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          'inline-flex items-center gap-1 rounded-full border font-medium cursor-help transition-opacity hover:opacity-80',
          color, sizeClasses[size], className
        )}
        title={result.message}
      >
        <span>{icon}</span>
        <span>
          {result.status === 'full' ? 'Deducibile'
           : result.status === 'partial' ? `${result.irpefDeduzionePct}% ded`
           : result.status === 'none' ? 'No ded'
           : 'Verificare'}
        </span>
      </button>

      {open && (
        <div className="absolute z-50 left-0 top-full mt-1.5 w-72 bg-white border border-gray-200 rounded-2xl shadow-xl p-4 text-left">
          <div className="flex items-start gap-2.5">
            <span className="text-xl shrink-0 mt-0.5">{icon}</span>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-sm text-gray-900">{result.categoria}</p>
              <p className="text-xs text-gray-600 mt-1 leading-relaxed">{result.message}</p>
              {result.warning && (
                <p className="text-xs text-amber-700 mt-2 font-medium bg-amber-50 rounded-lg px-2.5 py-1.5 border border-amber-100">
                  ⚠️ {result.warning}
                </p>
              )}
              {result.norma && (
                <p className="text-xs text-gray-400 mt-2 font-mono">{result.norma}</p>
              )}
              <div className="flex gap-4 mt-3 pt-3 border-t border-gray-100">
                <div className="text-center">
                  <p className="text-xs text-gray-500 mb-0.5">IRPEF</p>
                  <p className="text-sm font-bold text-gray-800">{result.irpefDeduzionePct}%</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-500 mb-0.5">IVA detraibile</p>
                  <p className="text-sm font-bold text-gray-800">{result.ivaDetraibile ? `${result.ivaDetraibilePct}%` : 'No'}</p>
                </div>
              </div>
            </div>
          </div>
          <button onClick={(e) => { e.stopPropagation(); setOpen(false) }}
            className="absolute top-2.5 right-2.5 text-gray-400 hover:text-gray-600 text-xs w-5 h-5 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors">
            ✕
          </button>
        </div>
      )}
    </div>
  )
}
