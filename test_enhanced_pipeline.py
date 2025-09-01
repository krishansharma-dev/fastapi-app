#!/usr/bin/env python3
"""
Test script for the enhanced news processing pipeline
"""

import asyncio
import httpx
import time
import json
from typing import Dict, Any


class PipelineTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def test_news_fetching(self) -> Dict[str, Any]:
        """Test news fetching with background processing"""
        print("🔍 Testing news fetching...")
        
        payload = {
            "query": "artificial intelligence",
            "page_size": 5,
            "language": "en"
        }
        
        response = await self.client.post(f"{self.base_url}/news/fetch", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ News fetch initiated. Task ID: {result['task_id']}")
            return result
        else:
            print(f"❌ News fetch failed: {response.text}")
            return {"error": response.text}
    
    async def monitor_task(self, task_id: str, max_wait: int = 120) -> Dict[str, Any]:
        """Monitor task progress until completion"""
        print(f"📊 Monitoring task {task_id}...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = await self.client.get(f"{self.base_url}/tasks/{task_id}")
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("status")
                
                if status == "completed":
                    print(f"✅ Task completed: {result.get('message')}")
                    return result
                elif status == "failed":
                    print(f"❌ Task failed: {result.get('error')}")
                    return result
                elif status == "processing":
                    progress = result.get("progress", 0)
                    print(f"⏳ Task in progress: {progress}%")
                else:
                    print(f"⏳ Task status: {status}")
            
            await asyncio.sleep(2)
        
        print(f"⏰ Task monitoring timed out after {max_wait} seconds")
        return {"status": "timeout"}
    
    async def test_cache_operations(self):
        """Test cache operations"""
        print("\\n🔄 Testing cache operations...")
        
        # Test cache info
        response = await self.client.get(f"{self.base_url}/cache/info")
        if response.status_code == 200:
            cache_info = response.json()
            print(f"📈 Cache info: {cache_info.get('cached_articles_count', 0)} articles cached")
        
        # Test cache warming
        print("🔥 Starting cache warming...")
        response = await self.client.post(f"{self.base_url}/cache/warm")
        if response.status_code == 200:
            warm_result = response.json()
            task_id = warm_result.get("task_id")
            print(f"✅ Cache warming started. Task ID: {task_id}")
            
            # Monitor warming task
            await self.monitor_task(task_id, max_wait=60)
        
        # Check cache info again
        response = await self.client.get(f"{self.base_url}/cache/info")
        if response.status_code == 200:
            cache_info = response.json()
            print(f"📈 After warming: {cache_info.get('cached_articles_count', 0)} articles cached")
    
    async def test_article_retrieval(self):
        """Test article retrieval with caching"""
        print("\\n📄 Testing article retrieval...")
        
        # Test getting approved articles (should use cache)
        start_time = time.time()
        response = await self.client.get(f"{self.base_url}/articles/approved")
        cache_time = time.time() - start_time
        
        if response.status_code == 200:
            articles = response.json()
            print(f"✅ Retrieved {len(articles)} approved articles in {cache_time:.3f}s (cached)")
        
        # Test getting articles by category
        start_time = time.time()
        response = await self.client.get(f"{self.base_url}/articles/category/technology")
        category_time = time.time() - start_time
        
        if response.status_code == 200:
            tech_articles = response.json()
            print(f"✅ Retrieved {len(tech_articles)} technology articles in {category_time:.3f}s")
        
        # Test general articles endpoint
        start_time = time.time()
        response = await self.client.get(f"{self.base_url}/articles?status=approved&limit=10")
        db_time = time.time() - start_time
        
        if response.status_code == 200:
            filtered_articles = response.json()
            print(f"✅ Retrieved {len(filtered_articles)} filtered articles in {db_time:.3f}s")
    
    async def test_statistics(self):
        """Test statistics retrieval"""
        print("\\n📊 Testing statistics...")
        
        response = await self.client.get(f"{self.base_url}/articles/stats/summary")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Statistics retrieved:")
            print(f"   Total articles: {stats.get('total_articles', 0)}")
            print(f"   Approved: {stats.get('status_distribution', {}).get('approved', 0)}")
            print(f"   Pending: {stats.get('status_distribution', {}).get('pending', 0)}")
            print(f"   Rejected: {stats.get('status_distribution', {}).get('rejected', 0)}")
            
            category_dist = stats.get('category_distribution', {})
            print(f"   Category distribution: {category_dist}")
    
    async def run_full_test(self):
        """Run complete pipeline test"""
        print("🚀 Starting Enhanced News Pipeline Test\\n")
        
        try:
            # Step 1: Test news fetching
            fetch_result = await self.test_news_fetching()
            if "task_id" in fetch_result:
                # Monitor the fetching task
                await self.monitor_task(fetch_result["task_id"])
            
            # Step 2: Test cache operations
            await self.test_cache_operations()
            
            # Step 3: Test article retrieval
            await self.test_article_retrieval()
            
            # Step 4: Test statistics
            await self.test_statistics()
            
            print("\\n🎉 All tests completed successfully!")
            
        except Exception as e:
            print(f"\\n❌ Test failed with error: {str(e)}")
        
        finally:
            await self.client.aclose()


async def main():
    """Main test function"""
    test = PipelineTest()
    await test.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())
