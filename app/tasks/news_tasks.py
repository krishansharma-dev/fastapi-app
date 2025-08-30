from celery import current_task
from app.core.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.article import Article, ArticleStatus, ArticleCategory
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def process_article_approval(self, article_id: int):
    """
    Background task to process article approval
    This is a simplified approval logic - in real world, this might involve
    content filtering, spam detection, etc.
    """
    db = SessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return {"status": "error", "message": "Article not found"}
        
        # Update task progress
        current_task.update_state(state="PROGRESS", meta={"progress": 25})
        
        # Simple approval logic based on content quality
        approval_score = 0
        approval_reasons = []
        
        # Check if title exists and is meaningful
        if article.title and len(article.title.strip()) > 10:
            approval_score += 30
        else:
            approval_reasons.append("Title too short or missing")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 50})
        
        # Check if description exists
        if article.description and len(article.description.strip()) > 20:
            approval_score += 25
        else:
            approval_reasons.append("Description too short or missing")
        
        # Check for spam-like content (simple check)
        spam_keywords = ["click here", "free money", "urgent", "!!!", "100% guaranteed"]
        title_lower = (article.title or "").lower()
        desc_lower = (article.description or "").lower()
        
        has_spam = any(keyword in title_lower or keyword in desc_lower for keyword in spam_keywords)
        if not has_spam:
            approval_score += 25
        else:
            approval_reasons.append("Contains potential spam content")
        
        current_task.update_state(state="PROGRESS", meta={"progress": 75})
        
        # Check URL validity
        if article.url and article.url.startswith(("http://", "https://")):
            approval_score += 20
        else:
            approval_reasons.append("Invalid or missing URL")
        
        # Determine approval status
        if approval_score >= 70:
            article.status = ArticleStatus.APPROVED
            article.approval_reason = "Article meets quality standards"
        else:
            article.status = ArticleStatus.REJECTED
            article.approval_reason = "; ".join(approval_reasons)
        
        article.processed_at = datetime.utcnow()
        db.commit()
        
        current_task.update_state(state="PROGRESS", meta={"progress": 100})
        
        logger.info(f"Article {article_id} processed: {article.status.value}")
        
        return {
            "status": "completed",
            "article_id": article_id,
            "approval_status": article.status.value,
            "approval_reason": article.approval_reason,
            "approval_score": approval_score
        }
        
    except Exception as e:
        logger.error(f"Error processing article {article_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True)
def categorize_article(self, article_id: int):
    """
    Background task to categorize articles based on content
    """
    db = SessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return {"status": "error", "message": "Article not found"}
        
        current_task.update_state(state="PROGRESS", meta={"progress": 25})
        
        # Simple keyword-based categorization
        title_content = (article.title or "").lower()
        desc_content = (article.description or "").lower()
        full_content = f"{title_content} {desc_content}"
        
        current_task.update_state(state="PROGRESS", meta={"progress": 50})
        
        # Define category keywords
        category_keywords = {
            ArticleCategory.TECHNOLOGY: ["tech", "ai", "software", "computer", "digital", "app", "coding", "programming"],
            ArticleCategory.BUSINESS: ["business", "economy", "finance", "market", "stock", "investment", "company"],
            ArticleCategory.SPORTS: ["sport", "football", "basketball", "soccer", "game", "player", "team", "match"],
            ArticleCategory.ENTERTAINMENT: ["movie", "music", "celebrity", "film", "tv", "show", "entertainment"],
            ArticleCategory.HEALTH: ["health", "medical", "doctor", "medicine", "hospital", "disease", "treatment"],
            ArticleCategory.SCIENCE: ["science", "research", "study", "discovery", "scientist", "experiment"],
            ArticleCategory.POLITICS: ["politics", "government", "election", "president", "minister", "policy", "vote"]
        }
        
        current_task.update_state(state="PROGRESS", meta={"progress": 75})
        
        # Score each category
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in full_content)
            if score > 0:
                category_scores[category] = score
        
        # Assign category with highest score
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            article.category = best_category
        else:
            article.category = ArticleCategory.GENERAL
        
        db.commit()
        
        current_task.update_state(state="PROGRESS", meta={"progress": 100})
        
        logger.info(f"Article {article_id} categorized as: {article.category.value}")
        
        return {
            "status": "completed",
            "article_id": article_id,
            "category": article.category.value,
            "category_scores": {cat.value: score for cat, score in category_scores.items()}
        }
        
    except Exception as e:
        logger.error(f"Error categorizing article {article_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True)
def process_fetched_articles(self, articles_data: list):
    """
    Background task to save fetched articles and trigger approval/categorization
    """
    db = SessionLocal()
    try:
        saved_articles = []
        
        for i, article_data in enumerate(articles_data):
            current_task.update_state(
                state="PROGRESS", 
                meta={"progress": int((i / len(articles_data)) * 100)}
            )
            
            # Check if article already exists
            existing_article = db.query(Article).filter(Article.url == article_data["url"]).first()
            if existing_article:
                continue
            
            # Create new article
            article = Article(**article_data)
            db.add(article)
            db.commit()
            db.refresh(article)
            
            saved_articles.append(article.id)
            
            # Trigger approval and categorization tasks
            process_article_approval.delay(article.id)
            categorize_article.delay(article.id)
        
        return {
            "status": "completed",
            "saved_articles_count": len(saved_articles),
            "saved_article_ids": saved_articles
        }
        
    except Exception as e:
        logger.error(f"Error processing articles: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
