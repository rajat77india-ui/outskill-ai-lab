import { cn } from '@/lib/utils'
import { CheckCircle2, XCircle, AlertCircle, Minus } from 'lucide-react'
import type { AuditTestRowPayload, BinaryResult } from '@/lib/api'

const RESULT_CONFIG: Record<BinaryResult, { icon: typeof CheckCircle2; color: string; label: string }> = {
  pass: { icon: CheckCircle2, color: 'text-emerald-400', label: 'Pass' },
  fail: { icon: XCircle, color: 'text-red-400', label: 'Fail' },
  partial: { icon: AlertCircle, color: 'text-amber-400', label: 'Partial' },
  not_applicable: { icon: Minus, color: 'text-muted-foreground', label: 'N/A' },
  unknown: { icon: AlertCircle, color: 'text-violet-400', label: '—' },
}

interface AuditSheetTableProps {
  tests: AuditTestRowPayload[]
}

export function AuditSheetTable({ tests }: AuditSheetTableProps) {
  if (tests.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-center">
        <p className="text-sm text-muted-foreground">No audit tests recorded yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-foreground">Audit Test Sheet</h3>
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs min-w-[700px]">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="text-left px-3 py-2 text-muted-foreground font-medium w-20">Test ID</th>
                <th className="text-left px-3 py-2 text-muted-foreground font-medium">Control Objective</th>
                <th className="text-left px-3 py-2 text-muted-foreground font-medium">PA Validation</th>
                <th className="text-left px-3 py-2 text-muted-foreground font-medium">Evidence</th>
                <th className="text-left px-3 py-2 text-muted-foreground font-medium w-16">Result</th>
              </tr>
            </thead>
            <tbody>
              {tests.map((test, i) => {
                const cfg = RESULT_CONFIG[test.result]
                const Icon = cfg.icon
                return (
                  <tr
                    key={test.test_id}
                    className={cn(
                      'border-b border-border/50 hover:bg-muted/20 transition-colors',
                      i % 2 === 0 ? '' : 'bg-muted/10',
                    )}
                  >
                    <td className="px-3 py-2.5 font-mono text-primary/80 whitespace-nowrap">
                      {test.test_id}
                    </td>
                    <td className="px-3 py-2.5 text-foreground/80 max-w-[200px]">
                      <p className="line-clamp-2">{test.control_objective}</p>
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground max-w-[200px]">
                      <p className="line-clamp-2">{test.palo_alto_validation}</p>
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground max-w-[180px]">
                      <p className="line-clamp-2">{test.evidence}</p>
                      {test.finding && (
                        <p className="text-red-400/80 mt-0.5 line-clamp-1">↳ {test.finding}</p>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={cn('inline-flex items-center gap-1 font-medium whitespace-nowrap', cfg.color)}>
                        <Icon className="h-3 w-3" />
                        {cfg.label}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
