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
from app.services.cache_service import cache_service
from app.tasks.news_tasks import process_fetched_articles, process_article_approval, categorize_article, warm_cache_task
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
    use_cache: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get articles with optional filtering by status and category
    Uses Redis cache for improved performance
    """
    # Try to get from cache first
    if use_cache:
        status_str = status.value if status else None
        category_str = category.value if category else None
        cached_articles = cache_service.get_cached_articles_list(
            status=status_str, 
            category=category_str, 
            skip=skip, 
            limit=limit
        )
        if cached_articles:
            return cached_articles
    
    # If not in cache, query database
    query = db.query(Article)
    
    if status:
        query = query.filter(Article.status == ArticleStatus(status.value))
    
    if category:
        query = query.filter(Article.category == ArticleCategory(category.value))
    
    articles = query.offset(skip).limit(limit).all()
    
    # Cache the results for future requests
    if use_cache and articles:
        status_str = status.value if status else None
        category_str = category.value if category else None
        cache_service.cache_articles_list(
            articles, 
            status=status_str, 
            category=category_str, 
            skip=skip, 
            limit=limit
        )
    
    return articles


@router.get("/articles/{article_id}", response_model=ArticleSchema)
def get_article(article_id: int, use_cache: bool = True, db: Session = Depends(get_db)):
    """
    Get a specific article by ID with caching support
    """
    # Try cache first
    if use_cache:
        cached_article = cache_service.get_cached_article(article_id)
        if cached_article:
            return cached_article
    
    # Query database if not in cache
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Cache the article for future requests
    if use_cache:
        cache_service.cache_article(article)
    
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
    
    # Update cache with the modified article
    cache_service.cache_article(article)
    
    # Invalidate article lists to reflect changes
    cache_service.invalidate_articles_lists()
    
    # If category was updated and article is approved, update category cache
    if "category" in update_data and article.status == ArticleStatus.APPROVED:
        category_articles = db.query(Article).filter(
            Article.category == article.category,
            Article.status == ArticleStatus.APPROVED
        ).all()
        cache_service.cache_category_articles(article.category.value, category_articles)
    
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
def get_articles_summary(use_cache: bool = True, db: Session = Depends(get_db)):
    """
    Get summary statistics of articles with caching support
    """
    # Try cache first
    if use_cache:
        cached_stats = cache_service.get_cached_stats()
        if cached_stats:
            return cached_stats
    
    # Calculate stats from database
    total_articles = db.query(Article).count()
    pending_articles = db.query(Article).filter(Article.status == ArticleStatus.PENDING).count()
    approved_articles = db.query(Article).filter(Article.status == ArticleStatus.APPROVED).count()
    rejected_articles = db.query(Article).filter(Article.status == ArticleStatus.REJECTED).count()
    
    # Category distribution (only approved articles)
    category_stats = {}
    for category in ArticleCategory:
        count = db.query(Article).filter(
            Article.category == category,
            Article.status == ArticleStatus.APPROVED
        ).count()
        category_stats[category.value] = count
    
    stats = {
        "total_articles": total_articles,
        "status_distribution": {
            "pending": pending_articles,
            "approved": approved_articles,
            "rejected": rejected_articles
        },
        "category_distribution": category_stats
    }
    
    # Cache the stats
    if use_cache:
        cache_service.cache_stats(stats)
    
    return stats


# Cache Management Endpoints
@router.post("/cache/warm", response_model=TaskResponse)
def warm_cache(db: Session = Depends(get_db)):
    """
    Trigger cache warming as a background task
    """
    task = warm_cache_task.delay()
    
    return TaskResponse(
        task_id=task.id,
        status="processing",
        message="Started cache warming process"
    )


@router.delete("/cache/invalidate")
def invalidate_cache():
    """
    Invalidate all cached articles and lists
    """
    try:
        # Invalidate article lists and stats
        cache_service.invalidate_articles_lists()
        
        # Invalidate individual articles
        article_keys = cache_service.redis_client.keys("article:*")
        if article_keys:
            cache_service.redis_client.delete(*article_keys)
        
        # Invalidate NewsAPI cache
        newsapi_keys = cache_service.redis_client.keys("newsapi:*")
        if newsapi_keys:
            cache_service.redis_client.delete(*newsapi_keys)
        
        return {
            "message": "All caches invalidated successfully",
            "invalidated_keys": len(article_keys) + len(newsapi_keys)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to invalidate cache: {str(e)}")


@router.delete("/cache/articles/{article_id}")
def invalidate_article_cache(article_id: int):
    """
    Invalidate cache for a specific article
    """
    try:
        success = cache_service.invalidate_article(article_id)
        if success:
            return {"message": f"Cache invalidated for article {article_id}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to invalidate article cache")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/category/{category}")
def invalidate_category_cache(category: str):
    """
    Invalidate cache for a specific category
    """
    try:
        # Validate category
        valid_categories = [cat.value for cat in ArticleCategory]
        if category not in valid_categories:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid category. Must be one of: {valid_categories}"
            )
        
        success = cache_service.invalidate_category_cache(category)
        if success:
            return {"message": f"Cache invalidated for category: {category}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to invalidate category cache")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/info")
def get_cache_info():
    """
    Get information about the current cache state
    """
    try:
        cache_info = cache_service.get_cache_info()
        return cache_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/approved", response_model=List[ArticleSchema])
def get_approved_articles(use_cache: bool = True, db: Session = Depends(get_db)):
    """
    Get approved articles with caching (optimized endpoint for public use)
    """
    # Try cache first
    if use_cache:
        cached_articles = cache_service.get_cached_approved_articles()
        if cached_articles:
            return cached_articles
    
    # Query database if not in cache
    articles = db.query(Article).filter(
        Article.status == ArticleStatus.APPROVED
    ).order_by(Article.created_at.desc()).limit(50).all()
    
    # Cache the results
    if use_cache:
        cache_service.cache_approved_articles(articles)
    
    return articles


@router.get("/articles/category/{category}", response_model=List[ArticleSchema])
def get_articles_by_category(category: str, use_cache: bool = True, db: Session = Depends(get_db)):
    """
    Get approved articles by category with caching
    """
    # Validate category
    valid_categories = [cat.value for cat in ArticleCategory]
    if category not in valid_categories:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid category. Must be one of: {valid_categories}"
        )
    
    # Try cache first
    if use_cache:
        cached_articles = cache_service.get_cached_category_articles(category)
        if cached_articles:
            return cached_articles
    
    # Query database if not in cache
    articles = db.query(Article).filter(
        Article.category == ArticleCategory(category),
        Article.status == ArticleStatus.APPROVED
    ).order_by(Article.created_at.desc()).limit(50).all()
    
    # Cache the results
    if use_cache:
        cache_service.cache_category_articles(category, articles)
    
    return articles
