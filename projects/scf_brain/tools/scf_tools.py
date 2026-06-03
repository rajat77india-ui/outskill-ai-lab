"""SCF control lookup and crosswalk mapping tools."""

import json
import logging
from pathlib import Path

from agents import RunContextWrapper, function_tool

from scf_brain.models.audit import SCFAssessmentContext

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"

_scf_controls: dict | None = None
_crosswalk: dict | None = None
_pa_checks: dict | None = None


def _load_scf() -> dict:
    global _scf_controls
    if _scf_controls is None:
        _scf_controls = json.loads((_DATA_DIR / "scf_controls.json").read_text())
    return _scf_controls


def _load_crosswalk() -> dict:
    global _crosswalk
    if _crosswalk is None:
        _crosswalk = json.loads((_DATA_DIR / "crosswalk.json").read_text())
    return _crosswalk


def _load_pa_checks() -> dict:
    global _pa_checks
    if _pa_checks is None:
        _pa_checks = json.loads((_DATA_DIR / "pa_checks.json").read_text())
    return _pa_checks


@function_tool
def list_scf_domains(ctx: RunContextWrapper[SCFAssessmentContext]) -> str:
    """List all available SCF control domains and the controls within each.

    Returns:
        JSON string with domain names and control IDs/names.
    """
    data = _load_scf()
    domains: dict[str, list[dict]] = {}
    for control in data["controls"]:
        domain = control["domain"]
        if domain not in domains:
            domains[domain] = []
        domains[domain].append({"id": control["id"], "name": control["name"]})
    return json.dumps({"domains": domains}, indent=2)


@function_tool
def list_controls_by_domain(
    ctx: RunContextWrapper[SCFAssessmentContext], domain: str
) -> str:
    """List all SCF controls within a specific domain.

    Args:
        domain: Domain name to filter by (e.g. 'Network Security').

    Returns:
        JSON string with matching controls.
    """
    data = _load_scf()
    controls = [
        {"id": c["id"], "name": c["name"], "objective": c["objective"]}
        for c in data["controls"]
        if domain.lower() in c["domain"].lower()
    ]
    if not controls:
        return json.dumps({"error": f"No controls found for domain '{domain}'"})
    return json.dumps({"domain": domain, "controls": controls}, indent=2)


@function_tool
def lookup_scf_control(
    ctx: RunContextWrapper[SCFAssessmentContext], control_id: str
) -> str:
    """Look up full details for a specific SCF control by its ID.

    Args:
        control_id: SCF control ID (e.g. 'NET-02').

    Returns:
        JSON string with full control details including objective, requirements, domain.
    """
    data = _load_scf()
    control = next(
        (c for c in data["controls"] if c["id"].upper() == control_id.upper()), None
    )
    if control is None:
        return json.dumps({"error": f"Control '{control_id}' not found"})
    return json.dumps(control, indent=2)


@function_tool
def search_scf_controls(
    ctx: RunContextWrapper[SCFAssessmentContext], query: str
) -> str:
    """Search SCF controls by keyword across name, objective, and description.

    Args:
        query: Search keyword or phrase (e.g. 'firewall', 'logging', 'MFA').

    Returns:
        JSON string with matching controls.
    """
    data = _load_scf()
    q = query.lower()
    matches = [
        {"id": c["id"], "name": c["name"], "domain": c["domain"], "objective": c["objective"]}
        for c in data["controls"]
        if q in c["name"].lower()
        or q in c["objective"].lower()
        or q in c.get("description", "").lower()
        or q in c["domain"].lower()
    ]
    return json.dumps({"query": query, "matches": matches, "count": len(matches)}, indent=2)


@function_tool
def get_crosswalk_mappings(
    ctx: RunContextWrapper[SCFAssessmentContext], scf_control_id: str
) -> str:
    """Get NIST 800-53, CIS Controls, ISO 27001, and PCI DSS mappings for an SCF control.

    Args:
        scf_control_id: SCF control ID to look up (e.g. 'NET-02').

    Returns:
        JSON string with all framework crosswalk mappings.
    """
    data = _load_crosswalk()
    entry = data["crosswalk"].get(scf_control_id.upper())
    if entry is None:
        return json.dumps({"error": f"No crosswalk found for '{scf_control_id}'"})
    return json.dumps(entry, indent=2)


@function_tool
def get_palo_alto_checks(
    ctx: RunContextWrapper[SCFAssessmentContext], scf_control_id: str
) -> str:
    """Get Palo Alto firewall-specific validation checks for an SCF control.

    Returns the list of binary checks, evidence sources, pass/fail conditions,
    and remediation steps specific to Palo Alto firewalls.

    Args:
        scf_control_id: SCF control ID (e.g. 'NET-02').

    Returns:
        JSON string with Palo Alto checks for that control.
    """
    data = _load_pa_checks()
    checks = data["checks_by_control"].get(scf_control_id.upper(), [])
    if not checks:
        return json.dumps(
            {
                "scf_control_id": scf_control_id,
                "message": f"No Palo Alto-specific checks defined for control '{scf_control_id}'",
                "checks": [],
            }
        )
    return json.dumps(
        {
            "technology": data["technology"],
            "scf_control_id": scf_control_id,
            "check_count": len(checks),
            "checks": checks,
        },
        indent=2,
    )


@function_tool
def get_all_pa_checks_for_controls(
    ctx: RunContextWrapper[SCFAssessmentContext], scf_control_ids: list[str]
) -> str:
    """Get all Palo Alto checks for a list of SCF control IDs at once.

    Args:
        scf_control_ids: List of SCF control IDs (e.g. ['NET-01', 'NET-02', 'IAC-07']).

    Returns:
        JSON string with all checks grouped by control ID.
    """
    data = _load_pa_checks()
    result = {}
    for cid in scf_control_ids:
        checks = data["checks_by_control"].get(cid.upper(), [])
        result[cid.upper()] = checks
    total = sum(len(v) for v in result.values())
    return json.dumps(
        {"technology": data["technology"], "total_checks": total, "by_control": result},
        indent=2,
    )
