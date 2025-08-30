import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class NewsAPIService:
    def __init__(self):
        self.base_url = settings.news_api_url
        self.api_key = settings.news_api_key
    
    async def fetch_articles(
        self,
        query: str,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 20,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Fetch articles from NewsAPI
        """
        params = {
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": page_size,
            "page": page,
            "apiKey": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to fetch news: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise Exception("Failed to connect to NewsAPI")
    
    def parse_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse article data from NewsAPI response to our format
        """
        published_at = None
        if article_data.get("publishedAt"):
            try:
                published_at = datetime.fromisoformat(
                    article_data["publishedAt"].replace("Z", "+00:00")
                )
            except ValueError:
                pass
        
        return {
            "title": article_data.get("title", ""),
            "description": article_data.get("description"),
            "content": article_data.get("content"),
            "url": article_data.get("url", ""),
            "url_to_image": article_data.get("urlToImage"),
            "published_at": published_at,
            "source_name": article_data.get("source", {}).get("name"),
            "author": article_data.get("author")
        }


# Create singleton instance
news_service = NewsAPIService()
