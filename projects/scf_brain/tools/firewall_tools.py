"""Palo Alto firewall configuration analysis tools.

These tools parse and analyze Palo Alto firewall configuration and log
data (provided as JSON or structured text) and return normalized findings
that can be converted into binary compliance facts.
"""

import json
import logging
import re
from datetime import datetime, timezone

from agents import RunContextWrapper, function_tool

from scf_brain.models.audit import SCFAssessmentContext

logger = logging.getLogger(__name__)


def _parse_config(config_input: str) -> dict:
    """Attempt to parse config input as JSON, falling back to structured analysis."""
    try:
        return json.loads(config_input)
    except (json.JSONDecodeError, ValueError):
        return {"raw_text": config_input, "parse_error": "Input is not valid JSON"}


@function_tool
def analyze_security_rules(
    ctx: RunContextWrapper[SCFAssessmentContext], config_data: str
) -> str:
    """Parse and analyze Palo Alto security policy rules from config data.

    Examines all security rules and identifies:
    - Any-any-any allow rules (critical risk)
    - Rules with no threat prevention profiles
    - Rules with logging disabled
    - Overly broad rules by zone/address

    Args:
        config_data: Palo Alto configuration data as JSON string or structured text.

    Returns:
        JSON string with rule analysis findings.
    """
    config = _parse_config(config_data)
    rules = config.get("security_rules", [])

    findings = []
    for rule in rules:
        if rule.get("disabled"):
            continue

        name = rule.get("name", "unknown")
        src_addr = rule.get("source_address", "")
        dst_addr = rule.get("destination_address", "")
        app = rule.get("application", "")
        service = rule.get("service", "")
        action = rule.get("action", "allow")
        log_end = rule.get("log_end", False)
        av = rule.get("antivirus_profile")
        vuln = rule.get("vulnerability_profile")
        spy = rule.get("spyware_profile")
        hit_count = rule.get("hit_count", -1)
        last_hit = rule.get("last_hit")

        finding = {
            "rule_name": name,
            "action": action,
            "issues": [],
        }

        if action == "allow":
            if src_addr == "any" and dst_addr == "any" and (app == "any" or service == "any"):
                finding["issues"].append("CRITICAL: any-any-any allow rule — excessive network access")

            if not log_end:
                finding["issues"].append("HIGH: Traffic logging disabled — missing audit trail")

            src_zone = rule.get("source_zone", "")
            if src_zone in ("untrust", "internet", "external") or dst_addr == "any":
                if not av or not vuln or not spy:
                    missing = []
                    if not av:
                        missing.append("antivirus")
                    if not vuln:
                        missing.append("vulnerability protection")
                    if not spy:
                        missing.append("anti-spyware")
                    finding["issues"].append(
                        f"HIGH: Missing threat prevention profiles: {', '.join(missing)}"
                    )

            if hit_count == 0 and last_hit is None:
                finding["issues"].append("MEDIUM: Zero hit count — stale rule candidate")

        if finding["issues"]:
            findings.append(finding)

    return json.dumps(
        {
            "total_rules_analyzed": len(rules),
            "rules_with_issues": len(findings),
            "findings": findings,
        },
        indent=2,
    )


@function_tool
def detect_any_any_rules(
    ctx: RunContextWrapper[SCFAssessmentContext], config_data: str
) -> str:
    """Detect any-any-any allow rules (broadest permissive policy).

    Args:
        config_data: Firewall configuration as JSON string.

    Returns:
        JSON string with list of detected any-any-any rules and binary result.
    """
    config = _parse_config(config_data)
    rules = config.get("security_rules", [])

    broad_rules = [
        {
            "rule_name": r["name"],
            "source_zone": r.get("source_zone"),
            "source_address": r.get("source_address"),
            "destination_zone": r.get("destination_zone"),
            "destination_address": r.get("destination_address"),
            "application": r.get("application"),
            "service": r.get("service"),
        }
        for r in rules
        if not r.get("disabled")
        and r.get("action") == "allow"
        and r.get("source_address") == "any"
        and r.get("destination_address") == "any"
        and r.get("application") == "any"
    ]

    return json.dumps(
        {
            "check": "any-any-any allow rules",
            "binary_result": "fail" if broad_rules else "pass",
            "broad_rule_count": len(broad_rules),
            "broad_rules": broad_rules,
            "evidence_value": (
                f"{len(broad_rules)} rule(s) with any-source, any-destination, any-application"
                if broad_rules
                else "No any-any-any allow rules detected"
            ),
        },
        indent=2,
    )


@function_tool
def check_logging_configuration(
    ctx: RunContextWrapper[SCFAssessmentContext], config_data: str
) -> str:
    """Check if traffic logging is enabled on security rules and syslog is configured.

    Args:
        config_data: Firewall configuration as JSON string.

    Returns:
        JSON string with logging configuration status.
    """
    config = _parse_config(config_data)
    rules = config.get("security_rules", [])
    log_settings = config.get("log_settings", {})

    rules_without_logging = [
        r["name"]
        for r in rules
        if not r.get("disabled") and r.get("action") == "allow" and not r.get("log_end")
    ]

    syslog_configured = bool(log_settings.get("syslog_servers"))
    traffic_forwarded = log_settings.get("traffic_log_forwarding", False)
    threat_forwarded = log_settings.get("threat_log_forwarding", False)

    if rules_without_logging:
        rule_result = "fail"
    else:
        rule_result = "pass"

    if syslog_configured and traffic_forwarded and threat_forwarded:
        forwarding_result = "pass"
    elif syslog_configured:
        forwarding_result = "partial"
    else:
        forwarding_result = "fail"

    return json.dumps(
        {
            "rule_logging_result": rule_result,
            "rules_without_logging": rules_without_logging,
            "syslog_configured": syslog_configured,
            "traffic_forwarding_enabled": traffic_forwarded,
            "threat_forwarding_enabled": threat_forwarded,
            "log_forwarding_result": forwarding_result,
            "overall_result": "fail" if rule_result == "fail" or forwarding_result == "fail" else "partial" if forwarding_result == "partial" else "pass",
        },
        indent=2,
    )


@function_tool
def check_security_profiles(
    ctx: RunContextWrapper[SCFAssessmentContext], config_data: str
) -> str:
    """Check if threat prevention security profiles are attached to allow rules.

    Examines antivirus, anti-spyware, vulnerability protection, and URL filtering
    profile attachment on all active allow rules.

    Args:
        config_data: Firewall configuration as JSON string.

    Returns:
        JSON string with security profile coverage findings.
    """
    config = _parse_config(config_data)
    rules = config.get("security_rules", [])

    profile_gaps = []
    for rule in rules:
        if rule.get("disabled") or rule.get("action") != "allow":
            continue

        missing = []
        if not rule.get("antivirus_profile"):
            missing.append("antivirus")
        if not rule.get("vulnerability_profile"):
            missing.append("vulnerability_protection")
        if not rule.get("spyware_profile"):
            missing.append("anti_spyware")

        if missing:
            profile_gaps.append(
                {
                    "rule_name": rule["name"],
                    "missing_profiles": missing,
                    "source_zone": rule.get("source_zone"),
                    "destination_zone": rule.get("destination_zone"),
                }
            )

    binary_result = "pass" if not profile_gaps else "fail"

    return json.dumps(
        {
            "check": "threat prevention profile attachment",
            "binary_result": binary_result,
            "rules_without_profiles": len(profile_gaps),
            "profile_gaps": profile_gaps,
            "evidence_value": (
                f"{len(profile_gaps)} rule(s) missing threat prevention profiles"
                if profile_gaps
                else "All allow rules have threat prevention profiles attached"
            ),
        },
        indent=2,
    )


@function_tool
def detect_stale_rules(
    ctx: RunContextWrapper[SCFAssessmentContext],
    config_data: str,
    days_threshold: int = 90,
) -> str:
    """Find firewall rules with zero hits or no recent traffic matches.

    Args:
        config_data: Firewall configuration as JSON string.
        days_threshold: Days without hits to qualify as stale (default 90).

    Returns:
        JSON string with stale rule findings.
    """
    config = _parse_config(config_data)
    rules = config.get("security_rules", [])
    today = datetime.now(tz=timezone.utc).date()

    stale_rules = []
    for rule in rules:
        if rule.get("disabled"):
            continue

        hit_count = rule.get("hit_count", -1)
        last_hit_str = rule.get("last_hit")

        is_stale = False
        stale_reason = ""

        if hit_count == 0 and last_hit_str is None:
            is_stale = True
            stale_reason = "Zero hits, never matched traffic"
        elif last_hit_str:
            try:
                last_hit = datetime.strptime(last_hit_str, "%Y-%m-%d").date()
                days_ago = (today - last_hit).days
                if days_ago > days_threshold:
                    is_stale = True
                    stale_reason = f"Last hit {days_ago} days ago (threshold: {days_threshold} days)"
            except ValueError:
                pass

        if is_stale:
            stale_rules.append(
                {
                    "rule_name": rule["name"],
                    "hit_count": hit_count,
                    "last_hit": last_hit_str,
                    "stale_reason": stale_reason,
                    "action": rule.get("action"),
                    "source_zone": rule.get("source_zone"),
                    "destination_zone": rule.get("destination_zone"),
                }
            )

    return json.dumps(
        {
            "check": f"stale rules (>{days_threshold} days no hits)",
            "binary_result": "fail" if stale_rules else "pass",
            "stale_rule_count": len(stale_rules),
            "stale_rules": stale_rules,
            "evidence_value": (
                f"{len(stale_rules)} stale rule(s) detected"
                if stale_rules
                else f"No stale rules detected in last {days_threshold} days"
            ),
        },
        indent=2,
    )


@function_tool
def check_admin_authentication(
    ctx: RunContextWrapper[SCFAssessmentContext], config_data: str
) -> str:
    """Check administrator authentication settings including MFA and account hygiene.

    Evaluates: default admin account, shared accounts, MFA enforcement,
    superuser-only roles, password-only authentication.

    Args:
        config_data: Firewall configuration as JSON string.

    Returns:
        JSON string with admin authentication findings.
    """
    config = _parse_config(config_data)
    admins = config.get("admin_accounts", [])

    findings = []
    default_admin_active = any(
        a["username"] == "admin" and not a.get("disabled", False) for a in admins
    )
    admins_without_mfa = [a["username"] for a in admins if not a.get("mfa_enabled", False)]
    superuser_count = sum(1 for a in admins if a.get("role") == "superuser")
    total_admins = len(admins)

    if default_admin_active:
        findings.append("CRITICAL: Default 'admin' account is active — must be renamed or disabled")

    if admins_without_mfa:
        findings.append(
            f"CRITICAL: {len(admins_without_mfa)} admin(s) without MFA: {', '.join(admins_without_mfa)}"
        )

    if superuser_count == total_admins and total_admins > 0:
        findings.append(
            "MEDIUM: All admins have superuser role — RBAC with least privilege not enforced"
        )

    if total_admins > 5:
        findings.append(f"MEDIUM: {total_admins} local admin accounts — consider reducing and centralizing")

    mfa_result = "fail" if admins_without_mfa else "pass"
    rbac_result = "fail" if superuser_count == total_admins and total_admins > 0 else "pass"

    return json.dumps(
        {
            "total_admins": total_admins,
            "default_admin_active": default_admin_active,
            "admins_without_mfa": admins_without_mfa,
            "mfa_result": mfa_result,
            "superuser_count": superuser_count,
            "rbac_result": rbac_result,
            "findings": findings,
            "overall_result": "fail" if findings else "pass",
        },
        indent=2,
    )


@function_tool
def check_management_interface(
    ctx: RunContextWrapper[SCFAssessmentContext], config_data: str
) -> str:
    """Check management interface security settings.

    Evaluates: permitted IP restrictions, insecure protocols (Telnet/HTTP),
    SNMP default community strings.

    Args:
        config_data: Firewall configuration as JSON string.

    Returns:
        JSON string with management interface security findings.
    """
    config = _parse_config(config_data)
    mgmt = config.get("management_interface", {})

    findings = []
    permitted_ips = mgmt.get("permitted_ips", [])
    telnet = mgmt.get("telnet_enabled", False)
    http = mgmt.get("http_enabled", False)
    snmp = mgmt.get("snmp_enabled", False)
    snmp_community = mgmt.get("snmp_community", "")

    if not permitted_ips:
        findings.append(
            "CRITICAL: No permitted-IP list configured on management interface — access unrestricted"
        )

    if telnet:
        findings.append("HIGH: Telnet enabled on management interface — insecure protocol")

    if http:
        findings.append("HIGH: HTTP enabled on management interface — unencrypted access")

    if snmp and snmp_community in ("public", "private", ""):
        findings.append(
            f"HIGH: SNMP using default community string '{snmp_community}' — change required"
        )

    ip_restriction_result = "fail" if not permitted_ips else "pass"
    protocol_result = "fail" if telnet or http else "pass"
    snmp_result = "fail" if snmp and snmp_community in ("public", "private", "") else "pass"

    return json.dumps(
        {
            "permitted_ip_restriction": ip_restriction_result,
            "permitted_ips_configured": permitted_ips,
            "telnet_enabled": telnet,
            "http_enabled": http,
            "snmp_community_default": snmp and snmp_community in ("public", "private", ""),
            "protocol_result": protocol_result,
            "snmp_result": snmp_result,
            "findings": findings,
            "overall_result": "fail" if findings else "pass",
        },
        indent=2,
    )


@function_tool
def check_tls_profiles(
    ctx: RunContextWrapper[SCFAssessmentContext], config_data: str
) -> str:
    """Check SSL/TLS service profiles for weak protocol versions and cipher suites.

    Args:
        config_data: Firewall configuration as JSON string.

    Returns:
        JSON string with TLS configuration findings.
    """
    config = _parse_config(config_data)
    profiles = config.get("ssl_tls_profiles", [])

    weak_versions = {"ssl3-0", "tls1-0", "tls1-1", "sslv3", "tlsv1", "tlsv1.1"}
    weak_ciphers = {"rc4", "des", "3des", "null", "export", "md5", "rc4-md5"}

    findings = []
    for profile in profiles:
        name = profile.get("name", "unknown")
        min_ver = profile.get("min_version", "").lower()
        ciphers = [c.lower() for c in profile.get("cipher_suites", [])]

        if min_ver in weak_versions:
            findings.append(
                {
                    "profile": name,
                    "issue": f"Weak minimum TLS version: {min_ver}",
                    "severity": "high",
                }
            )

        for cipher in ciphers:
            for weak in weak_ciphers:
                if weak in cipher:
                    findings.append(
                        {
                            "profile": name,
                            "issue": f"Weak cipher suite: {cipher}",
                            "severity": "high",
                        }
                    )
                    break

    return json.dumps(
        {
            "check": "TLS profile strength",
            "binary_result": "fail" if findings else "pass",
            "profiles_analyzed": len(profiles),
            "weak_findings": len(findings),
            "findings": findings,
            "evidence_value": (
                f"{len(findings)} weak TLS configuration(s) found"
                if findings
                else "All TLS profiles use strong versions and cipher suites"
            ),
        },
        indent=2,
    )


@function_tool
def analyze_zone_topology(
    ctx: RunContextWrapper[SCFAssessmentContext], config_data: str
) -> str:
    """Analyze firewall zone configuration for segmentation quality.

    Args:
        config_data: Firewall configuration as JSON string.

    Returns:
        JSON string with zone topology findings.
    """
    config = _parse_config(config_data)
    zones = config.get("zones", [])

    zone_names = [z["name"] for z in zones]
    has_dmz = any("dmz" in z.lower() for z in zone_names)
    has_mgmt = any("mgmt" in z.lower() or "management" in z.lower() for z in zone_names)
    zones_without_protection = [
        z["name"] for z in zones if not z.get("protection_profile")
    ]

    findings = []
    if len(zones) < 3:
        findings.append("HIGH: Fewer than 3 zones defined — insufficient network segmentation")
    if not has_dmz:
        findings.append("MEDIUM: No DMZ zone defined — internet-facing services may be on internal network")
    if not has_mgmt:
        findings.append("MEDIUM: No management zone defined — management traffic may not be isolated")
    if zones_without_protection:
        findings.append(
            f"MEDIUM: Zones without protection profiles: {', '.join(zones_without_protection)}"
        )

    return json.dumps(
        {
            "check": "zone segmentation",
            "binary_result": "fail" if findings else "pass",
            "zone_count": len(zones),
            "zones": zone_names,
            "has_dmz": has_dmz,
            "has_management_zone": has_mgmt,
            "zones_without_protection": zones_without_protection,
            "findings": findings,
        },
        indent=2,
    )
