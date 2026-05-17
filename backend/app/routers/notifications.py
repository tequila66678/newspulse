"""Notification endpoints."""
from fastapi import APIRouter, Header, Query
from app.auth import get_user_id_from_header
from app.database import get_pool
from app.models.tables import NotificationResponse, ArticleResponse, ListResponse

router = APIRouter()


@router.get("", response_model=ListResponse)
async def list_notifications(
    authorization: str = Header(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    n_type: str = Query("track", pattern="^(track|daily)$"),
):
    user_id = await get_user_id_from_header(authorization)
    pool = await get_pool()
    offset = (page - 1) * page_size
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT n.id, n.article_id, n.type, n.sent_at, n.read,
                      a.id as a_id, a.title, a.summary, a.source, a.source_url, a.published_at, a.score
               FROM notifications n
               LEFT JOIN articles a ON n.article_id = a.id
               WHERE n.user_id = $1 AND n.type = $2
               ORDER BY n.sent_at DESC LIMIT $3 OFFSET $4""",
            user_id, n_type, page_size, offset,
        )
        total_row = await conn.fetchrow(
            "SELECT COUNT(*) as c FROM notifications WHERE user_id = $1 AND type = $2",
            user_id, n_type,
        )
    items = []
    for r in rows:
        article = None
        if r["a_id"]:
            article = ArticleResponse(
                id=r["a_id"], title=r["title"], summary=r["summary"],
                source=r["source"], source_url=r["source_url"],
                published_at=r["published_at"], score=r["score"],
            )
        items.append(NotificationResponse(
            id=r["id"], article_id=r["article_id"], type=r["type"],
            sent_at=r["sent_at"], read=r["read"], article=article,
        ))
    return ListResponse(items=items, total=total_row["c"])


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: int, authorization: str = Header(...)):
    user_id = await get_user_id_from_header(authorization)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE notifications SET read = TRUE WHERE id = $1 AND user_id = $2",
            notification_id, user_id,
        )
    return {"ok": True}
