"""Fail-closed API authentication for multi-user ForgeVault deployments.

Configure FORGEVAULT_AUTH_PRINCIPALS as JSON mapping bearer tokens to
{"actor": "verified-name", "role": "reader|editor|reviewer|admin"}.
Tokens are credentials, not user-supplied actor identities. Use TLS off-host.
"""
import hmac
import json
import os

from fastapi import Request
from fastapi.responses import JSONResponse

ROLES = {"reader", "editor", "reviewer", "admin"}
MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _principals():
    raw = os.environ.get("FORGEVAULT_AUTH_PRINCIPALS", "")
    try:
        value = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        token: principal
        for token, principal in value.items()
        if isinstance(token, str) and len(token) >= 24
        and isinstance(principal, dict)
        and isinstance(principal.get("actor"), str)
        and principal["actor"].strip()
        and principal.get("role") in ROLES
    }


def _actor_values(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"actor", "reviewer"}:
                yield item
            else:
                yield from _actor_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _actor_values(item)


async def authorize_api_request(request: Request, call_next):
    if not request.url.path.startswith("/api/v1/"):
        return await call_next(request)

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    supplied = auth[7:]
    principals = _principals()
    principal = next(
        (entry for token, entry in principals.items() if hmac.compare_digest(token, supplied)),
        None,
    )
    if principal is None:
        return JSONResponse({"detail": "Invalid credentials"}, status_code=401)

    request.state.actor = principal["actor"]
    request.state.role = principal["role"]
    if request.method in MUTATION_METHODS:
        role = principal["role"]
        path = request.url.path
        if role == "reader":
            return JSONResponse({"detail": "Insufficient role"}, status_code=403)
        if path.endswith("/decision") and role not in {"reviewer", "admin"}:
            return JSONResponse({"detail": "Reviewer role required"}, status_code=403)
        if "/integrations/jobboss2/" in path and role != "admin":
            return JSONResponse({"detail": "Admin role required"}, status_code=403)
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() == "application/json":
            try:
                data = await request.json()
            except (ValueError, UnicodeError):
                return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
            if any(not isinstance(name, str) or not hmac.compare_digest(name, principal["actor"])
                   for name in _actor_values(data)):
                return JSONResponse({"detail": "Actor identity does not match authenticated principal"}, status_code=403)

    return await call_next(request)
