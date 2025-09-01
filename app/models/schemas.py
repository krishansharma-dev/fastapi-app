from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional
from datetime import datetime
from enum import Enum


# News Article Schemas
class ArticleStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ArticleCategoryEnum(str, Enum):
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    SCIENCE = "science"
    GENERAL = "general"
    POLITICS = "politics"


class ArticleBase(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    url: str
    url_to_image: Optional[str] = None
    published_at: Optional[datetime] = None
    source_name: Optional[str] = None
    author: Optional[str] = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    status: Optional[ArticleStatusEnum] = None
    category: Optional[ArticleCategoryEnum] = None
    approval_reason: Optional[str] = None


class Article(ArticleBase):
    id: int
    status: ArticleStatusEnum
    category: Optional[ArticleCategoryEnum] = None
    approval_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NewsRequest(BaseModel):
    query: str
    language: Optional[str] = "en"
    sort_by: Optional[str] = "publishedAt"
    page_size: Optional[int] = 20
    page: Optional[int] = 1


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str