import React from 'react'
import { Check, Clock, AlertTriangle, Gavel, ShieldAlert } from 'lucide-react'

interface EscalationTimelineProps {
  currentStage: string
  className?: string
}

const STAGE_CONFIG: Record<string, {
  label: string
  shortLabel: string
  color: string
  bgColor: string
  icon: React.ComponentType<{ className?: string }>
}> = {
  none: {
    label: 'Regolare',
    shortLabel: 'OK',
    color: '#22c55e',
    bgColor: '#dcfce7',
    icon: Clock,
  },
  sollecito_1: {
    label: '1° Sollecito',
    shortLabel: 'Sollecito 1',
    color: '#22c55e',
    bgColor: '#dcfce7',
    icon: AlertTriangle,
  },
  sollecito_2: {
    label: '2° Sollecito',
    shortLabel: 'Sollecito 2',
    color: '#eab308',
    bgColor: '#fef9c3',
    icon: AlertTriangle,
  },
  diffida: {
    label: 'Diffida',
    shortLabel: 'Diffida',
    color: '#f97316',
    bgColor: '#ffedd5',
    icon: ShieldAlert,
  },
  legal_action: {
    label: 'Azione Legale',
    shortLabel: 'Legale',
    color: '#ef4444',
    bgColor: '#fee2e2',
    icon: Gavel,
  },
  // Backend stage_1..stage_5 aliases (for compatibility)
  stage_1: {
    label: '1° Sollecito',
    shortLabel: 'Sollecito 1',
    color: '#22c55e',
    bgColor: '#dcfce7',
    icon: AlertTriangle,
  },
  stage_2: {
    label: '2° Sollecito',
    shortLabel: 'Sollecito 2',
    color: '#eab308',
    bgColor: '#fef9c3',
    icon: AlertTriangle,
  },
  stage_3: {
    label: 'Diffida',
    shortLabel: 'Diffida',
    color: '#f97316',
    bgColor: '#ffedd5',
    icon: ShieldAlert,
  },
  stage_4: {
    label: 'Azione Legale',
    shortLabel: 'Legale',
    color: '#ef4444',
    bgColor: '#fee2e2',
    icon: Gavel,
  },
  stage_5: {
    label: 'Recupero Legale',
    shortLabel: 'Legale',
    color: '#991b1b',
    bgColor: '#fecaca',
    icon: Gavel,
  },
}

const STAGE_ORDER = [
  'none',
  'sollecito_1',
  'sollecito_2',
  'diffida',
  'legal_action',
]

export function EscalationTimeline({ currentStage, className = '' }: EscalationTimelineProps) {
  const currentIdx = STAGE_ORDER.indexOf(currentStage)
  const displayIdx = currentIdx === -1 ? 0 : currentIdx

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {STAGE_ORDER.map((stage, idx) => {
        const config = STAGE_CONFIG[stage] || STAGE_CONFIG.none
        const isPast = idx < displayIdx
        const isCurrent = idx === displayIdx
        const Icon = config.icon

        return (
          <React.Fragment key={stage}>
            <div className="flex flex-col items-center">
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all"
                style={{
                  backgroundColor: isPast || isCurrent ? config.bgColor : '#f3f4f6',
                  borderColor: isCurrent ? config.color : isPast ? config.color : '#d1d5db',
                  color: isPast || isCurrent ? config.color : '#6b7280',
                }}
                title={config.label}
              >
                {isPast ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
              </div>
              <span
                className="text-[9px] mt-0.5 text-center leading-tight hidden sm:block max-w-[50px]"
                style={{
                  color: isCurrent ? config.color : '#6b7280',
                  fontWeight: isCurrent ? 600 : 400,
                }}
              >
                {config.shortLabel}
              </span>
            </div>
            {idx < STAGE_ORDER.length - 1 && (
              <div
                className="flex-1 h-0.5 mb-3 min-w-[12px]"
                style={{
                  backgroundColor: idx < displayIdx ? config.color : '#e5e7eb',
                }}
              />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

interface EscalationBadgeProps {
  stage: string
  label?: string
  color?: string
  size?: 'sm' | 'md'
}

export function EscalationBadge({ stage, label, color, size = 'md' }: EscalationBadgeProps) {
  const config = STAGE_CONFIG[stage] || { label: stage, color: '#6b7280', bgColor: '#f3f4f6' }
  const displayLabel = label || config.label
  const displayColor = color || config.color
  const displayBg = config.bgColor

  const padding = size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-xs'
  const dotSize = size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${padding}`}
      style={{
        backgroundColor: displayBg,
        color: displayColor,
      }}
    >
      <span
        className={`${dotSize} rounded-full`}
        style={{ backgroundColor: displayColor }}
      />
      {displayLabel}
    </span>
  )
}
