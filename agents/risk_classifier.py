import json
from pathlib import Path

# Safely load the risk rules config file
_dir = Path(__file__).parent.parent
RISK_PATH = _dir / "config" / "risk_rules.json"

with open(RISK_PATH) as f:
    RISK_RULES = json.load(f)

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
        return {
            "risk_level": "high",
            "approval_required": True,
            "reason": "Sensitive action — requires admin approval before execution.",
            "tier": "Tier 2: High Risk",
            "approvers": RISK_RULES["risk_levels"]["high"]["approvers"],
        }
    else:
        # Unknown = default to high risk (safety first!)
        return {
            "risk_level": "high",
            "approval_required": True,
            "reason": "Unknown action type — defaulting to high risk for safety.",
            "tier": "Tier 2: High Risk",
            "approvers": ["admin"],
        }