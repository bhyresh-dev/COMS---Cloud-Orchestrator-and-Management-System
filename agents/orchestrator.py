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
    activate_pending_resource,
)
from utils.cost_estimator import estimate_cost

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

# Name field key per intent
_RESOURCE_NAME_KEY = {
    "create_iam_role":        "role_name",
    "launch_ec2_instance":    "instance_name",
    "create_lambda_function": "function_name",
    "create_sns_topic":       "topic_name",
    "create_log_group":       "log_group_name",
}

# Human-friendly label per intent (used in the "What would you name the X?" prompt)
_RESOURCE_FRIENDLY = {
    "create_iam_role":        "IAM role",
    "launch_ec2_instance":    "EC2 instance",
    "create_lambda_function": "Lambda function",
    "create_sns_topic":       "SNS topic",
    "create_log_group":       "CloudWatch log group",
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
        explain = []  # explainability chain
        t_start = time.time()

        # ── STAGE 1: NLP PARSE ─────────────────────────────
        t1 = time.time()
        parse_result = self.conversation.send_message(user_message)
        nlp_time = round(time.time() - t1, 2)
        self.pipeline_stages.append({
            "stage": "NLP Parsing (Llama 3.1 via Groq)",
            "time_seconds": nlp_time,
            "status": "success" if parse_result["success"] else "error",
        })

        if not parse_result["success"]:
            return {"status": "error", "message": f"Parse failed: {parse_result.get('error')}"}

        parsed = _normalize_intent(parse_result["data"])
        parsed = _inject_auto_defaults(parsed)

        intent  = parsed.get("intent", "unknown")
        service = parsed.get("service", "unknown")
        params  = parsed.get("parameters", {})
        confidence = parsed.get("confidence", 1.0)

        explain.append({
            "agent": "NLP Agent",
            "decision": f"Parsed intent as '{intent}' (service: {service})",
            "detail": f"Confidence {int(confidence * 100)}% — extracted {len(params)} parameter(s)",
            "status": "success",
        })

        # ── Clarification logic ─────────────────────────────
        # S3: let the LLM decide what to ask (name, region, purpose all required)
        # All others: ONLY ask for resource name if missing — nothing else, ever
        if intent == "create_s3_bucket":
            if parsed.get("clarification_needed"):
                return {
                    "status": "clarification_needed",
                    "message": parsed.get("clarification_question", "Could you provide more details?"),
                }
        else:
            name_key = _RESOURCE_NAME_KEY.get(intent)
            if name_key:
                current_name = (params.get(name_key) or "").strip()
                # If LLM lost the name, try to recover it from the raw message
                if not current_name:
                    words = [w.strip("\"',;") for w in user_message.split()]
                    guessed = next((w for w in words if len(w) >= 2 and w.replace("-","").replace("_","").isalnum()), None)
                    if guessed:
                        params[name_key] = guessed
                        parsed["parameters"] = params
                        current_name = guessed
                if not current_name:
                    friendly = _RESOURCE_FRIENDLY.get(intent, "resource")
                    return {
                        "status": "clarification_needed",
                        "message": f"What would you like to name the {friendly}?",
                    }
            # Name present — clear any LLM-generated clarification, always proceed
            parsed["clarification_needed"] = False
            parsed["clarification_question"] = None

        # Auto-applied defaults note
        defaults_applied = {k: v for k, v in (_HIGH_RISK_DEFAULTS.get(intent) or {}).items()
                            if not (parse_result["data"].get("parameters") or {}).get(k)}
        if defaults_applied:
            explain.append({
                "agent": "Orchestrator",
                "decision": "Auto-filled missing optional parameters with safe defaults",
                "detail": ", ".join(f"{k} = {v}" for k, v in defaults_applied.items()),
                "status": "info",
            })

        # Region note
        region = params.get("region")
        if region:
            explain.append({
                "agent": "Orchestrator",
                "decision": f"Region resolved to '{region}'",
                "detail": "Extracted from request or applied default",
                "status": "info",
            })

        # ── STAGE 2: POLICY VALIDATION ─────────────────────
        t2 = time.time()
        policy_result = validate_request(parsed, self.user_role, user_id=self.user_id)
        self.pipeline_stages.append({
            "stage": "Policy Validation",
            "time_seconds": round(time.time() - t2, 2),
            "status": "approved" if policy_result["approved"] else "denied",
        })

        if policy_result["approved"]:
            explain.append({
                "agent": "Policy Engine",
                "decision": f"RBAC check passed — role '{self.user_role}' can request '{service}'",
                "detail": f"Region '{region or 'ap-south-1'}' is whitelisted. Resource limits within bounds.",
                "status": "success",
            })
        else:
            explain.append({
                "agent": "Policy Engine",
                "decision": "Request denied by policy",
                "detail": "; ".join(policy_result["violations"]),
                "status": "denied",
            })
            log_action(
                "policy_denied",
                {"intent": intent, "violations": policy_result["violations"]},
                "denied", self.user_role, user_id=self.user_id,
            )
            return {
                "status": "denied",
                "message": "Request denied by policy engine.",
                "violations": policy_result["violations"],
                "warnings": policy_result.get("warnings", []),
                "explain": explain,
            }

        # ── STAGE 3: RISK CLASSIFICATION ───────────────────
        t3 = time.time()
        risk_result = classify_risk(parsed)
        self.pipeline_stages.append({
            "stage": "Risk Classification",
            "time_seconds": round(time.time() - t3, 2),
            "status": "success",
        })

        explain.append({
            "agent": "Risk Classifier",
            "decision": f"{risk_result['tier']} — {'approval required' if risk_result['approval_required'] else 'auto-execute'}",
            "detail": risk_result["reason"],
            "status": "warning" if risk_result["approval_required"] else "success",
        })

        # ── COST ESTIMATE ───────────────────────────────────
        cost = estimate_cost(intent, params)

        # ── STAGE 4: EXECUTE or ESCALATE ───────────────────
        if risk_result["approval_required"]:
            aid = add_approval(parsed, risk_result, self.user_role, user_id=self.user_id)
            log_action("escalated", {"intent": intent, "approval_id": aid},
                       "pending", self.user_role, user_id=self.user_id)
            explain.append({
                "agent": "Orchestrator",
                "decision": "Escalated to admin approval queue",
                "detail": f"Approval ID: {aid}",
                "status": "warning",
            })
            return {
                "status": "pending_approval",
                "message": f"This is a {risk_result['tier']} action. Requires admin approval.",
                "approval_id": aid,
                "risk_result": risk_result,
                "cost_estimate": cost,
                "explain": explain,
                "pipeline_stages": self.pipeline_stages,
                "total_time_seconds": round(time.time() - t_start, 2),
            }
        else:
            t4 = time.time()
            exec_result = execute_request(parsed, self.user_role, user_id=self.user_id)
            exec_time = round(time.time() - t4, 2)
            self.pipeline_stages.append({
                "stage": "AWS Execution",
                "time_seconds": exec_time,
                "status": "success" if exec_result.get("success") else "error",
            })
            explain.append({
                "agent": "Executor",
                "decision": "AWS API call dispatched" if exec_result.get("success") else "AWS execution failed",
                "detail": exec_result.get("message", exec_result.get("error", "")),
                "status": "success" if exec_result.get("success") else "error",
            })
            return {
                "status": "executed" if exec_result.get("success") else "error",
                "message": exec_result.get("message", exec_result.get("error", "Execution failed.")),
                "resource": exec_result.get("resource", {}),
                "cost_estimate": cost,
                "explain": explain,
                "pipeline_stages": self.pipeline_stages,
                "total_time_seconds": round(time.time() - t_start, 2),
            }

    def reset(self):
        self.conversation.reset()


# ── ADMIN ACTIONS ──────────────────────────────────────────

def do_approve(approval_id: str, approver: str) -> dict:
    """Approve a pending request, execute it, and transition pending→active resource record."""
    entry = approve_approval(approval_id, approver)
    if not entry:
        return {"status": "error", "message": "Approval not found or already resolved."}

    parsed  = entry["parsed_request"]
    exec_result = execute_request(parsed, entry.get("user_role", "unknown"),
                                   user_id=entry.get("userId") or entry.get("user_id"))

    # Transition the pending resource record to active
    if exec_result.get("success"):
        intent   = parsed.get("intent", "")
        name_key = _RESOURCE_NAME_KEY.get(intent)
        if name_key:
            res_name = (parsed.get("parameters") or {}).get(name_key)
            if res_name:
                activate_pending_resource(res_name)

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
