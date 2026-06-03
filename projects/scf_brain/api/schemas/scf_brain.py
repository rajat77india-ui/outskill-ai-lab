"""Pydantic schemas for the SCF Brain API."""

from typing import Literal

from pydantic import BaseModel, Field

AssessmentMode = Literal["top_down", "bottom_up"]
RunStatus = Literal["pending", "running", "completed", "failed"]
PhaseType = Literal[
    "analyzing",
    "ingesting",
    "mapping",
    "validating",
    "generating",
    "completed",
]
BinaryResult = Literal["pass", "fail", "partial", "not_applicable", "unknown"]
SeverityLevel = Literal["critical", "high", "medium", "low", "info"]

SSEEventType = Literal[
    "phase_change",
    "agent_start",
    "agent_end",
    "tool_start",
    "tool_end",
    "handoff",
    "result",
    "done",
    "error",
]


class AssessmentRequest(BaseModel):
    """Request body to start a new SCF Brain assessment.

    Attributes:
        mode: Assessment mode — top_down (control → checks) or bottom_up (evidence → controls).
        scf_control_ids: For top_down mode, list of SCF control IDs to assess.
        technology: Technology being assessed (default: Palo Alto Firewall).
        asset_id: Asset identifier for evidence tracking.
        config_data: For bottom_up mode, raw firewall config/log data as JSON string.
    """

    mode: AssessmentMode
    scf_control_ids: list[str] = Field(default_factory=list)
    technology: str = "Palo Alto Firewall"
    asset_id: str = "PA-FW-001"
    config_data: str = ""


class AssessmentRunResponse(BaseModel):
    """Response after initiating an assessment run.

    Attributes:
        run_id: Unique identifier for this assessment run.
        status: Current run status.
        mode: Assessment mode.
    """

    run_id: str
    status: RunStatus
    mode: AssessmentMode


class BinaryFactPayload(BaseModel):
    """A single binary compliance fact for API responses.

    Attributes:
        check_id: Unique check identifier.
        check_name: Human-readable check name.
        control_area: High-level control domain.
        binary_result: Pass/fail/partial/not_applicable/unknown.
        severity: Risk severity.
        evidence_source: Source of evidence.
        evidence_value: Actual evidence value or finding.
        mapped_scf_control: Mapped SCF control.
        mapped_nist_control: Mapped NIST 800-53 control(s).
        mapped_cis_check: Mapped CIS Controls identifier(s).
        remediation: Remediation steps.
    """

    check_id: str
    check_name: str
    control_area: str = ""
    binary_result: BinaryResult
    severity: SeverityLevel
    evidence_source: str
    evidence_value: str
    mapped_scf_control: str
    mapped_nist_control: str
    mapped_cis_check: str
    remediation: str


class AuditTestRowPayload(BaseModel):
    """A single audit test sheet row for API responses.

    Attributes:
        test_id: Unique test ID.
        control_objective: Control objective tested.
        palo_alto_validation: What was validated on the firewall.
        expected_result: Expected compliant state.
        evidence: Evidence reference.
        result: Test result.
        finding: Finding detail for failures.
    """

    test_id: str
    control_objective: str
    palo_alto_validation: str
    expected_result: str
    evidence: str
    result: BinaryResult
    finding: str = ""


class AssessmentResultResponse(BaseModel):
    """Complete assessment result for a finished run.

    Attributes:
        run_id: Unique run identifier.
        status: Run status.
        mode: Assessment mode.
        technology: Technology assessed.
        asset_id: Asset identifier.
        binary_facts: All binary compliance facts.
        audit_tests: Audit test sheet rows.
        compliance_score: Overall compliance score (0-100).
        gaps: Identified compliance gaps.
        remediation_plan: Prioritized remediation guidance.
        report: Full assessment report in markdown.
    """

    run_id: str
    status: RunStatus
    mode: AssessmentMode
    technology: str
    asset_id: str
    binary_facts: list[BinaryFactPayload] = Field(default_factory=list)
    audit_tests: list[AuditTestRowPayload] = Field(default_factory=list)
    compliance_score: float = 0.0
    gaps: list[str] = Field(default_factory=list)
    remediation_plan: str = ""
    report: str = ""
