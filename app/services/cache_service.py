import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.db.redis_client import redis_client
from app.models.article import Article, ArticleStatus, ArticleCategory
from app.models.schemas import Article as ArticleSchema

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self.redis_client = redis_client
        self.default_ttl = 3600  # 1 hour
        self.long_ttl = 86400  # 24 hours
        
    # Cache key generators
    def _article_key(self, article_id: int) -> str:
        return f"article:{article_id}"
    
    def _articles_list_key(self, status: Optional[str] = None, category: Optional[str] = None, 
                          skip: int = 0, limit: int = 20) -> str:
        filters = []
        if status:
            filters.append(f"status:{status}")
        if category:
            filters.append(f"category:{category}")
        filters.append(f"skip:{skip}")
        filters.append(f"limit:{limit}")
        return f"articles:list:{'_'.join(filters)}"
    
    def _category_articles_key(self, category: str) -> str:
        return f"articles:category:{category}"
    
    def _approved_articles_key(self) -> str:
        return "articles:approved"
    
    def _stats_key(self) -> str:
        return "articles:stats"
    
    # Article caching methods
    def cache_article(self, article: Article, ttl: Optional[int] = None) -> bool:
        """Cache a single article"""
        try:
            ttl = ttl or self.default_ttl
            key = self._article_key(article.id)
            
            # Convert article to dict for JSON serialization
            article_data = {
                "id": article.id,
                "title": article.title,
                "description": article.description,
                "content": article.content,
                "url": article.url,
                "url_to_image": article.url_to_image,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "source_name": article.source_name,
                "author": article.author,
                "status": article.status.value,
                "category": article.category.value if article.category else None,
                "approval_reason": article.approval_reason,
                "created_at": article.created_at.isoformat() if article.created_at else None,
                "updated_at": article.updated_at.isoformat() if article.updated_at else None,
                "processed_at": article.processed_at.isoformat() if article.processed_at else None,
            }
            
            self.redis_client.setex(key, ttl, json.dumps(article_data))
            logger.info(f"Cached article {article.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache article {article.id}: {str(e)}")
            return False
    
    def get_cached_article(self, article_id: int) -> Optional[Dict[str, Any]]:
        """Get cached article by ID"""
        try:
            key = self._article_key(article_id)
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached article {article_id}: {str(e)}")
            return None
    
    def cache_articles_list(self, articles: List[Article], status: Optional[str] = None, 
                           category: Optional[str] = None, skip: int = 0, limit: int = 20,
                           ttl: Optional[int] = None) -> bool:
        """Cache a list of articles with specific filters"""
        try:
            ttl = ttl or self.default_ttl
            key = self._articles_list_key(status, category, skip, limit)
            
            articles_data = []
            for article in articles:
                article_data = {
                    "id": article.id,
                    "title": article.title,
                    "description": article.description,
                    "content": article.content,
                    "url": article.url,
                    "url_to_image": article.url_to_image,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "source_name": article.source_name,
                    "author": article.author,
                    "status": article.status.value,
                    "category": article.category.value if article.category else None,
                    "approval_reason": article.approval_reason,
                    "created_at": article.created_at.isoformat() if article.created_at else None,
                    "updated_at": article.updated_at.isoformat() if article.updated_at else None,
                    "processed_at": article.processed_at.isoformat() if article.processed_at else None,
                }
                articles_data.append(article_data)
            
            self.redis_client.setex(key, ttl, json.dumps(articles_data))
            logger.info(f"Cached articles list with filters: status={status}, category={category}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache articles list: {str(e)}")
            return False
    
    def get_cached_articles_list(self, status: Optional[str] = None, category: Optional[str] = None,
                                skip: int = 0, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """Get cached articles list"""
        try:
            key = self._articles_list_key(status, category, skip, limit)
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached articles list: {str(e)}")
            return None
    
    def cache_approved_articles(self, articles: List[Article], ttl: Optional[int] = None) -> bool:
        """Cache approved articles for quick access"""
        try:
            ttl = ttl or self.long_ttl
            key = self._approved_articles_key()
            
            # Only cache approved articles
            approved_articles = [a for a in articles if a.status == ArticleStatus.APPROVED]
            
            articles_data = []
            for article in approved_articles:
                article_data = {
                    "id": article.id,
                    "title": article.title,
                    "description": article.description,
                    "url": article.url,
                    "url_to_image": article.url_to_image,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "source_name": article.source_name,
                    "author": article.author,
                    "category": article.category.value if article.category else None,
                    "created_at": article.created_at.isoformat() if article.created_at else None,
                }
                articles_data.append(article_data)
            
            self.redis_client.setex(key, ttl, json.dumps(articles_data))
            logger.info(f"Cached {len(approved_articles)} approved articles")
            return True
        except Exception as e:
            logger.error(f"Failed to cache approved articles: {str(e)}")
            return False
    
    def get_cached_approved_articles(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached approved articles"""
        try:
            key = self._approved_articles_key()
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached approved articles: {str(e)}")
            return None
    
    def cache_category_articles(self, category: str, articles: List[Article], ttl: Optional[int] = None) -> bool:
        """Cache articles by category"""
        try:
            ttl = ttl or self.default_ttl
            key = self._category_articles_key(category)
            
            # Filter articles by category and approved status
            category_articles = [
                a for a in articles 
                if a.category and a.category.value == category and a.status == ArticleStatus.APPROVED
            ]
            
            articles_data = []
            for article in category_articles:
                article_data = {
                    "id": article.id,
                    "title": article.title,
                    "description": article.description,
                    "url": article.url,
                    "url_to_image": article.url_to_image,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "source_name": article.source_name,
                    "author": article.author,
                    "created_at": article.created_at.isoformat() if article.created_at else None,
                }
                articles_data.append(article_data)
            
            self.redis_client.setex(key, ttl, json.dumps(articles_data))
            logger.info(f"Cached {len(category_articles)} articles for category: {category}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache category articles: {str(e)}")
            return False
    
    def get_cached_category_articles(self, category: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached articles by category"""
        try:
            key = self._category_articles_key(category)
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached category articles: {str(e)}")
            return None
    
    def cache_stats(self, stats: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache article statistics"""
        try:
            ttl = ttl or 300  # 5 minutes for stats
            key = self._stats_key()
            self.redis_client.setex(key, ttl, json.dumps(stats))
            logger.info("Cached article statistics")
            return True
        except Exception as e:
            logger.error(f"Failed to cache stats: {str(e)}")
            return False
    
    def get_cached_stats(self) -> Optional[Dict[str, Any]]:
        """Get cached article statistics"""
        try:
            key = self._stats_key()
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached stats: {str(e)}")
            return None
    
    # Cache invalidation methods
    def invalidate_article(self, article_id: int) -> bool:
        """Invalidate cache for a specific article"""
        try:
            key = self._article_key(article_id)
            self.redis_client.delete(key)
            logger.info(f"Invalidated cache for article {article_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate article cache: {str(e)}")
            return False
    
    def invalidate_articles_lists(self) -> bool:
        """Invalidate all cached article lists"""
        try:
            # Get all keys matching article list patterns
            patterns = ["articles:list:*", "articles:approved", "articles:category:*", "articles:stats"]
            keys_deleted = 0
            
            for pattern in patterns:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    keys_deleted += len(keys)
            
            logger.info(f"Invalidated {keys_deleted} cached article lists")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate article lists cache: {str(e)}")
            return False
    
    def invalidate_category_cache(self, category: str) -> bool:
        """Invalidate cache for a specific category"""
        try:
            key = self._category_articles_key(category)
            self.redis_client.delete(key)
            logger.info(f"Invalidated cache for category: {category}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate category cache: {str(e)}")
            return False
    
    def warm_cache(self, articles: List[Article]) -> bool:
        """Warm up the cache with articles"""
        try:
            # Cache individual articles
            for article in articles:
                self.cache_article(article)
            
            # Cache approved articles
            approved_articles = [a for a in articles if a.status == ArticleStatus.APPROVED]
            if approved_articles:
                self.cache_approved_articles(approved_articles)
            
            # Cache by categories
            for category in ArticleCategory:
                category_articles = [a for a in articles if a.category == category]
                if category_articles:
                    self.cache_category_articles(category.value, category_articles)
            
            logger.info(f"Warmed cache with {len(articles)} articles")
            return True
        except Exception as e:
            logger.error(f"Failed to warm cache: {str(e)}")
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information and statistics"""
        try:
            info = self.redis_client.info()
            
            # Count cached articles
            article_keys = self.redis_client.keys("article:*")
            list_keys = self.redis_client.keys("articles:list:*")
            category_keys = self.redis_client.keys("articles:category:*")
            
            return {
                "redis_info": {
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "uptime": info.get("uptime_in_seconds")
                },
                "cached_articles_count": len(article_keys),
                "cached_lists_count": len(list_keys),
                "cached_categories_count": len(category_keys),
                "has_approved_articles_cache": self.redis_client.exists(self._approved_articles_key()),
                "has_stats_cache": self.redis_client.exists(self._stats_key())
            }
        except Exception as e:
            logger.error(f"Failed to get cache info: {str(e)}")
            return {"error": str(e)}


# Create singleton instance
cache_service = CacheService()
