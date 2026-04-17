"""
COMS — Streamlit session compatibility shim.

Provides the Streamlit-session API that app.py expects while the frontend
migration (Phase 2 → React) is in progress. This file will be deleted once
app.py is replaced by the FastAPI + React stack.

Auth flow here uses the OLD SQLite path so Streamlit stays bootable.
New code must NOT import from this module — use utils/auth.py instead.
"""
import streamlit as st
from utils.database import verify_password
from utils.auth import ROLE_RANK, require_role as _require_role_pure


def login(username: str, password: str) -> dict | None:
    """Validate credentials against SQLite. Returns user dict or None."""
    if not username or not password:
        return None
    try:
        return verify_password(username.strip(), password)
    except Exception:
        return None


def set_session(user: dict):
    st.session_state.authenticated = True
    st.session_state.user_id       = user.get("id")
    st.session_state.username      = user.get("username", "")
    st.session_state.role          = user.get("role", "")


def clear_session():
    for key in ("authenticated", "user_id", "username", "role",
                "orchestrator", "messages"):
        st.session_state.pop(key, None)


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def current_user() -> dict:
    return {
        "id":       st.session_state.get("user_id"),
        "username": st.session_state.get("username", ""),
        "role":     st.session_state.get("role", ""),
    }


def require_role(minimum_role: str):
    """Streamlit-flavoured role guard — calls st.stop() on failure."""
    if not is_authenticated():
        st.session_state.page = "login"
        st.rerun()
    user_rank     = ROLE_RANK.get(st.session_state.get("role", ""), 0)
    required_rank = ROLE_RANK.get(minimum_role, 999)
    if user_rank < required_rank:
        st.error(
            f"Access denied. '{minimum_role}' role required. "
            f"Your role: '{st.session_state.get('role', 'unknown')}'."
        )
        st.stop()
