"""SCF Brain — Control ↔ Technology Evidence Engine Entry Point.

Bidirectional compliance intelligence pipeline:
  Top-down:   SCF control → crosswalk → Palo Alto checks → audit sheet
  Bottom-up:  Palo Alto configs/logs → binary facts → control posture → report

Usage:
    PYTHONPATH=projects uv run python -m scf_brain.main
"""

import asyncio
import json
import logging

from agents import (
    AgentHooks,
    AsyncOpenAI,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    set_tracing_disabled,
)

from scf_brain.agents.audit_sheet_writer import create_audit_sheet_writer_agent
from scf_brain.agents.control_analyst import create_control_analyst_agent
from scf_brain.agents.control_mapper import create_control_mapper_agent
from scf_brain.agents.evidence_normalizer import create_evidence_normalizer_agent
from scf_brain.agents.tech_check_builder import create_tech_check_builder_agent
from scf_brain.models.audit import SCFAssessmentContext
from scf_brain.utils.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class SCFBrainHooks(AgentHooks):
    """Lifecycle hooks for observability during agent execution."""

    async def on_start(self, context, agent):
        """Log when an agent starts processing."""
        print(f"\n{'='*60}")
        print(f"  AGENT: {agent.name}")
        print(f"{'='*60}")

    async def on_end(self, context, agent, output):
        """Log when an agent completes processing."""
        print(f"\n  [{agent.name}] completed.")

    async def on_tool_start(self, context, agent, tool):
        """Log when a tool is invoked."""
        print(f"  [{agent.name}] calling tool: {tool.name}")

    async def on_tool_end(self, context, agent, tool, result):
        """Log when a tool completes."""
        print(f"  [{agent.name}] tool {tool.name} done.")

    async def on_handoff(self, context, agent, source):
        """Log when a handoff occurs between agents."""
        print(f"\n  >> Handoff: {source.name} → {agent.name}")


def create_openrouter_model() -> OpenAIChatCompletionsModel:
    """Create an OpenRouter-backed model.

    Returns:
        OpenAIChatCompletionsModel: Model instance configured for OpenRouter.
    """
    config = load_config()
    api_key = config["openrouter_api_key"]
    assert api_key, (
        "OPENROUTER_API_KEY not set. "
        "Add it to your .env file: OPENROUTER_API_KEY=your_key_here"
    )

    client = AsyncOpenAI(
        base_url=config["openrouter_base_url"],
        api_key=api_key,
    )
    set_tracing_disabled(True)

    model = OpenAIChatCompletionsModel(
        model=config["model_name"],
        openai_client=client,
    )
    logger.info("OpenRouter model configured: model=%s", config["model_name"])
    return model


def build_top_down_pipeline(model: OpenAIChatCompletionsModel, hooks: AgentHooks):
    """Build the top-down pipeline: Control Analyst → Tech Check Builder → Audit Sheet Writer.

    Args:
        model: The OpenRouter-backed model instance.
        hooks: AgentHooks instance for lifecycle callbacks.

    Returns:
        Agent: The Control Analyst entry agent.
    """
    audit_writer = create_audit_sheet_writer_agent(hooks=hooks)
    tech_checker = create_tech_check_builder_agent(audit_writer, hooks=hooks)
    control_analyst = create_control_analyst_agent(tech_checker, hooks=hooks)

    all_agents = [control_analyst, tech_checker, audit_writer]
    for agent in all_agents:
        agent.model = model

    logger.info("Top-down pipeline built: Control Analyst → Tech Check Builder → Audit Sheet Writer")
    return control_analyst


def build_bottom_up_pipeline(model: OpenAIChatCompletionsModel, hooks: AgentHooks):
    """Build the bottom-up pipeline: Evidence Normalizer → Control Mapper → Audit Sheet Writer.

    Args:
        model: The OpenRouter-backed model instance.
        hooks: AgentHooks instance for lifecycle callbacks.

    Returns:
        Agent: The Evidence Normalizer entry agent.
    """
    audit_writer = create_audit_sheet_writer_agent(hooks=hooks)
    control_mapper = create_control_mapper_agent(audit_writer, hooks=hooks)
    evidence_normalizer = create_evidence_normalizer_agent(control_mapper, hooks=hooks)

    all_agents = [evidence_normalizer, control_mapper, audit_writer]
    for agent in all_agents:
        agent.model = model

    logger.info("Bottom-up pipeline built: Evidence Normalizer → Control Mapper → Audit Sheet Writer")
    return evidence_normalizer


async def run_top_down(scf_control_ids: list[str], technology: str = "Palo Alto Firewall", asset_id: str = "PA-FW-001") -> str:
    """Run the top-down pipeline: SCF controls → Palo Alto checks → audit sheet.

    Args:
        scf_control_ids: List of SCF control IDs to assess.
        technology: Technology to generate checks for.
        asset_id: Asset identifier.

    Returns:
        str: Final assessment report.
    """
    config = load_config()
    model = create_openrouter_model()
    hooks = SCFBrainHooks()

    context = SCFAssessmentContext(
        mode="top_down",
        technology=technology,
        asset_id=asset_id,
        raw_input=", ".join(scf_control_ids),
        config=config,
        scf_control_ids=scf_control_ids,
    )

    entry_agent = build_top_down_pipeline(model, hooks)

    pipeline_input = (
        f"TOP-DOWN COMPLIANCE ASSESSMENT\n"
        f"Technology: {technology}\n"
        f"Asset ID: {asset_id}\n"
        f"SCF Controls to Assess: {', '.join(scf_control_ids)}\n\n"
        f"Please look up each SCF control, retrieve crosswalk mappings to NIST/CIS, "
        f"identify all Palo Alto-specific validation checks, and build the complete "
        f"audit test sheet with evidence requirements."
    )

    run_config = RunConfig(workflow_name="scf_brain_top_down", tracing_disabled=True)

    result = await Runner.run(
        starting_agent=entry_agent,
        input=pipeline_input,
        context=context,
        max_turns=60,
        run_config=run_config,
    )
    return context.final_report or result.final_output


async def run_bottom_up(config_data: str, technology: str = "Palo Alto Firewall", asset_id: str = "PA-FW-001") -> str:
    """Run the bottom-up pipeline: firewall config → binary facts → compliance posture.

    Args:
        config_data: Raw Palo Alto configuration data as JSON string.
        technology: Technology name.
        asset_id: Asset identifier.

    Returns:
        str: Final assessment report.
    """
    config = load_config()
    model = create_openrouter_model()
    hooks = SCFBrainHooks()

    context = SCFAssessmentContext(
        mode="bottom_up",
        technology=technology,
        asset_id=asset_id,
        raw_input=config_data,
        config=config,
    )

    entry_agent = build_bottom_up_pipeline(model, hooks)

    pipeline_input = (
        f"BOTTOM-UP COMPLIANCE ASSESSMENT\n"
        f"Technology: {technology}\n"
        f"Asset ID: {asset_id}\n\n"
        f"FIREWALL CONFIGURATION DATA:\n{config_data}\n\n"
        f"Please analyze this Palo Alto firewall configuration, run all validation checks, "
        f"normalize findings into binary compliance facts, map them to SCF/NIST/CIS controls, "
        f"calculate compliance score, identify gaps, and produce a complete audit report."
    )

    run_config = RunConfig(workflow_name="scf_brain_bottom_up", tracing_disabled=True)

    result = await Runner.run(
        starting_agent=entry_agent,
        input=pipeline_input,
        context=context,
        max_turns=60,
        run_config=run_config,
    )
    return context.final_report or result.final_output


async def main():
    """Interactive CLI entry point for the SCF Brain engine."""
    print("\n" + "=" * 60)
    print("  SCF BRAIN — ControlBridge AI")
    print("  Control ↔ Technology Evidence Engine")
    print("=" * 60)
    print("\n[1] Top-Down: SCF Controls → Palo Alto Checks → Audit Sheet")
    print("[2] Bottom-Up: Palo Alto Config → Binary Facts → Compliance Posture")

    choice = input("\nSelect mode (1 or 2): ").strip()

    if choice == "1":
        print("\nEnter SCF control IDs to assess (comma-separated).")
        print("Example: NET-02, IAC-07, LOG-01")
        ids_input = input("SCF Control IDs: ").strip()
        control_ids = [x.strip().upper() for x in ids_input.split(",") if x.strip()]
        if not control_ids:
            print("No control IDs provided. Exiting.")
            return

        print(f"\nRunning top-down assessment for: {', '.join(control_ids)}")
        report = await run_top_down(control_ids)

    elif choice == "2":
        print("\nEnter the path to your Palo Alto config JSON file, or press Enter to use the sample config:")
        file_path = input("Config file path: ").strip()

        if file_path:
            import json as _json
            try:
                config_data = open(file_path).read()
            except FileNotFoundError:
                print(f"File not found: {file_path}. Using sample config.")
                config_data = _get_sample_config()
        else:
            config_data = _get_sample_config()
            print("Using built-in sample firewall configuration...")

        asset_id = input("Asset ID (default: PA-FW-001): ").strip() or "PA-FW-001"
        print(f"\nRunning bottom-up assessment for asset: {asset_id}")
        report = await run_bottom_up(config_data, asset_id=asset_id)

    else:
        print("Invalid choice. Exiting.")
        return

    print("\n" + "=" * 60)
    print("  ASSESSMENT REPORT")
    print("=" * 60)
    print(report)


def _get_sample_config() -> str:
    """Load the sample Palo Alto configuration from pa_checks.json."""
    from pathlib import Path
    data_file = Path(__file__).parent / "data" / "pa_checks.json"
    data = json.loads(data_file.read_text())
    return json.dumps(data.get("sample_firewall_config", {}), indent=2)


if __name__ == "__main__":
    asyncio.run(main())
