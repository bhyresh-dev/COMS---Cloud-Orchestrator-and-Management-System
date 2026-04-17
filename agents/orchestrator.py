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
from utils.database import (
    log_action, add_approval, get_pending_approvals,
    approve_approval, reject_approval, get_all_approvals,
)


class MasterOrchestrator:
    def __init__(self):
        self.conversation = ConversationManager()
        self.user_role = "developer"
        self.username = "anonymous"
        self.pipeline_stages = []

    def set_user_role(self, role: str):
        self.user_role = role

    def set_username(self, username: str):
        self.username = username

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

        parsed = parse_result["data"]

        if parsed.get("clarification_needed"):
            return {
                "status": "clarification_needed",
                "message": parsed.get("clarification_question", "Could you provide more details?"),
            }

        # ── STAGE 2: POLICY VALIDATION ─────────────────────
        t2 = time.time()
        policy_result = validate_request(parsed, self.user_role)
        self.pipeline_stages.append({
            "stage": "Policy Validation",
            "time_seconds": round(time.time() - t2, 2),
            "status": "approved" if policy_result["approved"] else "denied",
        })

        if not policy_result["approved"]:
            log_action(
                "policy_denied",
                {"intent": parsed["intent"], "violations": policy_result["violations"]},
                "denied", self.user_role,
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
            aid = add_approval(parsed, risk_result, self.user_role)
            log_action("escalated", {"intent": parsed["intent"], "approval_id": aid},
                       "pending", self.user_role)
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
            exec_result = execute_request(parsed, self.user_role)
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

def do_approve(approval_id: int, approver: str = "admin") -> dict:
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


def do_reject(approval_id: int, reason: str = "Rejected by admin", approver: str = "admin") -> dict:
    reject_approval(approval_id, reason, approver)
    log_action("admin_rejected", {"approval_id": approval_id, "reason": reason},
               "rejected", approver)
    return {"status": "rejected", "message": f"Request #{approval_id} rejected."}
