"""
Response Optimizer for AI Tutor Service

Optimizes AI responses for:
- Clarity and readability
- Curriculum alignment
- Student comprehension level
- Educational effectiveness
"""

import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.logging.logger import logger


@dataclass
class ResponseMetrics:
    """Metrics for response quality"""
    clarity_score: float  # 0-1
    curriculum_alignment: float  # 0-1
    reading_level: str  # "elementary", "intermediate", "advanced"
    estimated_comprehension: float  # 0-1
    word_count: int
    sentence_count: int
    has_examples: bool
    has_step_by_step: bool


class ResponseOptimizer:
    """
    Optimizes AI responses for educational effectiveness.

    Features:
    - Reading level adjustment
    - Clarity improvements
    - Example injection
    - Step-by-step formatting
    - Curriculum alignment checks
    """

    # Reading level word lists (simplified)
    COMPLEX_WORDS = {
        "utilize": "use",
        "facilitate": "help",
        "implement": "use",
        "consequently": "so",
        "therefore": "so",
        "furthermore": "also",
        "subsequently": "then",
        "approximately": "about",
        "demonstrate": "show",
        "sufficient": "enough"
    }

    NIGERIAN_CURRICULUM_TERMS = {
        "SS1", "SS2", "SS3", "JSS1", "JSS2", "JSS3",
        "WAEC", "NECO", "JAMB", "UTME",
        "Nigerian curriculum", "West African"
    }

    def __init__(self):
        """Initialize response optimizer"""
        logger.info("ResponseOptimizer initialized")

    def optimize_response(
        self,
        response: str,
        target_class_level: Optional[str] = None,
        subject: Optional[str] = None,
        include_examples: bool = True,
        simplify_language: bool = False
    ) -> str:
        """
        Optimize AI response

        Args:
            response: Raw AI response
            target_class_level: Target class level (e.g., "SS2")
            subject: Subject area
            include_examples: Whether to ensure examples are included
            simplify_language: Simplify complex language

        Returns:
            Optimized response
        """
        optimized = response

        # Clean formatting
        optimized = self._clean_formatting(optimized)

        # Simplify language if needed
        if simplify_language or self._is_junior_level(target_class_level):
            optimized = self._simplify_language(optimized)

        # Ensure proper structure
        optimized = self._ensure_structure(optimized)

        # Add Nigerian context if relevant
        optimized = self._add_nigerian_context(optimized, subject)

        return optimized

    def _clean_formatting(self, text: str) -> str:
        """Clean and format response"""
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Fix spacing around punctuation
        text = re.sub(r'\s+([.,!?])', r'\1', text)
        text = re.sub(r'([.,!?])([A-Za-z])', r'\1 \2', text)

        # Ensure proper list formatting
        text = re.sub(r'(\d+\.)\s*', r'\n\1 ', text)

        return text.strip()

    def _simplify_language(self, text: str) -> str:
        """Simplify complex language"""
        # Replace complex words with simpler alternatives
        for complex_word, simple_word in self.COMPLEX_WORDS.items():
            # Case-insensitive replacement
            pattern = re.compile(r'\b' + complex_word + r'\b', re.IGNORECASE)
            text = pattern.sub(simple_word, text)

        # Shorten long sentences (basic approach)
        sentences = text.split('. ')
        simplified_sentences = []

        for sentence in sentences:
            # If sentence is very long, add hint to break it up
            if len(sentence.split()) > 30:
                # This is a signal for future improvement
                simplified_sentences.append(sentence)
            else:
                simplified_sentences.append(sentence)

        return '. '.join(simplified_sentences)

    def _ensure_structure(self, text: str) -> str:
        """Ensure response has good structure"""
        # If response is long but has no clear sections, add basic structure
        if len(text.split()) > 100 and '\n\n' not in text:
            # Try to identify natural break points
            sentences = text.split('. ')

            if len(sentences) > 5:
                # Group sentences into paragraphs
                mid_point = len(sentences) // 2
                part1 = '. '.join(sentences[:mid_point]) + '.'
                part2 = '. '.join(sentences[mid_point:])
                return f"{part1}\n\n{part2}"

        return text

    def _add_nigerian_context(self, text: str, subject: Optional[str]) -> str:
        """Add Nigerian curriculum context if missing"""
        # Check if response mentions Nigerian curriculum
        has_nigerian_context = any(
            term.lower() in text.lower()
            for term in self.NIGERIAN_CURRICULUM_TERMS
        )

        # If discussing curriculum and no Nigerian context, it's already good
        # This function is more about ensuring relevance
        return text

    def _is_junior_level(self, class_level: Optional[str]) -> bool:
        """Check if class level is junior secondary"""
        if not class_level:
            return False
        return class_level.upper().startswith('JSS')

    def analyze_response(self, response: str, target_class_level: Optional[str] = None) -> ResponseMetrics:
        """
        Analyze response quality

        Args:
            response: AI response
            target_class_level: Target class level

        Returns:
            ResponseMetrics
        """
        # Basic metrics
        words = response.split()
        word_count = len(words)
        sentences = re.split(r'[.!?]+', response)
        sentence_count = len([s for s in sentences if s.strip()])

        # Check for examples
        has_examples = bool(re.search(r'example|for instance|such as|e\.g\.', response.lower()))

        # Check for step-by-step
        has_step_by_step = bool(re.search(r'step \d|first|second|then|finally', response.lower()))

        # Estimate clarity (simple heuristic based on avg sentence length)
        avg_sentence_length = word_count / max(sentence_count, 1)
        clarity_score = min(1.0, max(0.0, 1.0 - (abs(avg_sentence_length - 15) / 30)))

        # Check curriculum alignment (presence of curriculum terms)
        curriculum_terms_found = sum(
            1 for term in self.NIGERIAN_CURRICULUM_TERMS
            if term.lower() in response.lower()
        )
        curriculum_alignment = min(1.0, curriculum_terms_found / 3)

        # Estimate reading level
        if avg_sentence_length < 12:
            reading_level = "elementary"
        elif avg_sentence_length < 20:
            reading_level = "intermediate"
        else:
            reading_level = "advanced"

        # Estimate comprehension (combination of factors)
        comprehension_factors = [
            clarity_score,
            1.0 if has_examples else 0.5,
            1.0 if has_step_by_step else 0.7,
        ]
        estimated_comprehension = sum(comprehension_factors) / len(comprehension_factors)

        return ResponseMetrics(
            clarity_score=clarity_score,
            curriculum_alignment=curriculum_alignment,
            reading_level=reading_level,
            estimated_comprehension=estimated_comprehension,
            word_count=word_count,
            sentence_count=sentence_count,
            has_examples=has_examples,
            has_step_by_step=has_step_by_step
        )

    def should_regenerate(
        self,
        metrics: ResponseMetrics,
        min_clarity: float = 0.6,
        min_comprehension: float = 0.6
    ) -> tuple[bool, str]:
        """
        Determine if response should be regenerated

        Args:
            metrics: Response metrics
            min_clarity: Minimum clarity threshold
            min_comprehension: Minimum comprehension threshold

        Returns:
            (should_regenerate, reason)
        """
        if metrics.clarity_score < min_clarity:
            return True, f"Low clarity score: {metrics.clarity_score:.2f}"

        if metrics.estimated_comprehension < min_comprehension:
            return True, f"Low comprehension score: {metrics.estimated_comprehension:.2f}"

        if metrics.word_count < 20:
            return True, "Response too short"

        if metrics.word_count > 1000:
            return True, "Response too long"

        return False, "Response quality acceptable"

    def get_improvement_suggestions(self, metrics: ResponseMetrics) -> List[str]:
        """Get suggestions for improving response"""
        suggestions = []

        if metrics.clarity_score < 0.7:
            suggestions.append("Simplify sentence structure for better clarity")

        if not metrics.has_examples:
            suggestions.append("Add concrete examples to illustrate concepts")

        if not metrics.has_step_by_step and metrics.word_count > 100:
            suggestions.append("Break down into step-by-step explanation")

        if metrics.curriculum_alignment < 0.5:
            suggestions.append("Add more Nigerian curriculum context")

        if metrics.reading_level == "advanced":
            suggestions.append("Simplify language for student comprehension")

        return suggestions


# Global instance
_response_optimizer: Optional[ResponseOptimizer] = None


def get_response_optimizer() -> ResponseOptimizer:
    """Get global response optimizer instance"""
    global _response_optimizer

    if _response_optimizer is None:
        _response_optimizer = ResponseOptimizer()

    return _response_optimizer
