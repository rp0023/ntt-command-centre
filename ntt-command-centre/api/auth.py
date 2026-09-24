"""Email/password demo login. Tokens identify a server-configured account."""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from config import ACCESS_SECRET
from demo_accounts import check_password, find_by_email, find_by_id, load_registry

TOKEN_TTL_S = 8 * 60 * 60
EXEMPT_PATHS = frozenset({"/healthz", "/api/health", "/api/auth/login", "/docs", "/openapi.json"})
router = APIRouter()

def _sign(payload: str, registry: dict) -> str:
    secret = ACCESS_SECRET or registry["signingSecret"]
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

def issue(account: dict, registry: dict, now: float | None = None) -> tuple[str, int]:
    exp = int(time.time() if now is None else now) + TOKEN_TTL_S
    payload = base64.urlsafe_b64encode(json.dumps({"v": 2, "sub": account["id"], "exp": exp}, separators=(",", ":")).encode()).decode()
    return f"{payload}.{_sign(payload, registry)}", exp

def verify(token: str, registry: dict) -> dict | None:
    try:
        if len(token) > 2048:
            return None
        payload, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _sign(payload, registry)):
            return None
        claims = json.loads(base64.urlsafe_b64decode(payload).decode())
        if claims.get("v") != 2 or not isinstance(claims.get("exp"), int) or claims["exp"] <= time.time():
            return None
        return find_by_id(registry, claims["sub"])
    except (ValueError, KeyError, TypeError, AttributeError):
        return None

def principal_for(account: dict):
    from semantic import personas as PR
    role, identity = account["role"], account["identity"]
    valid = (role == "ae" and identity in set(PR.roster()["owner"])) or (
        role == "manager" and identity in set(PR.pods()["pod_id"])) or (
        role == "executive" and identity == "north-america")
    if not valid:
        raise HTTPException(403, "Account scope is not available")
    return PR.resolve(role, identity)

def principal(request: Request):
    account = getattr(request.state, "account", None)
    if account is None:
        raise HTTPException(401, "Sign in required")
    return principal_for(account)

def profile(account: dict) -> dict:
    p = principal_for(account)
    return {"id": account["id"], "name": account["name"], "email": account["email"],
            "role": p.key, "roleLabel": p.persona.label, "identity": p.identity,
            "scopeLabel": p.identity_label, "home": p.persona.home, "pages": list(p.persona.pages)}

class LoginBody(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)

@router.post("/api/auth/login")
def login(body: LoginBody):
    try:
        registry = load_registry()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    account = find_by_email(registry, body.email)
    dummy = "pbkdf2_sha256$600000$unknown-account$" + "0" * 64
    valid = check_password(body.password, account["passwordHash"] if account else dummy)
    if not valid or account is None:
        raise HTTPException(401, "Email or password is incorrect")
    user = profile(account)
    token, exp = issue(account, registry)
    return JSONResponse({"token": token, "expiresAt": datetime.fromtimestamp(exp, timezone.utc).isoformat(),
                         "user": user}, headers={"Cache-Control": "no-store"})

@router.get("/api/auth/me")
def me(request: Request):
    return JSONResponse(profile(request.state.account), headers={"Cache-Control": "no-store"})

class AccessGate:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope.get("method") == "OPTIONS" or scope.get("path") in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return
        token = ""
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                parts = value.decode("latin-1").split(None, 1)
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    token = parts[1]
        try:
            account = verify(token, load_registry()) if token else None
        except RuntimeError:
            await JSONResponse({"detail": "Demo accounts are not configured"}, status_code=503)(scope, receive, send)
            return
        if account is None:
            await JSONResponse({"detail": "Sign in required"}, status_code=401,
                               headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"})(scope, receive, send)
            return
        scope.setdefault("state", {})["account"] = account
        async def private_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"cache-control"]
                message["headers"].append((b"cache-control", b"no-store"))
            await send(message)
        await self.app(scope, receive, private_send)
