"""
COMS — Policy Engine.

Enforces RBAC, region, resource limits (checked against live DB counts),
and input validation before any executor call.
"""
import json
import re
from pathlib import Path
from utils.firestore_db import count_resources

_dir = Path(__file__).parent.parent
POLICY_PATH = _dir / "config" / "policies.json"

with open(POLICY_PATH) as f:
    POLICIES = json.load(f)

# S3 bucket name rules (AWS enforced)
_BUCKET_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$')


def validate_request(parsed_request: dict, user_role: str = "user",
                     user_id: str | None = None) -> dict:
    """
    Validate a parsed request against policies.

    Checks (in order):
      1. RBAC — can this role touch this service?
      2. Region whitelist
      3. Input format (bucket names, instance types)
      4. Live resource-count limits (queries DB)
      5. Missing mandatory tags (warning only)

    Returns dict with 'approved', 'violations', 'warnings'.
    """
    violations: list[str] = []
    warnings:   list[str] = []
    params       = parsed_request.get("parameters", {}) or {}
    service      = (parsed_request.get("service") or "").lower()
    intent       = parsed_request.get("intent", "")
    user_context = parsed_request.get("user_context", {}) or {}

    # ── 1. RBAC ──────────────────────────────────────────────
    role_config = POLICIES.get("rbac_roles", {}).get(user_role)
    if not role_config:
        violations.append(f"Unknown role '{user_role}'. Access denied.")
        return _result(violations, warnings)

    if service and service != "unknown":
        if service not in role_config.get("can_request", []):
            violations.append(
                f"Role '{user_role}' cannot request '{service}' resources. "
                f"Allowed: {role_config['can_request']}"
            )

    # ── 2. Region whitelist ───────────────────────────────────
    region = params.get("region") or "ap-south-1"
    allowed_regions = POLICIES.get("allowed_regions", [])
    if region not in allowed_regions:
        violations.append(
            f"Region '{region}' is not permitted. Allowed: {allowed_regions}"
        )

    # ── 3. Input format validation ────────────────────────────
    limits = POLICIES.get("resource_limits", {}).get(service, {})

    if service == "s3":
        name = params.get("bucket_name", "")
        if name and not _BUCKET_NAME_RE.match(name):
            violations.append(
                f"Invalid bucket name '{name}'. "
                "Must be 3-63 chars, lowercase letters, numbers, hyphens only."
            )
        size_gb = params.get("size_gb") or 0
        max_size = limits.get("max_size_gb", 5)
        if size_gb and size_gb > max_size:
            violations.append(
                f"Requested {size_gb} GB exceeds max {max_size} GB limit."
            )

    elif service == "ec2":
        itype = params.get("instance_type", "t2.micro")
        allowed_types = limits.get("allowed_instance_types", [])
        if allowed_types and itype not in allowed_types:
            violations.append(
                f"Instance type '{itype}' not allowed. "
                f"Permitted: {allowed_types}"
            )

    elif service == "lambda":
        runtime = params.get("runtime", "python3.12")
        allowed_runtimes = limits.get("allowed_runtimes", [])
        if allowed_runtimes and runtime not in allowed_runtimes:
            violations.append(
                f"Runtime '{runtime}' not allowed. "
                f"Permitted: {allowed_runtimes}"
            )

    # ── 4. Live resource-count limits ─────────────────────────
    if not violations and (intent.startswith("create_") or intent.startswith("launch_")):
        _check_live_limits(service, intent, limits, user_id, user_role, violations)

    # ── 5. Missing tags (warning only) ───────────────────────
    for tag in POLICIES.get("mandatory_tags", []):
        if not user_context.get(tag):
            warnings.append(f"Missing recommended tag: '{tag}'")

    return _result(violations, warnings)


def _check_live_limits(service: str, intent: str, limits: dict,
                       user_id: str | None, user_role: str,
                       violations: list):
    """Query DB and compare against configured maximums."""
    type_map = {
        "s3":     "S3 Bucket",
        "ec2":    "EC2 Instance",
        "iam":    "IAM Role",
        "lambda": "Lambda Function",
        "sns":    "SNS Topic",
        "logs":   "CloudWatch Log Group",
    }
    resource_type = type_map.get(service)
    if not resource_type:
        return

    # Count resources for this user (or globally if no user_id)
    current = count_resources(resource_type, user_id=user_id)

    limit_key_map = {
        "S3 Bucket":            "max_buckets_per_team",
        "EC2 Instance":         "max_instances",
        "IAM Role":             "max_roles_per_team",
        "Lambda Function":      "max_functions",
        "SNS Topic":            "max_topics",
        "CloudWatch Log Group": "max_log_groups",
    }
    limit_key = limit_key_map.get(resource_type)
    if not limit_key:
        return

    max_allowed = limits.get(limit_key)
    if max_allowed and current >= max_allowed:
        violations.append(
            f"Resource limit reached: you have {current} active {resource_type}(s), "
            f"maximum is {max_allowed}."
        )


def _result(violations: list, warnings: list) -> dict:
    return {
        "approved":   len(violations) == 0,
        "violations": violations,
        "warnings":   warnings,
        "checked_by": "COMS Policy Engine v2.0",
    }
