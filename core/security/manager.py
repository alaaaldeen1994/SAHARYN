import logging
import os
from typing import List, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel

# Enterprise Cryptography Settings
SECRET_KEY = os.getenv("JWT_SECRET", "industrial-zero-trust-2024-alpha")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger("SecurityManager")

class User(BaseModel):
    username: str
    role: str # 'OPERATOR', 'MANAGER', 'ADMIN'
    disabled: Optional[bool] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class SecurityManager:
    """
    Zero-Trust Security & RBAC Manager for OT-IT Integration.
    Ensures every request to the API is authenticated and logged for ISO27001 compliance.
    """

    def __init__(self):
        self.audit_log_path = "data/audit/access_logs.csv"
        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[User]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            role: str = payload.get("role")
            if username is None:
                return None
            return User(username=username, role=role)
        except JWTError:
            return None

    def audit_log(self, user: str, action: str, resource: str, status: str):
        """
        Immutable-style audit logging for compliance.
        In production, this would stream to Webhook / SIEM (Splunk/Sentinel).
        """
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp},{user},{action},{resource},{status}\n"
        with open(self.audit_log_path, "a") as f:
            f.write(log_entry)

        logger.info(f"AUDIT: {user} performed {action} on {resource} - STATUS: {status}")

    def authorize_role(self, user: User, allowed_roles: List[str]) -> bool:
        """
        Role-Based Access Control (RBAC) check.
        """
        if user.role in allowed_roles:
            return True
        self.audit_log(user.username, "UNAUTHORIZED_ACCESS_ATTEMPT", "RBAC_CHECK", "DENIED")
        return False

if __name__ == "__main__":
    sec = SecurityManager()
    token = sec.create_access_token({"sub": "tariq_ops", "role": "OPERATOR"})
    user = sec.verify_token(token)
    if user:
        authorized = sec.authorize_role(user, ["MANAGER", "ADMIN"])
        print(f"User {user.username} ({user.role}) Auth Status: {authorized}")
