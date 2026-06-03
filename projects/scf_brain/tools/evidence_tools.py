"""Evidence normalization and binary fact accumulation tools."""

import json
import logging

from agents import RunContextWrapper, function_tool

from scf_brain.models.audit import SCFAssessmentContext
from scf_brain.models.evidence import BinaryFact

logger = logging.getLogger(__name__)


@function_tool
def record_binary_fact(
    ctx: RunContextWrapper[SCFAssessmentContext],
    check_id: str,
    check_name: str,
    control_area: str,
    binary_result: str,
    severity: str,
    evidence_source: str,
    evidence_value: str,
    mapped_scf_control: str,
    mapped_nist_control: str,
    mapped_cis_check: str,
    remediation: str,
) -> str:
    """Record a normalized binary compliance fact into the assessment context.

    This is the core recording tool. Call once per check after evaluating
    a specific control aspect of the firewall configuration.

    Args:
        check_id: Unique check identifier (e.g. 'PA-NET02-001').
        check_name: Short descriptive check name.
        control_area: High-level control domain (e.g. 'Network Security').
        binary_result: One of: 'pass', 'fail', 'partial', 'not_applicable', 'unknown'.
        severity: Risk severity if failing: 'critical', 'high', 'medium', 'low', 'info'.
        evidence_source: Where the evidence was obtained.
        evidence_value: Actual finding or value from evidence.
        mapped_scf_control: Mapped SCF control ID and name.
        mapped_nist_control: Mapped NIST 800-53 control(s).
        mapped_cis_check: Mapped CIS Controls identifier(s).
        remediation: Recommended remediation steps.

    Returns:
        JSON string confirming fact was recorded.
    """
    valid_results = {"pass", "fail", "partial", "not_applicable", "unknown"}
    valid_severities = {"critical", "high", "medium", "low", "info"}

    if binary_result not in valid_results:
        binary_result = "unknown"
    if severity not in valid_severities:
        severity = "medium"

    fact = BinaryFact(
        technology=ctx.context.technology,
        asset_id=ctx.context.asset_id,
        control_area=control_area,
        check_id=check_id,
        check_name=check_name,
        binary_result=binary_result,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        evidence_source=evidence_source,
        evidence_value=evidence_value,
        mapped_scf_control=mapped_scf_control,
        mapped_nist_control=mapped_nist_control,
        mapped_cis_check=mapped_cis_check,
        remediation=remediation,
    )
    ctx.context.binary_facts.append(fact)
    logger.info("Recorded binary fact: check_id=%s result=%s", check_id, binary_result)

    return json.dumps(
        {
            "recorded": True,
            "check_id": check_id,
            "result": binary_result,
            "total_facts": len(ctx.context.binary_facts),
        }
    )


@function_tool
def get_facts_summary(ctx: RunContextWrapper[SCFAssessmentContext]) -> str:
    """Get a summary of all binary facts recorded so far in this assessment.

    Returns:
        JSON string with counts by result and severity, and full fact list.
    """
    facts = ctx.context.binary_facts
    by_result: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    failed_critical: list[dict] = []

    for f in facts:
        by_result[f.binary_result] = by_result.get(f.binary_result, 0) + 1
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        if f.binary_result == "fail" and f.severity == "critical":
            failed_critical.append({"check_id": f.check_id, "check_name": f.check_name})

    total = len(facts)
    passing = by_result.get("pass", 0) + by_result.get("partial", 0) * 0.5
    score = round((passing / total) * 100, 1) if total > 0 else 0.0

    return json.dumps(
        {
            "total_facts": total,
            "by_result": by_result,
            "by_severity": by_severity,
            "compliance_score": score,
            "critical_failures": failed_critical,
            "facts": [
                {
                    "check_id": f.check_id,
                    "check_name": f.check_name,
                    "result": f.binary_result,
                    "severity": f.severity,
                    "control_area": f.control_area,
                    "mapped_scf": f.mapped_scf_control,
                }
                for f in facts
            ],
        },
        indent=2,
    )


@function_tool
def calculate_compliance_score(ctx: RunContextWrapper[SCFAssessmentContext]) -> str:
    """Calculate the overall compliance score from recorded binary facts.

    Scoring: pass=1.0, partial=0.5, fail=0.0, not_applicable=excluded.
    Score is expressed as percentage of applicable checks passing.

    Returns:
        JSON string with compliance score and breakdown.
    """
    facts = ctx.context.binary_facts
    applicable = [f for f in facts if f.binary_result != "not_applicable"]
    total = len(applicable)

    if total == 0:
        return json.dumps({"error": "No applicable facts recorded yet"})

    passing = sum(
        1.0 if f.binary_result == "pass" else 0.5 if f.binary_result == "partial" else 0.0
        for f in applicable
    )
    score = round((passing / total) * 100, 1)
    ctx.context.compliance_score = score

    by_control: dict[str, dict] = {}
    for f in applicable:
        cid = f.mapped_scf_control.split(":")[0].strip() if ":" in f.mapped_scf_control else f.mapped_scf_control
        if cid not in by_control:
            by_control[cid] = {"pass": 0, "fail": 0, "partial": 0}
        by_control[cid][f.binary_result if f.binary_result in ("pass", "fail", "partial") else "fail"] += 1

    return json.dumps(
        {
            "overall_compliance_score": score,
            "total_applicable_checks": total,
            "passing": int(passing),
            "failing": total - int(passing),
            "score_label": (
                "Critical Risk" if score < 40
                else "High Risk" if score < 60
                else "Medium Risk" if score < 75
                else "Low Risk" if score < 90
                else "Compliant"
            ),
            "by_scf_control": by_control,
        },
        indent=2,
    )


@function_tool
def identify_gaps(
    ctx: RunContextWrapper[SCFAssessmentContext], scf_control_ids: list[str]
) -> str:
    """Identify compliance gaps — controls with failing evidence or missing checks.

    Args:
        scf_control_ids: List of SCF control IDs that should be covered.

    Returns:
        JSON string with identified gaps per control.
    """
    facts = ctx.context.binary_facts
    covered_controls = set()
    for f in facts:
        covered_controls.add(f.mapped_scf_control.split(":")[0].strip())

    gaps = []
    for cid in scf_control_ids:
        cid_upper = cid.upper()
        control_facts = [
            f for f in facts
            if cid_upper in f.mapped_scf_control.upper()
        ]

        if not control_facts:
            gaps.append(f"{cid_upper}: No evidence collected — control not assessed")
        else:
            failing = [f for f in control_facts if f.binary_result in ("fail", "partial")]
            if failing:
                for f in failing:
                    gaps.append(
                        f"{cid_upper}: {f.check_name} — {f.binary_result.upper()} "
                        f"({f.severity} severity)"
                    )

    ctx.context.gaps = gaps

    return json.dumps(
        {
            "scf_controls_requested": scf_control_ids,
            "gap_count": len(gaps),
            "gaps": gaps,
        },
        indent=2,
    )
