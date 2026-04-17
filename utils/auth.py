"""
COMS — Authentication module.

Backed entirely by Firebase Auth + Firestore.
Fails CLOSED: any exception during token verification → 401.
No Streamlit dependency. No fallback to admin.

Public API:
  verify_token(id_token)  → user dict  or raises AuthError
  require_role(user, min) → None       or raises AuthError(403)
  get_user_role(uid)      → str        ("user" | "admin")
"""
import sys
from firebase_admin import auth as firebase_auth
from utils.firebase_init import get_app
from utils.firestore_db import get_user_by_uid, create_or_update_user

# Role hierarchy — higher = more privileged
ROLE_RANK = {
    "user":  1,
    "admin": 2,
}


class AuthError(Exception):
    """Raised when authentication or authorisation fails."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail      = detail
        super().__init__(detail)


def verify_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token server-side.

    Returns:
        {
            "uid":   str,
            "email": str,
            "name":  str,
            "role":  str,   # from Firestore — never from the token claims
        }

    Raises:
        AuthError(401) — token absent, expired, revoked, or malformed
        AuthError(403) — token valid but account is deactivated
    """
    if not id_token:
        raise AuthError(401, "Authorization token is required.")

    # Ensure Firebase app is initialised — get_app() exits fatally if creds missing
    get_app()

    try:
        decoded = firebase_auth.verify_id_token(id_token, check_revoked=True)
    except firebase_auth.RevokedIdTokenError:
        raise AuthError(401, "Token has been revoked. Please sign in again.")
    except firebase_auth.ExpiredIdTokenError:
        raise AuthError(401, "Token has expired. Please sign in again.")
    except firebase_auth.InvalidIdTokenError:
        raise AuthError(401, "Token is invalid.")
    except Exception:
        # Any other Firebase / network error → deny access, never degrade
        raise AuthError(401, "Token verification failed.")

    uid   = decoded["uid"]
    email = decoded.get("email", "")
    name  = decoded.get("name", "")

    # Upsert user in Firestore (new accounts default to role "user")
    user_doc = create_or_update_user(uid, email, name)
    role     = user_doc.get("role", "user")

    return {
        "uid":   uid,
        "email": email,
        "name":  name,
        "role":  role,
    }


def get_user_role(uid: str) -> str:
    """Look up a user's role directly from Firestore. Returns 'user' if not found."""
    doc = get_user_by_uid(uid)
    if not doc:
        return "user"
    return doc.get("role", "user")


def require_role(user: dict, minimum_role: str) -> None:
    """
    Assert that user meets or exceeds minimum_role.

    Raises:
        AuthError(403) — insufficient privileges
    """
    user_rank     = ROLE_RANK.get(user.get("role", ""), 0)
    required_rank = ROLE_RANK.get(minimum_role, 999)
    if user_rank < required_rank:
        raise AuthError(
            403,
            f"Forbidden. '{minimum_role}' role required. "
            f"Your role: '{user.get('role', 'unknown')}'.",
        )
