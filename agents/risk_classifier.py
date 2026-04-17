import json
from pathlib import Path

# Safely load the risk rules config file
_dir = Path(__file__).parent.parent
RISK_PATH = _dir / "config" / "risk_rules.json"

with open(RISK_PATH) as f:
    RISK_RULES = json.load(f)

_AUTO_DEFAULTS = {
    "create_iam_role":        {"trust_policy_service": "ec2.amazonaws.com", "description": "Managed by COMS"},
    "launch_ec2_instance":    {"instance_type": "t2.micro", "region": "ap-south-1"},
    "create_lambda_function": {"runtime": "python3.12", "handler": "lambda_function.lambda_handler", "region": "ap-south-1", "description": "Managed by COMS"},
    "create_log_group":       {"region": "ap-south-1"},
}

def classify_risk(parsed_request: dict) -> dict:
    """
    Classify risk: low-risk = auto-execute, high-risk = needs approval.
    """
    intent = parsed_request.get("intent", "unknown")

    low_actions = RISK_RULES["risk_levels"]["low"]["actions"]
    high_actions = RISK_RULES["risk_levels"]["high"]["actions"]

    if intent in low_actions:
        return {
            "risk_level": "low",
            "approval_required": False,
            "reason": "Routine operation — auto-approved per policy.",
            "tier": "Tier 1: Low Risk",
        }
    elif intent in high_actions:
        auto_applied = _AUTO_DEFAULTS.get(intent, {})
        # Fill missing params with auto defaults
        params = parsed_request.get("parameters", {})
        for k, v in auto_applied.items():
            if not params.get(k):
                params[k] = v
        return {
            "risk_level": "high",
            "approval_required": True,
            "reason": "Sensitive action — requires admin approval before execution.",
            "tier": "Tier 2: High Risk",
            "approvers": RISK_RULES["risk_levels"]["high"]["approvers"],
            "auto_applied": {k: v for k, v in auto_applied.items() if not parsed_request.get("parameters", {}).get(k)},
        }
    else:
        return {
            "risk_level": "high",
            "approval_required": True,
            "reason": "Unknown action type — defaulting to high risk for safety.",
            "tier": "Tier 2: High Risk",
            "approvers": ["admin"],
            "auto_applied": {},
        }