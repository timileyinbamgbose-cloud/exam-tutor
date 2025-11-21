"""
AI Package
Exports AI services for question answering and generation
"""
from src.ai.openai_service import OpenAIService, openai_service

__all__ = ["OpenAIService", "openai_service"]
