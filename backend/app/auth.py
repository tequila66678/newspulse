"""Shared auth utilities."""
from datetime import datetime, timezone, timedelta

from jose import jwt

from app.config import settings


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def verify_token(token: str) -> int:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return int(payload["sub"])


async def get_user_id_from_header(authorization: str) -> int:
    """Extract user ID from Bearer token header."""
    from fastapi import HTTPException
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    try:
        return verify_token(authorization[7:])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
