"""
Model Router for AI Tutor Service

Intelligently selects the best AI model for each query based on:
- Query complexity
- Subject matter
- Performance requirements
- Cost optimization
- Fine-tuned model availability
"""

import re
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from src.logging.logger import logger


class QueryType(str, Enum):
    """Types of queries"""
    SIMPLE_FACTUAL = "simple_factual"  # Simple definition or fact
    COMPLEX_REASONING = "complex_reasoning"  # Multi-step reasoning
    PRACTICE_QUESTION = "practice_question"  # Generate practice question
    EXPLANATION = "explanation"  # Explain a concept
    STEP_BY_STEP = "step_by_step"  # Step-by-step solution
    CURRICULUM = "curriculum"  # Curriculum-specific query
    DIAGNOSTIC = "diagnostic"  # Diagnostic assessment


class ModelTier(str, Enum):
    """Model capability tiers"""
    FAST = "fast"  # Fast, cheap models (GPT-4o-mini)
    BALANCED = "balanced"  # Balanced quality/speed (GPT-4o)
    PREMIUM = "premium"  # Highest quality (GPT-4)
    SPECIALIZED = "specialized"  # Fine-tuned models


@dataclass
class ModelConfig:
    """Model configuration"""
    model_id: str
    tier: ModelTier
    max_tokens: int
    temperature: float
    description: str
    cost_per_1k_tokens: float
    avg_latency_ms: int


class ModelRouter:
    """
    Routes queries to the most appropriate AI model.

    Selection criteria:
    1. Query complexity → Model capability
    2. Subject specificity → Fine-tuned vs general
    3. Speed requirements → Fast vs quality
    4. Cost optimization → Cheapest adequate model
    """

    # Model configurations
    MODELS = {
        "gpt-4o-mini": ModelConfig(
            model_id="gpt-4o-mini",
            tier=ModelTier.FAST,
            max_tokens=16000,
            temperature=0.7,
            description="Fast and cost-effective for simple queries",
            cost_per_1k_tokens=0.15,
            avg_latency_ms=800
        ),
        "gpt-4o": ModelConfig(
            model_id="gpt-4o",
            tier=ModelTier.BALANCED,
            max_tokens=128000,
            temperature=0.7,
            description="Balanced performance for most queries",
            cost_per_1k_tokens=2.50,
            avg_latency_ms=1500
        ),
        "gpt-4": ModelConfig(
            model_id="gpt-4",
            tier=ModelTier.PREMIUM,
            max_tokens=8000,
            temperature=0.7,
            description="Highest quality for complex reasoning",
            cost_per_1k_tokens=30.0,
            avg_latency_ms=3000
        )
    }

    # Query patterns for complexity detection
    SIMPLE_PATTERNS = [
        r"^what is ",
        r"^define ",
        r"^who is ",
        r"^when ",
        r"^where ",
    ]

    COMPLEX_PATTERNS = [
        r"explain .* and .* and",  # Multiple concepts
        r"compare .* with ",
        r"derive ",
        r"prove ",
        r"analyze ",
        r"evaluate ",
        r"why does .* work",
    ]

    STEP_BY_STEP_PATTERNS = [
        r"show steps",
        r"step by step",
        r"how to solve",
        r"walk me through",
        r"work out",
    ]

    def __init__(
        self,
        enable_finetuned: bool = False,
        finetuned_model_map: Optional[Dict[str, str]] = None,
        default_model: str = "gpt-4o-mini"
    ):
        """
        Initialize model router

        Args:
            enable_finetuned: Whether to use fine-tuned models
            finetuned_model_map: Map of subject -> fine-tuned model ID
            default_model: Default model to use
        """
        self.enable_finetuned = enable_finetuned
        self.finetuned_model_map = finetuned_model_map or {}
        self.default_model = default_model

        logger.info(
            f"ModelRouter initialized (Default: {default_model}, "
            f"Fine-tuned: {enable_finetuned})"
        )

    def classify_query(self, query: str) -> QueryType:
        """
        Classify query type

        Args:
            query: User query

        Returns:
            QueryType
        """
        query_lower = query.lower().strip()

        # Check for practice question generation
        if any(word in query_lower for word in ["generate", "create", "give me"] +
               ["practice", "question", "quiz", "test"]):
            return QueryType.PRACTICE_QUESTION

        # Check for step-by-step
        if any(re.search(pattern, query_lower) for pattern in self.STEP_BY_STEP_PATTERNS):
            return QueryType.STEP_BY_STEP

        # Check for simple factual
        if any(re.search(pattern, query_lower) for pattern in self.SIMPLE_PATTERNS):
            if len(query.split()) < 15:  # Short query
                return QueryType.SIMPLE_FACTUAL

        # Check for complex reasoning
        if any(re.search(pattern, query_lower) for pattern in self.COMPLEX_PATTERNS):
            return QueryType.COMPLEX_REASONING

        # Check for explanation
        if "explain" in query_lower or "what does" in query_lower:
            return QueryType.EXPLANATION

        # Default to explanation for medium-length queries
        return QueryType.EXPLANATION

    def select_model(
        self,
        query: str,
        subject: Optional[str] = None,
        query_type: Optional[QueryType] = None,
        priority: str = "balanced",  # "speed", "quality", "cost", "balanced"
        context_length: int = 0,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Select the best model for the query

        Args:
            query: User query
            subject: Subject area (e.g., "mathematics", "physics")
            query_type: Query type (auto-detected if not provided)
            priority: Optimization priority
            context_length: Length of conversation context (tokens)
            user_preferences: User-specific preferences

        Returns:
            Dict with model selection and parameters
        """
        # Auto-classify if not provided
        if query_type is None:
            query_type = self.classify_query(query)

        logger.info(f"Query type: {query_type}, Priority: {priority}")

        # Check for fine-tuned model
        if self.enable_finetuned and subject and subject in self.finetuned_model_map:
            finetuned_model_id = self.finetuned_model_map[subject]
            return self._build_model_selection(
                finetuned_model_id,
                tier=ModelTier.SPECIALIZED,
                temperature=0.7,
                max_tokens=2000,
                reasoning=f"Using fine-tuned model for {subject}"
            )

        # Select based on query type and priority
        model_config = self._select_base_model(
            query_type, priority, context_length
        )

        # Adjust parameters based on query type
        temperature, max_tokens = self._get_generation_params(query_type)

        return self._build_model_selection(
            model_config.model_id,
            tier=model_config.tier,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning=self._get_selection_reasoning(
                query_type, model_config, priority
            )
        )

    def _select_base_model(
        self,
        query_type: QueryType,
        priority: str,
        context_length: int
    ) -> ModelConfig:
        """Select base model based on query type and priority"""

        # Priority: Speed
        if priority == "speed":
            return self.MODELS["gpt-4o-mini"]

        # Priority: Cost
        if priority == "cost":
            return self.MODELS["gpt-4o-mini"]

        # Priority: Quality (always use best)
        if priority == "quality":
            return self.MODELS["gpt-4o"]

        # Priority: Balanced (default)
        # Use query type to determine model
        if query_type in [QueryType.SIMPLE_FACTUAL, QueryType.PRACTICE_QUESTION]:
            return self.MODELS["gpt-4o-mini"]

        elif query_type in [QueryType.COMPLEX_REASONING, QueryType.DIAGNOSTIC]:
            return self.MODELS["gpt-4o"]

        elif query_type in [QueryType.EXPLANATION, QueryType.STEP_BY_STEP, QueryType.CURRICULUM]:
            # Use balanced model for explanations
            return self.MODELS["gpt-4o"]

        # Default
        return self.MODELS[self.default_model]

    def _get_generation_params(self, query_type: QueryType) -> tuple[float, int]:
        """Get temperature and max_tokens based on query type"""

        params = {
            QueryType.SIMPLE_FACTUAL: (0.3, 500),  # Low temp, short
            QueryType.COMPLEX_REASONING: (0.7, 2000),  # Medium temp, long
            QueryType.PRACTICE_QUESTION: (0.9, 1000),  # High temp for variety
            QueryType.EXPLANATION: (0.7, 1500),  # Medium temp, medium length
            QueryType.STEP_BY_STEP: (0.5, 2000),  # Lower temp, detailed
            QueryType.CURRICULUM: (0.5, 1500),  # Lower temp, curriculum-focused
            QueryType.DIAGNOSTIC: (0.3, 1000),  # Low temp, factual
        }

        return params.get(query_type, (0.7, 1000))

    def _build_model_selection(
        self,
        model_id: str,
        tier: ModelTier,
        temperature: float,
        max_tokens: int,
        reasoning: str
    ) -> Dict[str, Any]:
        """Build model selection response"""
        return {
            "model_id": model_id,
            "tier": tier.value,
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            "reasoning": reasoning,
            "timestamp": None  # Will be set by caller
        }

    def _get_selection_reasoning(
        self,
        query_type: QueryType,
        model_config: ModelConfig,
        priority: str
    ) -> str:
        """Generate human-readable selection reasoning"""
        reasons = [
            f"Query type: {query_type.value}",
            f"Model tier: {model_config.tier.value}",
            f"Priority: {priority}",
            f"Model: {model_config.model_id}",
            f"Est. cost: ${model_config.cost_per_1k_tokens}/1K tokens"
        ]
        return " | ".join(reasons)

    def get_fallback_model(self, failed_model: str) -> Optional[str]:
        """
        Get fallback model if primary fails

        Args:
            failed_model: Model that failed

        Returns:
            Fallback model ID or None
        """
        # Fallback hierarchy
        fallback_map = {
            "gpt-4": "gpt-4o",
            "gpt-4o": "gpt-4o-mini",
            "gpt-4o-mini": None  # No fallback for cheapest model
        }

        # For fine-tuned models, fallback to base model
        if failed_model not in fallback_map:
            return "gpt-4o-mini"

        return fallback_map.get(failed_model)

    def estimate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate cost for model usage

        Args:
            model_id: Model identifier
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Estimated cost in USD
        """
        if model_id not in self.MODELS:
            logger.warning(f"Unknown model: {model_id}, using default pricing")
            cost_per_1k = 1.0
        else:
            cost_per_1k = self.MODELS[model_id].cost_per_1k_tokens

        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000) * cost_per_1k

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model information"""
        if model_id not in self.MODELS:
            return None

        config = self.MODELS[model_id]
        return {
            "model_id": config.model_id,
            "tier": config.tier.value,
            "max_tokens": config.max_tokens,
            "description": config.description,
            "cost_per_1k_tokens": config.cost_per_1k_tokens,
            "avg_latency_ms": config.avg_latency_ms
        }

    def get_all_models(self) -> List[Dict[str, Any]]:
        """Get information about all available models"""
        return [self.get_model_info(model_id) for model_id in self.MODELS.keys()]


# Global instance
_model_router: Optional[ModelRouter] = None


def get_model_router(
    enable_finetuned: bool = False,
    finetuned_model_map: Optional[Dict[str, str]] = None
) -> ModelRouter:
    """Get global model router instance"""
    global _model_router

    if _model_router is None:
        _model_router = ModelRouter(
            enable_finetuned=enable_finetuned,
            finetuned_model_map=finetuned_model_map or {}
        )

    return _model_router
