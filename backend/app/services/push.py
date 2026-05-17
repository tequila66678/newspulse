"""Push notification service via Firebase Cloud Messaging."""
import firebase_admin
from firebase_admin import credentials, messaging


_initialized = False


def _init_firebase():
    global _initialized
    if _initialized:
        return
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)
    _initialized = True


def send_track_push(fcm_token: str, title: str, body: str, article_id: int) -> str | None:
    """Send an instant tracking push to a single device."""
    if not fcm_token:
        return None
    _init_firebase()
    message = messaging.Message(
        token=fcm_token,
        notification=messaging.Notification(title=f"📡 {title}"[:100], body=body[:200]),
        data={"article_id": str(article_id), "type": "track"},
    )
    try:
        result = messaging.send(message)
        return result
    except messaging.UnregisteredError:
        return None


def send_daily_digest_push(fcm_token: str, digest_title: str, digest_id: int) -> str | None:
    """Send daily digest push to a single device."""
    if not fcm_token:
        return None
    _init_firebase()
    message = messaging.Message(
        token=fcm_token,
        notification=messaging.Notification(
            title="📰 每日精选",
            body=digest_title[:200],
        ),
        data={"digest_id": str(digest_id), "type": "daily"},
    )
    try:
        result = messaging.send(message)
        return result
    except messaging.UnregisteredError:
        return None


async def broadcast_daily_digest(digest_id: int, digest_title: str):
    """Send daily digest to all users with FCM tokens."""
    from app.database import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT fcm_token FROM users WHERE fcm_token IS NOT NULL")
        for row in rows:
            send_daily_digest_push(row["fcm_token"], digest_title, digest_id)


async def send_track_to_user(user_id: int, title: str, body: str, article_id: int):
    """Send track push to a specific user."""
    from app.database import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT fcm_token FROM users WHERE id = $1 AND fcm_token IS NOT NULL", user_id)
        if row:
            send_track_push(row["fcm_token"], title, body, article_id)
