"""
Simple YAML-based authentication for COMS.
Uses streamlit-authenticator (free, no backend needed).

Default credentials (change these!):
  admin   / Admin@123
  devlead / DevLead@123
  dev     / Dev@1234
"""
import yaml
import bcrypt
from pathlib import Path
import streamlit_authenticator as stauth

USERS_FILE = Path(__file__).parent.parent / "config" / "users.yaml"


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


DEFAULT_CONFIG = {
    "credentials": {
        "usernames": {
            "admin": {
                "name": "Admin User",
                "email": "admin@coms.ai",
                "password": _hash("Admin@123"),
                "role": "admin",
            },
            "devlead": {
                "name": "Dev Lead",
                "email": "devlead@coms.ai",
                "password": _hash("DevLead@123"),
                "role": "dev-lead",
            },
            "dev": {
                "name": "Developer",
                "email": "dev@coms.ai",
                "password": _hash("Dev@1234"),
                "role": "developer",
            },
        }
    },
    "cookie": {
        "name": "coms_auth",
        "key": "coms_secret_key_change_in_prod",
        "expiry_days": 7,
    },
}


def _ensure_users_file():
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        with open(USERS_FILE, "w") as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)


def load_auth_config() -> dict:
    _ensure_users_file()
    with open(USERS_FILE) as f:
        return yaml.safe_load(f)


def save_auth_config(config: dict):
    with open(USERS_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def get_authenticator():
    config = load_auth_config()
    auth = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )
    return auth, config


def get_user_role(username: str) -> str:
    config = load_auth_config()
    user = config["credentials"]["usernames"].get(username, {})
    return user.get("role", "developer")
