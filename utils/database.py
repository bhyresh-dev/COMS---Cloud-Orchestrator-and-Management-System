"""
COMS — Thread-safe SQLite persistence layer.

Thread safety strategy:
  - WAL journal mode (concurrent reads, serialised writes)
  - One connection per call (never shared across threads)
  - _write_lock guards every INSERT / UPDATE / DELETE
"""
import sqlite3
import json
import threading
import bcrypt
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "coms.db"
_write_lock = threading.Lock()


# ── connection factory ──────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    """New connection per call — thread safe, no shared state."""
    conn = sqlite3.connect(str(DB_PATH))   # no check_same_thread needed
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── schema init ─────────────────────────────────────────────

def init_db():
    """Create / migrate all tables and seed default users."""
    with _write_lock:
        conn = get_conn()
        conn.executescript("""
            -- Users (single source of truth for identity)
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                role          TEXT    NOT NULL DEFAULT 'developer',
                created_at    TEXT    NOT NULL,
                is_active     INTEGER NOT NULL DEFAULT 1
            );

            -- Audit log
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL,
                action      TEXT    NOT NULL,
                details     TEXT,
                status      TEXT    NOT NULL,
                user_id     INTEGER REFERENCES users(id),
                user_role   TEXT,
                duration_s  REAL
            );

            -- Approval queue
            CREATE TABLE IF NOT EXISTS approvals (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                parsed_request  TEXT    NOT NULL,
                risk_result     TEXT    NOT NULL,
                user_id         INTEGER REFERENCES users(id),
                user_role       TEXT    NOT NULL,
                status          TEXT    NOT NULL DEFAULT 'pending',
                timestamp       TEXT    NOT NULL,
                resolved_at     TEXT,
                resolved_by     TEXT,
                reject_reason   TEXT
            );

            -- Provisioned resources
            CREATE TABLE IF NOT EXISTS resources (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT    NOT NULL,
                resource_type   TEXT    NOT NULL,
                resource_name   TEXT    NOT NULL,
                region          TEXT,
                details         TEXT,
                status          TEXT    NOT NULL DEFAULT 'active',
                user_id         INTEGER REFERENCES users(id),
                created_by_role TEXT
            );

            -- Budget tracking
            CREATE TABLE IF NOT EXISTS budget_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp     TEXT    NOT NULL,
                action        TEXT    NOT NULL,
                estimated_usd REAL    DEFAULT 0,
                user_id       INTEGER REFERENCES users(id),
                user_role     TEXT
            );

            -- Base indexes (columns guaranteed to exist)
            CREATE INDEX IF NOT EXISTS idx_audit_ts      ON audit_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_approvals_st  ON approvals(status);
            CREATE INDEX IF NOT EXISTS idx_resources_st  ON resources(status);
        """)

        # Non-destructive column migrations (idempotent)
        for migration in [
            "ALTER TABLE audit_log ADD COLUMN user_id INTEGER REFERENCES users(id)",
            "ALTER TABLE resources ADD COLUMN user_id INTEGER REFERENCES users(id)",
            "ALTER TABLE approvals ADD COLUMN user_id INTEGER REFERENCES users(id)",
            "ALTER TABLE budget_log ADD COLUMN user_id INTEGER REFERENCES users(id)",
            "ALTER TABLE budget_log ADD COLUMN user_role TEXT",
        ]:
            try:
                conn.execute(migration)
            except Exception:
                pass   # Column already exists

        # Indexes on migrated columns (safe after ALTER TABLE)
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_audit_user    ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_resources_usr ON resources(user_id)",
        ]:
            try:
                conn.execute(idx_sql)
            except Exception:
                pass

        conn.commit()
        _seed_users(conn)
        conn.close()


def _seed_users(conn: sqlite3.Connection):
    """Create default accounts if they don't already exist."""
    defaults = [
        ("admin",   "Admin@123",    "admin"),
        ("devlead", "DevLead@123",  "dev-lead"),
        ("dev",     "Dev@1234",     "developer"),
    ]
    for username, password, role in defaults:
        if not conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
                (username, hashed, role, datetime.now().isoformat()),
            )
    conn.commit()


# ── USER MANAGEMENT ─────────────────────────────────────────

def get_user_by_username(username: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND is_active=1", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, username, role, created_at, is_active FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username: str, password: str, role: str = "developer") -> dict:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with _write_lock:
        conn = get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
                (username, hashed, role, datetime.now().isoformat()),
            )
            conn.commit()
            uid = cur.lastrowid
        finally:
            conn.close()
    return {"id": uid, "username": username, "role": role}


def verify_password(username: str, password: str) -> dict | None:
    """Returns user dict on success, None on failure. No exceptions raised."""
    user = get_user_by_username(username)
    if not user:
        return None
    try:
        if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return user
    except Exception:
        pass
    return None


# ── AUDIT LOG ───────────────────────────────────────────────

def log_action(action: str, details: dict, status: str = "success",
               user_role: str = None, duration_s: float = None,
               user_id: int = None):
    with _write_lock:
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO audit_log "
                "(timestamp, action, details, status, user_id, user_role, duration_s) "
                "VALUES (?,?,?,?,?,?,?)",
                (datetime.now().isoformat(), action, json.dumps(details),
                 status, user_id, user_role, duration_s),
            )
            conn.commit()
        finally:
            conn.close()
    icon = "✅" if status == "success" else "❌" if status == "error" else "⚠️"
    print(f"[AUDIT] {icon} {action} | {status.upper()}")


def get_audit_log(limit: int = 200, user_id: int = None) -> list:
    conn = get_conn()
    if user_id:
        rows = conn.execute(
            "SELECT a.*, u.username FROM audit_log a "
            "LEFT JOIN users u ON a.user_id=u.id "
            "WHERE a.user_id=? ORDER BY a.id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT a.*, u.username FROM audit_log a "
            "LEFT JOIN users u ON a.user_id=u.id "
            "ORDER BY a.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_logs(n: int = 50, user_id: int = None) -> list:
    return get_audit_log(n, user_id=user_id)


def get_audit_stats(user_id: int = None) -> dict:
    conn = get_conn()
    base = "FROM audit_log" + (" WHERE user_id=?" if user_id else "")
    args = (user_id,) if user_id else ()
    total   = conn.execute(f"SELECT COUNT(*) {base}", args).fetchone()[0]
    success = conn.execute(f"SELECT COUNT(*) {base} {'AND' if user_id else 'WHERE'} status='success'",
                           args).fetchone()[0]
    errors  = conn.execute(f"SELECT COUNT(*) {base} {'AND' if user_id else 'WHERE'} status='error'",
                           args).fetchone()[0]
    pending = conn.execute(f"SELECT COUNT(*) {base} {'AND' if user_id else 'WHERE'} status='pending'",
                           args).fetchone()[0]
    conn.close()
    return {"total": total, "success": success, "errors": errors, "pending": pending}


# ── APPROVALS ───────────────────────────────────────────────

def add_approval(parsed_request: dict, risk_result: dict,
                 user_role: str, user_id: int = None) -> int:
    with _write_lock:
        conn = get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO approvals "
                "(parsed_request, risk_result, user_id, user_role, status, timestamp) "
                "VALUES (?,?,?,?,?,?)",
                (json.dumps(parsed_request), json.dumps(risk_result),
                 user_id, user_role, "pending", datetime.now().isoformat()),
            )
            aid = cur.lastrowid
            conn.commit()
        finally:
            conn.close()
    return aid


def get_pending_approvals() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT a.*, u.username FROM approvals a "
        "LEFT JOIN users u ON a.user_id=u.id "
        "WHERE a.status='pending' ORDER BY a.id DESC"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["parsed_request"] = json.loads(d["parsed_request"])
        d["risk_result"]    = json.loads(d["risk_result"])
        result.append(d)
    return result


def approve_approval(approval_id: int, resolved_by: str = "admin") -> dict:
    with _write_lock:
        conn = get_conn()
        try:
            conn.execute(
                "UPDATE approvals SET status='approved', resolved_at=?, resolved_by=? "
                "WHERE id=? AND status='pending'",
                (datetime.now().isoformat(), resolved_by, approval_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        finally:
            conn.close()
    if row:
        d = dict(row)
        d["parsed_request"] = json.loads(d["parsed_request"])
        d["risk_result"]    = json.loads(d["risk_result"])
        return d
    return {}


def reject_approval(approval_id: int, reason: str = "Rejected by admin",
                    resolved_by: str = "admin"):
    with _write_lock:
        conn = get_conn()
        try:
            conn.execute(
                "UPDATE approvals SET status='rejected', resolved_at=?, "
                "resolved_by=?, reject_reason=? WHERE id=? AND status='pending'",
                (datetime.now().isoformat(), resolved_by, reason, approval_id),
            )
            conn.commit()
        finally:
            conn.close()


def get_all_approvals(limit: int = 100) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT a.*, u.username FROM approvals a "
        "LEFT JOIN users u ON a.user_id=u.id "
        "ORDER BY a.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["parsed_request"] = json.loads(d["parsed_request"])
        d["risk_result"]    = json.loads(d["risk_result"])
        result.append(d)
    return result


# ── RESOURCES ───────────────────────────────────────────────

def record_resource(resource_type: str, resource_name: str, region: str,
                    details: dict, created_by_role: str = None,
                    user_id: int = None):
    with _write_lock:
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO resources "
                "(timestamp, resource_type, resource_name, region, details, "
                " created_by_role, user_id) VALUES (?,?,?,?,?,?,?)",
                (datetime.now().isoformat(), resource_type, resource_name,
                 region, json.dumps(details), created_by_role, user_id),
            )
            conn.commit()
        finally:
            conn.close()


def get_resources(status: str = "active", user_id: int = None) -> list:
    conn = get_conn()
    if user_id:
        rows = conn.execute(
            "SELECT r.*, u.username FROM resources r "
            "LEFT JOIN users u ON r.user_id=u.id "
            "WHERE r.status=? AND r.user_id=? ORDER BY r.id DESC",
            (status, user_id),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT r.*, u.username FROM resources r "
            "LEFT JOIN users u ON r.user_id=u.id "
            "WHERE r.status=? ORDER BY r.id DESC",
            (status,),
        ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["details"] = json.loads(d["details"])
        result.append(d)
    return result


def count_resources(resource_type: str, user_id: int = None,
                    created_by_role: str = None) -> int:
    """Used by policy engine to enforce limits."""
    conn = get_conn()
    if user_id:
        count = conn.execute(
            "SELECT COUNT(*) FROM resources WHERE resource_type=? AND status='active' AND user_id=?",
            (resource_type, user_id),
        ).fetchone()[0]
    elif created_by_role:
        count = conn.execute(
            "SELECT COUNT(*) FROM resources WHERE resource_type=? AND status='active' AND created_by_role=?",
            (resource_type, created_by_role),
        ).fetchone()[0]
    else:
        count = conn.execute(
            "SELECT COUNT(*) FROM resources WHERE resource_type=? AND status='active'",
            (resource_type,),
        ).fetchone()[0]
    conn.close()
    return count


def delete_resource_record(resource_name: str):
    with _write_lock:
        conn = get_conn()
        try:
            conn.execute(
                "UPDATE resources SET status='deleted' WHERE resource_name=?",
                (resource_name,),
            )
            conn.commit()
        finally:
            conn.close()


# ── BUDGET ──────────────────────────────────────────────────

def log_budget(action: str, estimated_usd: float,
               user_role: str = None, user_id: int = None):
    with _write_lock:
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO budget_log (timestamp, action, estimated_usd, user_id, user_role) "
                "VALUES (?,?,?,?,?)",
                (datetime.now().isoformat(), action, estimated_usd, user_id, user_role),
            )
            conn.commit()
        finally:
            conn.close()


def get_monthly_spend() -> float:
    month_start = datetime.now().strftime("%Y-%m-01")
    conn = get_conn()
    result = conn.execute(
        "SELECT SUM(estimated_usd) FROM budget_log WHERE timestamp >= ?",
        (month_start,),
    ).fetchone()[0]
    conn.close()
    return result or 0.0


# ── boot ────────────────────────────────────────────────────
init_db()
