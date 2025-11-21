"""
Interactive Feedback Loop Router
Handles feedback collection, analytics, and automated response management
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, desc
from src.api.models import (
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
    FeedbackAnalyticsResponse,
    FeedbackTrendingResponse,
    FeedbackCategory
)
from src.api.auth import get_current_student
from src.database.config import get_db
from src.database.models import ResponseFeedback, Question as QuestionModel, UserRole
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])
logger = logging.getLogger(__name__)

# Simple sentiment analysis (can be enhanced with NLP later)
def analyze_sentiment(text: Optional[str]) -> float:
    """
    Basic sentiment analysis
    Returns: -1 (negative) to 1 (positive)
    """
    if not text:
        return 0.0

    text_lower = text.lower()

    positive_words = ["good", "great", "helpful", "excellent", "clear", "perfect", "amazing", "thanks", "thank you"]
    negative_words = ["bad", "poor", "unclear", "confusing", "wrong", "incorrect", "useless", "terrible"]

    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    total = positive_count + negative_count
    if total == 0:
        return 0.0

    return (positive_count - negative_count) / total


async def invalidate_cache_for_question(question_id: str):
    """
    Invalidate cache for poorly-rated responses
    """
    try:
        from src.cache.redis_cache import cache
        cache_key = f"question:{question_id}"
        await cache.delete(cache_key)
        logger.info(f"Cache invalidated for question {question_id}")
    except Exception as e:
        logger.warning(f"Could not invalidate cache: {e}")


async def send_alert(message: str, severity: str = "medium"):
    """
    Send alert for poor feedback patterns
    In production, this would integrate with Slack, email, or monitoring system
    """
    logger.warning(f"[{severity.upper()}] FEEDBACK ALERT: {message}")
    # TODO: Integrate with Slack/Email/Monitoring system


async def check_feedback_pattern(db: Session, subject: Optional[str], rating: int) -> bool:
    """
    Check if there's a pattern of poor feedback
    Returns True if pattern detected (3+ poor ratings in last hour)
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    query = db.query(ResponseFeedback).filter(
        ResponseFeedback.rating <= 2,
        ResponseFeedback.created_at >= one_hour_ago
    )

    if subject:
        query = query.join(QuestionModel).filter(QuestionModel.subject == subject)

    poor_feedback_count = query.count()

    return poor_feedback_count >= 3


@router.post("/{question_id}", response_model=FeedbackSubmitResponse)
async def submit_feedback(
    question_id: str,
    feedback: FeedbackSubmitRequest,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Submit feedback on an AI response

    - **was_helpful**: Boolean thumbs up/down
    - **rating**: 1-5 stars
    - **feedback_text**: Optional detailed feedback
    - **categories**: What aspects need improvement
    - **time_to_feedback_sec**: How long after response was feedback given
    """

    # 1. Validate that question exists
    question = db.query(QuestionModel).filter(QuestionModel.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question {question_id} not found"
        )

    # 2. Analyze sentiment
    sentiment = analyze_sentiment(feedback.feedback_text)

    # 3. Create feedback record
    feedback_id = str(uuid.uuid4())
    db_feedback = ResponseFeedback(
        id=feedback_id,
        question_id=question_id,
        user_id=current_user.get("sub"),
        was_helpful=feedback.was_helpful,
        rating=feedback.rating,
        feedback_text=feedback.feedback_text,
        feedback_category=",".join([cat.value for cat in feedback.categories]) if feedback.categories else None,
        sentiment_score=sentiment,
        time_to_feedback_sec=feedback.time_to_feedback_sec,
        model_used="rag_pipeline",  # Could extract from question metadata
        rag_enabled=question.num_sources > 0,
        response_time_ms=question.response_time_ms
    )

    db.add(db_feedback)

    # 4. Update question with basic feedback (for backward compatibility)
    question.was_helpful = feedback.was_helpful
    question.user_rating = feedback.rating
    question.feedback_text = feedback.feedback_text

    db.commit()
    db.refresh(db_feedback)

    # 5. Handle poor feedback (rating <= 2)
    if feedback.rating <= 2:
        # Invalidate cache
        await invalidate_cache_for_question(question_id)
        db_feedback.action_taken = "cache_invalidated"

        # Check for patterns and alert
        pattern_detected = await check_feedback_pattern(db, question.subject, feedback.rating)
        if pattern_detected:
            await send_alert(
                f"Poor feedback pattern detected for {question.subject or 'general questions'}. "
                f"3+ ratings ≤2 in the last hour.",
                severity="medium"
            )
            db_feedback.action_taken = "cache_invalidated,alerted"

        db.commit()

    logger.info(
        f"Feedback submitted: question_id={question_id}, rating={feedback.rating}, "
        f"helpful={feedback.was_helpful}, sentiment={sentiment:.2f}"
    )

    return FeedbackSubmitResponse(
        message="Thank you for your feedback! This helps us improve.",
        feedback_id=feedback_id,
        processed=False
    )


@router.get("/analytics", response_model=FeedbackAnalyticsResponse)
async def get_feedback_analytics(
    timeframe: str = Query(default="7d", regex="^(24h|7d|30d|all)$"),
    subject: Optional[str] = None,
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Get feedback analytics

    - **timeframe**: 24h, 7d, 30d, or all
    - **subject**: Optional subject filter
    """

    # Calculate date filter
    now = datetime.utcnow()
    if timeframe == "24h":
        start_date = now - timedelta(hours=24)
    elif timeframe == "7d":
        start_date = now - timedelta(days=7)
    elif timeframe == "30d":
        start_date = now - timedelta(days=30)
    else:
        start_date = None

    # Base query for questions
    questions_query = db.query(QuestionModel)
    if start_date:
        questions_query = questions_query.filter(QuestionModel.created_at >= start_date)
    if subject:
        questions_query = questions_query.filter(QuestionModel.subject == subject)

    # Base query for feedback
    feedback_query = db.query(ResponseFeedback)
    if start_date:
        feedback_query = feedback_query.filter(ResponseFeedback.created_at >= start_date)
    if subject:
        feedback_query = feedback_query.join(QuestionModel).filter(QuestionModel.subject == subject)

    # Get metrics
    total_responses = questions_query.count()
    feedback_received = feedback_query.count()
    feedback_rate = feedback_received / total_responses if total_responses > 0 else 0.0

    # Average rating
    avg_rating_result = feedback_query.filter(ResponseFeedback.rating.isnot(None)).with_entities(
        func.avg(ResponseFeedback.rating)
    ).scalar()
    average_rating = float(avg_rating_result) if avg_rating_result else 0.0

    # Helpfulness rate
    helpful_count = feedback_query.filter(ResponseFeedback.was_helpful == True).count()
    helpfulness_rate = helpful_count / feedback_received if feedback_received > 0 else 0.0

    # Sentiment distribution
    positive_sentiment = feedback_query.filter(ResponseFeedback.sentiment_score > 0.2).count()
    neutral_sentiment = feedback_query.filter(
        and_(ResponseFeedback.sentiment_score >= -0.2, ResponseFeedback.sentiment_score <= 0.2)
    ).count()
    negative_sentiment = feedback_query.filter(ResponseFeedback.sentiment_score < -0.2).count()

    total_sentiment = positive_sentiment + neutral_sentiment + negative_sentiment
    sentiment_distribution = {
        "positive": positive_sentiment / total_sentiment if total_sentiment > 0 else 0.0,
        "neutral": neutral_sentiment / total_sentiment if total_sentiment > 0 else 0.0,
        "negative": negative_sentiment / total_sentiment if total_sentiment > 0 else 0.0
    }

    # Top issues (from categories)
    feedback_with_categories = feedback_query.filter(
        ResponseFeedback.feedback_category.isnot(None)
    ).all()

    category_counts = {}
    for fb in feedback_with_categories:
        if fb.feedback_category:
            categories = fb.feedback_category.split(",")
            for cat in categories:
                category_counts[cat] = category_counts.get(cat, 0) + 1

    top_issues = [
        {"category": cat, "count": count}
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    # By subject (if not filtered by subject)
    by_subject = None
    if not subject:
        subject_stats = db.query(
            QuestionModel.subject,
            func.avg(ResponseFeedback.rating).label("avg_rating"),
            func.count(ResponseFeedback.id).label("feedback_count"),
            func.sum(case((ResponseFeedback.was_helpful == True, 1), else_=0)).label("helpful_count")
        ).join(ResponseFeedback).group_by(QuestionModel.subject).all()

        by_subject = [
            {
                "subject": stat.subject or "General",
                "avg_rating": float(stat.avg_rating) if stat.avg_rating else 0.0,
                "helpfulness": float(stat.helpful_count) / float(stat.feedback_count) if stat.feedback_count > 0 else 0.0,
                "total_responses": stat.feedback_count
            }
            for stat in subject_stats
        ]

    return FeedbackAnalyticsResponse(
        total_responses=total_responses,
        feedback_received=feedback_received,
        feedback_rate=feedback_rate,
        average_rating=average_rating,
        helpfulness_rate=helpfulness_rate,
        sentiment_distribution=sentiment_distribution,
        top_issues=top_issues,
        by_subject=by_subject
    )


@router.get("/trending", response_model=FeedbackTrendingResponse)
async def get_trending_feedback(
    period: str = Query(default="24h", regex="^(24h|7d)$"),
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Get trending positive and negative feedback

    - **period**: 24h or 7d
    """

    # Calculate date filter
    now = datetime.utcnow()
    if period == "24h":
        start_date = now - timedelta(hours=24)
    else:
        start_date = now - timedelta(days=7)

    # Trending positive (avg rating >= 4)
    positive_query = db.query(
        QuestionModel.topic,
        QuestionModel.subject,
        func.avg(ResponseFeedback.rating).label("avg_rating"),
        func.count(ResponseFeedback.id).label("feedback_count")
    ).join(ResponseFeedback).filter(
        ResponseFeedback.created_at >= start_date,
        QuestionModel.topic.isnot(None)
    ).group_by(QuestionModel.topic, QuestionModel.subject).having(
        func.avg(ResponseFeedback.rating) >= 4.0
    ).order_by(desc("avg_rating")).limit(5).all()

    trending_positive = [
        {
            "topic": p.topic,
            "subject": p.subject,
            "avg_rating": float(p.avg_rating),
            "feedback_count": p.feedback_count
        }
        for p in positive_query
    ]

    # Trending negative (avg rating <= 2.5)
    negative_query = db.query(
        QuestionModel.topic,
        QuestionModel.subject,
        func.avg(ResponseFeedback.rating).label("avg_rating"),
        func.count(ResponseFeedback.id).label("feedback_count")
    ).join(ResponseFeedback).filter(
        ResponseFeedback.created_at >= start_date,
        QuestionModel.topic.isnot(None)
    ).group_by(QuestionModel.topic, QuestionModel.subject).having(
        func.avg(ResponseFeedback.rating) <= 2.5
    ).order_by("avg_rating").limit(5).all()

    trending_negative = [
        {
            "topic": n.topic,
            "subject": n.subject,
            "avg_rating": float(n.avg_rating),
            "feedback_count": n.feedback_count
        }
        for n in negative_query
    ]

    # Action required (low ratings + multiple feedback)
    action_required = []
    for neg in trending_negative:
        if neg["feedback_count"] >= 3:
            # Analyze common categories for this topic
            topic_feedback = db.query(ResponseFeedback).join(QuestionModel).filter(
                QuestionModel.topic == neg["topic"],
                ResponseFeedback.created_at >= start_date
            ).all()

            common_issues = {}
            for fb in topic_feedback:
                if fb.feedback_category:
                    for cat in fb.feedback_category.split(","):
                        common_issues[cat] = common_issues.get(cat, 0) + 1

            top_issue = max(common_issues.items(), key=lambda x: x[1])[0] if common_issues else "unclear"

            action_required.append({
                "subject": neg["subject"],
                "topic": neg["topic"],
                "avg_rating": neg["avg_rating"],
                "issue": top_issue,
                "suggestion": f"Review and improve {top_issue} for this topic"
            })

    return FeedbackTrendingResponse(
        trending_positive=trending_positive,
        trending_negative=trending_negative,
        action_required=action_required
    )


@router.get("/low-performing")
async def get_low_performing_responses(
    min_rating: int = Query(default=2, ge=1, le=5),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Get low-performing responses (for review and improvement)
    Admin/Teacher only in production
    """

    # Get questions with low ratings
    low_rated = db.query(QuestionModel, ResponseFeedback).join(ResponseFeedback).filter(
        ResponseFeedback.rating <= min_rating
    ).order_by(desc(ResponseFeedback.created_at)).limit(limit).all()

    results = [
        {
            "question_id": q.id,
            "question": q.question_text,
            "answer": q.answer_text[:200] + "..." if len(q.answer_text) > 200 else q.answer_text,
            "subject": q.subject,
            "topic": q.topic,
            "rating": fb.rating,
            "was_helpful": fb.was_helpful,
            "feedback": fb.feedback_text,
            "categories": fb.feedback_category.split(",") if fb.feedback_category else [],
            "created_at": fb.created_at.isoformat()
        }
        for q, fb in low_rated
    ]

    return {
        "total": len(results),
        "min_rating": min_rating,
        "responses": results
    }
