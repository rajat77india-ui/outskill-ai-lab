"""Input guardrails for the SCF Brain assessment pipeline."""

from agents import (
    GuardrailFunctionOutput,
    InputGuardrail,
    RunContextWrapper,
    Agent,
)
from pydantic import BaseModel

from scf_brain.models.audit import SCFAssessmentContext


class InputCheckResult(BaseModel):
    is_valid: bool
    reason: str


async def _validate_scf_input(
    ctx: RunContextWrapper[SCFAssessmentContext],
    agent: Agent,
    input_text: str,
) -> GuardrailFunctionOutput:
    text = input_text if isinstance(input_text, str) else str(input_text)

    if len(text.strip()) < 5:
        return GuardrailFunctionOutput(
            output_info=InputCheckResult(
                is_valid=False,
                reason="Input too short — provide at least one SCF control ID or domain name",
            ),
            tripwire_triggered=True,
        )

    return GuardrailFunctionOutput(
        output_info=InputCheckResult(is_valid=True, reason="Valid SCF input"),
        tripwire_triggered=False,
    )


scf_input_guardrail = InputGuardrail(guardrail_function=_validate_scf_input)


async def _validate_firewall_input(
    ctx: RunContextWrapper[SCFAssessmentContext],
    agent: Agent,
    input_text: str,
) -> GuardrailFunctionOutput:
    text = input_text if isinstance(input_text, str) else str(input_text)

    if len(text.strip()) < 20:
        return GuardrailFunctionOutput(
            output_info=InputCheckResult(
                is_valid=False,
                reason="Firewall config data too short — provide actual configuration data",
            ),
            tripwire_triggered=True,
        )

    return GuardrailFunctionOutput(
        output_info=InputCheckResult(is_valid=True, reason="Valid firewall input"),
        tripwire_triggered=False,
    )


firewall_input_guardrail = InputGuardrail(guardrail_function=_validate_firewall_input)
