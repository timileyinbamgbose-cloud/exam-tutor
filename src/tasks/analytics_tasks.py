"""
Analytics Background Tasks
Periodic data processing and cleanup
"""
from celery import shared_task
from src.database.config import get_db
from src.database import crud, models
from datetime import datetime, timedelta
from sqlalchemy import func


@shared_task(bind=True, name="src.tasks.analytics_tasks.cleanup_old_sessions")
def cleanup_old_sessions(self):
    """
    Clean up expired sessions from database
    """
    try:
        db = next(get_db())
        try:
            # Delete sessions expired more than 7 days ago
            cutoff_date = datetime.utcnow() - timedelta(days=7)

            deleted = db.query(models.UserSession).filter(
                models.UserSession.expires_at < cutoff_date
            ).delete()

            db.commit()

            return {
                "status": "success",
                "deleted_sessions": deleted,
                "cutoff_date": cutoff_date.isoformat()
            }

        finally:
            db.close()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@shared_task(bind=True, name="src.tasks.analytics_tasks.update_subscription_status")
def update_subscription_status(self):
    """
    Update subscription statuses (expire inactive subscriptions)
    """
    try:
        db = next(get_db())
        try:
            now = datetime.utcnow()

            # Find expired subscriptions
            expired_count = db.query(models.Subscription).filter(
                models.Subscription.end_date < now,
                models.Subscription.status == "active"
            ).update({
                "status": "expired"
            })

            db.commit()

            return {
                "status": "success",
                "expired_subscriptions": expired_count
            }

        finally:
            db.close()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@shared_task(bind=True, name="src.tasks.analytics_tasks.generate_daily_analytics")
def generate_daily_analytics(self):
    """
    Generate daily analytics report
    """
    try:
        db = next(get_db())
        try:
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)

            # Count new users
            new_users = db.query(func.count(models.User.id)).filter(
                func.date(models.User.created_at) == yesterday
            ).scalar()

            # Count questions asked
            questions_asked = db.query(func.count(models.Question.id)).filter(
                func.date(models.Question.created_at) == yesterday
            ).scalar()

            # Count active subscriptions
            active_subscriptions = db.query(func.count(models.Subscription.id)).filter(
                models.Subscription.status == "active"
            ).scalar()

            # Average response time
            avg_response_time = db.query(func.avg(models.Question.response_time_ms)).filter(
                func.date(models.Question.created_at) == yesterday
            ).scalar()

            analytics = {
                "date": yesterday.isoformat(),
                "new_users": new_users or 0,
                "questions_asked": questions_asked or 0,
                "active_subscriptions": active_subscriptions or 0,
                "avg_response_time_ms": float(avg_response_time) if avg_response_time else 0.0
            }

            return {
                "status": "success",
                "analytics": analytics
            }

        finally:
            db.close()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@shared_task(bind=True, name="src.tasks.analytics_tasks.calculate_student_mastery")
def calculate_student_mastery(self, user_id: str):
    """
    Calculate student mastery levels across subjects
    """
    try:
        db = next(get_db())
        try:
            progress_records = crud.get_student_progress(db, user_id)

            mastery_summary = {}
            for progress in progress_records:
                mastery_summary[progress.subject] = {
                    "accuracy": progress.accuracy,
                    "mastery_level": progress.mastery_level,
                    "questions_answered": progress.questions_answered,
                    "study_time_hours": progress.total_study_time_minutes / 60
                }

            return {
                "status": "success",
                "user_id": user_id,
                "mastery_summary": mastery_summary
            }

        finally:
            db.close()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }


@shared_task(bind=True, name="src.tasks.analytics_tasks.generate_feedback_analytics")
def generate_feedback_analytics(self):
    """
    Generate daily feedback analytics report
    Tracks feedback metrics, ratings, and trends
    """
    try:
        db = next(get_db())
        try:
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            start_of_day = datetime.combine(yesterday, datetime.min.time())
            end_of_day = datetime.combine(yesterday, datetime.max.time())

            # Total responses and feedback received
            total_responses = db.query(func.count(models.Question.id)).filter(
                models.Question.created_at >= start_of_day,
                models.Question.created_at <= end_of_day
            ).scalar() or 0

            feedback_received = db.query(func.count(models.ResponseFeedback.id)).filter(
                models.ResponseFeedback.created_at >= start_of_day,
                models.ResponseFeedback.created_at <= end_of_day
            ).scalar() or 0

            # Average rating
            avg_rating = db.query(func.avg(models.ResponseFeedback.rating)).filter(
                models.ResponseFeedback.created_at >= start_of_day,
                models.ResponseFeedback.created_at <= end_of_day
            ).scalar()

            # Helpfulness rate
            helpful_count = db.query(func.count(models.ResponseFeedback.id)).filter(
                models.ResponseFeedback.created_at >= start_of_day,
                models.ResponseFeedback.created_at <= end_of_day,
                models.ResponseFeedback.was_helpful == True
            ).scalar() or 0

            # Poor feedback count (rating <= 2)
            poor_feedback_count = db.query(func.count(models.ResponseFeedback.id)).filter(
                models.ResponseFeedback.created_at >= start_of_day,
                models.ResponseFeedback.created_at <= end_of_day,
                models.ResponseFeedback.rating <= 2
            ).scalar() or 0

            # Average sentiment
            avg_sentiment = db.query(func.avg(models.ResponseFeedback.sentiment_score)).filter(
                models.ResponseFeedback.created_at >= start_of_day,
                models.ResponseFeedback.created_at <= end_of_day,
                models.ResponseFeedback.sentiment_score.isnot(None)
            ).scalar()

            analytics = {
                "date": yesterday.isoformat(),
                "total_responses": total_responses,
                "feedback_received": feedback_received,
                "feedback_rate": feedback_received / total_responses if total_responses > 0 else 0.0,
                "average_rating": float(avg_rating) if avg_rating else 0.0,
                "helpfulness_rate": helpful_count / feedback_received if feedback_received > 0 else 0.0,
                "poor_feedback_count": poor_feedback_count,
                "average_sentiment": float(avg_sentiment) if avg_sentiment else 0.0
            }

            return {
                "status": "success",
                "analytics": analytics
            }

        finally:
            db.close()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@shared_task(bind=True, name="src.tasks.analytics_tasks.identify_problem_areas")
def identify_problem_areas(self):
    """
    Identify subjects/topics with consistently poor feedback
    Runs weekly to generate improvement recommendations
    """
    try:
        db = next(get_db())
        try:
            # Look at last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)

            # Find topics with avg rating <= 2.5 and at least 5 feedback entries
            from sqlalchemy import and_

            poor_topics = db.query(
                models.Question.subject,
                models.Question.topic,
                func.avg(models.ResponseFeedback.rating).label("avg_rating"),
                func.count(models.ResponseFeedback.id).label("feedback_count")
            ).join(
                models.ResponseFeedback
            ).filter(
                models.ResponseFeedback.created_at >= week_ago,
                models.Question.topic.isnot(None)
            ).group_by(
                models.Question.subject,
                models.Question.topic
            ).having(
                and_(
                    func.avg(models.ResponseFeedback.rating) <= 2.5,
                    func.count(models.ResponseFeedback.id) >= 5
                )
            ).all()

            problem_areas = [
                {
                    "subject": topic.subject,
                    "topic": topic.topic,
                    "avg_rating": float(topic.avg_rating),
                    "feedback_count": topic.feedback_count,
                    "recommendation": "Review and improve content/responses for this topic"
                }
                for topic in poor_topics
            ]

            return {
                "status": "success",
                "problem_areas_count": len(problem_areas),
                "problem_areas": problem_areas
            }

        finally:
            db.close()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
