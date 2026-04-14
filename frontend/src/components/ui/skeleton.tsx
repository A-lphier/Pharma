import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={clsx(
        'animate-pulse rounded-lg bg-gray-200',
        className
      )}
    />
  )
}

export function Spinner({ size = 'md', className = '' }: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }
  return (
    <div
      className={clsx(
        'border-2 border-primary-600 border-t-transparent rounded-full animate-spin',
        sizes[size],
        className
      )}
    />
  )
}

export function InvoiceListSkeleton() {
  return (
    <div className="divide-y divide-gray-100">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-5 py-4">
          <Skeleton className="w-4 h-4 rounded" />
          <div className="flex-1 min-w-0 flex items-center gap-4">
            <div className="flex-1 min-w-0 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-40" />
            </div>
            <div className="hidden sm:block space-y-2 text-right">
              <Skeleton className="h-4 w-20 ml-auto" />
              <Skeleton className="h-3 w-16 ml-auto" />
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Skeleton className="w-11 h-11 rounded-lg" />
            <Skeleton className="w-11 h-11 rounded-lg" />
            <Skeleton className="w-11 h-11 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-3">
            <Skeleton className="w-10 h-10 rounded-lg" />
            <div className="space-y-2">
              <Skeleton className="h-7 w-16" />
              <Skeleton className="h-3 w-12" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export function ClientGridSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <Skeleton className="w-10 h-10 rounded-full" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-20" />
              </div>
            </div>
            <Skeleton className="w-12 h-5 rounded-full" />
          </div>
          <div className="space-y-2 pt-2">
            <div className="flex items-center gap-2">
              <Skeleton className="w-4 h-4" />
              <Skeleton className="h-3 w-40" />
            </div>
            <div className="flex items-center gap-2">
              <Skeleton className="w-4 h-4" />
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export function DashboardInvoiceListSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-gray-100">
          <div className="flex-1 min-w-0 space-y-1">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-36" />
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right space-y-1">
              <Skeleton className="h-4 w-20 ml-auto" />
              <Skeleton className="h-3 w-16 ml-auto" />
            </div>
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  )
}
