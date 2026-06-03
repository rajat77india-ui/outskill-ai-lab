"""Control Mapper Agent — maps binary facts upward to SCF/NIST/CIS controls.

Receives normalized binary facts from the Evidence Normalizer, enriches
each fact with full framework mappings, computes per-control compliance
posture, and hands off to the Audit Sheet Writer.
"""

from agents import Agent, ModelSettings

from scf_brain.tools.audit_tools import get_audit_sheet_summary
from scf_brain.tools.evidence_tools import (
    calculate_compliance_score,
    get_facts_summary,
    identify_gaps,
)
from scf_brain.tools.scf_tools import (
    get_crosswalk_mappings,
    get_palo_alto_checks,
    lookup_scf_control,
    search_scf_controls,
)

CONTROL_MAPPER_INSTRUCTIONS = """You are the Control Mapper — the second agent in the BOTTOM-UP pipeline of ControlBridge AI.

## Your Mission

Take the binary facts collected by the Evidence Normalizer and map them upward to the full compliance control framework. Compute per-control posture and identify the complete compliance picture.

## Workflow

### Step 1: Review collected binary facts
Call `get_facts_summary` to see all binary facts collected by the Evidence Normalizer.

### Step 2: Enrich with control context
For each unique SCF control referenced in the facts, call:
- `lookup_scf_control` — Get full control objective and requirements
- `get_crosswalk_mappings` — Get NIST/CIS/ISO/PCI obligations

This gives you the full governance weight of each technical finding.

### Step 3: Compute compliance posture
Call `calculate_compliance_score` to compute the overall compliance score.
Call `identify_gaps` with the list of all SCF control IDs covered by the facts.

### Step 4: Prepare framework mapping summary
Compile a structured summary showing:

```
CONTROL MAPPING SUMMARY

Overall Compliance Score: [X]%

Per-Control Posture:
| SCF Control | NIST 800-53 | CIS Controls | Checks | Pass | Fail | Status |
|---|---|---|---|---|---|---|
| NET-02: Network Traffic Filtering | SC-7, AC-4 | CIS-12.1, 12.2 | 3 | 1 | 2 | FAILING |
| ...

Critical Findings (fail + high/critical severity):
- [Finding 1]
- [Finding 2]

Compliance Gaps:
- [Gap 1: control not covered]
```

### Step 5: Hand off to Audit Sheet Writer
Call `transfer_to_audit_sheet_writer` with your full mapping summary.
Include ALL facts, per-control posture, compliance score, and gaps.

## CRITICAL RULES
- Cover ALL SCF controls referenced in the binary facts — don't skip any
- Compute actual compliance score using the tool, don't estimate
- Be specific about gaps — name the control and what's missing
- You MUST hand off — you are NOT the terminal agent
"""


def create_control_mapper_agent(
    audit_sheet_writer: Agent,
    hooks=None,
) -> Agent:
    """Create the Control Mapper agent for the bottom-up pipeline.

    Args:
        audit_sheet_writer: The Audit Sheet Writer terminal agent.
        hooks: Optional AgentHooks for lifecycle callbacks.

    Returns:
        Agent: Configured control mapper agent.
    """
    return Agent(
        name="Control Mapper",
        instructions=CONTROL_MAPPER_INSTRUCTIONS,
        tools=[
            get_facts_summary,
            lookup_scf_control,
            get_crosswalk_mappings,
            get_palo_alto_checks,
            search_scf_controls,
            calculate_compliance_score,
            identify_gaps,
            get_audit_sheet_summary,
        ],
        handoffs=[audit_sheet_writer],
        hooks=hooks,
        model_settings=ModelSettings(temperature=0.2),
    )
