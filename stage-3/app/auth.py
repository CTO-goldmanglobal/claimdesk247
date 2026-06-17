"""Auth + role middleware for the dashboard.

Roles (G-33):
    customer            — no dashboard access
    panel_shop_staff    — dashboard list, summary, PDF download, notes
    legal_staff         — list + intake brief + callback notes + audit-log view
    admin               — everything + audit-log export

The middleware checks roles server-side (not just UI hiding). The
production deployment will wire a real OIDC/SAML provider behind this
interface; Stage 3 ships a stub auth backed by a hard-coded test user
list so the gate can be tested. MFA is Stage 4.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


ROLES = ("customer", "panel_shop_staff", "legal_staff", "admin")


@dataclass(frozen=True)
class User:
    email: str
    role: str
    display_name: str

    def has_role(self, *allowed: str) -> bool:
        return self.role in allowed


# Test/stub user table. Stage 4 replaces with a real identity provider.
STUB_USERS: dict[str, "User"] = {
    "alice@customer.example": User(email="alice@customer.example", role="customer", display_name="Alice Customer"),
    "pat@panel.example":     User(email="pat@panel.example",     role="panel_shop_staff", display_name="Pat Panel"),
    "lou@legal.example":     User(email="lou@legal.example",     role="legal_staff",     display_name="Lou Legal"),
    "ada@admin.example":     User(email="ada@admin.example",     role="admin",           display_name="Ada Admin"),
}


class AuthError(Exception):
    """Raised when authentication or authorisation fails."""


def authenticate(email: str) -> "User":
    """Resolve a user from their email. Stage 4 swaps for real OIDC."""
    u = STUB_USERS.get(email.lower().strip())
    if not u:
        raise AuthError(f"unknown user: {email}")
    return u


def require_role(user: "User" | None, *allowed: str) -> "User":
    """Enforce that the user has one of the allowed roles. Server-side
    enforcement of G-33. Raises AuthError if not allowed."""
    if user is None:
        raise AuthError("not authenticated")
    if user.role not in allowed:
        raise AuthError(f"role {user.role!r} not in {allowed}")
    return user


def dashboard_visible_for(user: "User") -> bool:
    """Server-side check. Customers are blocked (G-33)."""
    return user.role in ("panel_shop_staff", "legal_staff", "admin")
