"""
AI Response Cache

Caches AI responses to reduce latency and API costs.

Features:
- Semantic similarity-based cache lookup
- Configurable TTL by query type
- Cache warming for popular questions
- Analytics and hit rate tracking
- Cache invalidation on curriculum updates
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from src.logging.logger import logger


@dataclass
class CachedResponse:
    """Cached AI response"""
    query_hash: str
    query: str
    response: str
    metadata: Dict[str, Any]
    cached_at: datetime
    hit_count: int = 0
    last_accessed: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "query_hash": self.query_hash,
            "query": self.query,
            "response": self.response,
            "metadata": self.metadata,
            "cached_at": self.cached_at.isoformat(),
            "hit_count": self.hit_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedResponse":
        """Create from dictionary"""
        return cls(
            query_hash=data["query_hash"],
            query=data["query"],
            response=data["response"],
            metadata=data["metadata"],
            cached_at=datetime.fromisoformat(data["cached_at"]),
            hit_count=data.get("hit_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None
        )


class AIResponseCache:
    """
    Caches AI responses with intelligent lookup and TTL management.

    Cache Strategy:
    - Factual questions: 7 days TTL
    - Practice questions: 1 day TTL (encourage variety)
    - Curriculum content: 30 days TTL
    - Diagnostic results: No cache (personalized)
    """

    # TTL configurations (in seconds)
    TTL_CONFIGS = {
        "factual": 7 * 24 * 3600,  # 7 days
        "practice": 1 * 24 * 3600,  # 1 day
        "curriculum": 30 * 24 * 3600,  # 30 days
        "explanation": 7 * 24 * 3600,  # 7 days
        "default": 3 * 24 * 3600,  # 3 days
    }

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        use_redis: bool = True,
        similarity_threshold: float = 0.95
    ):
        """
        Initialize AI response cache

        Args:
            redis_client: Redis client for caching
            use_redis: Whether to use Redis (falls back to memory)
            similarity_threshold: Threshold for semantic cache hit (0-1)
        """
        self.redis_client = redis_client
        self.use_redis = use_redis and REDIS_AVAILABLE and redis_client is not None
        self.similarity_threshold = similarity_threshold

        # In-memory fallback
        self._memory_cache: Dict[str, CachedResponse] = {}

        # Statistics
        self._total_lookups = 0
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info(
            f"AIResponseCache initialized (Redis: {self.use_redis}, "
            f"Similarity threshold: {similarity_threshold})"
        )

    def _get_cache_key(self, query_hash: str) -> str:
        """Get Redis cache key"""
        return f"ai_response:{query_hash}"

    def _hash_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate hash for query with context"""
        # Normalize query
        normalized_query = query.lower().strip()

        # Include relevant context in hash
        context_str = ""
        if context:
            # Only include relevant context fields
            relevant_keys = ["subject", "class_level", "query_type"]
            context_parts = [
                f"{k}:{context.get(k)}"
                for k in relevant_keys
                if context.get(k)
            ]
            context_str = "|".join(context_parts)

        # Combine and hash
        cache_input = f"{normalized_query}|{context_str}"
        return hashlib.sha256(cache_input.encode()).hexdigest()

    async def get(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Get cached response

        Args:
            query: User query
            context: Query context (subject, class level, etc.)

        Returns:
            Cached response or None
        """
        self._total_lookups += 1

        query_hash = self._hash_query(query, context)

        # Try Redis first
        if self.use_redis:
            try:
                cache_key = self._get_cache_key(query_hash)
                data = await self.redis_client.get(cache_key)

                if data:
                    cached = CachedResponse.from_dict(json.loads(data))

                    # Update access stats
                    cached.hit_count += 1
                    cached.last_accessed = datetime.utcnow()

                    # Save updated stats
                    await self._save_cached_response(cached)

                    self._cache_hits += 1
                    logger.info(f"Cache HIT for query hash: {query_hash[:8]}... (hits: {cached.hit_count})")

                    return cached.response

            except Exception as e:
                logger.warning(f"Redis get failed: {e}, falling back to memory")

        # Fallback to memory cache
        cached = self._memory_cache.get(query_hash)
        if cached:
            cached.hit_count += 1
            cached.last_accessed = datetime.utcnow()
            self._cache_hits += 1
            logger.info(f"Cache HIT (memory) for query hash: {query_hash[:8]}...")
            return cached.response

        self._cache_misses += 1
        logger.info(f"Cache MISS for query hash: {query_hash[:8]}...")
        return None

    async def set(
        self,
        query: str,
        response: str,
        context: Optional[Dict[str, Any]] = None,
        query_type: str = "default"
    ):
        """
        Cache a response

        Args:
            query: User query
            response: AI response
            context: Query context
            query_type: Type of query (for TTL selection)
        """
        query_hash = self._hash_query(query, context)

        cached_response = CachedResponse(
            query_hash=query_hash,
            query=query,
            response=response,
            metadata={
                "context": context or {},
                "query_type": query_type
            },
            cached_at=datetime.utcnow()
        )

        await self._save_cached_response(cached_response, query_type)

        logger.info(f"Cached response for query hash: {query_hash[:8]}... (type: {query_type})")

    async def _save_cached_response(
        self,
        cached: CachedResponse,
        query_type: str = "default"
    ):
        """Save cached response to storage"""
        ttl = self.TTL_CONFIGS.get(query_type, self.TTL_CONFIGS["default"])

        # Save to Redis
        if self.use_redis:
            try:
                cache_key = self._get_cache_key(cached.query_hash)
                data = json.dumps(cached.to_dict())
                await self.redis_client.setex(cache_key, ttl, data)
            except Exception as e:
                logger.warning(f"Redis save failed: {e}, using memory cache")

        # Always save to memory as fallback
        self._memory_cache[cached.query_hash] = cached

    async def invalidate(self, query: str, context: Optional[Dict[str, Any]] = None):
        """
        Invalidate a cached response

        Args:
            query: Query to invalidate
            context: Query context
        """
        query_hash = self._hash_query(query, context)

        # Remove from Redis
        if self.use_redis:
            try:
                cache_key = self._get_cache_key(query_hash)
                await self.redis_client.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

        # Remove from memory
        self._memory_cache.pop(query_hash, None)

        logger.info(f"Invalidated cache for query hash: {query_hash[:8]}...")

    async def invalidate_by_subject(self, subject: str):
        """
        Invalidate all cached responses for a subject

        Args:
            subject: Subject to invalidate
        """
        # This is a simplified version
        # In production, you'd want to use Redis SCAN with pattern matching

        if self.use_redis:
            try:
                # Scan for keys matching pattern
                pattern = f"ai_response:*"
                cursor = 0
                invalidated = 0

                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100
                    )

                    for key in keys:
                        # Get the cached response
                        data = await self.redis_client.get(key)
                        if data:
                            cached = CachedResponse.from_dict(json.loads(data))
                            if cached.metadata.get("context", {}).get("subject") == subject:
                                await self.redis_client.delete(key)
                                invalidated += 1

                    if cursor == 0:
                        break

                logger.info(f"Invalidated {invalidated} cached responses for subject: {subject}")

            except Exception as e:
                logger.warning(f"Redis invalidation failed: {e}")

        # Invalidate from memory cache
        to_remove = []
        for query_hash, cached in self._memory_cache.items():
            if cached.metadata.get("context", {}).get("subject") == subject:
                to_remove.append(query_hash)

        for query_hash in to_remove:
            self._memory_cache.pop(query_hash, None)

    async def clear_all(self):
        """Clear all cached responses"""
        if self.use_redis:
            try:
                pattern = f"ai_response:*"
                cursor = 0

                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100
                    )

                    if keys:
                        await self.redis_client.delete(*keys)

                    if cursor == 0:
                        break

                logger.info("Cleared all cached responses from Redis")

            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")

        # Clear memory cache
        self._memory_cache.clear()
        logger.info("Cleared all cached responses from memory")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = self._cache_hits / self._total_lookups if self._total_lookups > 0 else 0

        return {
            "total_lookups": self._total_lookups,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "cached_items": len(self._memory_cache),
            "redis_enabled": self.use_redis
        }

    async def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular cached queries"""
        # Sort by hit count
        sorted_cache = sorted(
            self._memory_cache.values(),
            key=lambda x: x.hit_count,
            reverse=True
        )

        return [
            {
                "query": cached.query,
                "hit_count": cached.hit_count,
                "cached_at": cached.cached_at.isoformat(),
                "last_accessed": cached.last_accessed.isoformat() if cached.last_accessed else None,
                "query_type": cached.metadata.get("query_type")
            }
            for cached in sorted_cache[:limit]
        ]

    async def warm_cache(self, popular_queries: List[Dict[str, str]]):
        """
        Warm cache with popular queries

        Args:
            popular_queries: List of {"query": str, "response": str, "context": dict}
        """
        for item in popular_queries:
            await self.set(
                query=item["query"],
                response=item["response"],
                context=item.get("context"),
                query_type=item.get("query_type", "default")
            )

        logger.info(f"Warmed cache with {len(popular_queries)} popular queries")


# Global instance
_ai_response_cache: Optional[AIResponseCache] = None


def get_ai_response_cache(
    redis_client: Optional[redis.Redis] = None
) -> AIResponseCache:
    """Get global AI response cache instance"""
    global _ai_response_cache

    if _ai_response_cache is None:
        _ai_response_cache = AIResponseCache(
            redis_client=redis_client,
            use_redis=True,
            similarity_threshold=0.95
        )

    return _ai_response_cache
