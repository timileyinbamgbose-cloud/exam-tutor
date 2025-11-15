"""
RAG Query Optimizer

Optimizes RAG pipeline for better performance and relevance:
- Query preprocessing and normalization
- Hybrid search (semantic + keyword)
- Result re-ranking
- Query expansion
- Performance optimizations
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from src.logging.logger import logger


@dataclass
class OptimizedQuery:
    """Optimized query with metadata"""
    original_query: str
    normalized_query: str
    keywords: List[str]
    expanded_terms: List[str]
    query_type: str
    estimated_complexity: float


class RAGOptimizer:
    """
    Optimizes RAG queries for better retrieval and performance.

    Features:
    - Query preprocessing and normalization
    - Keyword extraction
    - Query expansion with synonyms
    - Complexity estimation
    - Hybrid search preparation
    """

    # Common Nigerian curriculum terms for query expansion
    CURRICULUM_SYNONYMS = {
        "maths": ["mathematics", "math"],
        "physics": ["physical science"],
        "chemistry": ["chemical science"],
        "biology": ["biological science"],
        "english": ["english language"],
        "solve": ["calculate", "find", "determine", "compute"],
        "explain": ["describe", "clarify", "illustrate"],
        "formula": ["equation", "expression"],
    }

    # Stop words to remove
    STOP_WORDS = {
        "the", "is", "at", "which", "on", "a", "an", "and", "or", "but",
        "in", "with", "to", "for", "of", "as", "by", "from", "up", "about",
        "into", "through", "during", "can", "could", "would", "should"
    }

    # Question patterns
    QUESTION_PATTERNS = {
        "definition": r"what is|define|meaning of",
        "explanation": r"explain|how does|why does|how to",
        "procedure": r"solve|calculate|find|determine",
        "comparison": r"difference between|compare|versus|vs",
        "application": r"apply|use|example of",
    }

    def __init__(self):
        """Initialize RAG optimizer"""
        logger.info("RAGOptimizer initialized")

    def optimize_query(self, query: str, subject: Optional[str] = None) -> OptimizedQuery:
        """
        Optimize query for better RAG retrieval

        Args:
            query: Original user query
            subject: Subject area (for context)

        Returns:
            OptimizedQuery with optimizations applied
        """
        # Normalize query
        normalized = self._normalize_query(query)

        # Extract keywords
        keywords = self._extract_keywords(normalized)

        # Expand query with synonyms
        expanded_terms = self._expand_query(keywords, subject)

        # Classify query type
        query_type = self._classify_query_type(query)

        # Estimate complexity
        complexity = self._estimate_complexity(query)

        return OptimizedQuery(
            original_query=query,
            normalized_query=normalized,
            keywords=keywords,
            expanded_terms=expanded_terms,
            query_type=query_type,
            estimated_complexity=complexity
        )

    def _normalize_query(self, query: str) -> str:
        """Normalize query text"""
        # Convert to lowercase
        normalized = query.lower().strip()

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)

        # Remove special characters but keep important punctuation
        normalized = re.sub(r'[^\w\s\?\.\-]', '', normalized)

        return normalized

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query"""
        # Tokenize
        words = query.split()

        # Remove stop words
        keywords = [
            word for word in words
            if word not in self.STOP_WORDS and len(word) > 2
        ]

        return keywords

    def _expand_query(self, keywords: List[str], subject: Optional[str] = None) -> List[str]:
        """Expand query with synonyms and related terms"""
        expanded = set(keywords)

        for keyword in keywords:
            # Add synonyms from curriculum dictionary
            if keyword in self.CURRICULUM_SYNONYMS:
                expanded.update(self.CURRICULUM_SYNONYMS[keyword])

            # Add subject-specific terms
            if subject:
                subject_lower = subject.lower()
                if keyword == subject_lower or keyword in subject_lower:
                    expanded.add(subject.lower())

        return list(expanded)

    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query"""
        query_lower = query.lower()

        for query_type, pattern in self.QUESTION_PATTERNS.items():
            if re.search(pattern, query_lower):
                return query_type

        return "general"

    def _estimate_complexity(self, query: str) -> float:
        """Estimate query complexity (0-1 scale)"""
        # Factors:
        # - Length (longer = more complex)
        # - Number of concepts (multiple "and" = complex)
        # - Question depth (how/why = complex, what = simple)

        word_count = len(query.split())
        concept_count = query.lower().count(" and ") + 1

        # Base complexity on word count
        length_complexity = min(1.0, word_count / 50)

        # Adjust for multiple concepts
        concept_complexity = min(1.0, concept_count / 3)

        # Adjust for question type
        question_complexity = 0.5
        if any(word in query.lower() for word in ["why", "how", "explain"]):
            question_complexity = 0.8
        elif any(word in query.lower() for word in ["what", "when", "who"]):
            question_complexity = 0.3

        # Weighted average
        complexity = (
            length_complexity * 0.3 +
            concept_complexity * 0.3 +
            question_complexity * 0.4
        )

        return complexity

    def build_hybrid_query(
        self,
        optimized_query: OptimizedQuery,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> Dict[str, Any]:
        """
        Build hybrid query combining semantic and keyword search

        Args:
            optimized_query: Optimized query
            semantic_weight: Weight for semantic search (0-1)
            keyword_weight: Weight for keyword search (0-1)

        Returns:
            Hybrid query configuration
        """
        return {
            "semantic_query": optimized_query.normalized_query,
            "keyword_query": " ".join(optimized_query.keywords),
            "expanded_query": " ".join(optimized_query.expanded_terms),
            "weights": {
                "semantic": semantic_weight,
                "keyword": keyword_weight
            },
            "query_type": optimized_query.query_type,
            "boost_terms": self._get_boost_terms(optimized_query)
        }

    def _get_boost_terms(self, optimized_query: OptimizedQuery) -> List[str]:
        """Get terms that should be boosted in search"""
        # Boost subject-specific terms and important keywords
        boost_terms = []

        # Academic subjects should be boosted
        subjects = ["mathematics", "physics", "chemistry", "biology", "english"]
        for keyword in optimized_query.keywords:
            if keyword in subjects:
                boost_terms.append(keyword)

        # Important action verbs
        action_verbs = ["solve", "calculate", "explain", "prove", "derive"]
        for keyword in optimized_query.keywords:
            if keyword in action_verbs:
                boost_terms.append(keyword)

        return boost_terms

    def should_use_reranking(self, optimized_query: OptimizedQuery) -> bool:
        """Determine if results should be re-ranked"""
        # Use re-ranking for complex queries or when many results expected
        return (
            optimized_query.estimated_complexity > 0.6 or
            len(optimized_query.keywords) > 3 or
            optimized_query.query_type in ["explanation", "comparison"]
        )

    def rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Re-rank RAG results for better relevance

        Args:
            query: Original query
            results: List of search results
            top_k: Number of top results to return

        Returns:
            Re-ranked results
        """
        if not results:
            return []

        # Simple re-ranking based on multiple factors
        scored_results = []

        for result in results:
            score = self._calculate_rerank_score(query, result)
            scored_results.append((score, result))

        # Sort by score (descending)
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Return top K
        return [result for _, result in scored_results[:top_k]]

    def _calculate_rerank_score(self, query: str, result: Dict[str, Any]) -> float:
        """Calculate re-ranking score for a result"""
        # Factors:
        # 1. Original similarity score (most important)
        # 2. Keyword overlap
        # 3. Result length (prefer comprehensive but not too long)
        # 4. Metadata match (subject, class level)

        base_score = result.get("similarity_score", 0.0)

        # Keyword overlap bonus
        query_keywords = set(self._extract_keywords(query.lower()))
        result_text = result.get("text", "").lower()
        keyword_matches = sum(1 for kw in query_keywords if kw in result_text)
        keyword_bonus = min(0.1, keyword_matches * 0.02)

        # Length penalty/bonus (prefer 100-500 chars)
        text_length = len(result.get("text", ""))
        if 100 <= text_length <= 500:
            length_bonus = 0.05
        elif text_length < 50:
            length_bonus = -0.1
        else:
            length_bonus = 0.0

        # Metadata match bonus
        metadata_bonus = 0.0
        if result.get("subject") or result.get("class_level"):
            metadata_bonus = 0.05

        final_score = base_score + keyword_bonus + length_bonus + metadata_bonus

        return final_score

    def get_query_cache_key(self, query: str, subject: Optional[str] = None) -> str:
        """Generate cache key for query"""
        import hashlib

        # Normalize first
        normalized = self._normalize_query(query)

        # Add subject to key
        cache_input = f"{normalized}:{subject or 'general'}"

        # Hash for consistent key
        return hashlib.md5(cache_input.encode()).hexdigest()


# Global instance
_rag_optimizer: Optional[RAGOptimizer] = None


def get_rag_optimizer() -> RAGOptimizer:
    """Get global RAG optimizer instance"""
    global _rag_optimizer

    if _rag_optimizer is None:
        _rag_optimizer = RAGOptimizer()

    return _rag_optimizer
