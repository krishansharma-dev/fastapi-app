from fastapi import FastAPI

from app.api.news import router as news_router
from app.db.database import engine, Base
from app.core.config import settings
# Import models to ensure they are registered with SQLAlchemy
from app.models.article import Article
# Import services to ensure they are initialized
from app.services.cache_service import cache_service

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Enhanced News Processing Pipeline",
    description="FastAPI application with background processing, approval logic, categorization, PostgreSQL storage, and Redis caching",
    version="2.0.0"
)

# Include routers
app.include_router(news_router, prefix="/api/v1", tags=["news"])


@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI with PostgreSQL and Redis!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
