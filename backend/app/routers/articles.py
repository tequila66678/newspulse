"""Article feed endpoints."""
from fastapi import APIRouter, Header, Query
from app.auth import get_user_id_from_header
from app.database import get_pool
from app.models.tables import ArticleResponse, ListResponse

router = APIRouter()


@router.get("", response_model=ListResponse)
async def list_articles(
    authorization: str = Header(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    await get_user_id_from_header(authorization)
    pool = await get_pool()
    offset = (page - 1) * page_size
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, title, summary, source, source_url, published_at, score
               FROM articles ORDER BY published_at DESC LIMIT $1 OFFSET $2""",
            page_size, offset,
        )
        total_row = await conn.fetchrow("SELECT COUNT(*) as c FROM articles")
    items = [ArticleResponse(**r) for r in rows]
    return ListResponse(items=items, total=total_row["c"])


@router.get("/digest/{date}", response_model=ListResponse)
async def get_daily_digest(date: str, authorization: str = Header(...)):
    await get_user_id_from_header(authorization)
    pool = await get_pool()
    async with pool.acquire() as conn:
        digest = await conn.fetchrow(
            "SELECT article_ids FROM daily_digests WHERE date = $1::date", date
        )
        if not digest:
            return ListResponse(items=[], total=0)
        ids = digest["article_ids"]
        rows = await conn.fetch(
            "SELECT id, title, summary, source, source_url, published_at, score FROM articles WHERE id = ANY($1)",
            ids,
        )
    items = [ArticleResponse(**r) for r in rows]
    return ListResponse(items=items, total=len(items))
