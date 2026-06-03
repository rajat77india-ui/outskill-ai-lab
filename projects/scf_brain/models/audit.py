"""Data models for audit test sheets and compliance assessments."""

from dataclasses import dataclass, field
from typing import Literal

from scf_brain.models.evidence import BinaryFact, BinaryResult


@dataclass(frozen=True)
class AuditTestRow:
    """A single row in an audit test sheet.

    Attributes:
        test_id: Unique test identifier (e.g. 'PA-001').
        control_objective: The control objective being tested.
        palo_alto_validation: What was checked on the firewall.
        expected_result: What the correct state should be.
        evidence: Evidence source and reference.
        result: Binary test result.
        finding: Optional finding detail if result is fail/partial.
    """

    test_id: str
    control_objective: str
    palo_alto_validation: str
    expected_result: str
    evidence: str
    result: BinaryResult
    finding: str = ""


@dataclass
class AuditSheet:
    """Complete audit test sheet for an assessment run.

    Attributes:
        technology: Technology assessed.
        asset_id: Asset assessed.
        assessment_date: ISO 8601 date of assessment.
        mode: Assessment mode (top_down or bottom_up).
        scf_control_ids: SCF controls covered by this assessment.
        tests: List of audit test rows.
        binary_facts: Underlying binary facts (for bottom-up mode).
        overall_score: Compliance score as a percentage.
        critical_findings: List of critical severity findings.
        high_findings: List of high severity findings.
        gaps: List of evidence gaps or missing controls.
        remediation_plan: Prioritized remediation guidance.
        executive_summary: Brief assessment summary for leadership.
    """

    technology: str
    asset_id: str
    assessment_date: str
    mode: Literal["top_down", "bottom_up"]
    scf_control_ids: list[str] = field(default_factory=list)
    tests: list[AuditTestRow] = field(default_factory=list)
    binary_facts: list[BinaryFact] = field(default_factory=list)
    overall_score: float = 0.0
    critical_findings: list[str] = field(default_factory=list)
    high_findings: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    remediation_plan: str = ""
    executive_summary: str = ""


@dataclass
class SCFAssessmentContext:
    """Shared context passed through the SCF Brain agent pipeline.

    Accumulates controls, checks, facts, and audit results as
    agents work through the assessment pipeline.

    Attributes:
        mode: Assessment mode.
        technology: Technology being assessed.
        asset_id: Asset identifier.
        raw_input: Original user input (control IDs or config data).
        config: API keys and model settings.
        scf_control_ids: Resolved SCF control IDs to assess.
        binary_facts: Accumulated binary facts.
        audit_tests: Accumulated audit test rows.
        compliance_score: Running compliance score.
        gaps: Identified gaps.
        remediation_plan: Generated remediation plan.
        final_report: Final assessment report content.
    """

    mode: Literal["top_down", "bottom_up"]
    technology: str
    asset_id: str
    raw_input: str
    config: dict[str, str | None]
    scf_control_ids: list[str] = field(default_factory=list)
    binary_facts: list[BinaryFact] = field(default_factory=list)
    audit_tests: list[AuditTestRow] = field(default_factory=list)
    compliance_score: float = 0.0
    gaps: list[str] = field(default_factory=list)
    remediation_plan: str = ""
    final_report: str = ""
