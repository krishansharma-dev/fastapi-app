from fastapi import FastAPI
from app.api.users import router as users_router
from app.api.news import router as news_router
from app.db.database import engine, Base
from app.core.config import settings
# Import models to ensure they are registered with SQLAlchemy
from app.models.user import User
from app.models.article import Article

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="FastAPI with PostgreSQL and Redis",
    description="A sample FastAPI application with PostgreSQL database and Redis caching",
    version="1.0.0"
)

# Include routers
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(news_router, prefix="/api/v1", tags=["news"])


@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI with PostgreSQL and Redis!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
