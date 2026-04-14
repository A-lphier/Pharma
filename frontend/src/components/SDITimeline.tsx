import { Check, Clock, FileCheck, FileX, Loader2 } from 'lucide-react'
import { format } from 'date-fns'
import { it } from 'date-fns/locale'

export interface SDITimelineProps {
  invoiceId: number
  currentStatus: 'draft' | 'sent' | 'sdi_received' | 'delivered' | 'accepted' | 'rejected'
  timestamps: {
    sent?: string
    sdi_received?: string
    delivered?: string
    accepted?: string
    rejected?: string
    rejected_reason?: string
  }
}

type StatusStep = 'sent' | 'sdi_received' | 'delivered' | 'accepted'

const STEPS: { key: StatusStep; label: string; icon: typeof Check }[] = [
  { key: 'sent', label: 'Spedita', icon: Check },
  { key: 'sdi_received', label: 'SDI', icon: FileCheck },
  { key: 'delivered', label: 'Ricevuta', icon: Clock },
  { key: 'accepted', label: 'Accettata', icon: FileCheck },
]

const STEP_ORDER: StatusStep[] = ['sent', 'sdi_received', 'delivered', 'accepted']

function formatTimestamp(ts: string): string {
  try {
    return format(new Date(ts), "dd/MM/yyyy HH:mm", { locale: it })
  } catch {
    return ts
  }
}

function getStepState(
  stepKey: StatusStep,
  currentStatus: SDITimelineProps['currentStatus'],
  isRejected: boolean
): 'completed' | 'active' | 'pending' {
  if (isRejected) {
    const stepIdx = STEP_ORDER.indexOf(stepKey)
    // All steps before delivered (index 2) are completed in rejected flow
    if (stepIdx < 3) return 'completed'
    return 'pending'
  }

  const stepIdx = STEP_ORDER.indexOf(stepKey)
  const currentIdx = STEP_ORDER.indexOf(currentStatus as StatusStep)

  if (stepIdx < currentIdx) return 'completed'
  if (stepIdx === currentIdx) return 'active'
  return 'pending'
}

function StepCircle({ state, Icon }: { state: 'completed' | 'active' | 'pending'; Icon: typeof Check }) {
  if (state === 'completed') {
    return (
      <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center border-2 border-green-500">
        <Check className="w-5 h-5 text-white" />
      </div>
    )
  }
  if (state === 'active') {
    return (
      <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center border-2 border-blue-500">
        <Loader2 className="w-5 h-5 text-white animate-spin" />
      </div>
    )
  }
  return (
    <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center border-2 border-gray-300">
      <Icon className="w-5 h-5 text-gray-400" />
    </div>
  )
}

function ConnectorLine({ completed }: { completed: boolean }) {
  return (
    <div className={`flex-1 h-0.5 mx-1 ${completed ? 'bg-green-500' : 'bg-gray-200'}`} />
  )
}

function StepLabel({ label, state, timestamp }: { label: string; state: 'completed' | 'active' | 'pending'; timestamp?: string }) {
  const textColor = state === 'completed' ? 'text-green-600' : state === 'active' ? 'text-blue-600' : 'text-gray-400'
  return (
    <div className="flex flex-col items-center">
      <p className={`text-xs font-medium mt-1.5 text-center ${textColor}`}>{label}</p>
      {timestamp && <p className="text-[10px] text-gray-400 mt-0.5 text-center">{formatTimestamp(timestamp)}</p>}
    </div>
  )
}

export function SDITimeline({ currentStatus, timestamps }: SDITimelineProps) {
  const isRejected = currentStatus === 'rejected'
  const currentIdx = isRejected ? 3 : STEP_ORDER.indexOf(currentStatus as StatusStep)

  if (isRejected) {
    return (
      <div className="space-y-4">
        <div className="flex items-center">
          {STEPS.map((step, idx) => {
            const state = getStepState(step.key, currentStatus, true)
            const Icon = step.icon
            const ts = timestamps[step.key as keyof typeof timestamps]

            return (
              <div key={step.key} className="flex items-center flex-1">
                <div className="flex flex-col items-center">
                  <StepCircle state={state} Icon={Icon} />
                  <StepLabel label={step.label} state={state} timestamp={ts} />
                </div>
                {idx < STEPS.length - 1 && (
                  <ConnectorLine completed={idx < 2} />
                )}
              </div>
            )
          })}
          {/* Rejected final step */}
          <div className="flex flex-col items-center px-1">
            <div className="w-10 h-10 rounded-full border-2 border-red-500 bg-red-500 flex items-center justify-center">
              <FileX className="w-5 h-5 text-white" />
            </div>
            <p className="text-xs font-medium mt-1.5 text-red-600 text-center">Scartata</p>
            {timestamps.rejected && (
              <p className="text-[10px] text-gray-400 mt-0.5 text-center">
                {formatTimestamp(timestamps.rejected)}
              </p>
            )}
          </div>
        </div>

        {/* Rejection reason */}
        {timestamps.rejected_reason && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
            <p className="text-xs font-semibold text-red-700 mb-1">Motivo scartamento</p>
            <p className="text-sm text-red-800">{timestamps.rejected_reason}</p>
          </div>
        )}
      </div>
    )
  }

  // Normal flow: 4 steps horizontal
  return (
    <div className="flex items-center">
      {STEPS.map((step, idx) => {
        const state = getStepState(step.key, currentStatus, false)
        const Icon = step.icon
        const ts = timestamps[step.key as keyof typeof timestamps]

        return (
          <div key={step.key} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <StepCircle state={state} Icon={Icon} />
              <StepLabel label={step.label} state={state} timestamp={ts} />
            </div>
            {idx < STEPS.length - 1 && (
              <ConnectorLine completed={idx < currentIdx} />
            )}
          </div>
        )
      })}
    </div>
  )
}
