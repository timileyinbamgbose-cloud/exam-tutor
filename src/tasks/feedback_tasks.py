"""
Feedback Processing Background Tasks
Handles feedback analysis, sentiment processing, and automated actions
"""
from celery import shared_task
from src.database.config import get_db
from src.database import models
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import logging

logger = logging.getLogger(__name__)


def analyze_sentiment_advanced(text: str) -> float:
    """
    Enhanced sentiment analysis (can be upgraded with NLP models)
    Returns: -1 (negative) to 1 (positive)
    """
    if not text:
        return 0.0

    text_lower = text.lower()

    # Expanded sentiment dictionaries
    positive_words = [
        "good", "great", "helpful", "excellent", "clear", "perfect", "amazing",
        "thanks", "thank you", "awesome", "fantastic", "wonderful", "brilliant",
        "love", "best", "useful", "easy", "understand", "comprehensive"
    ]

    negative_words = [
        "bad", "poor", "unclear", "confusing", "wrong", "incorrect", "useless",
        "terrible", "hate", "worst", "difficult", "complicated", "incomplete",
        "missing", "error", "broken", "fail", "disappointing"
    ]

    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    total = positive_count + negative_count
    if total == 0:
        return 0.0

    return (positive_count - negative_count) / total


@shared_task(bind=True, name="src.tasks.feedback_tasks.process_unprocessed_feedback")
def process_unprocessed_feedback(self):
    """
    Process feedback entries that haven't been analyzed yet
    Updates sentiment scores and categorization
    """
    try:
        db = next(get_db())
        try:
            # Get unprocessed feedback
            unprocessed = db.query(models.ResponseFeedback).filter(
                models.ResponseFeedback.processed == False
            ).limit(100).all()

            processed_count = 0
            for feedback in unprocessed:
                # Re-analyze sentiment with advanced algorithm
                if feedback.feedback_text:
                    feedback.sentiment_score = analyze_sentiment_advanced(feedback.feedback_text)

                # Auto-categorize based on keywords if not already categorized
                if not feedback.feedback_category and feedback.feedback_text:
                    categories = auto_categorize_feedback(feedback.feedback_text)
                    if categories:
                        feedback.feedback_category = ",".join(categories)

                # Mark as processed
                feedback.processed = True
                processed_count += 1

            db.commit()

            return {
                "status": "success",
                "processed_count": processed_count,
                "unprocessed_remaining": len(unprocessed) - processed_count
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def auto_categorize_feedback(text: str) -> list:
    """
    Auto-categorize feedback based on keywords
    Returns list of categories
    """
    categories = []
    text_lower = text.lower()

    # Category keywords
    category_keywords = {
        "clarity": ["unclear", "confusing", "don't understand", "complicated", "complex"],
        "accuracy": ["wrong", "incorrect", "error", "mistake", "inaccurate"],
        "completeness": ["incomplete", "missing", "more detail", "not enough", "need more"],
        "needs_examples": ["example", "show me", "demonstrate", "concrete"],
        "relevance": ["off-topic", "not related", "irrelevant", "different"],
        "tone": ["tone", "rude", "friendly", "professional"]
    }

    for category, keywords in category_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            categories.append(category)

    return categories


@shared_task(bind=True, name="src.tasks.feedback_tasks.invalidate_poor_response_cache")
def invalidate_poor_response_cache(self):
    """
    Invalidate cache for responses with poor feedback
    Runs every hour to clean up bad cached responses
    """
    try:
        db = next(get_db())
        try:
            # Find responses with poor ratings in last 24 hours that haven't had cache invalidated
            day_ago = datetime.utcnow() - timedelta(hours=24)

            poor_feedback = db.query(models.ResponseFeedback).filter(
                models.ResponseFeedback.rating <= 2,
                models.ResponseFeedback.created_at >= day_ago,
                ~models.ResponseFeedback.action_taken.contains("cache_invalidated")
            ).all()

            invalidated_count = 0
            for feedback in poor_feedback:
                try:
                    # Import cache service
                    from src.cache.redis_cache import cache

                    # Invalidate cache for this question
                    cache_key = f"question:{feedback.question_id}"
                    cache.delete(cache_key)

                    # Update action_taken
                    if feedback.action_taken:
                        feedback.action_taken += ",cache_invalidated"
                    else:
                        feedback.action_taken = "cache_invalidated"

                    invalidated_count += 1

                except Exception as cache_error:
                    logger.warning(f"Could not invalidate cache for {feedback.question_id}: {cache_error}")

            db.commit()

            return {
                "status": "success",
                "invalidated_count": invalidated_count
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@shared_task(bind=True, name="src.tasks.feedback_tasks.detect_feedback_patterns")
def detect_feedback_patterns(self):
    """
    Detect patterns of poor feedback and send alerts
    Runs every 6 hours
    """
    try:
        db = next(get_db())
        try:
            # Check last 24 hours
            day_ago = datetime.utcnow() - timedelta(hours=24)

            # Group poor feedback by subject
            pattern_query = db.query(
                models.Question.subject,
                func.count(models.ResponseFeedback.id).label("poor_count"),
                func.avg(models.ResponseFeedback.rating).label("avg_rating")
            ).join(
                models.ResponseFeedback
            ).filter(
                models.ResponseFeedback.rating <= 2,
                models.ResponseFeedback.created_at >= day_ago
            ).group_by(
                models.Question.subject
            ).having(
                func.count(models.ResponseFeedback.id) >= 3
            ).all()

            alerts_sent = []
            for pattern in pattern_query:
                alert_message = (
                    f"⚠️ Poor feedback pattern detected for {pattern.subject or 'general questions'}. "
                    f"{pattern.poor_count} ratings ≤2 in the last 24 hours. "
                    f"Average rating: {pattern.avg_rating:.2f}"
                )

                # Log alert (in production, send to Slack/Email)
                logger.warning(alert_message)

                alerts_sent.append({
                    "subject": pattern.subject,
                    "poor_feedback_count": pattern.poor_count,
                    "avg_rating": float(pattern.avg_rating),
                    "message": alert_message
                })

            return {
                "status": "success",
                "patterns_detected": len(alerts_sent),
                "alerts": alerts_sent
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error detecting patterns: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@shared_task(bind=True, name="src.tasks.feedback_tasks.prepare_finetuning_data")
def prepare_finetuning_data(self):
    """
    Prepare fine-tuning dataset from highly-rated responses
    Runs weekly to collect training data
    """
    try:
        db = next(get_db())
        try:
            # Get responses with rating >= 4 from last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)

            high_quality = db.query(
                models.Question, models.ResponseFeedback
            ).join(
                models.ResponseFeedback
            ).filter(
                models.ResponseFeedback.rating >= 4,
                models.ResponseFeedback.created_at >= week_ago
            ).all()

            training_samples = []
            for question, feedback in high_quality:
                sample = {
                    "question_id": question.id,
                    "question": question.question_text,
                    "answer": question.answer_text,
                    "subject": question.subject,
                    "topic": question.topic,
                    "rating": feedback.rating,
                    "was_helpful": feedback.was_helpful,
                    "sentiment": feedback.sentiment_score
                }
                training_samples.append(sample)

            # In production, save to S3 or training data store
            logger.info(f"Prepared {len(training_samples)} samples for fine-tuning")

            return {
                "status": "success",
                "samples_prepared": len(training_samples),
                "period": "last_7_days",
                "avg_rating": sum(s["rating"] for s in training_samples) / len(training_samples) if training_samples else 0
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error preparing fine-tuning data: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@shared_task(bind=True, name="src.tasks.feedback_tasks.generate_weekly_feedback_report")
def generate_weekly_feedback_report(self):
    """
    Generate comprehensive weekly feedback report
    Runs every Monday
    """
    try:
        db = next(get_db())
        try:
            # Last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)

            # Overall metrics
            total_feedback = db.query(func.count(models.ResponseFeedback.id)).filter(
                models.ResponseFeedback.created_at >= week_ago
            ).scalar() or 0

            avg_rating = db.query(func.avg(models.ResponseFeedback.rating)).filter(
                models.ResponseFeedback.created_at >= week_ago
            ).scalar()

            helpful_count = db.query(func.count(models.ResponseFeedback.id)).filter(
                models.ResponseFeedback.created_at >= week_ago,
                models.ResponseFeedback.was_helpful == True
            ).scalar() or 0

            # By subject
            subject_stats = db.query(
                models.Question.subject,
                func.count(models.ResponseFeedback.id).label("count"),
                func.avg(models.ResponseFeedback.rating).label("avg_rating")
            ).join(models.ResponseFeedback).filter(
                models.ResponseFeedback.created_at >= week_ago
            ).group_by(models.Question.subject).all()

            # Top issues
            feedback_with_text = db.query(models.ResponseFeedback).filter(
                models.ResponseFeedback.created_at >= week_ago,
                models.ResponseFeedback.feedback_text.isnot(None)
            ).all()

            category_counts = {}
            for fb in feedback_with_text:
                if fb.feedback_category:
                    for cat in fb.feedback_category.split(","):
                        category_counts[cat] = category_counts.get(cat, 0) + 1

            report = {
                "period": {
                    "start": week_ago.isoformat(),
                    "end": datetime.utcnow().isoformat()
                },
                "overall": {
                    "total_feedback": total_feedback,
                    "average_rating": float(avg_rating) if avg_rating else 0.0,
                    "helpfulness_rate": helpful_count / total_feedback if total_feedback > 0 else 0.0
                },
                "by_subject": [
                    {
                        "subject": stat.subject or "General",
                        "feedback_count": stat.count,
                        "avg_rating": float(stat.avg_rating)
                    }
                    for stat in subject_stats
                ],
                "top_issues": [
                    {"category": cat, "count": count}
                    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                ]
            }

            # In production, send via email or save to database
            logger.info(f"Weekly feedback report generated: {report}")

            return {
                "status": "success",
                "report": report
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
