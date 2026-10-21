"""Token authentication and role checks for the ForgeVault API.

Store SHA-256 token digests, never raw tokens, in FORGEVAULT_API_TOKENS_JSON.
JSON form: {"64-character-sha256": {"user":"alice", "role":"admin"}}.
No default identity or permissive local-network bypass.
"""
from __future__ import annotations

from contextvars import ContextVar
import hashlib
import hmac
import json
import os

from fastapi import HTTPException, Request

_current_actor: ContextVar[str | None] = ContextVar("forgevault_verified_actor", default=None)
ROLES = {"viewer", "editor", "reviewer", "admin"}


def authenticated_actor() -> str:
    actor = _current_actor.get()
    if not actor:
        raise RuntimeError("A server-verified ForgeVault identity is required")
    return actor


async def authorize_api_request(request: Request):
    authorization = request.headers.get("authorization", "")
    kind, separator, token = authorization.partition(" ")
    if kind.lower() != "bearer" or not separator or not token.strip():
        raise HTTPException(401, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    try:
        principals = json.loads(os.environ.get("FORGEVAULT_API_TOKENS_JSON", "{}"))
    except ValueError:
        principals = {}
    if not isinstance(principals, dict):
        principals = {}
    hashed = hashlib.sha256(token.encode("utf-8")).hexdigest()
    principal = next((value for key, value in principals.items()
                      if isinstance(key, str) and hmac.compare_digest(key, hashed)), None)
    if not isinstance(principal, dict) or not isinstance(principal.get("user"), str) or not principal["user"].strip() or principal.get("role") not in ROLES:
        raise HTTPException(401, detail="Invalid or unconfigured credentials", headers={"WWW-Authenticate": "Bearer"})
    role = principal["role"]
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if role in ("viewer", "reviewer") and not (
            role == "reviewer" and request.url.path.endswith("/decision") and request.method == "POST"
        ):
            raise HTTPException(403, detail="Editor role required")
        if (request.method == "DELETE" or
                "/integrations/jobboss2/" in request.url.path) and role != "admin":
            raise HTTPException(403, detail="Administrator role required")
        if request.url.path.endswith("/decision") and role not in ("reviewer", "admin"):
            raise HTTPException(403, detail="Reviewer role required")
        # Reject explicit identity claims that conflict with the authenticated
        # principal, even though service code uses the verified actor instead.
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() == "application/json":
            try:
                payload = await request.json()
            except ValueError:
                payload = {}
            if isinstance(payload, dict):
                for field in ("actor", "submitted_by", "reviewer"):
                    if field in payload and payload[field] != principal["user"]:
                        raise HTTPException(403, detail="Caller-supplied identity does not match authenticated user")
    request.state.principal = dict(principal)
    _current_actor.set(principal["user"])
