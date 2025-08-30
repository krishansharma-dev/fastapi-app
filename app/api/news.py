from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.article import Article, ArticleStatus, ArticleCategory
from app.models.schemas import (
    Article as ArticleSchema,
    ArticleUpdate,
    NewsRequest,
    TaskResponse,
    ArticleStatusEnum,
    ArticleCategoryEnum
)
from app.services.news_service import news_service
from app.tasks.news_tasks import process_fetched_articles, process_article_approval, categorize_article
from app.core.celery_app import celery_app

router = APIRouter()


@router.post("/news/fetch", response_model=TaskResponse)
async def fetch_news(news_request: NewsRequest, db: Session = Depends(get_db)):
    """
    Fetch news articles from NewsAPI and process them in background
    """
    try:
        # Fetch articles from NewsAPI
        response = await news_service.fetch_articles(
            query=news_request.query,
            language=news_request.language,
            sort_by=news_request.sort_by,
            page_size=news_request.page_size,
            page=news_request.page
        )
        
        if response.get("status") != "ok":
            raise HTTPException(status_code=400, detail="Failed to fetch news from NewsAPI")
        
        articles = response.get("articles", [])
        if not articles:
            raise HTTPException(status_code=404, detail="No articles found for the given query")
        
        # Parse articles for our database format
        parsed_articles = []
        for article_data in articles:
            try:
                parsed_article = news_service.parse_article(article_data)
                parsed_articles.append(parsed_article)
            except Exception as e:
                continue  # Skip invalid articles
        
        # Start background processing
        task = process_fetched_articles.delay(parsed_articles)
        
        return TaskResponse(
            task_id=task.id,
            status="processing",
            message=f"Started processing {len(parsed_articles)} articles"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles", response_model=List[ArticleSchema])
def get_articles(
    skip: int = 0,
    limit: int = 20,
    status: Optional[ArticleStatusEnum] = None,
    category: Optional[ArticleCategoryEnum] = None,
    db: Session = Depends(get_db)
):
    """
    Get articles with optional filtering by status and category
    """
    query = db.query(Article)
    
    if status:
        query = query.filter(Article.status == ArticleStatus(status.value))
    
    if category:
        query = query.filter(Article.category == ArticleCategory(category.value))
    
    articles = query.offset(skip).limit(limit).all()
    return articles


@router.get("/articles/{article_id}", response_model=ArticleSchema)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """
    Get a specific article by ID
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.put("/articles/{article_id}", response_model=ArticleSchema)
def update_article(
    article_id: int,
    article_update: ArticleUpdate,
    db: Session = Depends(get_db)
):
    """
    Update article status, category, or approval reason
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Update fields
    update_data = article_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "status" and value:
            setattr(article, key, ArticleStatus(value.value))
        elif key == "category" and value:
            setattr(article, key, ArticleCategory(value.value))
        else:
            setattr(article, key, value)
    
    db.commit()
    db.refresh(article)
    return article


@router.post("/articles/{article_id}/reprocess", response_model=TaskResponse)
def reprocess_article(article_id: int, db: Session = Depends(get_db)):
    """
    Trigger reprocessing (approval and categorization) for a specific article
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Trigger both approval and categorization tasks
    approval_task = process_article_approval.delay(article_id)
    categorize_article.delay(article_id)
    
    return TaskResponse(
        task_id=approval_task.id,
        status="processing",
        message=f"Started reprocessing article {article_id}"
    )


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    """
    Get the status of a Celery task
    """
    task_result = celery_app.AsyncResult(task_id)
    
    if task_result.state == "PENDING":
        response = {
            "task_id": task_id,
            "status": "pending",
            "message": "Task is waiting to be processed"
        }
    elif task_result.state == "PROGRESS":
        response = {
            "task_id": task_id,
            "status": "processing",
            "message": "Task is being processed",
            "progress": task_result.info.get("progress", 0)
        }
    elif task_result.state == "SUCCESS":
        response = {
            "task_id": task_id,
            "status": "completed",
            "message": "Task completed successfully",
            "result": task_result.result
        }
    else:  # FAILURE
        response = {
            "task_id": task_id,
            "status": "failed",
            "message": "Task failed",
            "error": str(task_result.info)
        }
    
    return response


@router.get("/articles/stats/summary")
def get_articles_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics of articles
    """
    total_articles = db.query(Article).count()
    pending_articles = db.query(Article).filter(Article.status == ArticleStatus.PENDING).count()
    approved_articles = db.query(Article).filter(Article.status == ArticleStatus.APPROVED).count()
    rejected_articles = db.query(Article).filter(Article.status == ArticleStatus.REJECTED).count()
    
    # Category distribution
    category_stats = {}
    for category in ArticleCategory:
        count = db.query(Article).filter(Article.category == category).count()
        category_stats[category.value] = count
    
    return {
        "total_articles": total_articles,
        "status_distribution": {
            "pending": pending_articles,
            "approved": approved_articles,
            "rejected": rejected_articles
        },
        "category_distribution": category_stats
    }
