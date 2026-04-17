"""
Audit logger — thin wrapper around the SQLite database layer.
Kept for backwards compatibility with existing imports.
"""
from utils.database import log_action, get_audit_log, get_recent_logs

__all__ = ["log_action", "get_audit_log", "get_recent_logs"]
