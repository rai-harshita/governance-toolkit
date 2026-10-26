import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

USERS = Path("evidence/users.json")
ROLES = ("submitter", "reviewer", "admin")

ROLE_PAGES = {
    "submitter": ["Overview", "Audit a System"],
    "reviewer": ["Overview", "Fairness", "Model Comparison", "Intersectional", "Explainability",
                 "GenAI Safety", "Risk Register", "Release Gate", "Policy Mapping"],
    "admin": ["Overview", "Fairness", "Model Comparison", "Intersectional", "Explainability",
              "GenAI Safety", "Risk Register", "Release Gate", "Policy Mapping", "Audit a System"],
}


def _hash(password, salt=None):
    salt = salt or os.urandom(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + h.hex()


def _verify(password, stored):
    salt_hex, h_hex = stored.split(":")
    h = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(h.hex(), h_hex)


def load_users():
    if not USERS.exists():
        return {}
    try:
        return json.loads(USERS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def create_user(username, password, role="submitter", display=None):
    username = username.strip().lower()
    if not username.isidentifier() or len(username) < 3:
        raise ValueError("Username must be 3+ characters: letters, digits, underscore.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if role not in ROLES:
        raise ValueError(f"Role must be one of {ROLES}.")
    users = load_users()
    if username in users:
        raise ValueError("That username is already taken.")
    users[username] = {"hash": _hash(password), "role": role, "name": (display or username).strip()}
    USERS.parent.mkdir(exist_ok=True)
    USERS.write_text(json.dumps(users, indent=2), encoding="utf-8")


def authenticate(username, password):
    u = load_users().get(username.strip().lower())
    if u and _verify(password, u["hash"]):
        return {"username": username.strip().lower(), "role": u["role"], "name": u["name"]}
    return None


if __name__ == "__main__":
    # python -m checks.auth <username> <password> <role> "<Display Name>"
    if len(sys.argv) < 4:
        print('Usage: python -m checks.auth <username> <password> <role> "<Display Name>"')
        sys.exit(1)
    create_user(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    print("Created", sys.argv[1], "as", sys.argv[3])
