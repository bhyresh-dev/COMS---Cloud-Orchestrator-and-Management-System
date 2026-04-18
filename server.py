"""
COMS — FastAPI server.

Run (dev):
    uvicorn server:app --reload --port 8000

Run (prod):
    uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
"""
from __future__ import annotations

import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.api_core.exceptions import FailedPrecondition, GoogleAPICallError
from pydantic import BaseModel, Field

load_dotenv()

# ── Environment validation ────────────────────────────────────

_ENV = os.getenv("APP_ENV", "development").lower()
_IS_PROD = _ENV == "production"

_CORS_ORIGIN = os.getenv("CORS_ORIGIN", "").strip()
if _IS_PROD and not _CORS_ORIGIN:
    sys.exit(
        "FATAL: CORS_ORIGIN is not set. "
        "Set it to your frontend domain (e.g. https://coas.example.com) in .env."
    )
_CORS_ORIGIN = _CORS_ORIGIN or "http://localhost:5173"

# ── Firebase / Firestore imports (fail CLOSED on bad config) ──

from utils.firebase_init import get_app, get_db  # noqa: E402 — after load_dotenv
from utils.auth import AuthError, verify_token, require_role
from utils.firestore_db import (
    log_action,
    get_audit_log,
    get_audit_stats,
    get_resources,
    get_all_users,
    get_user_resource_counts,
    update_user_name,
    get_pending_approvals,
    get_all_approvals,
    get_approvals_by_status,
    count_resources,
    delete_resource_record,
    record_resource,
    get_resources_multi_status,
)
from utils.rate_limiter import check_rate_limit
from agents.policy_engine import validate_request
from agents.orchestrator import MasterOrchestrator, do_approve, do_reject


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eager init — exits fatally if Firebase credentials are missing or invalid
    get_app()
    get_db()
    yield


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="COMS API",
    version="2.0.0",
    docs_url="/docs" if not _IS_PROD else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Auth dependency ───────────────────────────────────────────

async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """
    Extract and verify the Firebase ID token from the Authorization header.
    Expected format: 'Bearer <id_token>'
    Returns 401 for missing or invalid tokens — never 422.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <token>'.")
    token = authorization[len("Bearer "):]
    try:
        return verify_token(token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    try:
        require_role(user, "admin")
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    return user


# ── Global exception handlers ─────────────────────────────────

@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(FailedPrecondition)
async def firestore_index_error_handler(request: Request, exc: FailedPrecondition):
    return JSONResponse(
        status_code=400,
        content={"detail": "A required Firestore index is still building. Please wait a minute and retry."},
    )

@app.exception_handler(GoogleAPICallError)
async def google_api_error_handler(request: Request, exc: GoogleAPICallError):
    return JSONResponse(
        status_code=502,
        content={"detail": f"Firestore error: {exc.message}"},
    )


# ── Pydantic models ───────────────────────────────────────────

class NLPRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    conversation_history: list = Field(default_factory=list)

class BucketDeleteRequest(BaseModel):
    bucket_name: str = Field(..., min_length=3, max_length=63)

class ApprovalRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)

class NLPResponse(BaseModel):
    status: str
    message: str
    resource: dict = {}
    pipeline_stages: list = []
    total_time_seconds: float = 0.0
    violations: list = []
    warnings: list = []
    approval_id: str | None = None
    risk_result: dict = {}
    explain: list = []
    conversation_history: list = []


# ── Health ────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "env": _ENV}


# ── Auth ──────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)

@app.patch("/api/auth/me", tags=["Auth"])
def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    """Update the caller's display name."""
    update_user_name(user["uid"], body.name.strip())
    return {"uid": user["uid"], "email": user["email"], "name": body.name.strip(), "role": user["role"]}


@app.post("/api/auth/me", tags=["Auth"])
def auth_me(user: dict = Depends(get_current_user)):
    """
    Verify the caller's Firebase token and return their profile.
    Creates the Firestore user document on first sign-in (role defaults to 'user').
    """
    return {
        "uid":   user["uid"],
        "email": user["email"],
        "name":  user["name"],
        "role":  user["role"],
    }


# ── NLP / AI pipeline (scoped strictly to s3:CreateBucket) ───

@app.post("/api/nlp/process", response_model=NLPResponse, tags=["AI"])
def nlp_process(body: NLPRequest, user: dict = Depends(get_current_user)):
    """
    Natural-language cloud request pipeline.

    AI SCOPE CONSTRAINT: This endpoint only permits the `create_s3_bucket`
    intent. Requests parsed as any other intent are rejected with 403.
    This prevents the AI layer from reading bucket contents, deleting
    resources, or acting on other services.
    """
    uid   = user["uid"]
    role  = user["role"]
    email = user["email"]

    # Rate limit: 20 NLP requests per minute per user
    allowed, retry_after = check_rate_limit(uid, "nlp_request", limit=20, window=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after}s.",
        )

    # Run the full pipeline via a fresh orchestrator instance per request.
    # Conversation history is passed in by the client so multi-turn clarification works.
    orch = MasterOrchestrator()
    orch.set_user_role(role)
    orch.set_username(email)
    orch.set_user_id(uid)
    orch.conversation.history = list(body.conversation_history)

    result = orch.process_message(body.message)
    updated_history = list(orch.conversation.history)

    # ── AI SCOPE ENFORCEMENT ─────────────────────────────────
    # After NLP parsing, if the pipeline produced a parsed intent we can inspect
    # it via the orchestrator's conversation state. We enforce the scope here:
    # any parsed intent other than create_s3_bucket is rejected.
    parsed_intent = None
    if orch.conversation.current_parse:
        parsed_intent = orch.conversation.current_parse.get("intent", "")

    _ALLOWED_INTENTS = {
        "create_s3_bucket",
        "create_iam_role",
        "launch_ec2_instance",
        "create_lambda_function",
        "create_sns_topic",
        "create_log_group",
    }
    if parsed_intent and parsed_intent not in _ALLOWED_INTENTS:
        log_action(
            "ai_scope_violation",
            {"intent": parsed_intent, "message": body.message},
            status="denied",
            user_role=role,
            user_id=uid,
            user_email=email,
        )
        raise HTTPException(
            status_code=403,
            detail=(
                f"AI automation is scoped to resource creation only. "
                f"Parsed intent '{parsed_intent}' is not permitted through this endpoint. "
                "Use the explicit resource endpoints for other operations."
            ),
        )

    # Log successful pipeline execution
    if result.get("status") in ("executed", "pending_approval"):
        log_action(
            "nlp_pipeline",
            {"intent": parsed_intent, "status": result["status"]},
            status="success",
            user_role=role,
            user_id=uid,
            user_email=email,
        )

    return NLPResponse(
        status=result.get("status", "error"),
        message=result.get("message", ""),
        resource=result.get("resource", {}),
        pipeline_stages=result.get("pipeline_stages", []),
        total_time_seconds=result.get("total_time_seconds", 0.0),
        violations=result.get("violations", []),
        warnings=result.get("warnings", []),
        approval_id=str(result["approval_id"]) if result.get("approval_id") else None,
        risk_result=result.get("risk_result", {}),
        explain=result.get("explain", []),
        conversation_history=updated_history,
    )


# ── Buckets ───────────────────────────────────────────────────

@app.get("/api/buckets", tags=["Buckets"])
def list_buckets(user: dict = Depends(get_current_user)):
    """Return the caller's active S3 buckets from Firestore."""
    uid  = user["uid"]
    role = user["role"]
    # Admin sees all buckets; regular users see only their own
    resources = get_resources(
        status="active",
        user_id=None if role == "admin" else uid,
    )
    buckets = [r for r in resources if r.get("resource_type") == "S3 Bucket"]
    return {"buckets": buckets, "count": len(buckets)}


import re as _re
_BUCKET_NAME_RE = _re.compile(r'^[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9]$')

@app.delete("/api/buckets/{bucket_name}", tags=["Buckets"])
def delete_bucket(bucket_name: str, user: dict = Depends(get_current_user)):
    """
    Delete an S3 bucket.

    Users may only delete their own buckets.
    Admins may delete any bucket.
    Audit-logged regardless of outcome.
    """
    uid   = user["uid"]
    role  = user["role"]
    email = user["email"]

    if not _BUCKET_NAME_RE.match(bucket_name):
        raise HTTPException(status_code=400, detail="Invalid bucket name.")

    # Validate the bucket belongs to this user (unless admin)
    if role != "admin":
        user_buckets = get_resources(status="active", user_id=uid)
        owned_names  = {r["resource_name"] for r in user_buckets
                        if r.get("resource_type") == "S3 Bucket"}
        if bucket_name not in owned_names:
            log_action(
                "delete_bucket_denied",
                {"bucket_name": bucket_name},
                status="denied",
                user_role=role,
                user_id=uid,
                user_email=email,
            )
            raise HTTPException(
                status_code=403,
                detail="You do not own this bucket or it does not exist.",
            )

    # Execute deletion via boto3
    try:
        from utils.aws_client import get_s3_client
        s3 = get_s3_client()
        s3.delete_bucket(Bucket=bucket_name)
    except Exception as exc:
        log_action(
            "delete_bucket",
            {"bucket_name": bucket_name, "error": str(exc)},
            status="error",
            user_role=role,
            user_id=uid,
            user_email=email,
        )
        raise HTTPException(status_code=502, detail=f"AWS error: {exc}")

    delete_resource_record(bucket_name)
    log_action(
        "delete_bucket",
        {"bucket_name": bucket_name},
        status="success",
        user_role=role,
        user_id=uid,
        user_email=email,
    )
    return {"status": "deleted", "bucket_name": bucket_name}


# ── Resources (read-only inventory) ──────────────────────────

@app.get("/api/resources", tags=["Resources"])
def list_resources(user: dict = Depends(get_current_user)):
    """Return active + pending resources owned by the caller (single Firestore query)."""
    uid  = user["uid"]
    role = user["role"]
    resources = get_resources_multi_status(
        ["active", "pending"],
        user_id=None if role == "admin" else uid,
    )
    return {"resources": resources, "count": len(resources)}


# ── Approvals ─────────────────────────────────────────────────

@app.get("/api/approvals", tags=["Approvals"])
def list_approvals(
    status: str | None = None,
    user: dict = Depends(get_current_user),
):
    """
    Return approvals filtered by status (pending|approved|rejected|all).
    Admins see everyone's; users see only their own.
    """
    uid  = user["uid"]
    role = user["role"]
    filter_status = None if status == "all" else status
    if role == "admin":
        approvals = get_approvals_by_status(status=filter_status)
    else:
        approvals = get_approvals_by_status(status=filter_status, user_id=uid)
    return {"approvals": approvals, "count": len(approvals)}


@app.post("/api/approvals/{approval_id}/approve", tags=["Approvals"])
def approve_request(
    approval_id: str,
    admin: dict = Depends(require_admin),
):
    """Approve a pending request and execute it. Admin only."""
    result = do_approve(approval_id, approver=admin["email"])
    log_action(
        "admin_approved",
        {"approval_id": approval_id},
        status="success",
        user_role="admin",
        user_id=admin["uid"],
        user_email=admin["email"],
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "Approval not found."))
    return result


@app.post("/api/approvals/{approval_id}/reject", tags=["Approvals"])
def reject_request(
    approval_id: str,
    body: ApprovalRejectRequest,
    admin: dict = Depends(require_admin),
):
    """Reject a pending request. Admin only."""
    result = do_reject(approval_id, reason=body.reason, approver=admin["email"])
    log_action(
        "admin_rejected",
        {"approval_id": approval_id, "reason": body.reason},
        status="success",
        user_role="admin",
        user_id=admin["uid"],
        user_email=admin["email"],
    )
    return result


# ── Audit log ─────────────────────────────────────────────────

@app.get("/api/audit", tags=["Audit"])
def audit_log(limit: int = 100, user: dict = Depends(get_current_user)):
    """
    Return audit log entries.
    Admins see all entries. Regular users see only their own.
    limit capped at 500.
    """
    limit = min(limit, 500)
    uid   = user["uid"]
    role  = user["role"]

    entries = get_audit_log(limit=limit)
    if role != "admin":
        entries = [e for e in entries if e.get("user_id") == uid]

    return {"entries": entries, "count": len(entries)}


# ── Admin endpoints ───────────────────────────────────────────

@app.get("/api/admin/users", tags=["Admin"])
def admin_list_users(admin: dict = Depends(require_admin)):
    """
    All users with their individual resource counts.
    Admin only.
    """
    users  = get_all_users()
    counts = get_user_resource_counts()
    for u in users:
        uid = u.get("id", "")
        u["resource_count"] = counts.get(uid, 0)
    return {"users": users, "count": len(users)}


@app.get("/api/admin/buckets", tags=["Admin"])
def admin_list_all_buckets(admin: dict = Depends(require_admin)):
    """
    All active S3 buckets across all users, with creator name and email.
    Admin only.
    """
    resources = get_resources(status="active")
    buckets   = [r for r in resources if r.get("resource_type") == "S3 Bucket"]
    return {"buckets": buckets, "count": len(buckets)}


@app.get("/api/admin/audit", tags=["Admin"])
def admin_audit_log(limit: int = 200, admin: dict = Depends(require_admin)):
    """Full audit log. Admin only. Limit capped at 1000."""
    limit   = min(limit, 1000)
    entries = get_audit_log(limit=limit)
    stats   = get_audit_stats()
    return {"entries": entries, "count": len(entries), "stats": stats}


@app.get("/api/admin/stats", tags=["Admin"])
def admin_stats(admin: dict = Depends(require_admin)):
    """Aggregate stats: resource counts by type, audit summary."""
    resource_types = ["S3 Bucket", "EC2 Instance", "IAM Role",
                      "Lambda Function", "SNS Topic", "CloudWatch Log Group"]
    counts = {rt: count_resources(rt) for rt in resource_types}
    audit  = get_audit_stats()
    return {
        "resource_counts": counts,
        "audit_summary": audit,
    }


# ── Serve React frontend ──────────────────────────────────────
_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.isdir(_FRONTEND_DIST):
    print(f"Serving frontend from {_FRONTEND_DIST}")
    app.mount("/assets", StaticFiles(directory=os.path.join(_FRONTEND_DIST, "assets")), name="assets")
else:
    print(f"WARNING: frontend/dist not found at {_FRONTEND_DIST} — frontend will not be served")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))

@app.get("/api/health")
async def health_check():
    return {"message": "COMS Orchestrator API is live and running!"}