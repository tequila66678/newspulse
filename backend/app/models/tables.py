"""Pydantic models for request/response validation."""
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SubscriptionCreate(BaseModel):
    keyword: str
    type: str = "topic"


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    keyword: str
    type: str
    created_at: datetime


class ArticleResponse(BaseModel):
    id: int
    title: str
    summary: str | None
    source: str
    source_url: str
    published_at: datetime | None
    score: float


class NotificationResponse(BaseModel):
    id: int
    article_id: int
    type: str
    sent_at: datetime
    read: bool
    article: ArticleResponse | None


class FCMTokenUpdate(BaseModel):
    fcm_token: str


class ListResponse(BaseModel):
    items: list
    total: int
