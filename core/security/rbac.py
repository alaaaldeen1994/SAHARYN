"""
SAHARYN AI — Firebase + RBAC Role Manager
==========================================
Manages role-based access control claims on Firebase Custom Tokens.
Roles determine what sections of the dashboard are visible.

ROLES:
  OPERATOR    — Read-only: Telemetry, Physics, ESG views only
  ANALYST     — Telemetry + Physics + Audit + ESG + Diligence
  MANAGER     — All ANALYST views + Settings (read-only)
  ADMIN       — Full access including Delete Account, Sovereign Mode, Settings write
  SUPER_ADMIN — Full access + user management
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger("SAHARYN_RBAC")

class Role(str, Enum):
    OPERATOR    = "OPERATOR"
    ANALYST     = "ANALYST"
    MANAGER     = "MANAGER"
    ADMIN       = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class Permission(str, Enum):
    VIEW_TELEMETRY    = "view_telemetry"
    VIEW_PHYSICS      = "view_physics"
    VIEW_AUDIT        = "view_audit"
    VIEW_ESG          = "view_esg"
    VIEW_ENERGY       = "view_energy"
    VIEW_STRESS       = "view_stress"
    VIEW_DILIGENCE    = "view_diligence"
    VIEW_SETTINGS     = "view_settings"
    TRIGGER_INFERENCE = "trigger_inference"
    TOGGLE_SOVEREIGN  = "toggle_sovereign"
    EDIT_SETTINGS     = "edit_settings"
    DELETE_ACCOUNT    = "delete_account"
    MANAGE_USERS      = "manage_users"
    EXPORT_AUDIT      = "export_audit"
    VIEW_API_DOCS     = "view_api_docs"


ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.OPERATOR: [
        Permission.VIEW_TELEMETRY, Permission.VIEW_PHYSICS,
        Permission.VIEW_ESG, Permission.VIEW_ENERGY, Permission.VIEW_STRESS,
    ],
    Role.ANALYST: [
        Permission.VIEW_TELEMETRY, Permission.VIEW_PHYSICS, Permission.VIEW_AUDIT,
        Permission.VIEW_ESG, Permission.VIEW_ENERGY, Permission.VIEW_STRESS,
        Permission.VIEW_DILIGENCE, Permission.TRIGGER_INFERENCE, Permission.EXPORT_AUDIT,
    ],
    Role.MANAGER: [
        Permission.VIEW_TELEMETRY, Permission.VIEW_PHYSICS, Permission.VIEW_AUDIT,
        Permission.VIEW_ESG, Permission.VIEW_ENERGY, Permission.VIEW_STRESS,
        Permission.VIEW_DILIGENCE, Permission.VIEW_SETTINGS,
        Permission.TRIGGER_INFERENCE, Permission.EXPORT_AUDIT, Permission.VIEW_API_DOCS,
    ],
    Role.ADMIN: [
        Permission.VIEW_TELEMETRY, Permission.VIEW_PHYSICS, Permission.VIEW_AUDIT,
        Permission.VIEW_ESG, Permission.VIEW_ENERGY, Permission.VIEW_STRESS,
        Permission.VIEW_DILIGENCE, Permission.VIEW_SETTINGS,
        Permission.TRIGGER_INFERENCE, Permission.TOGGLE_SOVEREIGN,
        Permission.EDIT_SETTINGS, Permission.DELETE_ACCOUNT,
        Permission.EXPORT_AUDIT, Permission.VIEW_API_DOCS,
    ],
    Role.SUPER_ADMIN: list(Permission),
}


def get_permissions_for_role(role: str) -> List[str]:
    try:
        r = Role(role)
        return [p.value for p in ROLE_PERMISSIONS.get(r, [])]
    except ValueError:
        return [p.value for p in ROLE_PERMISSIONS[Role.OPERATOR]]


def get_role_capabilities_json(role: str) -> Dict[str, Any]:
    """Return JSON capability map consumed by the frontend dashboard for RBAC gating."""
    permissions = set(get_permissions_for_role(role))
    return {
        "role": role,
        "permissions": list(permissions),
        "dashboard_sections": {
            "telemetry":  Permission.VIEW_TELEMETRY.value in permissions,
            "physics":    Permission.VIEW_PHYSICS.value in permissions,
            "audit":      Permission.VIEW_AUDIT.value in permissions,
            "esg":        Permission.VIEW_ESG.value in permissions,
            "energy":     Permission.VIEW_ENERGY.value in permissions,
            "stress":     Permission.VIEW_STRESS.value in permissions,
            "diligence":  Permission.VIEW_DILIGENCE.value in permissions,
            "settings":   Permission.VIEW_SETTINGS.value in permissions,
        },
        "actions": {
            "trigger_inference": Permission.TRIGGER_INFERENCE.value in permissions,
            "toggle_sovereign":  Permission.TOGGLE_SOVEREIGN.value in permissions,
            "edit_settings":     Permission.EDIT_SETTINGS.value in permissions,
            "delete_account":    Permission.DELETE_ACCOUNT.value in permissions,
            "manage_users":      Permission.MANAGE_USERS.value in permissions,
            "export_audit":      Permission.EXPORT_AUDIT.value in permissions,
        },
    }


def set_user_role(uid: str, role: str) -> bool:
    """Assign RBAC role via Firebase custom claims (requires firebase-admin SDK)."""
    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth

        if not firebase_admin._apps:
            service_account = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
            cred = firebase_admin.credentials.Certificate(json.loads(service_account)) \
                if service_account else firebase_admin.credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)

        if role not in [r.value for r in Role]:
            logger.error(f"Invalid role '{role}'")
            return False

        firebase_auth.set_custom_user_claims(uid, {
            "role": role,
            "saharyn_platform": True,
            "role_set_at": datetime.utcnow().isoformat() + "Z",
            "permissions": get_permissions_for_role(role),
        })
        logger.info(f"RBAC: Role '{role}' assigned to user {uid}")
        return True
    except ImportError:
        logger.error("firebase-admin not installed. Run: pip install firebase-admin")
        return False
    except Exception as e:
        logger.error(f"Failed to set role for {uid}: {e}")
        return False


def get_user_role(uid: str) -> Optional[str]:
    """Retrieve a Firebase user's current RBAC role."""
    try:
        from firebase_admin import auth as firebase_auth
        user = firebase_auth.get_user(uid)
        return (user.custom_claims or {}).get("role", "OPERATOR")
    except Exception as e:
        logger.error(f"Failed to get role for {uid}: {e}")
        return None


# FastAPI dependency for RBAC-gated endpoints
def require_permission(required: Permission):
    """FastAPI dependency factory for permission-based endpoint guarding."""
    from fastapi import HTTPException, Header
    from core.security.manager import SecurityManager

    async def _check(x_api_key: str = Header(...)):
        # In production: decode JWT, extract role, check permissions
        # For now: API key holders get ADMIN access
        # TODO: Integrate with Firebase Admin to verify ID token
        return True

    return _check


# API endpoint helper
def get_api_rbac_endpoint():
    """Returns role capabilities for the authenticated user (used by frontend RBAC bootstrap)."""
    from fastapi import APIRouter, Header
    router = APIRouter()

    @router.get("/v2/auth/capabilities", tags=["Auth"])
    async def get_user_capabilities(x_user_role: str = Header(default="OPERATOR")):
        """
        Returns the capability map for the current user's role.
        Frontend calls this on login to configure the dashboard UI.
        """
        return get_role_capabilities_json(x_user_role)

    return router
