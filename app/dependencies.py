"""
JWT Auth Dependency — College Timetable System

Usage:
    from app.dependencies import get_current_admin

    @router.post("/endpoint")
    async def my_route(admin=Depends(get_current_admin)):
        ...  # admin = {"admin_id": str, "email": str}
"""

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

JWT_SECRET    = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

_bearer = HTTPBearer(auto_error=True)


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Verify the Bearer JWT from the Authorization header.
    Returns the decoded payload: {"admin_id": str, "email": str}.
    Raises HTTP 401 on any failure.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        admin_id: str = payload.get("sub")
        email: str    = payload.get("email")
        if not admin_id or not email:
            raise ValueError("Missing claims")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"admin_id": admin_id, "email": email}
