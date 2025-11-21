"""
AI Background Tasks
Asynchronous AI operations using Celery
"""
from celery import shared_task
from src.ai.openai_service import openai_service
from src.database.config import get_db
from src.database import crud
import asyncio


@shared_task(bind=True, name="src.tasks.ai_tasks.generate_practice_questions_async")
def generate_practice_questions_async(
    self,
    user_id: str,
    subject: str,
    topic: str,
    difficulty: str,
    num_questions: int
):
    """
    Generate practice questions asynchronously
    """
    try:
        # Run async function in sync context
        loop = asyncio.get_event_loop()
        questions = loop.run_until_complete(
            openai_service.generate_practice_questions(
                subject=subject,
                topic=topic,
                difficulty=difficulty,
                num_questions=num_questions,
                question_type="mcq"
            )
        )

        # Store in database
        db = next(get_db())
        try:
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
        finally:
            db.close()

        return {
            "status": "success",
            "num_questions": len(questions),
            "user_id": user_id
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }


@shared_task(bind=True, name="src.tasks.ai_tasks.generate_diagnostic_test_async")
def generate_diagnostic_test_async(
    self,
    user_id: str,
    subjects: list,
    class_level: str
):
    """
    Generate diagnostic test asynchronously
    """
    try:
        all_questions = []
        loop = asyncio.get_event_loop()

        for subject in subjects:
            questions = loop.run_until_complete(
                openai_service.generate_practice_questions(
                    subject=subject,
                    topic="Diagnostic Assessment",
                    difficulty="medium",
                    num_questions=10,
                    question_type="mcq"
                )
            )
            all_questions.extend(questions)

        return {
            "status": "success",
            "num_questions": len(all_questions),
            "subjects": subjects,
            "user_id": user_id,
            "questions": all_questions
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }


@shared_task(bind=True, name="src.tasks.ai_tasks.batch_answer_questions")
def batch_answer_questions(self, question_ids: list):
    """
    Process multiple questions in batch
    """
    try:
        db = next(get_db())
        try:
            results = []
            loop = asyncio.get_event_loop()

            for question_id in question_ids:
                question = crud.get_question_by_id(db, question_id)
                if question and not question.answer_text:
                    # Generate answer
                    answer = loop.run_until_complete(
                        openai_service.answer_question(
                            question=question.question_text,
                            subject=question.subject,
                            class_level=question.class_level
                        )
                    )

                    # Update question with answer
                    crud.update_question(
                        db=db,
                        question_id=question_id,
                        answer_text=answer["answer"],
                        confidence_score=answer.get("confidence", 0.0)
                    )

                    results.append({
                        "question_id": question_id,
                        "status": "answered"
                    })

            return {
                "status": "success",
                "processed": len(results),
                "results": results
            }

        finally:
            db.close()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
