import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, ArrowRight, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSCFStore } from '@/stores/scf-store'
import { startAssessment, SCF_DOMAINS, SAMPLE_CONFIG, type AssessmentMode } from '@/lib/api'

const QUICK_CONTROLS = ['NET-02', 'IAC-07', 'LOG-01', 'CFG-03', 'CRY-01']

export function HomePage() {
  const navigate = useNavigate()
  const { reset, setRunId, setMode, setScfControlIds, setTechnology, setAssetId } = useSCFStore()

  const [mode, setLocalMode] = useState<AssessmentMode>('top_down')
  const [selectedControls, setSelectedControls] = useState<string[]>([])
  const [configData, setConfigData] = useState('')
  const [assetId, setLocalAssetId] = useState('PA-FW-001')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expandedDomain, setExpandedDomain] = useState<string | null>('Network Security')

  const toggleControl = (id: string) => {
    setSelectedControls((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    )
  }

  const handleRun = async () => {
    setError('')
    if (mode === 'top_down' && selectedControls.length === 0) {
      setError('Select at least one SCF control to assess')
      return
    }
    if (mode === 'bottom_up' && !configData.trim()) {
      setError('Paste firewall configuration data or load the sample')
      return
    }

    setLoading(true)
    try {
      reset()
      setMode(mode)
      setScfControlIds(selectedControls)
      setTechnology('Palo Alto Firewall')
      setAssetId(assetId)

      const { run_id } = await startAssessment({
        mode,
        scf_control_ids: selectedControls,
        technology: 'Palo Alto Firewall',
        asset_id: assetId,
        config_data: configData,
      })
      setRunId(run_id)
      navigate(`/assessment/${run_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start assessment')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <span className="text-sm font-semibold tracking-tight">ControlBridge AI</span>
          <span className="text-xs text-muted-foreground ml-1">— SCF Brain</span>
        </div>
        <span className="text-xs text-muted-foreground hidden sm:block">
          Control ↔ Technology Evidence Engine
        </span>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-10">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-primary/10 border border-primary/20 rounded-full px-3 py-1 text-xs text-primary mb-4">
            <Shield className="h-3 w-3" />
            Palo Alto Firewall · SCF / NIST 800-53 / CIS Controls
          </div>
          <h1 className="text-3xl font-bold tracking-tight mb-3">
            Compliance Evidence Engine
          </h1>
          <p className="text-muted-foreground text-base max-w-xl mx-auto">
            Top-down: translate SCF controls into Palo Alto validation checks and audit sheets.<br />
            Bottom-up: ingest firewall configs and map findings to compliance controls.
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="grid grid-cols-2 gap-3 mb-8">
          <button
            onClick={() => setLocalMode('top_down')}
            className={cn(
              'p-4 rounded-xl border text-left transition-all duration-200',
              mode === 'top_down'
                ? 'border-primary bg-primary/10 shadow-lg shadow-primary/10'
                : 'border-border bg-card hover:border-primary/30 hover:bg-muted/30',
            )}
          >
            <div className="text-sm font-semibold mb-1">
              Control → Technology
            </div>
            <div className="text-xs text-muted-foreground">
              Select SCF controls → get Palo Alto checks + audit sheet
            </div>
            <div className="mt-3 text-xs font-mono text-primary/60">
              SCF → NIST/CIS → PA Checks → Audit Sheet
            </div>
          </button>

          <button
            onClick={() => setLocalMode('bottom_up')}
            className={cn(
              'p-4 rounded-xl border text-left transition-all duration-200',
              mode === 'bottom_up'
                ? 'border-primary bg-primary/10 shadow-lg shadow-primary/10'
                : 'border-border bg-card hover:border-primary/30 hover:bg-muted/30',
            )}
          >
            <div className="text-sm font-semibold mb-1">
              Technology → Control
            </div>
            <div className="text-xs text-muted-foreground">
              Paste firewall config → get compliance posture + gaps
            </div>
            <div className="mt-3 text-xs font-mono text-primary/60">
              PA Config → Binary Facts → SCF/NIST → Posture
            </div>
          </button>
        </div>

        {/* Asset ID */}
        <div className="mb-6">
          <label className="text-xs text-muted-foreground mb-1.5 block">Asset ID</label>
          <input
            type="text"
            value={assetId}
            onChange={(e) => setLocalAssetId(e.target.value)}
            placeholder="PA-FW-DXB-01"
            className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
          />
        </div>

        {/* Top-down: SCF Control Selector */}
        {mode === 'top_down' && (
          <div className="space-y-3 mb-6">
            <div className="flex items-center justify-between">
              <label className="text-xs text-muted-foreground">SCF Controls to Assess</label>
              <div className="flex gap-1.5">
                {QUICK_CONTROLS.map((id) => (
                  <button
                    key={id}
                    onClick={() => toggleControl(id)}
                    className={cn(
                      'px-2 py-0.5 rounded text-xs font-mono transition-colors',
                      selectedControls.includes(id)
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {id}
                  </button>
                ))}
              </div>
            </div>

            <div className="border border-border rounded-lg overflow-hidden">
              {SCF_DOMAINS.map((d) => {
                const isExpanded = expandedDomain === d.domain
                const selectedInDomain = d.controls.filter((c) => selectedControls.includes(c))
                return (
                  <div key={d.domain} className="border-b border-border last:border-0">
                    <button
                      onClick={() => setExpandedDomain(isExpanded ? null : d.domain)}
                      className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-muted/40 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{d.domain}</span>
                        {selectedInDomain.length > 0 && (
                          <span className="text-xs bg-primary/20 text-primary rounded-full px-2 py-0.5">
                            {selectedInDomain.length} selected
                          </span>
                        )}
                      </div>
                      {isExpanded ? (
                        <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                      )}
                    </button>
                    {isExpanded && (
                      <div className="px-4 pb-3 flex flex-wrap gap-2">
                        {d.controls.map((controlId) => (
                          <button
                            key={controlId}
                            onClick={() => toggleControl(controlId)}
                            className={cn(
                              'px-3 py-1.5 rounded-lg border text-xs font-mono transition-all',
                              selectedControls.includes(controlId)
                                ? 'border-primary bg-primary/10 text-primary'
                                : 'border-border bg-muted/30 text-muted-foreground hover:border-primary/30 hover:text-foreground',
                            )}
                          >
                            {controlId}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {selectedControls.length > 0 && (
              <p className="text-xs text-muted-foreground">
                {selectedControls.length} control{selectedControls.length > 1 ? 's' : ''} selected: {selectedControls.join(', ')}
              </p>
            )}
          </div>
        )}

        {/* Bottom-up: Config Input */}
        {mode === 'bottom_up' && (
          <div className="space-y-3 mb-6">
            <div className="flex items-center justify-between">
              <label className="text-xs text-muted-foreground">Firewall Configuration (JSON)</label>
              <button
                onClick={() => setConfigData(SAMPLE_CONFIG)}
                className="text-xs text-primary hover:text-primary/80 transition-colors"
              >
                Load sample config
              </button>
            </div>
            <textarea
              value={configData}
              onChange={(e) => setConfigData(e.target.value)}
              placeholder='Paste Palo Alto configuration JSON here, or click "Load sample config" above...'
              rows={10}
              className="w-full bg-card border border-border rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary resize-none text-foreground/80"
            />
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <button
          onClick={handleRun}
          disabled={loading}
          className={cn(
            'w-full flex items-center justify-center gap-2 py-3 px-6 rounded-xl font-medium text-sm transition-all duration-200',
            loading
              ? 'bg-primary/50 text-primary-foreground cursor-not-allowed'
              : 'bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/20 hover:shadow-primary/30',
          )}
        >
          {loading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
              Starting assessment...
            </>
          ) : (
            <>
              Run Assessment
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </main>

      <footer className="text-center py-4 text-xs text-muted-foreground border-t border-border">
        Outskill AI Lab · ControlBridge AI · SCF Brain
      </footer>
    </div>
  )
}
