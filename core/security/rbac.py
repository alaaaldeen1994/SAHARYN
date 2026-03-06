"""
SAHARYN AI — Role-Based Access Control (RBAC) System
======================================================
Enterprise-grade access control aligned with:
  - SOC2 Type II (CC6.1, CC6.3)
  - ISO 27001 (A.9 Access Control)
  - NIST CSF (PR.AC)

Four roles with progressive permissions:

  OPERATOR     → Read telemetry, view recommendations
  ENGINEER     → Operator + execute actions, view model details
  MANAGER      → Engineer + view financials, approve prescriptions
  ADMIN        → Full access including user management and audit logs

JWT-based authentication. Tokens expire in 8 hours (standard enterprise shift).
"""

import os
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Set

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

logger = logging.getLogger("SAHARYN_RBAC")

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "8"))   # One work shift

if not JWT_SECRET_KEY:
    logger.warning(
        "JWT_SECRET_KEY not set — using API key fallback only. "
        "Set JWT_SECRET_KEY in environment for full RBAC support."
    )


# ─────────────────────────────────────────────────────────────
# Role & Permission Definitions
# ─────────────────────────────────────────────────────────────

class Role(str, Enum):
    OPERATOR  = "operator"    # Field technicians, site operations crew
    ENGINEER  = "engineer"    # Process / maintenance engineers
    MANAGER   = "manager"     # Operations managers, site directors
    ADMIN     = "admin"       # System administrators, IT security


class Permission(str, Enum):
    # Telemetry & Monitoring
    READ_TELEMETRY          = "read:telemetry"
    READ_ALERTS             = "read:alerts"
    # AI Outputs
    READ_INFERENCE          = "read:inference"
    READ_CAUSAL_GRAPH       = "read:causal_graph"
    READ_RECOMMENDATIONS    = "read:recommendations"
    # Actions
    EXECUTE_RECOMMENDATION  = "execute:recommendation"
    APPROVE_MAINTENANCE     = "approve:maintenance"
    OVERRIDE_THRESHOLD      = "override:threshold"
    # Financial
    READ_FINANCIAL          = "read:financial"
    READ_ESG                = "read:esg"
    EXPORT_REPORT           = "export:report"
    # ML & Models
    READ_MODEL_METRICS      = "read:model_metrics"
    TRIGGER_RETRAIN         = "trigger:retrain"
    PROMOTE_MODEL           = "promote:model"
    # Security & Admin
    READ_AUDIT_LOG          = "read:audit_log"
    MANAGE_USERS            = "manage:users"
    MANAGE_SYSTEM           = "manage:system"
    VIEW_ALL_SITES          = "view:all_sites"


# Permission set for each role (additive — each role includes all lower permissions)
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.OPERATOR: {
        Permission.READ_TELEMETRY,
        Permission.READ_ALERTS,
        Permission.READ_INFERENCE,
        Permission.READ_RECOMMENDATIONS,
    },
    Role.ENGINEER: {
        Permission.READ_TELEMETRY,
        Permission.READ_ALERTS,
        Permission.READ_INFERENCE,
        Permission.READ_CAUSAL_GRAPH,
        Permission.READ_RECOMMENDATIONS,
        Permission.EXECUTE_RECOMMENDATION,
        Permission.READ_MODEL_METRICS,
        Permission.READ_ESG,
    },
    Role.MANAGER: {
        Permission.READ_TELEMETRY,
        Permission.READ_ALERTS,
        Permission.READ_INFERENCE,
        Permission.READ_CAUSAL_GRAPH,
        Permission.READ_RECOMMENDATIONS,
        Permission.EXECUTE_RECOMMENDATION,
        Permission.APPROVE_MAINTENANCE,
        Permission.OVERRIDE_THRESHOLD,
        Permission.READ_MODEL_METRICS,
        Permission.TRIGGER_RETRAIN,
        Permission.READ_FINANCIAL,
        Permission.READ_ESG,
        Permission.EXPORT_REPORT,
        Permission.READ_AUDIT_LOG,
        Permission.VIEW_ALL_SITES,
    },
    Role.ADMIN: {p for p in Permission},   # Admin has every permission
}


# ─────────────────────────────────────────────────────────────
# Token Models
# ─────────────────────────────────────────────────────────────

class TokenPayload(BaseModel):
    sub: str                     # User ID
    role: Role
    site_ids: List[str]          # Which sites this user can access ([] = all if ADMIN)
    exp: int                     # Unix timestamp expiry
    iat: int                     # Issued at
    jti: str                     # JWT ID (for revocation)


class UserContext(BaseModel):
    """Attached to every request after authentication. Available in all endpoints."""
    user_id: str
    role: Role
    permissions: Set[Permission]
    site_ids: List[str]
    token_id: str


# ─────────────────────────────────────────────────────────────
# Token Generation
# ─────────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    role: Role,
    site_ids: Optional[List[str]] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id:  The user's unique identifier
        role:     Their assigned role
        site_ids: List of site IDs they can access. Empty list = all sites (ADMIN only).

    Returns:
        Signed JWT string

    Raises:
        RuntimeError: If JWT is not configured
    """
    if not JWT_AVAILABLE or not JWT_SECRET_KEY:
        raise RuntimeError("JWT not configured. Set JWT_SECRET_KEY environment variable.")

    import uuid
    now = datetime.utcnow()
    expiry = now + timedelta(hours=TOKEN_EXPIRY_HOURS)

    payload = {
        "sub": user_id,
        "role": role.value,
        "site_ids": site_ids or [],
        "exp": int(expiry.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "iss": "saharyn-api",
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logger.info(f"Token issued: user={user_id} role={role.value} expires={expiry.isoformat()}")
    return token


# ─────────────────────────────────────────────────────────────
# Token Verification — FastAPI Dependencies
# ─────────────────────────────────────────────────────────────

security = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT. Raises HTTPException on any failure."""
    if not JWT_AVAILABLE or not JWT_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT authentication not configured on this server.",
        )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except JWTError as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
) -> UserContext:
    """
    FastAPI dependency: validates JWT Bearer token or API key fallback.
    Injects UserContext into every protected endpoint.

    Priority:
      1. JWT Bearer token (preferred — supports roles/sites)
      2. X-API-Key header (fallback — grants ADMIN role for service-to-service calls)
    """
    # --- JWT path ---
    if credentials and credentials.scheme == "Bearer":
        payload = _decode_token(credentials.credentials)
        permissions = ROLE_PERMISSIONS.get(Role(payload.role), set())
        return UserContext(
            user_id=payload.sub,
            role=Role(payload.role),
            permissions=permissions,
            site_ids=payload.site_ids,
            token_id=payload.jti,
        )

    # --- API key fallback (service accounts) ---
    api_key_secret = os.getenv("SAHARYN_API_KEY")
    if x_api_key and api_key_secret:
        # Constant-time comparison to prevent timing attacks
        if hmac.compare_digest(x_api_key.encode(), api_key_secret.encode()):
            return UserContext(
                user_id="service_account",
                role=Role.ADMIN,
                permissions=ROLE_PERMISSIONS[Role.ADMIN],
                site_ids=[],    # Empty = access all sites
                token_id="api_key_auth",
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission: Permission):
    """
    Factory for FastAPI dependencies that enforce a specific permission.

    Usage in endpoint:
        @app.get("/v2/financial/roi")
        async def get_roi(user: UserContext = Depends(require_permission(Permission.READ_FINANCIAL))):
            ...
    """
    def _check(user: UserContext = Depends(get_current_user)) -> UserContext:
        if permission not in user.permissions:
            logger.warning(
                f"ACCESS_DENIED: user={user.user_id} role={user.role} "
                f"attempted={permission} "
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required. Your role: {user.role}.",
            )
        return user
    return _check


def require_site_access(site_id: str, user: UserContext) -> None:
    """
    Validate that a user can access a specific site.
    ADMIN role and empty site_ids list = access to all sites.
    Raises HTTPException if access is denied.
    """
    if user.role == Role.ADMIN:
        return   # Admin always has access
    if user.site_ids and site_id not in user.site_ids:
        logger.warning(
            f"SITE_ACCESS_DENIED: user={user.user_id} role={user.role} "
            f"site={site_id} allowed={user.site_ids}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have access to site '{site_id}'.",
        )


# ─────────────────────────────────────────────────────────────
# Auth Endpoint Models (for /v2/auth/token endpoint)
# ─────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    user_id: str
    password: str
    site_ids: Optional[List[str]] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = TOKEN_EXPIRY_HOURS * 3600
    role: str
    permissions: List[str]
