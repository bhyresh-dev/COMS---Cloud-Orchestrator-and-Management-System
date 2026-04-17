"""
Master Orchestrator — the heart of COMS.
Pipeline: NLP Parse → Policy Validate → Risk Classify → Execute or Escalate

Upgraded: uses SQLite (persistent), approvals now actually execute on approval.
"""
import time
from agents.nlp_agent import ConversationManager
from agents.policy_engine import validate_request
from agents.risk_classifier import classify_risk
from agents.executor import execute_request
from utils.firestore_db import (
    log_action, add_approval, get_pending_approvals,
    approve_approval, reject_approval, get_all_approvals,
)

# Fuzzy normalization: map common LLM hallucinations to correct intent strings
_INTENT_MAP = {
    # S3
    "s3": "list_s3_buckets", "list_s3": "list_s3_buckets",
    "create_bucket": "create_s3_bucket", "make_s3_bucket": "create_s3_bucket",
    "delete_bucket": "delete_s3_bucket",
    # EC2
    "ec2": "describe_ec2_instances", "list_ec2": "describe_ec2_instances",
    "launch_ec2": "launch_ec2_instance", "create_ec2": "launch_ec2_instance",
    "stop_ec2": "terminate_ec2_instance", "terminate_ec2": "terminate_ec2_instance",
    # IAM
    "iam": "list_iam_roles", "list_iam": "list_iam_roles",
    "create_role": "create_iam_role", "make_iam_role": "create_iam_role",
    "delete_role": "delete_iam_role",
    # Lambda
    "lambda": "list_lambda_functions", "list_lambda": "list_lambda_functions",
    "create_function": "create_lambda_function", "make_lambda": "create_lambda_function",
    "invoke_function": "invoke_lambda_function", "run_lambda": "invoke_lambda_function",
    # SNS
    "sns": "list_sns_topics", "list_sns": "list_sns_topics",
    "create_topic": "create_sns_topic", "make_sns_topic": "create_sns_topic",
    # Logs
    "logs": "list_log_groups", "cloudwatch": "list_log_groups",
    "create_logs": "create_log_group",
}

_HIGH_RISK_DEFAULTS = {
    "create_iam_role": {
        "trust_policy_service": "ec2.amazonaws.com",
        "description": "Managed by COMS",
    },
    "launch_ec2_instance": {
        "instance_type": "t2.micro",
        "region": "ap-south-1",
    },
    "create_lambda_function": {
        "runtime": "python3.12",
        "handler": "lambda_function.lambda_handler",
        "region": "ap-south-1",
        "description": "Managed by COMS",
    },
    "create_sns_topic": {},
    "create_log_group": {
        "region": "ap-south-1",
    },
}

_NEVER_ASK = {"team", "purpose", "environment", "description", "trust_policy_service",
               "instance_type", "runtime", "handler", "region", "access_level"}

def _inject_auto_defaults(parsed: dict) -> dict:
    """For high-risk intents, fill missing optional fields and clear clarification_needed."""
    intent = parsed.get("intent", "")
    if intent not in _HIGH_RISK_DEFAULTS:
        return parsed
    defaults = _HIGH_RISK_DEFAULTS[intent]
    params = dict(parsed.get("parameters") or {})
    for k, v in defaults.items():
        if not params.get(k):
            params[k] = v
    # Strip anything optional from missing_fields — never ask for these
    missing = [f for f in (parsed.get("missing_fields") or [])
               if f not in _NEVER_ASK and f not in defaults]
    result = {**parsed, "parameters": params, "missing_fields": missing}
    if not missing:
        result["clarification_needed"] = False
        result["clarification_question"] = None
    return result


def _normalize_intent(parsed: dict) -> dict:
    """Fix LLM hallucinations like 'S3' → 'list_s3_buckets'."""
    intent = parsed.get("intent", "")
    normalized = _INTENT_MAP.get(intent.lower().strip(), intent)
    if normalized != intent:
        print(f"[WARN] Normalized intent '{intent}' → '{normalized}'")
        parsed = {**parsed, "intent": normalized}
    return parsed


class MasterOrchestrator:
    def __init__(self):
        self.conversation = ConversationManager()
        self.user_role = "developer"
        self.username  = "anonymous"
        self.user_id   = None
        self.pipeline_stages = []

    def set_user_role(self, role: str):
        self.user_role = role

    def set_username(self, username: str):
        self.username = username

    def set_user_id(self, user_id: str):
        self.user_id = user_id

    def process_message(self, user_message: str) -> dict:
        self.pipeline_stages = []
        t_start = time.time()

        # ── STAGE 1: NLP PARSE ─────────────────────────────
        t1 = time.time()
        parse_result = self.conversation.send_message(user_message)
        self.pipeline_stages.append({
            "stage": "NLP Parsing (Llama 3.3 70B via Groq)",
            "time_seconds": round(time.time() - t1, 2),
            "status": "success" if parse_result["success"] else "error",
        })

        if not parse_result["success"]:
            return {"status": "error", "message": f"Parse failed: {parse_result.get('error')}"}

        parsed = _normalize_intent(parse_result["data"])
        parsed = _inject_auto_defaults(parsed)

        # Only ask for clarification on S3 creates — all other intents auto-proceed
        if parsed.get("clarification_needed"):
            if parsed.get("intent") != "create_s3_bucket":
                parsed["clarification_needed"] = False
                parsed["clarification_question"] = None
            else:
                return {
                    "status": "clarification_needed",
                    "message": parsed.get("clarification_question", "Could you provide more details?"),
                }

        # ── STAGE 2: POLICY VALIDATION ─────────────────────
        t2 = time.time()
        policy_result = validate_request(parsed, self.user_role, user_id=self.user_id)
        self.pipeline_stages.append({
            "stage": "Policy Validation",
            "time_seconds": round(time.time() - t2, 2),
            "status": "approved" if policy_result["approved"] else "denied",
        })

        if not policy_result["approved"]:
            log_action(
                "policy_denied",
                {"intent": parsed["intent"], "violations": policy_result["violations"]},
                "denied", self.user_role, user_id=self.user_id,
            )
            return {
                "status": "denied",
                "message": "Request denied by policy engine.",
                "violations": policy_result["violations"],
                "warnings": policy_result.get("warnings", []),
            }

        # ── STAGE 3: RISK CLASSIFICATION ───────────────────
        t3 = time.time()
        risk_result = classify_risk(parsed)
        self.pipeline_stages.append({
            "stage": "Risk Classification",
            "time_seconds": round(time.time() - t3, 2),
            "status": "success",
        })

        # ── STAGE 4: EXECUTE or ESCALATE ───────────────────
        if risk_result["approval_required"]:
            aid = add_approval(parsed, risk_result, self.user_role, user_id=self.user_id)
            log_action("escalated", {"intent": parsed["intent"], "approval_id": aid},
                       "pending", self.user_role, user_id=self.user_id)
            return {
                "status": "pending_approval",
                "message": f"This is a {risk_result['tier']} action. Requires admin approval.",
                "approval_id": aid,
                "risk_result": risk_result,
                "pipeline_stages": self.pipeline_stages,
                "total_time_seconds": round(time.time() - t_start, 2),
            }
        else:
            t4 = time.time()
            exec_result = execute_request(parsed, self.user_role, user_id=self.user_id)
            self.pipeline_stages.append({
                "stage": "AWS Execution",
                "time_seconds": round(time.time() - t4, 2),
                "status": "success" if exec_result.get("success") else "error",
            })
            return {
                "status": "executed" if exec_result.get("success") else "error",
                "message": exec_result.get("message", exec_result.get("error", "Execution failed.")),
                "resource": exec_result.get("resource", {}),
                "pipeline_stages": self.pipeline_stages,
                "total_time_seconds": round(time.time() - t_start, 2),
            }

    def reset(self):
        self.conversation.reset()


# ── ADMIN ACTIONS ──────────────────────────────────────────

def do_approve(approval_id: str, approver: str) -> dict:
    """Approve a pending request and actually execute it."""
    entry = approve_approval(approval_id, approver)
    if not entry:
        return {"status": "error", "message": "Approval not found or already resolved."}
    exec_result = execute_request(entry["parsed_request"], entry.get("user_role", "unknown"))
    log_action("admin_approved", {"approval_id": approval_id, "approver": approver},
               "approved", approver)
    return {
        "status": "executed" if exec_result.get("success") else "error",
        "message": exec_result.get("message", exec_result.get("error", "Execution failed.")),
        "resource": exec_result.get("resource", {}),
    }


def do_reject(approval_id: str, reason: str, approver: str) -> dict:
    reject_approval(approval_id, reason, approver)
    log_action("admin_rejected", {"approval_id": approval_id, "reason": reason},
               "rejected", approver)
    return {"status": "rejected", "message": f"Request #{approval_id} rejected."}
