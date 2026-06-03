"""Data models for binary compliance facts and evidence records."""

from dataclasses import dataclass, field
from typing import Literal

BinaryResult = Literal["pass", "fail", "partial", "not_applicable", "unknown"]
Severity = Literal["critical", "high", "medium", "low", "info"]
EvidenceStatus = Literal["open", "closed", "in_progress", "accepted_risk"]


@dataclass(frozen=True)
class BinaryFact:
    """A normalized binary compliance validation fact.

    Each BinaryFact represents a single check on a technology asset,
    normalized from raw config/log data into a structured, mappable record.

    Attributes:
        technology: Technology that produced this fact (e.g. 'Palo Alto Firewall').
        asset_id: Asset identifier (hostname, serial, management IP).
        control_area: High-level control domain this check belongs to.
        check_id: Unique check identifier.
        check_name: Human-readable check description.
        binary_result: Pass / fail / partial / not_applicable / unknown.
        severity: Risk severity if result is fail.
        evidence_source: Where the evidence was obtained.
        evidence_value: Actual value or finding from evidence.
        mapped_scf_control: Mapped SCF control identifier and name.
        mapped_nist_control: Mapped NIST 800-53 control identifier(s).
        mapped_cis_check: Mapped CIS Controls identifier(s).
        remediation: Recommended remediation steps.
        owner: Team or individual responsible for remediation.
        status: Current remediation status.
    """

    technology: str
    asset_id: str
    control_area: str
    check_id: str
    check_name: str
    binary_result: BinaryResult
    severity: Severity
    evidence_source: str
    evidence_value: str
    mapped_scf_control: str
    mapped_nist_control: str
    mapped_cis_check: str
    remediation: str
    owner: str = "Network Security Team"
    status: EvidenceStatus = "open"


@dataclass
class EvidenceCollection:
    """Accumulated binary facts for an assessment run.

    Attributes:
        technology: Technology being assessed.
        asset_id: Asset being assessed.
        facts: All binary facts collected so far.
    """

    technology: str
    asset_id: str
    facts: list[BinaryFact] = field(default_factory=list)

    def add_fact(self, fact: BinaryFact) -> None:
        self.facts.append(fact)

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.facts if f.binary_result == "pass")

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.facts if f.binary_result == "fail")

    @property
    def partial_count(self) -> int:
        return sum(1 for f in self.facts if f.binary_result == "partial")

    @property
    def compliance_score(self) -> float:
        total = len(self.facts)
        if total == 0:
            return 0.0
        passing = self.pass_count + (self.partial_count * 0.5)
        return round((passing / total) * 100, 1)
