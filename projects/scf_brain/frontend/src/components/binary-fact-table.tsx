import { useState } from 'react'
import { ChevronDown, ChevronRight, ShieldCheck, ShieldX, ShieldAlert, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { BinaryFactPayload, BinaryResult, SeverityLevel } from '@/lib/api'

const RESULT_CONFIG: Record<BinaryResult, { icon: typeof ShieldCheck; color: string; bg: string; label: string }> = {
  pass: { icon: ShieldCheck, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', label: 'Pass' },
  fail: { icon: ShieldX, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20', label: 'Fail' },
  partial: { icon: ShieldAlert, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', label: 'Partial' },
  not_applicable: { icon: Minus, color: 'text-muted-foreground', bg: 'bg-muted/50 border-border', label: 'N/A' },
  unknown: { icon: ShieldAlert, color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20', label: 'Unknown' },
}

const SEVERITY_COLOR: Record<SeverityLevel, string> = {
  critical: 'text-red-500 bg-red-500/10',
  high: 'text-orange-400 bg-orange-500/10',
  medium: 'text-amber-400 bg-amber-500/10',
  low: 'text-emerald-400 bg-emerald-500/10',
  info: 'text-blue-400 bg-blue-500/10',
}

interface BinaryFactTableProps {
  facts: BinaryFactPayload[]
}

export function BinaryFactTable({ facts }: BinaryFactTableProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [filter, setFilter] = useState<BinaryResult | 'all'>('all')

  const filtered = filter === 'all' ? facts : facts.filter((f) => f.binary_result === filter)
  const counts = facts.reduce((acc, f) => {
    acc[f.binary_result] = (acc[f.binary_result] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Binary Fact Store</h3>
        <div className="flex gap-1.5">
          {(['all', 'fail', 'partial', 'pass', 'unknown'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setFilter(r)}
              className={cn(
                'px-2 py-0.5 rounded text-xs font-medium transition-colors',
                filter === r ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground',
              )}
            >
              {r === 'all' ? `All (${facts.length})` : `${r.charAt(0).toUpperCase() + r.slice(1)} (${counts[r] ?? 0})`}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              <th className="text-left px-3 py-2 text-muted-foreground font-medium w-8"></th>
              <th className="text-left px-3 py-2 text-muted-foreground font-medium">Check</th>
              <th className="text-left px-3 py-2 text-muted-foreground font-medium hidden sm:table-cell">SCF Control</th>
              <th className="text-left px-3 py-2 text-muted-foreground font-medium hidden md:table-cell">Severity</th>
              <th className="text-left px-3 py-2 text-muted-foreground font-medium">Result</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  No facts recorded yet
                </td>
              </tr>
            )}
            {filtered.map((fact) => {
              const cfg = RESULT_CONFIG[fact.binary_result]
              const Icon = cfg.icon
              const isExpanded = expandedRow === fact.check_id

              return (
                <>
                  <tr
                    key={fact.check_id}
                    onClick={() => setExpandedRow(isExpanded ? null : fact.check_id)}
                    className="border-b border-border/50 hover:bg-muted/30 cursor-pointer transition-colors"
                  >
                    <td className="px-3 py-2.5">
                      {isExpanded ? (
                        <ChevronDown className="h-3 w-3 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-3 w-3 text-muted-foreground" />
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <div>
                        <span className="font-mono text-primary/80">{fact.check_id}</span>
                        <span className="ml-1.5 text-foreground/80">{fact.check_name}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 hidden sm:table-cell text-muted-foreground">
                      {fact.mapped_scf_control}
                    </td>
                    <td className="px-3 py-2.5 hidden md:table-cell">
                      <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium capitalize', SEVERITY_COLOR[fact.severity])}>
                        {fact.severity}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium', cfg.bg, cfg.color)}>
                        <Icon className="h-3 w-3" />
                        {cfg.label}
                      </span>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${fact.check_id}-expanded`} className="bg-muted/20 border-b border-border/50">
                      <td colSpan={5} className="px-4 py-3">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                          <div>
                            <p className="text-muted-foreground mb-0.5">Evidence Source</p>
                            <p className="text-foreground/80">{fact.evidence_source}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-0.5">Evidence Value</p>
                            <p className="text-foreground/80">{fact.evidence_value}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-0.5">NIST 800-53</p>
                            <p className="text-foreground/80 font-mono">{fact.mapped_nist_control}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-0.5">CIS Controls</p>
                            <p className="text-foreground/80 font-mono">{fact.mapped_cis_check}</p>
                          </div>
                          {fact.binary_result !== 'pass' && (
                            <div className="sm:col-span-2">
                              <p className="text-muted-foreground mb-0.5">Remediation</p>
                              <p className="text-foreground/80">{fact.remediation}</p>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
