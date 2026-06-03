"""Audit sheet generation and report finalization tools."""

import json
import logging
from datetime import datetime, timezone

from agents import RunContextWrapper, function_tool

from scf_brain.models.audit import AuditTestRow, SCFAssessmentContext

logger = logging.getLogger(__name__)


@function_tool
def record_audit_test(
    ctx: RunContextWrapper[SCFAssessmentContext],
    test_id: str,
    control_objective: str,
    palo_alto_validation: str,
    expected_result: str,
    evidence: str,
    result: str,
    finding: str = "",
) -> str:
    """Record a single audit test row in the assessment test sheet.

    Call once per control check to build up the structured audit test sheet.
    The test sheet forms the deliverable for compliance teams and auditors.

    Args:
        test_id: Unique test ID (e.g. 'PA-001').
        control_objective: The control objective being tested.
        palo_alto_validation: What specific check was performed on the firewall.
        expected_result: What the correct/compliant state should be.
        evidence: Evidence source referenced and actual evidence found.
        result: Test result: 'pass', 'fail', 'partial', or 'not_applicable'.
        finding: Optional detail of the finding (required when result is fail/partial).

    Returns:
        JSON string confirming test was recorded.
    """
    valid_results = {"pass", "fail", "partial", "not_applicable", "unknown"}
    if result not in valid_results:
        result = "unknown"

    row = AuditTestRow(
        test_id=test_id,
        control_objective=control_objective,
        palo_alto_validation=palo_alto_validation,
        expected_result=expected_result,
        evidence=evidence,
        result=result,  # type: ignore[arg-type]
        finding=finding,
    )
    ctx.context.audit_tests.append(row)
    logger.info("Recorded audit test: test_id=%s result=%s", test_id, result)

    return json.dumps(
        {
            "recorded": True,
            "test_id": test_id,
            "result": result,
            "total_tests": len(ctx.context.audit_tests),
        }
    )


@function_tool
def set_remediation_plan(
    ctx: RunContextWrapper[SCFAssessmentContext], remediation_plan: str
) -> str:
    """Store the prioritized remediation plan in the assessment context.

    Args:
        remediation_plan: Full remediation plan text with prioritized actions.

    Returns:
        JSON string confirming plan was stored.
    """
    ctx.context.remediation_plan = remediation_plan
    return json.dumps({"stored": True, "length": len(remediation_plan)})


@function_tool
def finalize_report(
    ctx: RunContextWrapper[SCFAssessmentContext], report_content: str
) -> str:
    """Store the final compliance assessment report and compute final score.

    This is the last tool call in the pipeline. Stores the complete
    report and triggers final compliance score computation.

    Args:
        report_content: Full assessment report in markdown format.

    Returns:
        JSON string with final assessment summary.
    """
    ctx.context.final_report = report_content

    facts = ctx.context.binary_facts
    applicable = [f for f in facts if f.binary_result != "not_applicable"]
    total = len(applicable)
    if total > 0:
        passing = sum(
            1.0 if f.binary_result == "pass" else 0.5 if f.binary_result == "partial" else 0.0
            for f in applicable
        )
        ctx.context.compliance_score = round((passing / total) * 100, 1)

    tests = ctx.context.audit_tests
    pass_count = sum(1 for t in tests if t.result == "pass")
    fail_count = sum(1 for t in tests if t.result == "fail")
    partial_count = sum(1 for t in tests if t.result == "partial")

    logger.info(
        "Assessment finalized: score=%.1f%%, tests=%d, pass=%d, fail=%d",
        ctx.context.compliance_score,
        len(tests),
        pass_count,
        fail_count,
    )

    return json.dumps(
        {
            "finalized": True,
            "compliance_score": ctx.context.compliance_score,
            "total_tests": len(tests),
            "pass": pass_count,
            "fail": fail_count,
            "partial": partial_count,
            "binary_facts": len(facts),
            "gaps": len(ctx.context.gaps),
            "assessment_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        }
    )


@function_tool
def get_audit_sheet_summary(ctx: RunContextWrapper[SCFAssessmentContext]) -> str:
    """Get a summary of the audit test sheet built so far.

    Returns:
        JSON string with test counts, results, and current compliance score.
    """
    tests = ctx.context.audit_tests
    by_result: dict[str, int] = {}
    for t in tests:
        by_result[t.result] = by_result.get(t.result, 0) + 1

    return json.dumps(
        {
            "total_tests": len(tests),
            "by_result": by_result,
            "current_compliance_score": ctx.context.compliance_score,
            "gaps": ctx.context.gaps,
            "tests": [
                {
                    "test_id": t.test_id,
                    "control_objective": t.control_objective[:80],
                    "result": t.result,
                    "finding": t.finding[:120] if t.finding else "",
                }
                for t in tests
            ],
        },
        indent=2,
    )
