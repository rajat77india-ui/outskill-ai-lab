"""Data models for SCF controls and framework crosswalk mappings."""

from dataclasses import dataclass, field
from typing import Literal

ControlDomain = Literal[
    "Network Security",
    "Identity and Access Control",
    "Logging and Monitoring",
    "Configuration Management",
    "Change Management",
    "Vulnerability Management",
    "Cryptography",
    "Incident Response",
]


@dataclass(frozen=True)
class SCFControl:
    """A single SCF control objective.

    Attributes:
        id: SCF control identifier (e.g. 'NET-02').
        name: Short control name.
        objective: The compliance objective statement.
        domain: High-level control domain.
        sub_domain: Sub-domain classification.
        description: Detailed implementation guidance.
        key_requirements: List of specific requirements.
    """

    id: str
    name: str
    objective: str
    domain: str
    sub_domain: str
    description: str
    key_requirements: list[str]


@dataclass(frozen=True)
class CrosswalkEntry:
    """Framework crosswalk mappings for a single SCF control.

    Attributes:
        scf_id: SCF control identifier.
        nist_800_53: Mapped NIST 800-53 Rev 5 control identifiers.
        cis_controls_v8: Mapped CIS Controls v8 identifiers.
        iso_27001_2022: Mapped ISO 27001:2022 clause identifiers.
        pci_dss_v4: Mapped PCI DSS v4.0 requirement identifiers.
        nist_description: Human-readable NIST mapping summary.
        cis_description: Human-readable CIS mapping summary.
        pci_description: Human-readable PCI mapping summary.
    """

    scf_id: str
    nist_800_53: list[str]
    cis_controls_v8: list[str]
    iso_27001_2022: list[str]
    pci_dss_v4: list[str]
    nist_description: str = ""
    cis_description: str = ""
    pci_description: str = ""


@dataclass(frozen=True)
class PaloAltoCheck:
    """A Palo Alto-specific technical validation check.

    Attributes:
        check_id: Unique check identifier (e.g. 'PA-NET02-001').
        check_name: Short descriptive check name.
        binary_question: The yes/no question this check answers.
        pass_condition: Criteria for a passing result.
        fail_condition: Criteria for a failing result.
        evidence_source: Where to obtain the evidence.
        evidence_fields: Specific fields to collect from evidence source.
        severity: Risk severity if the check fails.
        remediation: Recommended remediation steps.
        scf_control_id: Parent SCF control identifier.
    """

    check_id: str
    check_name: str
    binary_question: str
    pass_condition: str
    fail_condition: str
    evidence_source: str
    evidence_fields: list[str]
    severity: Literal["critical", "high", "medium", "low"]
    remediation: str
    scf_control_id: str = ""
