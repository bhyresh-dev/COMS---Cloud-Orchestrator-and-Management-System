"""
COMS — Security Test Suite
Run: python tests/security_test.py

Tests (no running server or real Firebase credentials required):
  1. Unauthenticated requests return 401
  2. User-role token on admin endpoints returns 403
  3. Policy limit enforcement rejects requests over the limit
  4. Concurrency: 50 concurrent bucket creation requests respect the policy limit
     and produce no duplicate resource names

Results are printed as a pass/fail summary table.
"""
from __future__ import annotations

import os
import sys
import threading
import concurrent.futures
import time

# ── Path & env setup (before any project imports) ────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APP_ENV",          "development")
os.environ.setdefault("AWS_ENDPOINT_URL", "http://localhost:4566")

# ── Mock Firebase before importing server ────────────────────
from unittest.mock import patch, MagicMock, call

_fake_app = MagicMock()
_fake_db  = MagicMock()

firebase_init_patch = patch.multiple(
    "utils.firebase_init",
    _app=_fake_app,
    _db=_fake_db,
    get_app=lambda: _fake_app,
    get_db=lambda: _fake_db,
)
firebase_init_patch.start()

from fastapi.testclient import TestClient  # noqa: E402
import server  # noqa: E402

client = TestClient(server.app, raise_server_exceptions=False)

# ── Helpers ──────────────────────────────────────────────────

_USER_PROFILE  = {"uid": "test-user-uid",  "email": "user@example.com",  "name": "Test User",  "role": "user"}
_ADMIN_PROFILE = {"uid": "test-admin-uid", "email": "admin@example.com", "name": "Test Admin", "role": "admin"}

def _auth(profile: dict) -> dict:
    return {"Authorization": f"Bearer mock-token-{profile['uid']}"}

# ── Test runner ───────────────────────────────────────────────

_results: list[tuple[str, bool, str]] = []

def _run(name: str, fn):
    try:
        fn()
        _results.append((name, True, ""))
    except AssertionError as exc:
        _results.append((name, False, str(exc)))
    except Exception as exc:
        _results.append((name, False, f"UNEXPECTED: {exc}"))


# ═════════════════════════════════════════════════════════════
# TEST 1 — Unauthenticated requests → 401
# ═════════════════════════════════════════════════════════════

def test_401_no_auth():
    protected_endpoints = [
        ("GET",    "/api/buckets"),
        ("GET",    "/api/resources"),
        ("GET",    "/api/approvals"),
        ("GET",    "/api/audit"),
        ("POST",   "/api/nlp/process"),
        ("GET",    "/api/admin/users"),
        ("GET",    "/api/admin/buckets"),
        ("GET",    "/api/admin/audit"),
        ("GET",    "/api/admin/stats"),
    ]
    for method, path in protected_endpoints:
        resp = client.request(method, path)
        assert resp.status_code == 401, (
            f"{method} {path} returned {resp.status_code}, expected 401"
        )

_run("Unauthenticated requests return 401", test_401_no_auth)


# ═════════════════════════════════════════════════════════════
# TEST 2 — User token on admin endpoints → 403
# ═════════════════════════════════════════════════════════════

def test_403_user_on_admin():
    admin_endpoints = [
        ("GET",  "/api/admin/users"),
        ("GET",  "/api/admin/buckets"),
        ("GET",  "/api/admin/audit"),
        ("GET",  "/api/admin/stats"),
        ("POST", "/api/approvals/fake-id/approve"),
        ("POST", "/api/approvals/fake-id/reject"),
    ]
    # Patch at the location where server.py imported verify_token
    with patch("server.verify_token", return_value=_USER_PROFILE):
        for method, path in admin_endpoints:
            kwargs = {}
            if method == "POST" and "reject" in path:
                kwargs["json"] = {"reason": "test"}
            resp = client.request(method, path, headers=_auth(_USER_PROFILE), **kwargs)
            assert resp.status_code == 403, (
                f"{method} {path} returned {resp.status_code}, expected 403"
            )

_run("User token on admin endpoints returns 403", test_403_user_on_admin)


# ═════════════════════════════════════════════════════════════
# TEST 3 — Policy limit enforcement
# ═════════════════════════════════════════════════════════════

def test_policy_limit_enforcement():
    """
    When the user is already at the S3 bucket limit (10), the NLP pipeline
    must reject the request with a 'denied' status — no AWS call is made.
    """
    from agents.policy_engine import validate_request

    # Simulate a user AT the limit
    # Patch at the module where it was imported (policy_engine uses its local ref)
    with patch("agents.policy_engine.count_resources", return_value=10):
        result = validate_request(
            parsed_request={
                "intent":     "create_s3_bucket",
                "service":    "s3",
                "action":     "create",
                "parameters": {"bucket_name": "test-bucket", "region": "ap-south-1"},
                "user_context": {},
            },
            user_role="user",
            user_id="test-user-uid",
        )

    assert not result["approved"], "Policy should DENY when at limit"
    assert any("limit" in v.lower() for v in result["violations"]), (
        f"Expected a limit violation, got: {result['violations']}"
    )

    # Simulate a user one BELOW the limit — should be approved
    with patch("agents.policy_engine.count_resources", return_value=9):
        result_ok = validate_request(
            parsed_request={
                "intent":     "create_s3_bucket",
                "service":    "s3",
                "action":     "create",
                "parameters": {"bucket_name": "test-bucket", "region": "ap-south-1"},
                "user_context": {},
            },
            user_role="user",
            user_id="test-user-uid",
        )

    assert result_ok["approved"], (
        f"Policy should APPROVE below limit, got violations: {result_ok['violations']}"
    )

_run("Policy limit enforcement rejects requests over the limit", test_policy_limit_enforcement)


# ═════════════════════════════════════════════════════════════
# TEST 4 — Concurrency: 50 requests, no duplicates, limit respected
# ═════════════════════════════════════════════════════════════

def test_concurrency_no_duplicates():
    """
    Fire 50 concurrent NLP requests, each requesting a uniquely named bucket.

    Expectations:
      - The number of successfully created buckets must not exceed the policy
        limit (10 for S3).
      - No duplicate resource names may appear in the created set.

    A thread-safe counter simulates the Firestore resource count so that
    the policy engine sees the correct state as resources are created.
    """
    POLICY_LIMIT   = 10
    NUM_REQUESTS   = 50
    created_names: list[str] = []
    names_lock = threading.Lock()
    counter    = 0
    counter_lock = threading.Lock()

    def mock_count_resources(resource_type, user_id=None, created_by_role=None):
        with counter_lock:
            return counter

    def mock_record_resource(resource_type, name, region, details,
                              user_role=None, user_id=None, user_email=None):
        nonlocal counter
        with names_lock:
            created_names.append(name)
        with counter_lock:
            counter += 1
        return f"mock-doc-{name}"

    def mock_execute_request(parsed_request, user_role=None, user_id=None):
        params = parsed_request.get("parameters", {})
        name   = params.get("bucket_name", f"bucket-{time.time()}")
        mock_record_resource("S3 Bucket", name, "ap-south-1", {}, user_role, user_id)
        return {
            "success":  True,
            "message":  f"Bucket '{name}' created.",
            "resource": {"type": "S3 Bucket", "name": name},
        }

    def make_nlp_parse(index: int):
        bucket_name = f"concurrent-test-bucket-{index:03d}"
        return {
            "success": True,
            "data": {
                "intent":     "create_s3_bucket",
                "service":    "s3",
                "action":     "create",
                "parameters": {"bucket_name": bucket_name, "region": "ap-south-1"},
                "user_context": {},
                "confidence": 0.99,
                "missing_fields": [],
                "clarification_needed": False,
                "clarification_question": None,
            },
            "raw": "{}",
        }

    def make_request(index: int):
        bucket_name = f"concurrent-test-bucket-{index:03d}"
        return client.post(
            "/api/nlp/process",
            json={"message": f"create a private s3 bucket named {bucket_name}"},
            headers=_auth(_USER_PROFILE),
        )

    with patch("server.verify_token",               return_value=_USER_PROFILE), \
         patch("agents.nlp_agent.parse_request",    side_effect=make_nlp_parse), \
         patch("agents.policy_engine.count_resources", side_effect=mock_count_resources), \
         patch("agents.executor.record_resource",    side_effect=mock_record_resource), \
         patch("agents.executor.execute_request",    side_effect=mock_execute_request), \
         patch("server.log_action"), \
         patch("agents.executor.log_action"), \
         patch("agents.executor.log_budget"):

        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_REQUESTS) as pool:
            futures = [pool.submit(make_request, i) for i in range(NUM_REQUESTS)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    successes = [r for r in responses if r.status_code == 200]
    denials   = [r for r in responses if r.status_code in (200, 403)]

    # Check: no more than policy limit were created
    assert len(created_names) <= POLICY_LIMIT, (
        f"Expected at most {POLICY_LIMIT} creations, got {len(created_names)}"
    )

    # Check: no duplicate names
    assert len(created_names) == len(set(created_names)), (
        f"Duplicate bucket names detected: "
        f"{[n for n in created_names if created_names.count(n) > 1]}"
    )

_run("Concurrency: 50 requests respect policy limit and produce no duplicates",
     test_concurrency_no_duplicates)


# ═════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════

def _print_summary():
    width = 70
    print()
    print("=" * width)
    print(f"  COMS Security Test Suite")
    print("=" * width)

    passed = sum(1 for _, ok, _ in _results if ok)
    total  = len(_results)

    for i, (name, ok, detail) in enumerate(_results, 1):
        status = "PASS" if ok else "FAIL"
        marker = "+" if ok else "-"
        print(f"  [{marker}] Test {i}: {status}")
        print(f"       {name}")
        if not ok and detail:
            for line in detail.splitlines():
                print(f"       >> {line}")
        print()

    print("-" * width)
    print(f"  Results: {passed}/{total} passed")
    print("=" * width)
    print()

    return passed == total


firebase_init_patch.stop()

if __name__ == "__main__":
    all_passed = _print_summary()
    sys.exit(0 if all_passed else 1)
