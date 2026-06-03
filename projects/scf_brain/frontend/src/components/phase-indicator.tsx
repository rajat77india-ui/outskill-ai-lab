import { cn } from '@/lib/utils'
import type { Phase } from '@/stores/scf-store'

const TOP_DOWN_PHASES: { key: Phase; label: string }[] = [
  { key: 'analyzing', label: 'Analyzing Controls' },
  { key: 'mapping', label: 'Building Checks' },
  { key: 'generating', label: 'Generating Audit Sheet' },
  { key: 'completed', label: 'Complete' },
]

const BOTTOM_UP_PHASES: { key: Phase; label: string }[] = [
  { key: 'ingesting', label: 'Ingesting Evidence' },
  { key: 'mapping', label: 'Mapping Controls' },
  { key: 'generating', label: 'Generating Report' },
  { key: 'completed', label: 'Complete' },
]

const PHASE_ORDER_TOP_DOWN = ['analyzing', 'mapping', 'generating', 'completed']
const PHASE_ORDER_BOTTOM_UP = ['ingesting', 'mapping', 'generating', 'completed']

interface PhaseIndicatorProps {
  currentPhase: Phase
  mode: 'top_down' | 'bottom_up'
}

export function PhaseIndicator({ currentPhase, mode }: PhaseIndicatorProps) {
  const phases = mode === 'top_down' ? TOP_DOWN_PHASES : BOTTOM_UP_PHASES
  const order = mode === 'top_down' ? PHASE_ORDER_TOP_DOWN : PHASE_ORDER_BOTTOM_UP
  const currentIdx = order.indexOf(currentPhase)

  return (
    <div className="flex items-center gap-1 overflow-x-auto">
      {phases.map((phase, i) => {
        const phaseIdx = order.indexOf(phase.key)
        const isDone = phaseIdx < currentIdx
        const isActive = phase.key === currentPhase
        return (
          <div key={phase.key} className="flex items-center gap-1 shrink-0">
            <div className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-500',
              isDone && 'bg-primary/20 text-primary',
              isActive && 'bg-primary text-primary-foreground',
              !isDone && !isActive && 'bg-muted text-muted-foreground',
            )}>
              <div className={cn(
                'w-1.5 h-1.5 rounded-full',
                isDone && 'bg-primary',
                isActive && 'bg-primary-foreground animate-pulse',
                !isDone && !isActive && 'bg-muted-foreground/30',
              )} />
              {phase.label}
            </div>
            {i < phases.length - 1 && (
              <div className={cn(
                'w-4 h-px transition-colors duration-500',
                phaseIdx < currentIdx ? 'bg-primary/50' : 'bg-border',
              )} />
            )}
          </div>
        )
      })}
    </div>
  )
}
