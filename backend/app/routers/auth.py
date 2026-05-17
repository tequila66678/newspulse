"""Authentication endpoints."""
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext

from app.auth import create_token, get_user_id_from_header
from app.database import get_pool
from app.models.tables import UserRegister, UserLogin, UserResponse, TokenResponse, FCMTokenUpdate

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=TokenResponse)
async def register(body: UserRegister):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", body.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = pwd_context.hash(body.password)
        row = await conn.fetchrow(
            "INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id, email, created_at",
            body.email, hashed,
        )
        token = create_token(row["id"])
        return TokenResponse(
            access_token=token,
            user=UserResponse(id=row["id"], email=row["email"], created_at=row["created_at"]),
        )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = $1", body.email
        )
        if not row or not pwd_context.verify(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_token(row["id"])
        return TokenResponse(
            access_token=token,
            user=UserResponse(id=row["id"], email=row["email"], created_at=row["created_at"]),
        )


@router.patch("/me/fcm-token")
async def update_fcm_token(body: FCMTokenUpdate, authorization: str):
    """Update device FCM token."""
    user_id = await get_user_id_from_header(authorization)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET fcm_token = $1 WHERE id = $2", body.fcm_token, user_id)
    return {"ok": True}
