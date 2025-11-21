"""
AI Tutor Router
Handles AI tutoring features: Q&A, practice generation, diagnostics
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from src.api.models import QuestionRequest, QuestionResponse, PracticeRequest, DiagnosticTestRequest
from src.api.auth import get_current_student
from src.database.config import get_db
from src.database.models import Question as QuestionModel
from typing import Dict, Any, List, Optional
import time
import uuid

router = APIRouter(prefix="/api/v1/tutor", tags=["AI Tutor"])

# Initialize RAG pipeline (singleton) - lazy import
rag_pipeline: Optional[Any] = None


def get_rag_pipeline() -> Optional[Any]:
    """Get or initialize RAG pipeline (lazy import)"""
    global rag_pipeline
    if rag_pipeline is None:
        try:
            # Lazy import to avoid missing dependencies
            from src.offline.rag.rag_pipeline import OfflineRAGPipeline
            rag_pipeline = OfflineRAGPipeline(
                vector_store_type="faiss",
                collection_name="examstutor_curriculum",
                top_k=5
            )
        except Exception as e:
            # RAG not available (missing dependencies or not initialized)
            print(f"RAG pipeline not available: {e}")
            pass
    return rag_pipeline


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Ask the AI tutor a question
    Returns answer with curriculum sources and question_id for feedback
    """
    start_time = time.time()

    try:
        rag = get_rag_pipeline()

        if rag is None:
            # RAG not available - return mock response
            return QuestionResponse(
                answer="I'm here to help! However, the AI tutor system is currently being initialized. Please try again in a moment.",
                sources=[],
                confidence=0.0,
                response_time_ms=(time.time() - start_time) * 1000,
                retrieval_time_ms=0.0,
                num_sources=0
            )

        # Build filters if provided
        filters = {}
        if request.subject:
            filters["subject"] = request.subject
        if request.class_level:
            filters["class"] = request.class_level

        # Retrieve relevant context
        retrieval_start = time.time()
        results = rag.retrieve(
            query=request.question,
            top_k=5,
            filters=filters if filters else None
        )
        retrieval_time = (time.time() - retrieval_start) * 1000

        # Generate answer (mock for now - would use LLM in production)
        if results and len(results) > 0:
            # Combine sources into answer
            context = "\n\n".join([r["text"] for r in results[:3]])
            answer = f"Based on the curriculum:\n\n{context}\n\nDoes this help answer your question?"
            confidence = results[0].get("score", 0.8)
        else:
            answer = "I don't have enough information in the curriculum to answer that question. Could you rephrase it or provide more context?"
            confidence = 0.0

        response_time = (time.time() - start_time) * 1000

        # NEW: Save question to database for feedback tracking
        question_id = str(uuid.uuid4())
        db_question = QuestionModel(
            id=question_id,
            user_id=current_user.get("sub"),
            question_text=request.question,
            subject=request.subject,
            topic=request.topic,
            class_level=request.class_level,
            answer_text=answer,
            sources=[{
                "text": r.get("text", "")[:200],
                "subject": r.get("metadata", {}).get("subject", ""),
                "topic": r.get("metadata", {}).get("topic", ""),
                "score": r.get("score", 0.0)
            } for r in results],
            confidence_score=confidence,
            response_time_ms=response_time,
            retrieval_time_ms=retrieval_time,
            num_sources=len(results)
        )
        db.add(db_question)
        db.commit()
        db.refresh(db_question)

        return QuestionResponse(
            answer=answer,
            sources=[{
                "text": r.get("text", "")[:200],
                "subject": r.get("metadata", {}).get("subject", ""),
                "topic": r.get("metadata", {}).get("topic", ""),
                "score": r.get("score", 0.0)
            } for r in results],
            confidence=confidence,
            response_time_ms=response_time,
            retrieval_time_ms=retrieval_time,
            num_sources=len(results),
            question_id=question_id,  # NEW: Return question ID
            feedback_url=f"/api/v1/feedback/{question_id}"  # NEW: Feedback URL
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}"
        )


@router.post("/practice")
async def generate_practice(
    request: PracticeRequest,
    current_user: dict = Depends(get_current_student)
):
    """Generate practice questions for a subject/topic"""
    # Mock practice questions (would use AI generation in production)
    questions = []

    for i in range(request.num_questions):
        question = {
            "id": f"q_{i+1}",
            "question": f"Sample {request.difficulty} question {i+1} for {request.subject}",
            "type": request.question_type or "mcq",
            "difficulty": request.difficulty,
            "subject": request.subject,
            "topic": request.topic,
            "options": ["A", "B", "C", "D"] if request.question_type == "mcq" else None,
            "correct_answer": "B" if request.question_type == "mcq" else None
        }
        questions.append(question)

    return {
        "questions": questions,
        "total": len(questions),
        "subject": request.subject,
        "topic": request.topic,
        "difficulty": request.difficulty
    }


@router.post("/diagnostic")
async def create_diagnostic_test(
    request: DiagnosticTestRequest,
    current_user: dict = Depends(get_current_student)
):
    """Create a diagnostic test to assess student's knowledge"""
    # Mock diagnostic test
    test = {
        "test_id": "diag_001",
        "subjects": request.subjects,
        "class_level": request.class_level,
        "duration_minutes": request.duration_minutes,
        "num_questions": len(request.subjects) * 10,
        "questions": [
            {
                "id": f"dq_{i}",
                "subject": subject,
                "difficulty": "medium",
                "question": f"Diagnostic question {i} for {subject}"
            }
            for i, subject in enumerate(request.subjects)
        ],
        "created_at": time.time()
    }

    return test


@router.post("/submit-answer")
async def submit_answer(
    question_id: str,
    answer: str,
    current_user: dict = Depends(get_current_student)
):
    """Submit answer to a practice question"""
    # Mock answer submission
    is_correct = True  # Would check against actual answer

    return {
        "question_id": question_id,
        "submitted_answer": answer,
        "is_correct": is_correct,
        "explanation": "Great job! This is the correct answer." if is_correct else "Not quite. Let me explain...",
        "points_earned": 10 if is_correct else 0
    }
