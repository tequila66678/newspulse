"""Subscription management endpoints."""
from fastapi import APIRouter, Header
from app.auth import get_user_id_from_header
from app.database import get_pool
from app.models.tables import SubscriptionCreate, SubscriptionResponse, ListResponse

router = APIRouter()


@router.get("", response_model=ListResponse)
async def list_subscriptions(authorization: str = Header(...)):
    user_id = await get_user_id_from_header(authorization)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, user_id, keyword, type, created_at
               FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC""",
            user_id,
        )
    items = [SubscriptionResponse(**r) for r in rows]
    return ListResponse(items=items, total=len(items))


@router.post("", response_model=SubscriptionResponse)
async def create_subscription(body: SubscriptionCreate, authorization: str = Header(...)):
    user_id = await get_user_id_from_header(authorization)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO subscriptions (user_id, keyword, type) VALUES ($1, $2, $3)
               RETURNING id, user_id, keyword, type, created_at""",
            user_id, body.keyword, body.type,
        )
    return SubscriptionResponse(**row)


@router.delete("/{subscription_id}")
async def delete_subscription(subscription_id: int, authorization: str = Header(...)):
    user_id = await get_user_id_from_header(authorization)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM subscriptions WHERE id = $1 AND user_id = $2",
            subscription_id, user_id,
        )
    return {"ok": True}
