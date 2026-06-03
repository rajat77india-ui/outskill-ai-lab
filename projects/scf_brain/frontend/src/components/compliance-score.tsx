import { cn } from '@/lib/utils'

interface ComplianceScoreProps {
  score: number
  className?: string
}

function getRiskLabel(score: number): string {
  if (score < 40) return 'Critical Risk'
  if (score < 60) return 'High Risk'
  if (score < 75) return 'Medium Risk'
  if (score < 90) return 'Low Risk'
  return 'Compliant'
}

function getScoreColor(score: number): string {
  if (score < 40) return 'text-red-500'
  if (score < 60) return 'text-orange-500'
  if (score < 75) return 'text-amber-400'
  if (score < 90) return 'text-emerald-400'
  return 'text-emerald-500'
}

function getStrokeColor(score: number): string {
  if (score < 40) return '#ef4444'
  if (score < 60) return '#f97316'
  if (score < 75) return '#f59e0b'
  if (score < 90) return '#10b981'
  return '#22c55e'
}

export function ComplianceScore({ score, className }: ComplianceScoreProps) {
  const radius = 36
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  return (
    <div className={cn('flex flex-col items-center gap-2', className)}>
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 96 96">
          <circle
            cx="48" cy="48" r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-muted"
          />
          <circle
            cx="48" cy="48" r={radius}
            fill="none"
            stroke={getStrokeColor(score)}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 1s ease-out' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn('text-xl font-bold tabular-nums', getScoreColor(score))}>
            {score.toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="text-center">
        <p className={cn('text-sm font-semibold', getScoreColor(score))}>
          {getRiskLabel(score)}
        </p>
        <p className="text-xs text-muted-foreground">Compliance Score</p>
      </div>
    </div>
  )
}

interface ScoreBadgeProps {
  score: number
}

export function ScoreBadge({ score }: ScoreBadgeProps) {
  const color =
    score < 40 ? 'bg-red-500/20 text-red-400 border-red-500/30' :
    score < 60 ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' :
    score < 75 ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
    'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'

  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border', color)}>
      {score.toFixed(0)}%
    </span>
  )
}
