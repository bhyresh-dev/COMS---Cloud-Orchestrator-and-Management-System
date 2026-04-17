"""
COMS — Test Suite
Covers: auth, RBAC, policy engine, rate limiter, DB thread safety, stress.

Run:
    cd COAS
    python -m pytest tests/test_suite.py -v
"""
import pytest
import threading
import time
import sys
import os

# Make sure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import (
    init_db, create_user, verify_password, get_all_users,
    log_action, get_audit_log, count_resources,
)
from utils.auth import login, ROLE_RANK
from utils.rate_limiter import check_rate_limit
from agents.policy_engine import validate_request


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Ensure DB is initialised before any test runs."""
    init_db()


@pytest.fixture()
def test_user(tmp_path):
    """Create a throwaway developer account for isolation."""
    ts = str(int(time.time() * 1000))
    username = f"testuser_{ts}"
    password = "TestPass@99"
    user = create_user(username, password, "developer")
    yield {"username": username, "password": password, **user}


@pytest.fixture()
def admin_user():
    """Use the seeded admin account."""
    return {"username": "admin", "password": "Admin@123"}


# ════════════════════════════════════════════════════════════
# FUNCTIONAL TESTS
# ════════════════════════════════════════════════════════════

class TestAuth:
    def test_login_success(self, test_user):
        result = login(test_user["username"], test_user["password"])
        assert result is not None
        assert result["username"] == test_user["username"]
        assert result["role"] == "developer"

    def test_login_wrong_password(self, test_user):
        result = login(test_user["username"], "WrongPass@00")
        assert result is None

    def test_login_nonexistent_user(self):
        result = login("ghost_user_xyz", "any_password")
        assert result is None

    def test_login_empty_credentials(self):
        assert login("", "") is None
        assert login("admin", "") is None
        assert login("", "Admin@123") is None

    def test_login_admin_success(self, admin_user):
        result = login(admin_user["username"], admin_user["password"])
        assert result is not None
        assert result["role"] == "admin"

    def test_role_rank_ordering(self):
        assert ROLE_RANK["developer"] < ROLE_RANK["dev-lead"] < ROLE_RANK["admin"]


class TestRBAC:
    def test_developer_can_request_s3(self):
        parsed = {"intent": "create_s3_bucket", "service": "s3", "parameters": {"bucket_name": "test-bucket-abc"}}
        result = validate_request(parsed, "developer")
        # Should pass RBAC (may fail on other rules, but not RBAC)
        violations = [v for v in result["violations"] if "cannot request" in v]
        assert not violations, f"Unexpected RBAC violation: {violations}"

    def test_developer_cannot_request_iam(self):
        parsed = {"intent": "create_iam_role", "service": "iam", "parameters": {}}
        result = validate_request(parsed, "developer")
        assert not result["approved"]
        assert any("cannot request" in v for v in result["violations"])

    def test_admin_can_request_iam(self):
        parsed = {"intent": "create_iam_role", "service": "iam", "parameters": {"role_name": "test-role"}}
        result = validate_request(parsed, "admin")
        rbac_violations = [v for v in result["violations"] if "cannot request" in v]
        assert not rbac_violations

    def test_unknown_role_denied(self):
        parsed = {"intent": "list_s3_buckets", "service": "s3", "parameters": {}}
        result = validate_request(parsed, "hacker_role")
        assert not result["approved"]
        assert any("Unknown role" in v for v in result["violations"])


class TestPolicyEngine:
    def test_invalid_bucket_name_rejected(self):
        parsed = {
            "intent": "create_s3_bucket", "service": "s3",
            "parameters": {"bucket_name": "INVALID_BUCKET_NAME!!"},
        }
        result = validate_request(parsed, "admin")
        assert not result["approved"]
        assert any("Invalid bucket name" in v for v in result["violations"])

    def test_valid_bucket_name_passes(self):
        parsed = {
            "intent": "list_s3_buckets", "service": "s3",
            "parameters": {"bucket_name": "valid-bucket-name-123"},
        }
        result = validate_request(parsed, "admin")
        name_violations = [v for v in result["violations"] if "Invalid bucket name" in v]
        assert not name_violations

    def test_disallowed_region_rejected(self):
        parsed = {
            "intent": "list_s3_buckets", "service": "s3",
            "parameters": {"region": "us-gov-east-1"},
        }
        result = validate_request(parsed, "admin")
        assert not result["approved"]
        assert any("not permitted" in v for v in result["violations"])

    def test_allowed_region_passes(self):
        parsed = {
            "intent": "list_s3_buckets", "service": "s3",
            "parameters": {"region": "ap-south-1"},
        }
        result = validate_request(parsed, "admin")
        region_violations = [v for v in result["violations"] if "not permitted" in v]
        assert not region_violations

    def test_disallowed_instance_type_rejected(self):
        parsed = {
            "intent": "launch_ec2_instance", "service": "ec2",
            "parameters": {"instance_type": "p4d.24xlarge", "region": "ap-south-1"},
        }
        result = validate_request(parsed, "admin")
        assert not result["approved"]
        assert any("not allowed" in v for v in result["violations"])

    def test_allowed_instance_type_passes(self):
        parsed = {
            "intent": "launch_ec2_instance", "service": "ec2",
            "parameters": {"instance_type": "t2.micro", "region": "ap-south-1"},
        }
        result = validate_request(parsed, "admin")
        type_violations = [v for v in result["violations"] if "not allowed" in v]
        assert not type_violations


class TestDatabase:
    def test_create_and_verify_user(self):
        ts = str(int(time.time() * 1000))
        username = f"dbtest_{ts}"
        user = create_user(username, "DbTest@123", "developer")
        assert user["username"] == username
        verified = verify_password(username, "DbTest@123")
        assert verified is not None

    def test_wrong_password_returns_none(self):
        ts = str(int(time.time() * 1000))
        username = f"dbtest2_{ts}"
        create_user(username, "RealPass@456", "developer")
        assert verify_password(username, "WrongPass@000") is None

    def test_duplicate_username_raises(self):
        ts = str(int(time.time() * 1000))
        username = f"dup_{ts}"
        create_user(username, "Pass@001", "developer")
        with pytest.raises(Exception):
            create_user(username, "Pass@002", "developer")

    def test_audit_log_written(self):
        log_action("test_action", {"key": "value"}, "success", "developer")
        logs = get_audit_log(5)
        assert any(l["action"] == "test_action" for l in logs)

    def test_count_resources_returns_int(self):
        count = count_resources("S3 Bucket")
        assert isinstance(count, int)
        assert count >= 0


# ════════════════════════════════════════════════════════════
# SECURITY TESTS
# ════════════════════════════════════════════════════════════

class TestSecurity:
    def test_sql_injection_in_username(self):
        """SQL meta-characters in username must not break auth or return a user."""
        result = login("' OR '1'='1", "anything")
        assert result is None

    def test_sql_injection_in_password(self):
        result = login("admin", "' OR '1'='1'; --")
        assert result is None

    def test_bcrypt_hash_not_plaintext(self):
        """Password must be stored hashed, not in plain text."""
        ts = str(int(time.time() * 1000))
        username = f"sec_{ts}"
        password = "PlainText@999"
        create_user(username, password, "developer")
        # verify_password should return None for the plaintext value as a hash
        # (this confirms the stored hash is NOT equal to the password itself)
        users = get_all_users()
        from utils.database import get_user_by_username
        user_row = get_user_by_username(username)
        assert user_row["password_hash"] != password

    def test_developer_cannot_create_iam(self):
        parsed = {"intent": "create_iam_role", "service": "iam", "parameters": {}}
        result = validate_request(parsed, "developer")
        assert not result["approved"]

    def test_policy_checked_for_all_roles(self):
        """Every role must be validated — no free pass."""
        for role in ("developer", "dev-lead", "admin"):
            parsed = {"intent": "list_s3_buckets", "service": "s3", "parameters": {"region": "ap-south-1"}}
            result = validate_request(parsed, role)
            assert "approved" in result


# ════════════════════════════════════════════════════════════
# RATE LIMITER TESTS
# ════════════════════════════════════════════════════════════

class TestRateLimiter:
    def test_within_limit_allowed(self):
        allowed, wait = check_rate_limit(99001, "test_action", limit=5, window=60)
        assert allowed is True
        assert wait == 0

    def test_exceeds_limit_blocked(self):
        uid = 99002
        for _ in range(5):
            check_rate_limit(uid, "burst_action", limit=5, window=60)
        allowed, wait = check_rate_limit(uid, "burst_action", limit=5, window=60)
        assert allowed is False
        assert wait > 0

    def test_different_users_isolated(self):
        """Hitting the limit for user A must not affect user B."""
        for _ in range(5):
            check_rate_limit(99010, "isolated_action", limit=5, window=60)
        allowed_b, _ = check_rate_limit(99011, "isolated_action", limit=5, window=60)
        assert allowed_b is True

    def test_different_actions_isolated(self):
        """Hitting the limit for action X must not affect action Y."""
        for _ in range(5):
            check_rate_limit(99020, "action_x", limit=5, window=60)
        allowed, _ = check_rate_limit(99020, "action_y", limit=5, window=60)
        assert allowed is True


# ════════════════════════════════════════════════════════════
# STRESS / CONCURRENCY TESTS
# ════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_audit_log_writes(self):
        """50 threads writing to audit_log simultaneously — no crash, no lost entries."""
        errors = []
        count = 50

        def write_log(i):
            try:
                log_action(f"concurrent_test_{i}", {"thread": i}, "success", "developer")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=write_log, args=(i,)) for i in range(count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent write errors: {errors}"

        logs = get_audit_log(200)
        written = [l for l in logs if l["action"].startswith("concurrent_test_")]
        assert len(written) == count, f"Expected {count} entries, got {len(written)}"

    def test_concurrent_rate_limiter(self):
        """Rate limiter must be thread-safe — no race conditions."""
        results = []
        uid = 99099
        lock = threading.Lock()

        def hammer():
            allowed, _ = check_rate_limit(uid, "concurrent_rl", limit=10, window=60)
            with lock:
                results.append(allowed)

        threads = [threading.Thread(target=hammer) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 10 should be allowed, 10 blocked
        assert results.count(True) == 10
        assert results.count(False) == 10

    def test_concurrent_user_creation(self):
        """Create 10 users in parallel — all must succeed with unique usernames."""
        errors = []
        created = []
        ts = str(int(time.time() * 1000))
        lock = threading.Lock()

        def make_user(i):
            try:
                u = create_user(f"parallel_{ts}_{i}", "Parallel@Pass1", "developer")
                with lock:
                    created.append(u["id"])
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=make_user, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent user creation errors: {errors}"
        assert len(created) == 10
        assert len(set(created)) == 10  # all unique IDs
