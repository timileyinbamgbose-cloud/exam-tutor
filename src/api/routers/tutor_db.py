"""
AI Tutor Router (Database + Real AI Version)
Uses OpenAI API and PostgreSQL/SQLite
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from src.api.models import QuestionRequest, QuestionResponse, PracticeRequest, DiagnosticTestRequest
from src.database.config import get_db
from src.database import crud
from src.ai.openai_service import openai_service
from src.ai.rag_service import rag_service
from typing import Dict, Any
import time

router = APIRouter(prefix="/api/v1/tutor", tags=["AI Tutor"])


# Import get_current_user from auth_db
from src.api.routers.auth_db import get_current_user


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ask the AI tutor a question with real OpenAI integration
    Stores questions and answers in database
    """
    start_time = time.time()

    try:
        # Check subscription limits
        subscription = crud.get_user_subscription(db, current_user["id"])
        if subscription:
            if subscription.questions_limit and subscription.questions_used >= subscription.questions_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Monthly question limit reached ({subscription.questions_limit}). Please upgrade your subscription."
                )

        # Get answer using RAG (Retrieval-Augmented Generation)
        ai_response = await rag_service.answer_question_with_rag(
            question=request.question,
            subject=request.subject,
            class_level=request.class_level,
            use_rag=True,  # Enable RAG pipeline
            top_k=3,  # Retrieve top 3 context documents
            min_similarity=0.6  # Minimum similarity threshold
        )

        # Calculate metrics
        response_time = (time.time() - start_time) * 1000

        # Store question and answer in database
        db_question = crud.create_question(
            db=db,
            user_id=current_user["id"],
            question_text=request.question,
            answer_text=ai_response["answer"],
            subject=request.subject,
            class_level=request.class_level,
            sources=ai_response.get("sources", []),
            confidence_score=ai_response.get("confidence", 0.0),
            response_time_ms=response_time,
            retrieval_time_ms=ai_response.get("retrieval_time_ms", 0.0),
            num_sources=len(ai_response.get("sources", []))
        )

        # Increment subscription usage
        if subscription:
            crud.increment_subscription_usage(db, subscription.id)

        return QuestionResponse(
            answer=ai_response["answer"],
            sources=ai_response.get("sources", []),
            confidence=ai_response.get("confidence", 0.0),
            response_time_ms=response_time,
            retrieval_time_ms=ai_response.get("retrieval_time_ms", 0.0),
            num_sources=len(ai_response.get("sources", []))
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}"
        )


@router.post("/practice")
async def generate_practice(
    request: PracticeRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate practice questions using AI"""
    try:
        # Generate questions using OpenAI
        questions = await openai_service.generate_practice_questions(
            subject=request.subject,
            topic=request.topic or "General",
            difficulty=request.difficulty,
            num_questions=request.num_questions,
            question_type=request.question_type or "mcq"
        )

        # Store generated questions in database for analytics
        for q in questions:
            crud.create_practice_question(
                db=db,
                question_text=q["question"],
                question_type=q["type"],
                subject=q["subject"],
                topic=q["topic"],
                difficulty=q["difficulty"],
                options=q.get("options"),
                correct_answer=q.get("correct_answer"),
                explanation=q.get("explanation")
            )

        return {
            "questions": questions,
            "total": len(questions),
            "subject": request.subject,
            "topic": request.topic,
            "difficulty": request.difficulty
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating practice questions: {str(e)}"
        )


@router.post("/diagnostic")
async def create_diagnostic_test(
    request: DiagnosticTestRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a diagnostic test using AI"""
    try:
        all_questions = []

        # Generate questions for each subject
        for subject in request.subjects:
            questions = await openai_service.generate_practice_questions(
                subject=subject,
                topic="Diagnostic Assessment",
                difficulty="medium",
                num_questions=10,
                question_type="mcq"
            )
            all_questions.extend(questions)

        test = {
            "test_id": f"diag_{current_user['id']}_{int(time.time())}",
            "subjects": request.subjects,
            "class_level": request.class_level,
            "duration_minutes": request.duration_minutes,
            "num_questions": len(all_questions),
            "questions": all_questions,
            "created_at": time.time()
        }

        return test

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating diagnostic test: {str(e)}"
        )


@router.post("/submit-answer")
async def submit_answer(
    question_id: str,
    answer: str,
    correct_answer: str,
    subject: str,
    topic: str = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit answer to a practice question and update progress"""
    try:
        is_correct = (answer.strip().lower() == correct_answer.strip().lower())

        # Update student progress
        crud.update_student_progress(
            db=db,
            user_id=current_user["id"],
            subject=subject,
            topic=topic,
            correct=is_correct,
            study_time_minutes=2  # Estimate
        )

        return {
            "question_id": question_id,
            "submitted_answer": answer,
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": f"{'Correct!' if is_correct else 'Incorrect.'} The right answer is: {correct_answer}",
            "points_earned": 10 if is_correct else 0
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting answer: {str(e)}"
        )


@router.post("/feedback/{question_id}")
async def provide_feedback(
    question_id: str,
    was_helpful: bool,
    rating: int = None,
    feedback_text: str = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Provide feedback on a question/answer"""
    try:
        crud.update_question_feedback(
            db=db,
            question_id=question_id,
            was_helpful=was_helpful,
            rating=rating,
            feedback_text=feedback_text
        )

        return {"message": "Thank you for your feedback!"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting feedback: {str(e)}"
        )


@router.get("/history")
async def get_question_history(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's question history"""
    try:
        questions = crud.get_user_questions(db, current_user["id"], skip, limit)

        return {
            "questions": [
                {
                    "id": q.id,
                    "question": q.question_text,
                    "answer": q.answer_text[:200] + "..." if len(q.answer_text) > 200 else q.answer_text,
                    "subject": q.subject,
                    "created_at": q.created_at.isoformat(),
                    "was_helpful": q.was_helpful,
                    "rating": q.user_rating
                }
                for q in questions
            ],
            "total": len(questions),
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching history: {str(e)}"
        )


@router.get("/progress")
async def get_learning_progress(
    subject: str = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get student's learning progress"""
    try:
        progress_records = crud.get_student_progress(db, current_user["id"], subject)

        return {
            "progress": [
                {
                    "subject": p.subject,
                    "topic": p.topic,
                    "questions_answered": p.questions_answered,
                    "accuracy": round(p.accuracy * 100, 2),
                    "mastery_level": round(p.mastery_level * 100, 2),
                    "total_study_time_hours": round(p.total_study_time_minutes / 60, 2),
                    "last_studied": p.last_studied.isoformat() if p.last_studied else None
                }
                for p in progress_records
            ],
            "total_records": len(progress_records)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching progress: {str(e)}"
        )
