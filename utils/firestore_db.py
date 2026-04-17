"""
COMS — Firestore persistence layer.

Replaces utils/database.py (SQLite).
All public function signatures are intentionally compatible with the
old SQLite layer so that agents only need an import-path change.

user_id is now a Firebase Auth UID (str), not an integer.
Document IDs returned by add_approval() are Firestore auto-IDs (str).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud.firestore_v1 import FieldFilter

from utils.firebase_init import get_db
from config.admins import ADMIN_EMAILS

# ── Collection names ────────────────────────────────────────
_AUDIT      = "audit_logs"
_APPROVALS  = "approvals"
_RESOURCES  = "resources"
_BUDGET     = "budget_log"
_USERS      = "users"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _doc_to_dict(doc) -> dict:
    d = doc.to_dict() or {}
    d["id"] = doc.id
    # Firestore timestamps → ISO strings for uniform downstream handling
    for key in ("timestamp", "createdAt", "resolvedAt"):
        if key in d and hasattr(d[key], "isoformat"):
            d[key] = d[key].isoformat()
    return d


# ── Audit log ────────────────────────────────────────────────

def log_action(
    action: str,
    details: dict,
    status: str = "success",
    user_role: str | None = None,
    duration_s: float | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
) -> None:
    """Append-only write to audit_logs. No delete endpoint is exposed."""
    db = get_db()
    db.collection(_AUDIT).add({
        "timestamp":  _now(),
        "action":     action,
        "details":    details or {},
        "status":     status,
        "userRole":   user_role or "",
        "durationS":  duration_s,
        "userId":     user_id or "",
        "userEmail":  user_email or "",
    })


def get_audit_log(limit: int = 200) -> list[dict]:
    db   = get_db()
    docs = (
        db.collection(_AUDIT)
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    results = []
    for doc in docs:
        d = _doc_to_dict(doc)
        # Normalise key names to match old SQLite schema for template compat
        d.setdefault("user_role",  d.pop("userRole",  ""))
        d.setdefault("duration_s", d.pop("durationS", None))
        d.setdefault("user_id",    d.pop("userId",    ""))
        results.append(d)
    return results


def get_recent_logs(limit: int = 10) -> list[dict]:
    return get_audit_log(limit)


def get_audit_stats() -> dict:
    db   = get_db()
    docs = db.collection(_AUDIT).stream()
    total = success = errors = 0
    for doc in docs:
        d = doc.to_dict() or {}
        total   += 1
        s        = d.get("status", "")
        if s == "success":
            success += 1
        elif s in ("error", "failed"):
            errors  += 1
    return {"total": total, "success": success, "errors": errors}


# ── Approval queue ───────────────────────────────────────────

def add_approval(
    parsed_request: dict,
    risk_result: dict,
    user_role: str,
    user_id: str | None = None,
    user_email: str | None = None,
) -> str:
    """Add a pending approval. Returns the Firestore document ID (str)."""
    db  = get_db()
    ref = db.collection(_APPROVALS).add({
        "parsedRequest": parsed_request,
        "riskResult":    risk_result,
        "userId":        user_id    or "",
        "userEmail":     user_email or "",
        "userRole":      user_role,
        "status":        "pending",
        "timestamp":     _now(),
        "resolvedAt":    None,
        "resolvedBy":    None,
        "rejectReason":  None,
    })
    # ref is (update_time, DocumentReference)
    doc_ref = ref[1] if isinstance(ref, tuple) else ref
    return doc_ref.id


def get_pending_approvals() -> list[dict]:
    db   = get_db()
    docs = (
        db.collection(_APPROVALS)
        .where(filter=FieldFilter("status", "==", "pending"))
        .stream()
    )
    results = []
    for doc in docs:
        d = _doc_to_dict(doc)
        d.setdefault("parsed_request", d.pop("parsedRequest", {}))
        d.setdefault("risk_result",    d.pop("riskResult",    {}))
        d.setdefault("user_role",      d.pop("userRole",      ""))
        d.setdefault("user_email",     d.pop("userEmail",     ""))
        d.setdefault("user_id",        d.pop("userId",        ""))
        results.append(d)
    results.sort(key=lambda x: x.get("timestamp", ""))
    return results


def get_all_approvals(limit: int = 50) -> list[dict]:
    db   = get_db()
    docs = (
        db.collection(_APPROVALS)
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    results = []
    for doc in docs:
        d = _doc_to_dict(doc)
        d.setdefault("parsed_request", d.pop("parsedRequest", {}))
        d.setdefault("risk_result",    d.pop("riskResult",    {}))
        d.setdefault("user_role",      d.pop("userRole",      ""))
        d.setdefault("user_email",     d.pop("userEmail",     ""))
        d.setdefault("user_id",        d.pop("userId",        ""))
        d.setdefault("resolved_at",    d.pop("resolvedAt",    None))
        d.setdefault("resolved_by",    d.pop("resolvedBy",    None))
        d.setdefault("reject_reason",  d.pop("rejectReason",  None))
        results.append(d)
    return results


def get_approvals_by_status(status: str | None = None, user_id: str | None = None, limit: int = 100) -> list[dict]:
    """Return approvals filtered by status and/or user_id. status=None returns all."""
    db    = get_db()
    query = db.collection(_APPROVALS)
    if status:
        query = query.where(filter=FieldFilter("status", "==", status))
    if user_id:
        query = query.where(filter=FieldFilter("userId", "==", user_id))
    docs = query.stream()
    results = []
    for doc in docs:
        d = _doc_to_dict(doc)
        d.setdefault("parsed_request", d.pop("parsedRequest", {}))
        d.setdefault("risk_result",    d.pop("riskResult",    {}))
        d.setdefault("user_role",      d.pop("userRole",      ""))
        d.setdefault("user_email",     d.pop("userEmail",     ""))
        d.setdefault("user_id",        d.pop("userId",        ""))
        d.setdefault("resolved_at",    d.pop("resolvedAt",    None))
        d.setdefault("resolved_by",    d.pop("resolvedBy",    None))
        d.setdefault("reject_reason",  d.pop("rejectReason",  None))
        d.setdefault("admin_remark",   d.pop("adminRemark",   None))
        d.setdefault("updated_at",     d.pop("updatedAt",     None))
        results.append(d)
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results[:limit]


def approve_approval(doc_id: str, approver: str) -> dict | None:
    """Mark as approved. Returns the full entry (for execution) or None."""
    db  = get_db()
    ref = db.collection(_APPROVALS).document(doc_id)
    doc = ref.get()
    if not doc.exists:
        return None
    d = doc.to_dict() or {}
    if d.get("status") != "pending":
        return None
    ref.update({
        "status":     "approved",
        "resolvedAt": _now(),
        "updatedAt":  _now(),
        "resolvedBy": approver,
    })
    d["id"]             = doc_id
    d["parsed_request"] = d.pop("parsedRequest", {})
    d["risk_result"]    = d.pop("riskResult",    {})
    d["user_role"]      = d.pop("userRole",      "")
    return d


def reject_approval(doc_id: str, reason: str, approver: str) -> None:
    db  = get_db()
    ref = db.collection(_APPROVALS).document(doc_id)
    ref.update({
        "status":       "rejected",
        "resolvedAt":   _now(),
        "updatedAt":    _now(),
        "resolvedBy":   approver,
        "rejectReason": reason,
        "adminRemark":  reason,
    })


# ── Resource inventory ───────────────────────────────────────

def record_resource(
    resource_type: str,
    name: str,
    region: str,
    details: dict,
    user_role: str | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
) -> str:
    db  = get_db()
    ref = db.collection(_RESOURCES).add({
        "timestamp":      _now(),
        "resourceType":   resource_type,
        "resourceName":   name,
        "region":         region or "global",
        "details":        details or {},
        "status":         "active",
        "userId":         user_id    or "",
        "userEmail":      user_email or "",
        "createdByRole":  user_role  or "",
    })
    doc_ref = ref[1] if isinstance(ref, tuple) else ref
    return doc_ref.id


def delete_resource_record(name: str) -> None:
    """Soft-delete: set status = 'deleted'."""
    db   = get_db()
    docs = (
        db.collection(_RESOURCES)
        .where(filter=FieldFilter("resourceName", "==", name))
        .where(filter=FieldFilter("status", "==", "active"))
        .stream()
    )
    for doc in docs:
        doc.reference.update({"status": "deleted"})


def get_resources(status: str = "active", user_id: str | None = None) -> list[dict]:
    db    = get_db()
    query = db.collection(_RESOURCES).where(
        filter=FieldFilter("status", "==", status)
    )
    if user_id:
        query = query.where(filter=FieldFilter("userId", "==", user_id))
    docs = query.stream()
    results = []
    for doc in docs:
        d = _doc_to_dict(doc)
        d.setdefault("resource_type",   d.pop("resourceType",  ""))
        d.setdefault("resource_name",   d.pop("resourceName",  ""))
        d.setdefault("created_by_role", d.pop("createdByRole", ""))
        d.setdefault("user_id",         d.pop("userId",        ""))
        d.setdefault("user_email",      d.pop("userEmail",     ""))
        results.append(d)
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results


def count_resources(
    resource_type: str,
    user_id: str | None = None,
    created_by_role: str | None = None,
) -> int:
    """Count active resources of a given type. Used by the policy engine."""
    db    = get_db()
    query = (
        db.collection(_RESOURCES)
        .where(filter=FieldFilter("resourceType", "==", resource_type))
        .where(filter=FieldFilter("status", "==", "active"))
    )
    if user_id:
        query = query.where(filter=FieldFilter("userId", "==", user_id))
    return sum(1 for _ in query.stream())


# ── Budget tracking ──────────────────────────────────────────

def log_budget(
    action: str,
    estimated_usd: float,
    user_role: str | None = None,
    user_id: str | None = None,
) -> None:
    db = get_db()
    db.collection(_BUDGET).add({
        "timestamp":    _now(),
        "action":       action,
        "estimatedUsd": estimated_usd,
        "userRole":     user_role or "",
        "userId":       user_id   or "",
    })


def get_monthly_spend() -> float:
    db   = get_db()
    now  = datetime.now(timezone.utc)
    # First day of current month as ISO string prefix for simple string comparison
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    docs = (
        db.collection(_BUDGET)
        .where(filter=FieldFilter("timestamp", ">=", month_start))
        .stream()
    )
    return sum((doc.to_dict() or {}).get("estimatedUsd", 0.0) for doc in docs)


# ── User management ──────────────────────────────────────────

def get_user_by_uid(uid: str) -> dict | None:
    db  = get_db()
    doc = db.collection(_USERS).document(uid).get()
    if not doc.exists:
        return None
    d = _doc_to_dict(doc)
    d.setdefault("displayName", d.pop("displayName", ""))
    return d


def create_or_update_user(
    uid: str,
    email: str,
    display_name: str = "",
    role: str | None = None,
) -> dict:
    """
    Upsert a user document.
    - New users default to role 'user'.
    - Existing users' roles are NEVER downgraded by this function.
      Role promotion must be done manually in Firestore.
    """
    db  = get_db()
    ref = db.collection(_USERS).document(uid)
    doc = ref.get()

    if doc.exists:
        existing = doc.to_dict() or {}
        # Update mutable fields; never overwrite role with a lower value
        ref.update({
            "email":       email,
            "displayName": display_name,
        })
        existing["id"] = uid
        return existing
    else:
        assigned_role = "admin" if email in ADMIN_EMAILS else (role or "user")
        data = {
            "email":       email,
            "displayName": display_name,
            "role":        assigned_role,
            "createdAt":   _now(),
        }
        ref.set(data)
        data["id"] = uid
        return data


def get_all_users() -> list[dict]:
    db   = get_db()
    docs = db.collection(_USERS).order_by("createdAt").stream()
    results = []
    for doc in docs:
        d = _doc_to_dict(doc)
        results.append(d)
    return results


def get_user_resource_counts() -> dict[str, int]:
    """Return {userId: active_resource_count} for the admin users table."""
    db   = get_db()
    docs = (
        db.collection(_RESOURCES)
        .where(filter=FieldFilter("status", "==", "active"))
        .stream()
    )
    counts: dict[str, int] = {}
    for doc in docs:
        uid = (doc.to_dict() or {}).get("userId", "")
        if uid:
            counts[uid] = counts.get(uid, 0) + 1
    return counts
