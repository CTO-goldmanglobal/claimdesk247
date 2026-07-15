"""Auth + role middleware for the dashboard.

Roles (G-33 + DASHBOARD-SPEC 2026-07-15):
    customer            — no staff dashboard access (only their own case via /my-cases)
    panel_shop_staff    — staff dashboard: list, summary, no identity/brief
    legal_staff         — staff dashboard: list + intake brief + audit-log view
    admin               — everything + audit-log export + case assignment
    operator            — operator dashboard: system health, audit viewer,
                          retention trigger (added 2026-07-15)

The middleware checks roles server-side (not just UI hiding). Production
reads the role from the `user_roles` Supabase table (looked up by the JWT's
email claim); Stage 3 ships a stub auth backed by a hard-coded test user
list so the gate can be tested without Supabase auth configured.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


ROLES = ("customer", "panel_shop_staff", "legal_staff", "admin", "operator")


@dataclass(frozen=True)
class User:
    email: str
    role: str
    display_name: str

    def has_role(self, *allowed: str) -> bool:
        return self.role in allowed


# Test/stub user table. Production looks up role from the user_roles table
# via Supabase (see wrap.py::_resolve_user_from_jwt). These stubs are the
# fallback for test mode + dev environments without Supabase auth configured.
STUB_USERS: dict[str, "User"] = {
    "alice@customer.example": User(email="alice@customer.example", role="customer", display_name="Alice Customer"),
    "pat@panel.example":     User(email="pat@panel.example",     role="panel_shop_staff", display_name="Pat Panel"),
    "lou@legal.example":     User(email="lou@legal.example",     role="legal_staff",     display_name="Lou Legal"),
    "ada@admin.example":     User(email="ada@admin.example",     role="admin",           display_name="Ada Admin"),
    "ops@operator.example":  User(email="ops@operator.example",  role="operator",        display_name="Ops Operator"),
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
    return user.role in ("panel_shop_staff", "legal_staff", "admin", "operator")
