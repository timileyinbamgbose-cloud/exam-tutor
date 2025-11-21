"""
CRUD Operations
Database operations for all models
"""
from sqlalchemy.orm import Session
from src.database import models
from src.api.auth import hash_password
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid


# ============= USER OPERATIONS =============

def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str,
    role: str,
    school_id: Optional[str] = None,
    class_level: Optional[str] = None
) -> models.User:
    """Create a new user"""
    user = models.User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        school_id=school_id,
        class_level=class_level
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[models.User]:
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def update_user_last_login(db: Session, user_id: str):
    """Update user's last login timestamp"""
    user = get_user_by_id(db, user_id)
    if user:
        user.last_login = datetime.utcnow()
        db.commit()


def get_all_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None
) -> List[models.User]:
    """Get all users with optional filtering"""
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    return query.offset(skip).limit(limit).all()


# ============= QUESTION OPERATIONS =============

def create_question(
    db: Session,
    user_id: str,
    question_text: str,
    answer_text: str,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    class_level: Optional[str] = None,
    sources: Optional[List[Dict]] = None,
    confidence_score: Optional[float] = None,
    response_time_ms: Optional[float] = None,
    retrieval_time_ms: Optional[float] = None,
    num_sources: int = 0
) -> models.Question:
    """Create a new question record"""
    question = models.Question(
        id=str(uuid.uuid4()),
        user_id=user_id,
        question_text=question_text,
        answer_text=answer_text,
        subject=subject,
        topic=topic,
        class_level=class_level,
        sources=sources,
        confidence_score=confidence_score,
        response_time_ms=response_time_ms,
        retrieval_time_ms=retrieval_time_ms,
        num_sources=num_sources
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_user_questions(
    db: Session,
    user_id: str,
    skip: int = 0,
    limit: int = 50
) -> List[models.Question]:
    """Get all questions asked by a user"""
    return db.query(models.Question)\
        .filter(models.Question.user_id == user_id)\
        .order_by(models.Question.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_question_by_id(db: Session, question_id: str) -> Optional[models.Question]:
    """Get a specific question by ID"""
    return db.query(models.Question).filter(models.Question.id == question_id).first()


def update_question_feedback(
    db: Session,
    question_id: str,
    was_helpful: bool,
    rating: Optional[int] = None,
    feedback_text: Optional[str] = None
):
    """Update question feedback"""
    question = get_question_by_id(db, question_id)
    if question:
        question.was_helpful = was_helpful
        question.user_rating = rating
        question.feedback_text = feedback_text
        db.commit()


# ============= SESSION OPERATIONS =============

def create_session(
    db: Session,
    user_id: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_at: datetime,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> models.UserSession:
    """Create a new user session"""
    session = models.UserSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_token(db: Session, access_token: str) -> Optional[models.UserSession]:
    """Get session by access token"""
    return db.query(models.UserSession)\
        .filter(models.UserSession.access_token == access_token)\
        .filter(models.UserSession.is_active == True)\
        .first()


def revoke_session(db: Session, session_id: str):
    """Revoke a session"""
    session = db.query(models.UserSession).filter(models.UserSession.id == session_id).first()
    if session:
        session.is_active = False
        session.revoked_at = datetime.utcnow()
        db.commit()


def revoke_user_sessions(db: Session, user_id: str):
    """Revoke all sessions for a user"""
    sessions = db.query(models.UserSession)\
        .filter(models.UserSession.user_id == user_id)\
        .filter(models.UserSession.is_active == True)\
        .all()

    for session in sessions:
        session.is_active = False
        session.revoked_at = datetime.utcnow()

    db.commit()


# ============= SUBSCRIPTION OPERATIONS =============

def create_subscription(
    db: Session,
    user_id: str,
    tier: str,
    price_monthly: float,
    questions_limit: Optional[int] = None
) -> models.Subscription:
    """Create a new subscription"""
    subscription = models.Subscription(
        id=str(uuid.uuid4()),
        user_id=user_id,
        tier=tier,
        price_monthly=price_monthly,
        questions_limit=questions_limit,
        next_billing_date=datetime.utcnow() + timedelta(days=30)
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_user_subscription(db: Session, user_id: str) -> Optional[models.Subscription]:
    """Get active subscription for a user"""
    return db.query(models.Subscription)\
        .filter(models.Subscription.user_id == user_id)\
        .filter(models.Subscription.status == "active")\
        .first()


def increment_subscription_usage(db: Session, subscription_id: str):
    """Increment questions used count"""
    subscription = db.query(models.Subscription)\
        .filter(models.Subscription.id == subscription_id)\
        .first()

    if subscription:
        subscription.questions_used += 1
        db.commit()


# ============= PRACTICE QUESTION OPERATIONS =============

def create_practice_question(
    db: Session,
    question_text: str,
    question_type: str,
    subject: str,
    topic: str,
    difficulty: str,
    class_level: Optional[str] = None,
    options: Optional[List[str]] = None,
    correct_answer: Optional[str] = None,
    explanation: Optional[str] = None
) -> models.PracticeQuestion:
    """Create a practice question"""
    question = models.PracticeQuestion(
        id=str(uuid.uuid4()),
        question_text=question_text,
        question_type=question_type,
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        class_level=class_level,
        options=options,
        correct_answer=correct_answer,
        explanation=explanation
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_practice_questions(
    db: Session,
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 10
) -> List[models.PracticeQuestion]:
    """Get practice questions with filters"""
    query = db.query(models.PracticeQuestion)

    if subject:
        query = query.filter(models.PracticeQuestion.subject == subject)
    if difficulty:
        query = query.filter(models.PracticeQuestion.difficulty == difficulty)

    return query.limit(limit).all()


# ============= PROGRESS TRACKING =============

def update_student_progress(
    db: Session,
    user_id: str,
    subject: str,
    topic: Optional[str],
    correct: bool,
    study_time_minutes: int = 0
):
    """Update or create student progress record"""
    progress = db.query(models.StudentProgress)\
        .filter(models.StudentProgress.user_id == user_id)\
        .filter(models.StudentProgress.subject == subject)\
        .filter(models.StudentProgress.topic == topic)\
        .first()

    if not progress:
        progress = models.StudentProgress(
            id=str(uuid.uuid4()),
            user_id=user_id,
            subject=subject,
            topic=topic
        )
        db.add(progress)

    progress.questions_answered += 1
    if correct:
        progress.correct_answers += 1

    progress.accuracy = progress.correct_answers / progress.questions_answered
    progress.total_study_time_minutes += study_time_minutes
    progress.last_studied = datetime.utcnow()
    progress.mastery_level = min(progress.accuracy * 1.2, 1.0)  # Simplified mastery calculation

    db.commit()
    db.refresh(progress)
    return progress


def get_student_progress(
    db: Session,
    user_id: str,
    subject: Optional[str] = None
) -> List[models.StudentProgress]:
    """Get student progress records"""
    query = db.query(models.StudentProgress)\
        .filter(models.StudentProgress.user_id == user_id)

    if subject:
        query = query.filter(models.StudentProgress.subject == subject)

    return query.all()


# ============= ANALYTICS =============

def get_question_count(db: Session, user_id: Optional[str] = None) -> int:
    """Get total question count"""
    query = db.query(models.Question)
    if user_id:
        query = query.filter(models.Question.user_id == user_id)
    return query.count()


def get_user_count(db: Session, role: Optional[str] = None) -> int:
    """Get total user count"""
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    return query.count()


def get_avg_response_time(db: Session) -> float:
    """Get average response time"""
    from sqlalchemy import func
    result = db.query(func.avg(models.Question.response_time_ms)).scalar()
    return result or 0.0
