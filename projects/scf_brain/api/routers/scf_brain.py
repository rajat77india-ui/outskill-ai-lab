"""SCF Brain API routes — assessment pipeline endpoints."""

import asyncio
import logging

from agents import RunConfig, Runner
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from scf_brain.api.schemas.scf_brain import (
    AssessmentRequest,
    AssessmentResultResponse,
    AssessmentRunResponse,
    BinaryFactPayload,
    AuditTestRowPayload,
)
from scf_brain.api.streaming import (
    StreamingSCFHooks,
    _sse_line,
    create_run,
    event_generator,
    get_run,
)
from scf_brain.main import build_bottom_up_pipeline, build_top_down_pipeline, create_openrouter_model
from scf_brain.models.audit import SCFAssessmentContext
from scf_brain.utils.config import load_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scf-brain", tags=["scf-brain"])


async def _run_pipeline(run_id: str) -> None:
    """Execute the SCF Brain assessment pipeline as a background task.

    Args:
        run_id: The run identifier.
    """
    state = get_run(run_id)
    assert state is not None

    state.status = "running"
    hooks = StreamingSCFHooks(state)

    config = load_config()
    model = create_openrouter_model()

    assessment_context = SCFAssessmentContext(
        mode=state.mode,
        technology=state.technology,
        asset_id=state.asset_id,
        raw_input=state.config_data or ", ".join(state.scf_control_ids),
        config=config,
        scf_control_ids=state.scf_control_ids,
    )

    if state.mode == "top_down":
        entry_agent = build_top_down_pipeline(model, hooks)
        pipeline_input = (
            f"TOP-DOWN COMPLIANCE ASSESSMENT\n"
            f"Technology: {state.technology}\n"
            f"Asset ID: {state.asset_id}\n"
            f"SCF Controls to Assess: {', '.join(state.scf_control_ids)}\n\n"
            f"Please look up each SCF control, retrieve crosswalk mappings to NIST/CIS, "
            f"identify all Palo Alto-specific validation checks, and build the complete "
            f"audit test sheet with evidence requirements for each check."
        )
    else:
        entry_agent = build_bottom_up_pipeline(model, hooks)
        pipeline_input = (
            f"BOTTOM-UP COMPLIANCE ASSESSMENT\n"
            f"Technology: {state.technology}\n"
            f"Asset ID: {state.asset_id}\n\n"
            f"FIREWALL CONFIGURATION DATA:\n{state.config_data}\n\n"
            f"Please analyze this Palo Alto firewall configuration, run all validation checks, "
            f"normalize findings into binary compliance facts, map them to SCF/NIST/CIS controls, "
            f"calculate compliance score, identify gaps, and produce a complete audit report."
        )

    run_config = RunConfig(
        workflow_name="scf_brain_assessment",
        tracing_disabled=True,
    )

    try:
        result = await Runner.run(
            starting_agent=entry_agent,
            input=pipeline_input,
            context=assessment_context,
            max_turns=60,
            run_config=run_config,
        )

        state.report = assessment_context.final_report or result.final_output
        state.compliance_score = assessment_context.compliance_score
        state.gaps = assessment_context.gaps
        state.remediation_plan = assessment_context.remediation_plan

        state.binary_facts = [
            BinaryFactPayload(
                check_id=f.check_id,
                check_name=f.check_name,
                control_area=f.control_area,
                binary_result=f.binary_result,
                severity=f.severity,
                evidence_source=f.evidence_source,
                evidence_value=f.evidence_value,
                mapped_scf_control=f.mapped_scf_control,
                mapped_nist_control=f.mapped_nist_control,
                mapped_cis_check=f.mapped_cis_check,
                remediation=f.remediation,
            )
            for f in assessment_context.binary_facts
        ]

        state.audit_tests = [
            AuditTestRowPayload(
                test_id=t.test_id,
                control_objective=t.control_objective,
                palo_alto_validation=t.palo_alto_validation,
                expected_result=t.expected_result,
                evidence=t.evidence,
                result=t.result,
                finding=t.finding,
            )
            for t in assessment_context.audit_tests
        ]

        state.status = "completed"

        await state.queue.put(
            _sse_line(
                "result",
                {
                    "compliance_score": state.compliance_score,
                    "binary_facts": [f.model_dump() for f in state.binary_facts],
                    "audit_tests": [t.model_dump() for t in state.audit_tests],
                    "gaps": state.gaps,
                    "remediation_plan": state.remediation_plan,
                    "report": state.report,
                },
            )
        )
        await state.queue.put(
            _sse_line("phase_change", {"phase": "completed"})
        )
        await state.queue.put(_sse_line("done", {"run_id": run_id}))

    except Exception as exc:
        logger.exception("Assessment pipeline failed: run_id=%s", run_id)
        state.status = "failed"
        await state.queue.put(
            _sse_line("error", {"message": str(exc)})
        )


@router.post("", response_model=AssessmentRunResponse)
async def start_assessment(request: AssessmentRequest) -> AssessmentRunResponse:
    """Start a new SCF Brain compliance assessment.

    Creates a run state, spawns the pipeline as a background task,
    and returns the run_id for SSE streaming.

    Args:
        request: Assessment request with mode, controls, and optional config data.

    Returns:
        AssessmentRunResponse: The run_id, status, and mode.

    Raises:
        HTTPException: 400 if required fields are missing for the selected mode.
    """
    if request.mode == "top_down" and not request.scf_control_ids:
        raise HTTPException(
            status_code=400,
            detail="top_down mode requires at least one scf_control_id",
        )
    if request.mode == "bottom_up" and not request.config_data.strip():
        raise HTTPException(
            status_code=400,
            detail="bottom_up mode requires config_data with firewall configuration",
        )

    state = create_run(
        mode=request.mode,
        technology=request.technology,
        asset_id=request.asset_id,
        scf_control_ids=request.scf_control_ids,
        config_data=request.config_data,
    )
    asyncio.create_task(_run_pipeline(state.run_id))
    return AssessmentRunResponse(run_id=state.run_id, status="pending", mode=state.mode)


@router.get("/{run_id}/stream")
async def stream_assessment(run_id: str) -> EventSourceResponse:
    """Stream real-time SSE events for an assessment run.

    Args:
        run_id: The run identifier.

    Returns:
        EventSourceResponse: SSE stream of pipeline events.

    Raises:
        HTTPException: 404 if run_id is not found.
    """
    state = get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return EventSourceResponse(event_generator(state))


@router.get("/{run_id}", response_model=AssessmentResultResponse)
async def get_assessment_result(run_id: str) -> AssessmentResultResponse:
    """Fetch the result of a completed assessment run.

    Args:
        run_id: The run identifier.

    Returns:
        AssessmentResultResponse: Full assessment result.

    Raises:
        HTTPException: 404 if run_id is not found.
    """
    state = get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return AssessmentResultResponse(
        run_id=state.run_id,
        status=state.status,
        mode=state.mode,
        technology=state.technology,
        asset_id=state.asset_id,
        binary_facts=state.binary_facts,
        audit_tests=state.audit_tests,
        compliance_score=state.compliance_score,
        gaps=state.gaps,
        remediation_plan=state.remediation_plan,
        report=state.report,
    )
