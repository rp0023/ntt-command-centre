"""Server-only demo account registry and password hashing."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from config import ROOT

ITERATIONS = 600_000

def registry_path() -> Path:
    return Path(os.environ.get("NTT_DEMO_ACCOUNTS_FILE", ROOT / ".demo-accounts.json"))

def load_registry() -> dict:
    try:
        data = json.loads(registry_path().read_text(encoding="utf-8"))
        if data.get("version") != 1 or not data.get("signingSecret") or not isinstance(data.get("accounts"), list):
            raise ValueError("Invalid registry")
        return data
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError("Demo accounts are not configured. Run python -m api.scripts.setup_demo_accounts.") from exc

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"

def check_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt, expected = encoded.split("$")
        if scheme != "pbkdf2_sha256" or not 100_000 <= int(iterations) <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def find_by_email(registry: dict, email: str) -> dict | None:
    normalized = email.strip().lower()
    return next((a for a in registry["accounts"] if normalized in
                 [a["email"], *a.get("aliases", [])] and a.get("enabled", True)), None)

def find_by_id(registry: dict, account_id: str) -> dict | None:
    return next((a for a in registry["accounts"] if a["id"] == account_id and a.get("enabled", True)), None)
