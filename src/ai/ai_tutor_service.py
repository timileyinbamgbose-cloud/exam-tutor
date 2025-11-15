"""
AI Tutor Service - Unified AI Orchestrator

Coordinates all AI components for intelligent tutoring:
- Model selection and routing
- Context management
- RAG integration
- Response optimization
- Fallback mechanisms
- Performance tracking
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from src.ai.model_router import get_model_router, ModelRouter, QueryType
from src.ai.context_manager import get_context_manager, ContextManager, UserProfile
from src.ai.response_optimizer import get_response_optimizer, ResponseOptimizer
from src.ai.rag_service import get_rag_service
from src.ai.openai_service import get_openai_service
from src.logging.logger import logger
from src.core.config import settings


@dataclass
class TutorRequest:
    """AI Tutor request"""
    query: str
    user_id: str
    session_id: Optional[str] = None
    subject: Optional[str] = None
    class_level: Optional[str] = None
    use_rag: bool = True
    priority: str = "balanced"  # "speed", "quality", "cost", "balanced"
    user_profile: Optional[Dict[str, Any]] = None


@dataclass
class TutorResponse:
    """AI Tutor response"""
    answer: str
    session_id: str
    sources: Optional[List[Dict[str, Any]]] = None
    model_used: Optional[str] = None
    model_tier: Optional[str] = None
    query_type: Optional[str] = None
    rag_enabled: bool = False
    context_used: bool = False
    response_time_ms: float = 0
    tokens_used: Optional[Dict[str, int]] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class AITutorService:
    """
    Unified AI Tutor Service

    Orchestrates:
    - Intelligent model selection
    - Context-aware conversations
    - RAG-powered responses
    - Response quality optimization
    - Fallback handling
    - Performance monitoring
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        enable_finetuned: bool = False,
        finetuned_model_map: Optional[Dict[str, str]] = None
    ):
        """
        Initialize AI Tutor Service

        Args:
            redis_client: Redis client for caching/sessions
            enable_finetuned: Enable fine-tuned models
            finetuned_model_map: Map of subject -> fine-tuned model
        """
        self.model_router = get_model_router(
            enable_finetuned=enable_finetuned,
            finetuned_model_map=finetuned_model_map
        )
        self.context_manager = get_context_manager(redis_client=redis_client)
        self.response_optimizer = get_response_optimizer()
        self.rag_service = get_rag_service()
        self.openai_service = get_openai_service()

        # Performance tracking
        self._request_count = 0
        self._total_latency = 0.0
        self._cache_hits = 0

        logger.info("AITutorService initialized")

    async def ask(self, request: TutorRequest) -> TutorResponse:
        """
        Main query endpoint - intelligently answers student questions

        Args:
            request: TutorRequest with query and context

        Returns:
            TutorResponse with answer and metadata
        """
        start_time = time.time()
        self._request_count += 1

        try:
            # Step 1: Get or create session
            session_id = await self._get_or_create_session(request)

            # Step 2: Add user message to context
            await self.context_manager.add_user_message(
                session_id=session_id,
                message=request.query,
                metadata={
                    "subject": request.subject,
                    "class_level": request.class_level
                }
            )

            # Step 3: Classify query and select model
            query_type = self.model_router.classify_query(request.query)
            model_selection = self.model_router.select_model(
                query=request.query,
                subject=request.subject,
                query_type=query_type,
                priority=request.priority,
                context_length=0  # Will be calculated from session
            )

            logger.info(
                f"Query classified as {query_type}, using model {model_selection['model_id']}"
            )

            # Step 4: RAG retrieval (if enabled)
            rag_context = None
            sources = []

            if request.use_rag and self._should_use_rag(query_type):
                try:
                    rag_results = await self.rag_service.search_curriculum(
                        query=request.query,
                        subject=request.subject,
                        class_level=request.class_level,
                        top_k=3,
                        min_similarity=0.6
                    )

                    if rag_results:
                        rag_context = self._format_rag_context(rag_results)
                        sources = [
                            {
                                "topic": r.get("topic", "Unknown"),
                                "similarity_score": r.get("similarity_score", 0),
                                "text_preview": r.get("text", "")[:200]
                            }
                            for r in rag_results
                        ]
                        logger.info(f"RAG retrieved {len(sources)} sources")
                except Exception as e:
                    logger.warning(f"RAG retrieval failed: {e}, continuing without RAG")

            # Step 5: Get conversation context
            conversation_context = await self.context_manager.get_context_for_ai(
                session_id=session_id,
                include_recent_only=True,
                max_messages=10
            )

            # Step 6: Build prompt with context and RAG
            enhanced_messages = self._build_enhanced_prompt(
                conversation_context=conversation_context,
                rag_context=rag_context,
                query=request.query
            )

            # Step 7: Generate response with retry/fallback
            answer, tokens_used = await self._generate_with_fallback(
                model_selection=model_selection,
                messages=enhanced_messages,
                max_retries=2
            )

            # Step 8: Optimize response
            optimized_answer = self.response_optimizer.optimize_response(
                response=answer,
                target_class_level=request.class_level,
                subject=request.subject,
                simplify_language=self._is_junior_level(request.class_level)
            )

            # Step 9: Add assistant message to context
            await self.context_manager.add_assistant_message(
                session_id=session_id,
                message=optimized_answer,
                metadata={
                    "model": model_selection['model_id'],
                    "rag_sources": len(sources),
                    "query_type": query_type.value
                }
            )

            # Step 10: Calculate metrics
            response_time_ms = (time.time() - start_time) * 1000
            self._total_latency += response_time_ms

            # Analyze response quality
            response_metrics = self.response_optimizer.analyze_response(
                response=optimized_answer,
                target_class_level=request.class_level
            )

            # Build response
            tutor_response = TutorResponse(
                answer=optimized_answer,
                session_id=session_id,
                sources=sources if sources else None,
                model_used=model_selection['model_id'],
                model_tier=model_selection['tier'],
                query_type=query_type.value,
                rag_enabled=request.use_rag,
                context_used=bool(rag_context),
                response_time_ms=response_time_ms,
                tokens_used=tokens_used,
                confidence=response_metrics.estimated_comprehension,
                metadata={
                    "word_count": response_metrics.word_count,
                    "clarity_score": response_metrics.clarity_score,
                    "has_examples": response_metrics.has_examples,
                    "model_reasoning": model_selection['reasoning']
                }
            )

            logger.info(
                f"Response generated in {response_time_ms:.0f}ms "
                f"(Model: {model_selection['model_id']}, "
                f"Tokens: {tokens_used.get('total', 0)})"
            )

            return tutor_response

        except Exception as e:
            logger.error(f"AI Tutor error: {e}", exc_info=True)
            raise

    async def _get_or_create_session(self, request: TutorRequest) -> str:
        """Get existing session or create new one"""
        if request.session_id:
            # Check if session exists
            existing = await self.context_manager.get_session(request.session_id)
            if existing:
                return request.session_id

        # Create new session
        session_id = request.session_id or str(uuid.uuid4())

        user_profile = UserProfile(
            user_id=request.user_id,
            class_level=request.class_level,
            subjects=[request.subject] if request.subject else None
        )

        if request.user_profile:
            for key, value in request.user_profile.items():
                if hasattr(user_profile, key):
                    setattr(user_profile, key, value)

        await self.context_manager.create_session(
            session_id=session_id,
            user_profile=user_profile,
            metadata={
                "created_by": "ai_tutor_service",
                "initial_subject": request.subject
            }
        )

        return session_id

    def _should_use_rag(self, query_type: QueryType) -> bool:
        """Determine if RAG should be used for this query type"""
        # Use RAG for most query types except practice questions
        return query_type != QueryType.PRACTICE_QUESTION

    def _format_rag_context(self, rag_results: List[Dict[str, Any]]) -> str:
        """Format RAG results into context string"""
        if not rag_results:
            return ""

        context_parts = ["Relevant curriculum content:"]

        for i, result in enumerate(rag_results[:3], 1):
            topic = result.get("topic", "Unknown")
            text = result.get("text", "")
            context_parts.append(f"\n{i}. {topic}: {text}")

        return "\n".join(context_parts)

    def _build_enhanced_prompt(
        self,
        conversation_context: List[Dict[str, str]],
        rag_context: Optional[str],
        query: str
    ) -> List[Dict[str, str]]:
        """Build enhanced prompt with conversation and RAG context"""
        messages = conversation_context.copy()

        # If RAG context exists, enhance the latest user message
        if rag_context and messages:
            # Find the last user message
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "user":
                    # Enhance with RAG context
                    messages[i]["content"] = f"{rag_context}\n\nStudent question: {messages[i]['content']}"
                    break

        return messages

    async def _generate_with_fallback(
        self,
        model_selection: Dict[str, Any],
        messages: List[Dict[str, str]],
        max_retries: int = 2
    ) -> tuple[str, Dict[str, int]]:
        """Generate response with fallback on failure"""
        current_model = model_selection['model_id']
        params = model_selection['parameters']

        for attempt in range(max_retries + 1):
            try:
                # Generate response
                response = await self.openai_service.generate_completion(
                    messages=messages,
                    model=current_model,
                    temperature=params['temperature'],
                    max_tokens=params['max_tokens']
                )

                answer = response['choices'][0]['message']['content']
                tokens_used = {
                    "prompt": response['usage']['prompt_tokens'],
                    "completion": response['usage']['completion_tokens'],
                    "total": response['usage']['total_tokens']
                }

                return answer, tokens_used

            except Exception as e:
                logger.warning(f"Model {current_model} failed (attempt {attempt + 1}): {e}")

                if attempt < max_retries:
                    # Try fallback model
                    fallback_model = self.model_router.get_fallback_model(current_model)

                    if fallback_model:
                        logger.info(f"Falling back to model: {fallback_model}")
                        current_model = fallback_model
                    else:
                        # No fallback available
                        raise
                else:
                    raise

    def _is_junior_level(self, class_level: Optional[str]) -> bool:
        """Check if class level is junior secondary"""
        if not class_level:
            return False
        return class_level.upper().startswith('JSS')

    async def end_session(self, session_id: str):
        """End a conversation session"""
        await self.context_manager.end_session(session_id)
        logger.info(f"Session ended: {session_id}")

    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get session summary and statistics"""
        return await self.context_manager.get_session_summary(session_id)

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service performance statistics"""
        avg_latency = self._total_latency / self._request_count if self._request_count > 0 else 0

        return {
            "total_requests": self._request_count,
            "average_latency_ms": avg_latency,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": self._cache_hits / self._request_count if self._request_count > 0 else 0,
            "available_models": self.model_router.get_all_models()
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        health = {
            "status": "healthy",
            "components": {}
        }

        # Check OpenAI service
        try:
            await self.openai_service.test_connection()
            health["components"]["openai"] = {"status": "healthy"}
        except Exception as e:
            health["components"]["openai"] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "degraded"

        # Check RAG service
        try:
            rag_stats = await self.rag_service.get_stats()
            health["components"]["rag"] = {
                "status": "healthy",
                "documents": rag_stats.get("vector_store", {}).get("total_documents", 0)
            }
        except Exception as e:
            health["components"]["rag"] = {"status": "unhealthy", "error": str(e)}

        # Check context manager (Redis)
        health["components"]["context_manager"] = {
            "status": "healthy",
            "redis_enabled": self.context_manager.use_redis
        }

        return health


# Global instance
_ai_tutor_service: Optional[AITutorService] = None


def get_ai_tutor_service(
    redis_client: Optional[redis.Redis] = None,
    enable_finetuned: bool = False,
    finetuned_model_map: Optional[Dict[str, str]] = None
) -> AITutorService:
    """Get global AI tutor service instance"""
    global _ai_tutor_service

    if _ai_tutor_service is None:
        _ai_tutor_service = AITutorService(
            redis_client=redis_client,
            enable_finetuned=enable_finetuned,
            finetuned_model_map=finetuned_model_map
        )

    return _ai_tutor_service
