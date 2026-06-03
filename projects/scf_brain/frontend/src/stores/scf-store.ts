import { create } from 'zustand'
import type { AssessmentMode, BinaryFactPayload, AuditTestRowPayload, RunStatus } from '@/lib/api'

export type Phase =
  | 'analyzing'
  | 'ingesting'
  | 'mapping'
  | 'validating'
  | 'generating'
  | 'completed'

export interface TimelineEvent {
  type: string
  agent_name?: string
  detail?: string
  phase?: string
  message?: string
  timestamp: number
}

interface SCFState {
  runId: string | null
  mode: AssessmentMode
  technology: string
  assetId: string
  scfControlIds: string[]
  status: RunStatus
  phase: Phase
  binaryFacts: BinaryFactPayload[]
  auditTests: AuditTestRowPayload[]
  complianceScore: number
  gaps: string[]
  remediationPlan: string
  report: string
  events: TimelineEvent[]

  setRunId: (id: string) => void
  setMode: (mode: AssessmentMode) => void
  setTechnology: (tech: string) => void
  setAssetId: (id: string) => void
  setScfControlIds: (ids: string[]) => void
  setStatus: (status: RunStatus) => void
  setPhase: (phase: Phase) => void
  setBinaryFacts: (facts: BinaryFactPayload[]) => void
  setAuditTests: (tests: AuditTestRowPayload[]) => void
  setComplianceScore: (score: number) => void
  setGaps: (gaps: string[]) => void
  setRemediationPlan: (plan: string) => void
  setReport: (report: string) => void
  addEvent: (event: TimelineEvent) => void
  reset: () => void
}

const initialState = {
  runId: null,
  mode: 'top_down' as AssessmentMode,
  technology: 'Palo Alto Firewall',
  assetId: 'PA-FW-001',
  scfControlIds: [] as string[],
  status: 'idle' as RunStatus,
  phase: 'analyzing' as Phase,
  binaryFacts: [] as BinaryFactPayload[],
  auditTests: [] as AuditTestRowPayload[],
  complianceScore: 0,
  gaps: [] as string[],
  remediationPlan: '',
  report: '',
  events: [] as TimelineEvent[],
}

export const useSCFStore = create<SCFState>((set) => ({
  ...initialState,
  setRunId: (runId) => set({ runId, status: 'pending' }),
  setMode: (mode) => set({ mode }),
  setTechnology: (technology) => set({ technology }),
  setAssetId: (assetId) => set({ assetId }),
  setScfControlIds: (scfControlIds) => set({ scfControlIds }),
  setStatus: (status) => set({ status }),
  setPhase: (phase) => set({ phase, status: phase === 'completed' ? 'completed' : 'running' }),
  setBinaryFacts: (binaryFacts) => set({ binaryFacts }),
  setAuditTests: (auditTests) => set({ auditTests }),
  setComplianceScore: (complianceScore) => set({ complianceScore }),
  setGaps: (gaps) => set({ gaps }),
  setRemediationPlan: (remediationPlan) => set({ remediationPlan }),
  setReport: (report) => set({ report }),
  addEvent: (event) => set((s) => ({ events: [...s.events, event] })),
  reset: () => set(initialState),
}))
