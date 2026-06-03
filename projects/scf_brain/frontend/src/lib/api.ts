const API_BASE = '/api/scf-brain'

export type AssessmentMode = 'top_down' | 'bottom_up'
export type RunStatus = 'pending' | 'running' | 'completed' | 'failed'
export type BinaryResult = 'pass' | 'fail' | 'partial' | 'not_applicable' | 'unknown'
export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'info'

export interface BinaryFactPayload {
  check_id: string
  check_name: string
  control_area: string
  binary_result: BinaryResult
  severity: SeverityLevel
  evidence_source: string
  evidence_value: string
  mapped_scf_control: string
  mapped_nist_control: string
  mapped_cis_check: string
  remediation: string
}

export interface AuditTestRowPayload {
  test_id: string
  control_objective: string
  palo_alto_validation: string
  expected_result: string
  evidence: string
  result: BinaryResult
  finding: string
}

export interface AssessmentRequest {
  mode: AssessmentMode
  scf_control_ids?: string[]
  technology?: string
  asset_id?: string
  config_data?: string
}

export interface AssessmentRunResponse {
  run_id: string
  status: RunStatus
  mode: AssessmentMode
}

export interface AssessmentResult {
  run_id: string
  status: RunStatus
  mode: AssessmentMode
  technology: string
  asset_id: string
  binary_facts: BinaryFactPayload[]
  audit_tests: AuditTestRowPayload[]
  compliance_score: number
  gaps: string[]
  remediation_plan: string
  report: string
}

export async function startAssessment(req: AssessmentRequest): Promise<AssessmentRunResponse> {
  const res = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Failed to start assessment: ${err}`)
  }
  return res.json()
}

export async function getAssessmentResult(runId: string): Promise<AssessmentResult> {
  const res = await fetch(`${API_BASE}/${runId}`)
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Failed to get result: ${err}`)
  }
  return res.json()
}

export function getStreamUrl(runId: string): string {
  return `${API_BASE}/${runId}/stream`
}

export const SCF_DOMAINS = [
  { domain: 'Network Security', controls: ['NET-01', 'NET-02', 'NET-03', 'NET-04'] },
  { domain: 'Identity and Access Control', controls: ['IAC-01', 'IAC-07', 'IAC-09'] },
  { domain: 'Logging and Monitoring', controls: ['LOG-01', 'LOG-02'] },
  { domain: 'Configuration Management', controls: ['CFG-01', 'CFG-02', 'CFG-03'] },
  { domain: 'Change Management', controls: ['CHG-01'] },
  { domain: 'Vulnerability Management', controls: ['VUL-01'] },
  { domain: 'Cryptography', controls: ['CRY-01'] },
  { domain: 'Incident Response', controls: ['IRO-01'] },
]

export const SAMPLE_CONFIG = JSON.stringify({
  security_rules: [
    {
      name: 'Allow-All-Outbound',
      source_zone: 'trust',
      source_address: 'any',
      destination_zone: 'untrust',
      destination_address: 'any',
      application: 'any',
      service: 'any',
      action: 'allow',
      log_end: false,
      antivirus_profile: null,
      vulnerability_profile: null,
      spyware_profile: null,
      hit_count: 45231,
      last_hit: '2026-06-02',
      disabled: false,
    },
    {
      name: 'Allow-HTTP-Inbound',
      source_zone: 'untrust',
      source_address: 'any',
      destination_zone: 'dmz',
      destination_address: '10.10.10.50',
      application: 'web-browsing',
      service: 'application-default',
      action: 'allow',
      log_end: true,
      antivirus_profile: 'default',
      vulnerability_profile: 'strict',
      spyware_profile: 'strict',
      hit_count: 12043,
      last_hit: '2026-06-03',
      disabled: false,
    },
    {
      name: 'Allow-Legacy-System',
      source_zone: 'trust',
      source_address: '192.168.1.0/24',
      destination_zone: 'untrust',
      destination_address: 'any',
      application: 'any',
      service: 'any',
      action: 'allow',
      log_end: false,
      antivirus_profile: null,
      vulnerability_profile: null,
      spyware_profile: null,
      hit_count: 0,
      last_hit: null,
      disabled: false,
    },
  ],
  admin_accounts: [
    { username: 'admin', role: 'superuser', authentication_profile: 'local', mfa_enabled: false, last_login: '2026-05-15' },
    { username: 'netadmin', role: 'superuser', authentication_profile: 'local', mfa_enabled: false, last_login: '2026-06-01' },
  ],
  management_interface: {
    permitted_ips: [],
    telnet_enabled: false,
    http_enabled: true,
    https_enabled: true,
    ssh_enabled: true,
    snmp_enabled: true,
    snmp_community: 'public',
  },
  ssl_tls_profiles: [
    { name: 'Default-SSL-Profile', min_version: 'tls1-0', max_version: 'tls1-2', cipher_suites: ['RC4-MD5', 'AES256-SHA256'] },
  ],
  log_settings: {
    syslog_servers: [],
    traffic_log_forwarding: false,
    threat_log_forwarding: false,
    config_audit_enabled: true,
  },
  zones: [
    { name: 'trust', type: 'layer3', protection_profile: null },
    { name: 'untrust', type: 'layer3', protection_profile: 'default' },
    { name: 'dmz', type: 'layer3', protection_profile: null },
  ],
}, null, 2)
