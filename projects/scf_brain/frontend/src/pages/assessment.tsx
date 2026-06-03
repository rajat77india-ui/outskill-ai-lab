import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Shield, AlertTriangle } from 'lucide-react'
import { useSSE } from '@/hooks/use-sse'
import { useSCFStore } from '@/stores/scf-store'
import { PhaseIndicator } from '@/components/phase-indicator'
import { AgentTimeline } from '@/components/agent-timeline'
import { BinaryFactTable } from '@/components/binary-fact-table'
import { AuditSheetTable } from '@/components/audit-sheet-table'
import { ComplianceScore } from '@/components/compliance-score'
import { ControlReport } from '@/components/control-report'
import { cn } from '@/lib/utils'

export function AssessmentPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const {
    mode,
    technology,
    assetId,
    scfControlIds,
    status,
    phase,
    binaryFacts,
    auditTests,
    complianceScore,
    gaps,
    remediationPlan,
    report,
    events,
    reset,
  } = useSCFStore()

  useSSE(runId)

  const isStreaming = status === 'running' || status === 'pending'
  const isCompleted = status === 'completed'
  const hasFacts = binaryFacts.length > 0
  const hasTests = auditTests.length > 0

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-background/80 border-b border-border">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => { reset(); navigate('/') }}
              className="p-1.5 rounded-lg hover:bg-muted transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold tracking-tight">ControlBridge AI</span>
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className={cn(
              'px-2 py-0.5 rounded-full border font-medium',
              mode === 'top_down'
                ? 'border-blue-500/30 bg-blue-500/10 text-blue-400'
                : 'border-violet-500/30 bg-violet-500/10 text-violet-400',
            )}>
              {mode === 'top_down' ? 'Control → Technology' : 'Technology → Control'}
            </span>
            <span>{technology}</span>
            <span className="font-mono">{assetId}</span>
          </div>
        </div>

        <div className="px-6 pb-3">
          <PhaseIndicator currentPhase={phase} mode={mode} />
        </div>
      </header>

      <main className="flex-1 flex gap-6 px-6 py-6 max-w-[1400px] mx-auto w-full">
        {/* Left sidebar — agent timeline */}
        <div className="hidden lg:block w-72 shrink-0">
          <div className="sticky top-32 space-y-4">
            <AgentTimeline events={events} />

            {isCompleted && (
              <ComplianceScore score={complianceScore} />
            )}

            {mode === 'top_down' && scfControlIds.length > 0 && (
              <div className="border border-border rounded-lg bg-card p-4">
                <p className="text-xs text-muted-foreground mb-2">Controls Assessed</p>
                <div className="flex flex-wrap gap-1.5">
                  {scfControlIds.map((id) => (
                    <span key={id} className="text-xs font-mono bg-muted px-2 py-0.5 rounded text-foreground/70">
                      {id}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* Title */}
          <div>
            <h1 className="text-lg font-semibold text-foreground mb-1">
              {mode === 'top_down'
                ? `Control Assessment: ${scfControlIds.join(', ')}`
                : `Firewall Assessment: ${assetId}`}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isStreaming
                ? 'Agents are running the assessment pipeline...'
                : isCompleted
                ? `Assessment complete — ${complianceScore.toFixed(1)}% compliance score`
                : 'Starting assessment...'}
            </p>
          </div>

          {/* Streaming state */}
          {isStreaming && !hasFacts && !report && (
            <div className="flex items-center gap-3 py-12 text-muted-foreground justify-center">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-2 h-2 rounded-full bg-primary/60"
                    style={{
                      animation: 'pulse-dot 1.4s ease-in-out infinite',
                      animationDelay: `${i * 0.2}s`,
                    }}
                  />
                ))}
              </div>
              <span className="text-sm">
                {phase === 'analyzing' && 'Analyzing SCF controls and crosswalk mappings...'}
                {phase === 'ingesting' && 'Ingesting and normalizing firewall configuration...'}
                {phase === 'mapping' && 'Mapping findings to compliance controls...'}
                {phase === 'generating' && 'Generating audit sheet and remediation plan...'}
              </span>
            </div>
          )}

          {/* Error state */}
          {status === 'failed' && (
            <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3">
              <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
              <p className="text-sm text-red-400">
                Assessment failed. Check that OPENROUTER_API_KEY is set and try again.
              </p>
            </div>
          )}

          {/* Binary Facts Table */}
          {hasFacts && (
            <BinaryFactTable facts={binaryFacts} />
          )}

          {/* Audit Test Sheet */}
          {hasTests && (
            <AuditSheetTable tests={auditTests} />
          )}

          {/* Gaps */}
          {isCompleted && gaps.length > 0 && (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
              <h3 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Compliance Gaps ({gaps.length})
              </h3>
              <ul className="space-y-1">
                {gaps.map((gap, i) => (
                  <li key={i} className="text-xs text-foreground/70 flex gap-2">
                    <span className="text-amber-400 shrink-0">•</span>
                    {gap}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Report */}
          {(report || (isStreaming && phase === 'generating')) && (
            <ControlReport
              content={report}
              isStreaming={isStreaming && !report}
            />
          )}

          {/* Remediation Plan */}
          {isCompleted && remediationPlan && !report && (
            <div className="rounded-lg border border-border bg-card p-4">
              <h3 className="text-sm font-semibold mb-3">Remediation Plan</h3>
              <pre className="text-xs text-foreground/70 whitespace-pre-wrap font-mono leading-relaxed">
                {remediationPlan}
              </pre>
            </div>
          )}
        </div>
      </main>

      {/* Mobile: agent timeline drawer */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-background/90 backdrop-blur-xl border-t border-border p-4">
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground font-medium">
            Agent Activity ({events.length})
            {isCompleted && (
              <span className="ml-2 text-primary">{complianceScore.toFixed(0)}% score</span>
            )}
          </summary>
          <div className="mt-2 max-h-48 overflow-y-auto">
            <AgentTimeline events={events} />
          </div>
        </details>
      </div>
    </div>
  )
}
