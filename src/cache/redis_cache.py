"""
Redis Caching Service
Improves API performance with intelligent caching
"""
import json
import os
from typing import Optional, Any
from redis import Redis
from redis.exceptions import ConnectionError, RedisError
import hashlib


class RedisCache:
    """
    Redis caching service with automatic fallback
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", None)
        self.enabled = False
        self.client: Optional[Redis] = None

        if self.redis_url:
            try:
                self.client = Redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                self.client.ping()
                self.enabled = True
                print("✅ Redis cache enabled")
            except (ConnectionError, RedisError) as e:
                print(f"⚠️  Redis connection failed: {e}")
                print("   Cache disabled - running without Redis")
                self.enabled = False
                self.client = None
        else:
            print("⚠️  REDIS_URL not set - cache disabled")

    def _generate_key(self, prefix: str, data: dict) -> str:
        """
        Generate cache key from prefix and data
        """
        data_str = json.dumps(data, sort_keys=True)
        hash_str = hashlib.md5(data_str.encode()).hexdigest()
        return f"{prefix}:{hash_str}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        """
        if not self.enabled or not self.client:
            return None

        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except (ConnectionError, RedisError, json.JSONDecodeError) as e:
            print(f"⚠️  Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL (default 5 minutes)
        """
        if not self.enabled or not self.client:
            return False

        try:
            value_str = json.dumps(value)
            self.client.setex(key, ttl, value_str)
            return True
        except (ConnectionError, RedisError, TypeError) as e:
            print(f"⚠️  Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache
        """
        if not self.enabled or not self.client:
            return False

        try:
            self.client.delete(key)
            return True
        except (ConnectionError, RedisError) as e:
            print(f"⚠️  Cache delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern
        """
        if not self.enabled or not self.client:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except (ConnectionError, RedisError) as e:
            print(f"⚠️  Cache clear error: {e}")
            return 0

    async def cache_question_answer(self, question: str, subject: str, class_level: str, answer: dict, ttl: int = 3600) -> bool:
        """
        Cache AI question answer (1 hour default)
        """
        key = self._generate_key("qa", {
            "question": question.lower().strip(),
            "subject": subject,
            "class_level": class_level
        })
        return await self.set(key, answer, ttl)

    async def get_cached_question_answer(self, question: str, subject: str, class_level: str) -> Optional[dict]:
        """
        Get cached AI answer if available
        """
        key = self._generate_key("qa", {
            "question": question.lower().strip(),
            "subject": subject,
            "class_level": class_level
        })
        return await self.get(key)

    async def cache_user_progress(self, user_id: str, progress: dict, ttl: int = 600) -> bool:
        """
        Cache user progress (10 minutes)
        """
        key = f"progress:{user_id}"
        return await self.set(key, progress, ttl)

    async def get_cached_user_progress(self, user_id: str) -> Optional[dict]:
        """
        Get cached user progress
        """
        key = f"progress:{user_id}"
        return await self.get(key)

    async def invalidate_user_cache(self, user_id: str) -> int:
        """
        Clear all cache for a specific user
        """
        pattern = f"*:{user_id}:*"
        return await self.clear_pattern(pattern)

    def health_check(self) -> dict:
        """
        Check Redis health
        """
        if not self.enabled or not self.client:
            return {
                "status": "disabled",
                "message": "Redis not configured"
            }

        try:
            self.client.ping()
            info = self.client.info("stats")
            return {
                "status": "healthy",
                "connected": True,
                "total_connections": info.get("total_connections_received", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except (ConnectionError, RedisError) as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global cache instance
cache = RedisCache()
