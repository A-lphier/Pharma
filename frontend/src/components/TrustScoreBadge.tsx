import { cn } from '../lib/utils'

interface TrustScoreBadgeProps {
  score: number
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const TRUST_LEVELS = [
  { min: 80, max: 100, label: 'Eccellente', dot: 'bg-emerald-500', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  { min: 60, max: 79, label: 'Affidabile', dot: 'bg-blue-500', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  { min: 40, max: 59, label: 'Da verificare', dot: 'bg-amber-500', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  { min: 20, max: 39, label: 'Problemi', dot: 'bg-orange-500', color: 'bg-orange-50 text-orange-700 border-orange-200' },
  { min: 0, max: 19, label: 'Inaffidabile', dot: 'bg-red-500', color: 'bg-red-50 text-red-700 border-red-200' },
]

function getTrustLevel(score: number) {
  return TRUST_LEVELS.find((level) => score >= level.min && score <= level.max) || TRUST_LEVELS[4]
}

export function TrustScoreBadge({ score, showLabel = true, size = 'md', className }: TrustScoreBadgeProps) {
  const level = getTrustLevel(score)

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  }

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-semibold border',
        level.color,
        sizeClasses[size],
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', level.dot)} />
      <span>{score}</span>
      {showLabel && <span className="hidden sm:inline text-xs opacity-80">- {level.label}</span>}
    </div>
  )
}




