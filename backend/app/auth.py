"""
Classroom-grade auth: opaque bearer tokens in a process-local dict.
Role enforcement is server-side on every endpoint — see constitution Principle III.
"""

import secrets
from typing import NamedTuple

from fastapi import Depends, Header, HTTPException, status


class Actor(NamedTuple):
    role: str  # "patient" | "staff" | "doctor"
    id: str  # patient id, doctor id, or "" for staff


_tokens: dict[str, Actor] = {}


def issue_token(actor: Actor) -> str:
    token = secrets.token_urlsafe(24)
    _tokens[token] = actor
    return token


def revoke_token(token: str) -> None:
    _tokens.pop(token, None)


def current_actor(authorization: str | None = Header(default=None)) -> Actor:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    actor = _tokens.get(token)
    if actor is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return actor


def require_role(*roles: str):
    def _dep(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Role {actor.role} not permitted")
        return actor

    return _dep
