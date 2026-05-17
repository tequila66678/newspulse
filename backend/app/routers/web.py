"""Web page endpoints."""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from app.database import get_pool

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def root():
    return RedirectResponse(url="/web")


@router.get("/web")
async def web_feed(request: Request):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT title, summary, source, source_url, score, published_at
               FROM articles ORDER BY published_at DESC LIMIT 100"""
        )
        total = await conn.fetchrow("SELECT COUNT(*) as c FROM articles")

    articles = [dict(r) for r in rows]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "articles": articles, "total": total["c"]},
    )
