"""
COMS — Firebase Admin SDK initialization.

Fails CLOSED: if any required credential is absent or malformed,
the process exits immediately with a descriptive fatal error.
Never silently degrades to an insecure fallback.
"""
import os
import sys
import json

import firebase_admin
from firebase_admin import credentials, firestore as _firestore

_app: firebase_admin.App | None = None
_db = None


def _get_firebase_credentials() -> credentials.Certificate:
    json_string = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if json_string:
        print("Loading Firebase credentials from environment variable (JSON string)...")
        try:
            return credentials.Certificate(json.loads(json_string))
        except json.JSONDecodeError as exc:
            sys.exit(f"FATAL: FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON: {exc}")

    key_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
    if key_path:
        print("Loading Firebase credentials from file path...")
        if not os.path.isfile(key_path):
            sys.exit(
                f"FATAL: FIREBASE_SERVICE_ACCOUNT_KEY points to a file that does not exist: {key_path}"
            )
        return credentials.Certificate(key_path)

    sys.exit(
        "FATAL: Firebase credentials not configured. Set one of:\n"
        "  FIREBASE_SERVICE_ACCOUNT_JSON — full service account JSON as a single-line string (Docker)\n"
        "  FIREBASE_SERVICE_ACCOUNT_KEY  — path to service account JSON file (local dev)"
    )


def _init() -> None:
    global _app, _db

    project_id = os.environ.get("FIREBASE_PROJECT_ID")
    if not project_id:
        sys.exit(
            "FATAL: FIREBASE_PROJECT_ID is not set. "
            "Add it to your .env file."
        )

    cred = _get_firebase_credentials()

    try:
        _app = firebase_admin.initialize_app(cred, {"projectId": project_id})
        _db  = _firestore.client()
    except Exception as exc:
        sys.exit(f"FATAL: Firebase Admin SDK failed to initialise: {exc}")


def get_db():
    """Return the Firestore client. Initialises on first call."""
    if _db is None:
        _init()
    return _db


def get_app() -> firebase_admin.App:
    """Return the Firebase app. Initialises on first call."""
    if _app is None:
        _init()
    return _app
