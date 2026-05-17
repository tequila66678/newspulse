"""Application configuration from environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/newspulse"
    supabase_db: str = ""
    fcm_credentials_path: str = "firebase-credentials.json"
    newsapi_key: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30
    embedding_threshold: float = 0.65
    digest_hour: int = 8
    digest_count: int = 15
    fetch_interval_minutes: int = 15
    supported_rss_urls: list[str] = [
        "https://36kr.com/feed",
        "https://sspai.com/feed",
        "https://www.ruanyifeng.com/blog/atom.xml",
        "https://feed.infoq.com/",
        "https://www.ifanr.com/feed",
    ]

    class Config:
        env_file = ".env"


settings = Settings()
