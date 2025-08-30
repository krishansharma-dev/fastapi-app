from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class ArticleStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ArticleCategory(enum.Enum):
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    SCIENCE = "science"
    GENERAL = "general"
    POLITICS = "politics"


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String, unique=True, nullable=False)
    url_to_image = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    source_name = Column(String, nullable=True)
    author = Column(String, nullable=True)
    
    # Approval and categorization fields
    status = Column(Enum(ArticleStatus), default=ArticleStatus.PENDING)
    category = Column(Enum(ArticleCategory), nullable=True)
    approval_reason = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
