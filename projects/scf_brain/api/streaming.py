"""SSE streaming infrastructure for the SCF Brain API."""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Literal

from agents import AgentHooks

from scf_brain.api.schemas.scf_brain import (
    AssessmentMode,
    BinaryFactPayload,
    AuditTestRowPayload,
    PhaseType,
    RunStatus,
)

logger = logging.getLogger(__name__)

TOP_DOWN_PHASE_MAP: dict[str, PhaseType] = {
    "Control Analyst": "analyzing",
    "Tech Check Builder": "mapping",
    "Audit Sheet Writer": "generating",
}

BOTTOM_UP_PHASE_MAP: dict[str, PhaseType] = {
    "Evidence Normalizer": "ingesting",
    "Control Mapper": "mapping",
    "Audit Sheet Writer": "generating",
}


@dataclass
class AssessmentRunState:
    """In-memory state for a single SCF Brain assessment run.

    Attributes:
        run_id: Unique run identifier.
        mode: Assessment mode (top_down or bottom_up).
        technology: Technology being assessed.
        asset_id: Asset identifier.
        scf_control_ids: SCF controls to assess.
        config_data: Raw firewall config (for bottom-up mode).
        status: Current run status.
        queue: Async queue for SSE events.
        binary_facts: Accumulated binary facts.
        audit_tests: Audit test sheet rows.
        compliance_score: Overall compliance score.
        gaps: Identified gaps.
        remediation_plan: Generated remediation plan.
        report: Final assessment report.
        current_phase: Current pipeline phase.
    """

    run_id: str
    mode: AssessmentMode
    technology: str
    asset_id: str
    scf_control_ids: list[str]
    config_data: str
    status: RunStatus = "pending"
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    binary_facts: list[BinaryFactPayload] = field(default_factory=list)
    audit_tests: list[AuditTestRowPayload] = field(default_factory=list)
    compliance_score: float = 0.0
    gaps: list[str] = field(default_factory=list)
    remediation_plan: str = ""
    report: str = ""
    current_phase: PhaseType = "analyzing"


_runs: dict[str, AssessmentRunState] = {}


def create_run(
    mode: AssessmentMode,
    technology: str,
    asset_id: str,
    scf_control_ids: list[str],
    config_data: str,
) -> AssessmentRunState:
    """Create and register a new assessment run state.

    Args:
        mode: Assessment mode.
        technology: Technology being assessed.
        asset_id: Asset identifier.
        scf_control_ids: SCF controls to assess.
        config_data: Raw firewall configuration data.

    Returns:
        AssessmentRunState: The newly created run state.
    """
    run_id = uuid.uuid4().hex[:12]
    initial_phase: PhaseType = "analyzing" if mode == "top_down" else "ingesting"
    state = AssessmentRunState(
        run_id=run_id,
        mode=mode,
        technology=technology,
        asset_id=asset_id,
        scf_control_ids=scf_control_ids,
        config_data=config_data,
        current_phase=initial_phase,
    )
    _runs[run_id] = state
    logger.info("Created run: run_id=%s mode=%s", run_id, mode)
    return state


def get_run(run_id: str) -> AssessmentRunState | None:
    """Look up a run by ID.

    Args:
        run_id: The run identifier.

    Returns:
        AssessmentRunState | None: The run state, or None if not found.
    """
    return _runs.get(run_id)


def _sse_line(event: str, data: dict) -> str:
    """Format a single SSE message.

    Args:
        event: Event type name.
        data: JSON-serializable payload.

    Returns:
        str: SSE-formatted string.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class StreamingSCFHooks(AgentHooks):
    """AgentHooks that push lifecycle events to the SSE queue.

    Args:
        state: The AssessmentRunState to push events to.
    """

    def __init__(self, state: AssessmentRunState) -> None:
        self._state = state
        self._phase_map = (
            TOP_DOWN_PHASE_MAP if state.mode == "top_down" else BOTTOM_UP_PHASE_MAP
        )

    async def on_start(self, context, agent) -> None:
        """Push agent_start event and update phase.

        Args:
            context: The run context.
            agent: The agent that is starting.
        """
        phase = self._phase_map.get(agent.name, self._state.current_phase)
        if phase != self._state.current_phase:
            self._state.current_phase = phase
            await self._state.queue.put(
                _sse_line("phase_change", {"phase": phase})
            )

        await self._state.queue.put(
            _sse_line("agent_start", {"agent_name": agent.name})
        )
        logger.info("[%s] agent started: %s", self._state.run_id, agent.name)

    async def on_end(self, context, agent, output) -> None:
        """Push agent_end event.

        Args:
            context: The run context.
            agent: The agent that completed.
            output: The agent's output.
        """
        await self._state.queue.put(
            _sse_line("agent_end", {"agent_name": agent.name})
        )

    async def on_tool_start(self, context, agent, tool) -> None:
        """Push tool_start event.

        Args:
            context: The run context.
            agent: The agent invoking the tool.
            tool: The tool being invoked.
        """
        await self._state.queue.put(
            _sse_line(
                "tool_start",
                {"agent_name": agent.name, "detail": tool.name},
            )
        )

    async def on_tool_end(self, context, agent, tool, result) -> None:
        """Push tool_end event.

        Args:
            context: The run context.
            agent: The agent that invoked the tool.
            tool: The tool that completed.
            result: The tool's result.
        """
        await self._state.queue.put(
            _sse_line(
                "tool_end",
                {"agent_name": agent.name, "detail": tool.name},
            )
        )

    async def on_handoff(self, context, agent, source) -> None:
        """Push handoff event.

        Args:
            context: The run context.
            agent: The target agent receiving the handoff.
            source: The source agent performing the handoff.
        """
        await self._state.queue.put(
            _sse_line(
                "handoff",
                {
                    "agent_name": agent.name,
                    "detail": f"{source.name} → {agent.name}",
                },
            )
        )
        logger.info(
            "[%s] handoff: %s -> %s",
            self._state.run_id,
            source.name,
            agent.name,
        )


async def event_generator(state: AssessmentRunState):
    """Async generator that yields SSE-formatted strings from a run's queue.

    Args:
        state: The AssessmentRunState whose queue to consume.

    Yields:
        str: SSE-formatted event strings.
    """
    while True:
        msg: str = await state.queue.get()
        yield msg
        if '"done"' in msg or '"error"' in msg:
            break
