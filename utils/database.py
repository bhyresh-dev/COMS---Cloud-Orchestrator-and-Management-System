"""
SQLite persistence layer — replaces in-memory AUDIT_LOG and PENDING_APPROVALS.
Survives app restarts, works completely free (no cloud needed).
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "coms.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            action      TEXT    NOT NULL,
            details     TEXT,           -- JSON blob
            status      TEXT    NOT NULL,
            user_role   TEXT,
            duration_s  REAL
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            parsed_request  TEXT NOT NULL,   -- JSON blob
            risk_result     TEXT NOT NULL,   -- JSON blob
            user_role       TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            timestamp       TEXT NOT NULL,
            resolved_at     TEXT,
            resolved_by     TEXT,
            reject_reason   TEXT
        );

        CREATE TABLE IF NOT EXISTS resources (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_name TEXT NOT NULL,
            region      TEXT,
            details     TEXT,   -- JSON blob
            status      TEXT NOT NULL DEFAULT 'active',
            created_by_role TEXT
        );

        CREATE TABLE IF NOT EXISTS budget_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            action      TEXT NOT NULL,
            estimated_usd REAL DEFAULT 0,
            user_role   TEXT
        );
    """)
    conn.commit()
    conn.close()


# ===================== AUDIT LOG =====================

def log_action(action: str, details: dict, status: str = "success",
               user_role: str = None, duration_s: float = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO audit_log (timestamp, action, details, status, user_role, duration_s) VALUES (?,?,?,?,?,?)",
        (datetime.now().isoformat(), action, json.dumps(details), status, user_role, duration_s)
    )
    conn.commit()
    conn.close()
    icon = "✅" if status == "success" else "❌" if status == "error" else "⚠️"
    print(f"[AUDIT] {icon} {datetime.now().isoformat()} | {action} | {status.upper()}")


def get_audit_log(limit: int = 200) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_logs(n: int = 50) -> list:
    return get_audit_log(n)


def get_audit_stats() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    success = conn.execute("SELECT COUNT(*) FROM audit_log WHERE status='success'").fetchone()[0]
    errors = conn.execute("SELECT COUNT(*) FROM audit_log WHERE status='error'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM audit_log WHERE status='pending'").fetchone()[0]
    conn.close()
    return {"total": total, "success": success, "errors": errors, "pending": pending}


# ===================== APPROVALS =====================

def add_approval(parsed_request: dict, risk_result: dict, user_role: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO approvals (parsed_request, risk_result, user_role, status, timestamp) VALUES (?,?,?,?,?)",
        (json.dumps(parsed_request), json.dumps(risk_result), user_role, "pending", datetime.now().isoformat())
    )
    aid = cur.lastrowid
    conn.commit()
    conn.close()
    return aid


def get_pending_approvals() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM approvals WHERE status='pending' ORDER BY id DESC"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["parsed_request"] = json.loads(d["parsed_request"])
        d["risk_result"] = json.loads(d["risk_result"])
        result.append(d)
    return result


def approve_approval(approval_id: int, resolved_by: str = "admin") -> dict:
    conn = get_conn()
    conn.execute(
        "UPDATE approvals SET status='approved', resolved_at=?, resolved_by=? WHERE id=? AND status='pending'",
        (datetime.now().isoformat(), resolved_by, approval_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["parsed_request"] = json.loads(d["parsed_request"])
        d["risk_result"] = json.loads(d["risk_result"])
        return d
    return {}


def reject_approval(approval_id: int, reason: str = "Rejected by admin", resolved_by: str = "admin"):
    conn = get_conn()
    conn.execute(
        "UPDATE approvals SET status='rejected', resolved_at=?, resolved_by=?, reject_reason=? WHERE id=? AND status='pending'",
        (datetime.now().isoformat(), resolved_by, reason, approval_id)
    )
    conn.commit()
    conn.close()


def get_all_approvals(limit: int = 100) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM approvals ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["parsed_request"] = json.loads(d["parsed_request"])
        d["risk_result"] = json.loads(d["risk_result"])
        result.append(d)
    return result


# ===================== RESOURCES =====================

def record_resource(resource_type: str, resource_name: str, region: str,
                    details: dict, created_by_role: str = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO resources (timestamp, resource_type, resource_name, region, details, created_by_role) VALUES (?,?,?,?,?,?)",
        (datetime.now().isoformat(), resource_type, resource_name, region, json.dumps(details), created_by_role)
    )
    conn.commit()
    conn.close()


def get_resources(status: str = "active") -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM resources WHERE status=? ORDER BY id DESC", (status,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["details"] = json.loads(d["details"])
        result.append(d)
    return result


def delete_resource_record(resource_name: str):
    conn = get_conn()
    conn.execute(
        "UPDATE resources SET status='deleted' WHERE resource_name=?", (resource_name,)
    )
    conn.commit()
    conn.close()


# ===================== BUDGET =====================

def log_budget(action: str, estimated_usd: float, user_role: str = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO budget_log (timestamp, action, estimated_usd, user_role) VALUES (?,?,?,?)",
        (datetime.now().isoformat(), action, estimated_usd, user_role)
    )
    conn.commit()
    conn.close()


def get_monthly_spend() -> float:
    from datetime import datetime
    month_start = datetime.now().strftime("%Y-%m-01")
    conn = get_conn()
    result = conn.execute(
        "SELECT SUM(estimated_usd) FROM budget_log WHERE timestamp >= ?", (month_start,)
    ).fetchone()[0]
    conn.close()
    return result or 0.0


# Initialize on import
init_db()
