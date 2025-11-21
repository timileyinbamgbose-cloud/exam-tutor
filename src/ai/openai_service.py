"""
OpenAI Service
Real AI implementation using OpenAI API
Handles question answering, practice generation, and more
"""
from openai import OpenAI, AsyncOpenAI
from typing import Dict, List, Optional, Any
import os
import time
from datetime import datetime


class OpenAIService:
    """
    Service class for OpenAI integration
    Provides AI-powered tutoring features
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI service"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            print("⚠️  OPENAI_API_KEY not set - AI features will use mock responses")
            self.client = None
            self.async_client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
            self.async_client = AsyncOpenAI(api_key=self.api_key)
            print("✅ OpenAI service initialized")

        self.model = "gpt-4o-mini"  # Cost-effective model for education
        self.max_tokens = 1000

    def is_available(self) -> bool:
        """Check if OpenAI service is available"""
        return self.client is not None

    async def answer_question(
        self,
        question: str,
        subject: Optional[str] = None,
        class_level: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer a student's question using OpenAI

        Args:
            question: The student's question
            subject: Subject area (e.g., Mathematics, Physics)
            class_level: Class level (SS1, SS2, SS3)
            context: Additional context from curriculum (RAG results)

        Returns:
            Dict with answer, sources, confidence, etc.
        """
        start_time = time.time()

        # If OpenAI not available, return mock response
        if not self.is_available():
            return self._mock_answer(question, subject, class_level)

        # Build system prompt for Nigerian curriculum
        system_prompt = self._build_system_prompt(subject, class_level)

        # Build user message
        user_message = self._build_user_message(question, context)

        try:
            # Call OpenAI API
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )

            answer = response.choices[0].message.content
            response_time = (time.time() - start_time) * 1000

            return {
                "answer": answer,
                "sources": self._extract_sources(context) if context else [],
                "confidence": 0.85,  # Can be enhanced with more sophisticated scoring
                "response_time_ms": response_time,
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }

        except Exception as e:
            print(f"❌ OpenAI API error: {str(e)}")
            # Fall back to mock response
            return self._mock_answer(question, subject, class_level)

    async def generate_practice_questions(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        num_questions: int,
        question_type: str = "mcq"
    ) -> List[Dict[str, Any]]:
        """
        Generate practice questions using OpenAI

        Args:
            subject: Subject area
            topic: Specific topic
            difficulty: easy, medium, hard
            num_questions: Number of questions to generate
            question_type: mcq, short_answer, essay

        Returns:
            List of generated questions
        """
        if not self.is_available():
            return self._mock_practice_questions(subject, topic, difficulty, num_questions, question_type)

        try:
            prompt = self._build_practice_prompt(subject, topic, difficulty, num_questions, question_type)

            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Nigerian secondary school teacher."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.8
            )

            # Parse response and structure questions
            questions_text = response.choices[0].message.content
            questions = self._parse_practice_questions(questions_text, subject, topic, difficulty, question_type)

            return questions

        except Exception as e:
            print(f"❌ Practice generation error: {str(e)}")
            return self._mock_practice_questions(subject, topic, difficulty, num_questions, question_type)

    def _build_system_prompt(self, subject: Optional[str], class_level: Optional[str]) -> str:
        """Build system prompt for the AI"""
        base_prompt = """You are an expert AI tutor for Nigerian secondary school students preparing for WAEC and JAMB examinations.

Your role:
- Provide clear, accurate, and educational answers
- Use simple language appropriate for students
- Reference the Nigerian curriculum when relevant
- Encourage critical thinking
- Be supportive and patient
"""

        if subject:
            base_prompt += f"\n- You are currently helping with {subject}"
        if class_level:
            base_prompt += f"\n- The student is in {class_level}"

        base_prompt += "\n\nAlways provide thorough explanations and, when helpful, include examples."

        return base_prompt

    def _build_user_message(self, question: str, context: Optional[str]) -> str:
        """Build user message with context if available"""
        if context:
            return f"""Based on the following curriculum content:

{context}

Student's question: {question}

Please provide a comprehensive answer using the curriculum content as reference."""
        else:
            return f"Student's question: {question}"

    def _extract_sources(self, context: str) -> List[Dict[str, Any]]:
        """Extract sources from context (RAG results)"""
        # Simplified - in production, this would parse actual RAG results
        return [
            {
                "text": context[:200] if context else "",
                "subject": "General",
                "topic": "Various",
                "score": 0.85
            }
        ]

    def _build_practice_prompt(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        num_questions: int,
        question_type: str
    ) -> str:
        """Build prompt for practice question generation"""
        return f"""Generate {num_questions} {difficulty} {question_type} practice questions for Nigerian secondary school students.

Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}
Question Type: {question_type}

Requirements:
- Align with Nigerian curriculum (WAEC/JAMB)
- Include correct answers
- For MCQ: provide 4 options (A, B, C, D)
- Provide brief explanations

Format each question clearly numbered (1, 2, 3, etc.)"""

    def _parse_practice_questions(
        self,
        text: str,
        subject: str,
        topic: str,
        difficulty: str,
        question_type: str
    ) -> List[Dict[str, Any]]:
        """Parse generated questions into structured format"""
        # Simplified parser - in production, use more robust parsing
        questions = []
        lines = text.strip().split('\n')

        current_question = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect question number
            if line[0].isdigit() and '.' in line[:3]:
                if current_question:
                    questions.append(current_question)

                current_question = {
                    "id": f"q_{len(questions)+1}",
                    "question": line[line.index('.')+1:].strip(),
                    "type": question_type,
                    "difficulty": difficulty,
                    "subject": subject,
                    "topic": topic,
                    "options": [],
                    "correct_answer": None,
                    "explanation": None
                }
            elif current_question and line.startswith(('A)', 'B)', 'C)', 'D)')):
                current_question["options"].append(line[2:].strip())
            elif current_question and "answer:" in line.lower():
                current_question["correct_answer"] = line.split(':')[-1].strip()

        if current_question:
            questions.append(current_question)

        return questions

    def _mock_answer(
        self,
        question: str,
        subject: Optional[str],
        class_level: Optional[str]
    ) -> Dict[str, Any]:
        """Mock answer when OpenAI not available"""
        return {
            "answer": f"""I understand you're asking about: "{question}"

While I'm currently operating in demo mode (OpenAI API not configured), here's a helpful response:

For {subject or 'this subject'} at {class_level or 'your level'}, this is an important topic.

To get full AI-powered answers:
1. Set your OPENAI_API_KEY environment variable
2. Restart the server

The AI tutor will then provide comprehensive, curriculum-aligned answers with examples!""",
            "sources": [],
            "confidence": 0.0,
            "response_time_ms": 1.0,
            "model_used": "mock",
            "tokens_used": 0
        }

    def _mock_practice_questions(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        num_questions: int,
        question_type: str
    ) -> List[Dict[str, Any]]:
        """Mock practice questions when OpenAI not available"""
        questions = []
        for i in range(num_questions):
            questions.append({
                "id": f"q_{i+1}",
                "question": f"Sample {difficulty} {question_type} question {i+1} for {subject} - {topic} (OpenAI API not configured)",
                "type": question_type,
                "difficulty": difficulty,
                "subject": subject,
                "topic": topic,
                "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"] if question_type == "mcq" else None,
                "correct_answer": "B" if question_type == "mcq" else "Sample answer",
                "explanation": "Set OPENAI_API_KEY to generate real practice questions"
            })
        return questions


# Global instance
openai_service = OpenAIService()
