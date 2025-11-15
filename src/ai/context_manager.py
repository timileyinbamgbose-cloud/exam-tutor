"""
Context Manager for AI Tutor Service

Manages conversation context, session storage, and user profile integration.
Handles context window management, pruning, and Redis-based caching.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from src.core.config import settings
from src.logging.logger import logger


class MessageRole(str, Enum):
    """Message roles in conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """Conversation message"""
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata")
        )


@dataclass
class UserProfile:
    """User profile for context enrichment"""
    user_id: str
    class_level: Optional[str] = None
    subjects: Optional[List[str]] = None
    learning_style: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    recent_topics: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ConversationContext:
    """Conversation context"""
    session_id: str
    user_profile: UserProfile
    messages: List[Message]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "user_profile": self.user_profile.to_dict(),
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContext":
        """Create from dictionary"""
        return cls(
            session_id=data["session_id"],
            user_profile=UserProfile(**data["user_profile"]),
            messages=[Message.from_dict(msg) for msg in data["messages"]],
            metadata=data["metadata"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add message to context"""
        self.messages.append(Message(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata
        ))
        self.updated_at = datetime.utcnow()

    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get N most recent messages"""
        return self.messages[-count:] if count > 0 else self.messages

    def estimate_tokens(self) -> int:
        """Estimate total tokens in context (rough estimate: 4 chars = 1 token)"""
        total_chars = sum(len(msg.content) for msg in self.messages)
        return total_chars // 4

    def prune_to_token_limit(self, max_tokens: int = 4000):
        """Prune messages to stay within token limit"""
        current_tokens = self.estimate_tokens()

        if current_tokens <= max_tokens:
            return

        # Keep system message (usually first) and recent messages
        system_messages = [msg for msg in self.messages if msg.role == MessageRole.SYSTEM]
        other_messages = [msg for msg in self.messages if msg.role != MessageRole.SYSTEM]

        # Remove oldest messages until we're under limit
        while current_tokens > max_tokens and len(other_messages) > 2:
            # Remove oldest user-assistant pair
            other_messages = other_messages[2:]
            self.messages = system_messages + other_messages
            current_tokens = self.estimate_tokens()

        logger.info(f"Pruned context to {current_tokens} tokens (limit: {max_tokens})")


class ContextManager:
    """
    Manages conversation contexts across sessions.

    Features:
    - Session-based context storage
    - Sliding window for token management
    - Context summarization for long conversations
    - User profile integration
    - Redis-based caching for active sessions
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        max_context_tokens: int = 4000,
        session_ttl: int = 3600,  # 1 hour
        use_redis: bool = True
    ):
        """
        Initialize context manager

        Args:
            redis_client: Redis client for caching
            max_context_tokens: Maximum tokens to keep in context
            session_ttl: Session time-to-live in seconds
            use_redis: Whether to use Redis for caching
        """
        self.redis_client = redis_client
        self.max_context_tokens = max_context_tokens
        self.session_ttl = session_ttl
        self.use_redis = use_redis and REDIS_AVAILABLE and redis_client is not None

        # In-memory fallback
        self._memory_cache: Dict[str, ConversationContext] = {}

        logger.info(
            f"ContextManager initialized (Redis: {self.use_redis}, "
            f"MaxTokens: {max_context_tokens}, TTL: {session_ttl}s)"
        )

    def _get_cache_key(self, session_id: str) -> str:
        """Get Redis cache key for session"""
        return f"ai_tutor:session:{session_id}"

    async def create_session(
        self,
        session_id: str,
        user_profile: UserProfile,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """
        Create new conversation session

        Args:
            session_id: Unique session identifier
            user_profile: User profile for context enrichment
            metadata: Additional session metadata

        Returns:
            ConversationContext: New conversation context
        """
        now = datetime.utcnow()
        context = ConversationContext(
            session_id=session_id,
            user_profile=user_profile,
            messages=[],
            metadata=metadata or {},
            created_at=now,
            updated_at=now
        )

        # Add system message with user context
        system_message = self._build_system_message(user_profile)
        context.add_message(MessageRole.SYSTEM, system_message)

        # Save to cache
        await self._save_context(context)

        logger.info(f"Created new session: {session_id} for user: {user_profile.user_id}")
        return context

    def _build_system_message(self, user_profile: UserProfile) -> str:
        """Build system message with user context"""
        parts = [
            "You are ExamsTutor AI, a helpful and knowledgeable tutor for Nigerian secondary school students.",
            "You provide clear, accurate explanations aligned with the Nigerian curriculum."
        ]

        if user_profile.class_level:
            parts.append(f"The student is in {user_profile.class_level}.")

        if user_profile.subjects:
            subjects = ", ".join(user_profile.subjects)
            parts.append(f"Focus subjects: {subjects}.")

        if user_profile.learning_style:
            parts.append(f"Learning style: {user_profile.learning_style}.")

        if user_profile.strengths:
            strengths = ", ".join(user_profile.strengths)
            parts.append(f"Strengths: {strengths}.")

        if user_profile.weaknesses:
            weaknesses = ", ".join(user_profile.weaknesses)
            parts.append(f"Areas for improvement: {weaknesses}.")

        parts.append("Adapt your explanations to the student's level and needs.")

        return " ".join(parts)

    async def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """
        Get conversation session

        Args:
            session_id: Session identifier

        Returns:
            ConversationContext or None if not found
        """
        # Try Redis first
        if self.use_redis:
            try:
                cache_key = self._get_cache_key(session_id)
                data = await self.redis_client.get(cache_key)

                if data:
                    context_dict = json.loads(data)
                    return ConversationContext.from_dict(context_dict)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}, falling back to memory")

        # Fallback to memory
        return self._memory_cache.get(session_id)

    async def _save_context(self, context: ConversationContext):
        """Save context to cache"""
        # Save to Redis
        if self.use_redis:
            try:
                cache_key = self._get_cache_key(context.session_id)
                data = json.dumps(context.to_dict())
                await self.redis_client.setex(
                    cache_key,
                    self.session_ttl,
                    data
                )
            except Exception as e:
                logger.warning(f"Redis save failed: {e}, using memory cache")

        # Always save to memory as fallback
        self._memory_cache[context.session_id] = context

    async def add_user_message(
        self,
        session_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """
        Add user message to session

        Args:
            session_id: Session identifier
            message: User message content
            metadata: Optional message metadata

        Returns:
            Updated ConversationContext
        """
        context = await self.get_session(session_id)
        if not context:
            raise ValueError(f"Session not found: {session_id}")

        context.add_message(MessageRole.USER, message, metadata)
        context.prune_to_token_limit(self.max_context_tokens)

        await self._save_context(context)

        return context

    async def add_assistant_message(
        self,
        session_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """
        Add assistant message to session

        Args:
            session_id: Session identifier
            message: Assistant message content
            metadata: Optional message metadata

        Returns:
            Updated ConversationContext
        """
        context = await self.get_session(session_id)
        if not context:
            raise ValueError(f"Session not found: {session_id}")

        context.add_message(MessageRole.ASSISTANT, message, metadata)
        context.prune_to_token_limit(self.max_context_tokens)

        await self._save_context(context)

        return context

    async def end_session(self, session_id: str):
        """
        End conversation session

        Args:
            session_id: Session identifier
        """
        # Remove from Redis
        if self.use_redis:
            try:
                cache_key = self._get_cache_key(session_id)
                await self.redis_client.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

        # Remove from memory
        self._memory_cache.pop(session_id, None)

        logger.info(f"Ended session: {session_id}")

    async def get_context_for_ai(
        self,
        session_id: str,
        include_recent_only: bool = False,
        max_messages: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get context formatted for AI model

        Args:
            session_id: Session identifier
            include_recent_only: Only include recent messages
            max_messages: Maximum messages to include

        Returns:
            List of messages in OpenAI format
        """
        context = await self.get_session(session_id)
        if not context:
            return []

        messages = context.get_recent_messages(max_messages) if include_recent_only else context.messages

        return [
            {
                "role": msg.role.value,
                "content": msg.content
            }
            for msg in messages
        ]

    async def update_user_profile(
        self,
        session_id: str,
        profile_updates: Dict[str, Any]
    ):
        """
        Update user profile in session

        Args:
            session_id: Session identifier
            profile_updates: Profile fields to update
        """
        context = await self.get_session(session_id)
        if not context:
            raise ValueError(f"Session not found: {session_id}")

        # Update profile fields
        for key, value in profile_updates.items():
            if hasattr(context.user_profile, key):
                setattr(context.user_profile, key, value)

        # Rebuild system message with updated profile
        system_message = self._build_system_message(context.user_profile)

        # Update first message (system message)
        if context.messages and context.messages[0].role == MessageRole.SYSTEM:
            context.messages[0].content = system_message

        await self._save_context(context)
        logger.info(f"Updated user profile for session: {session_id}")

    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get session summary statistics

        Args:
            session_id: Session identifier

        Returns:
            Session summary dict
        """
        context = await self.get_session(session_id)
        if not context:
            return {}

        user_messages = [msg for msg in context.messages if msg.role == MessageRole.USER]
        assistant_messages = [msg for msg in context.messages if msg.role == MessageRole.ASSISTANT]

        return {
            "session_id": session_id,
            "user_id": context.user_profile.user_id,
            "total_messages": len(context.messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "estimated_tokens": context.estimate_tokens(),
            "duration_seconds": (context.updated_at - context.created_at).total_seconds(),
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "metadata": context.metadata
        }


# Global instance
_context_manager: Optional[ContextManager] = None


def get_context_manager(redis_client: Optional[redis.Redis] = None) -> ContextManager:
    """Get global context manager instance"""
    global _context_manager

    if _context_manager is None:
        _context_manager = ContextManager(
            redis_client=redis_client,
            max_context_tokens=4000,
            session_ttl=3600,
            use_redis=True
        )

    return _context_manager
