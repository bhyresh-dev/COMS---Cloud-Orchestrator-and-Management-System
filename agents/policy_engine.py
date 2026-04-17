import json
from pathlib import Path

# Safely load the policies config file
_dir = Path(__file__).parent.parent
POLICY_PATH = _dir / "config" / "policies.json"

with open(POLICY_PATH) as f:
    POLICIES = json.load(f)

def validate_request(parsed_request: dict, user_role: str = "developer") -> dict:
    """
    Validate a parsed request against organization policies.
    Checks: RBAC permissions, region, resource limits, tags.
    """
    violations = []
    warnings = []
    params = parsed_request.get("parameters", {})
    service = parsed_request.get("service", "")
    user_context = parsed_request.get("user_context", {})

    # --- RBAC: Can this role request this service? ---
    role_config = POLICIES.get("rbac_roles", {}).get(user_role)
    if not role_config:
        violations.append(f"Unknown role '{user_role}'. Access denied.")
        return {"approved": False, "violations": violations, "warnings": warnings}

    if service and service != "unknown":
        if service not in role_config.get("can_request", []):
            violations.append(
                f"Role '{user_role}' is not authorized to request '{service}' resources. "
                f"Allowed services: {role_config['can_request']}"
            )

    # --- Region Validation ---
    region = params.get("region", "ap-south-1")
    allowed_regions = POLICIES.get("allowed_regions", [])
    if region not in allowed_regions:
        violations.append(f"Region '{region}' is not allowed. Permitted: {allowed_regions}")

    # --- Service-Specific Limits ---
    limits = POLICIES.get("resource_limits", {}).get(service, {})

    if service == "s3":
        size_gb = params.get("size_gb", 0)
        max_size = limits.get("max_size_gb", 500)
        if size_gb and size_gb > max_size:
            violations.append(f"Requested {size_gb}GB exceeds max {max_size}GB limit.")

    elif service == "ec2":
        instance_type = params.get("instance_type", "t2.micro")
        allowed_types = limits.get("allowed_instance_types", [])
        if allowed_types and instance_type not in allowed_types:
            violations.append(f"Instance type '{instance_type}' not allowed.")

    # --- Missing Tags (warnings, not violations) ---
    for tag in POLICIES.get("mandatory_tags", []):
        if not user_context.get(tag):
            warnings.append(f"Missing recommended tag: '{tag}'")

    return {
        "approved": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "checked_by": "COMS Policy Engine v1.0",
    }