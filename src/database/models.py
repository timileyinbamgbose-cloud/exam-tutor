"""
Database Models
Defines all SQLAlchemy models for the application
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.config import Base
import enum
import uuid


class UserRole(str, enum.Enum):
    """User role enumeration"""
    student = "student"
    teacher = "teacher"
    admin = "admin"


class QuestionDifficulty(str, enum.Enum):
    """Question difficulty levels"""
    easy = "easy"
    medium = "medium"
    hard = "hard"


class User(Base):
    """User model - stores all user information"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.student)
    school_id = Column(String, nullable=True)
    class_level = Column(String, nullable=True)  # SS1, SS2, SS3

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    questions = relationship("Question", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")


class Question(Base):
    """Question model - stores all questions asked by users"""
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Question details
    question_text = Column(Text, nullable=False)
    subject = Column(String, nullable=True)  # Mathematics, Physics, etc.
    topic = Column(String, nullable=True)
    class_level = Column(String, nullable=True)
    difficulty = Column(SQLEnum(QuestionDifficulty), nullable=True)

    # Answer details
    answer_text = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)  # List of source documents used
    confidence_score = Column(Float, nullable=True)

    # Metrics
    response_time_ms = Column(Float, nullable=True)
    retrieval_time_ms = Column(Float, nullable=True)
    num_sources = Column(Integer, default=0)

    # Feedback
    was_helpful = Column(Boolean, nullable=True)
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    feedback_text = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="questions")


class UserSession(Base):
    """User session model - tracks user login sessions"""
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Session details
    access_token = Column(String, nullable=False, unique=True, index=True)
    refresh_token = Column(String, nullable=True, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Device/location info
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    device_type = Column(String, nullable=True)  # web, mobile, tablet

    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")


class Subscription(Base):
    """Subscription model - manages user subscriptions"""
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Subscription details
    tier = Column(String, nullable=False)  # free, premium, premium_plus, enterprise
    status = Column(String, default="active")  # active, cancelled, expired, suspended

    # Billing
    price_monthly = Column(Float, default=0.0)
    billing_cycle = Column(String, default="monthly")  # monthly, annual

    # Dates
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    next_billing_date = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    questions_used = Column(Integer, default=0)
    questions_limit = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="subscriptions")


class Payment(Base):
    """Payment model - tracks all payment transactions"""
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(String, ForeignKey("subscriptions.id"), nullable=True)

    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String, default="NGN")
    status = Column(String, nullable=False)  # pending, success, failed, refunded

    # Paystack details
    reference = Column(String, unique=True, nullable=False, index=True)
    authorization_url = Column(String, nullable=True)
    access_code = Column(String, nullable=True)

    # Payment info
    payment_method = Column(String, nullable=True)  # card, bank, ussd, mobile_money
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Payment metadata (renamed to avoid SQLAlchemy conflict)
    payment_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PracticeQuestion(Base):
    """Practice question model - stores generated practice questions"""
    __tablename__ = "practice_questions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Question details
    question_text = Column(Text, nullable=False)
    question_type = Column(String, nullable=False)  # mcq, short_answer, essay
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=True)
    difficulty = Column(SQLEnum(QuestionDifficulty), nullable=False)
    class_level = Column(String, nullable=True)

    # For MCQ
    options = Column(JSON, nullable=True)  # List of options
    correct_answer = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)

    # Metadata
    times_used = Column(Integer, default=0)
    avg_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ResponseFeedback(Base):
    """Response Feedback model - Enhanced feedback tracking separate from Question"""
    __tablename__ = "response_feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, nullable=True)  # Link to conversation session

    # Feedback data
    was_helpful = Column(Boolean, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    feedback_text = Column(Text, nullable=True)

    # Context (what generated the response)
    model_used = Column(String, nullable=True)  # Which model generated response
    rag_enabled = Column(Boolean, default=False)  # Was RAG used?
    response_time_ms = Column(Float, nullable=True)

    # Categorization
    feedback_category = Column(String, nullable=True)  # "clarity", "accuracy", "completeness", etc.
    sentiment_score = Column(Float, nullable=True)  # -1 to 1 (analyzed from feedback_text)

    # Implicit signals
    time_to_feedback_sec = Column(Float, nullable=True)  # How long after response was feedback given
    had_followup = Column(Boolean, default=False)  # Did user ask follow-up question

    # Processing status
    processed = Column(Boolean, default=False)  # Has this feedback been analyzed/acted upon
    action_taken = Column(String, nullable=True)  # "cache_invalidated", "alerted", etc.

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    question = relationship("Question", backref="feedback_entries")


class StudentProgress(Base):
    """Student progress model - tracks learning progress"""
    __tablename__ = "student_progress"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Progress details
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=True)

    # Metrics
    questions_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)

    # Time tracking
    total_study_time_minutes = Column(Integer, default=0)
    last_studied = Column(DateTime(timezone=True), nullable=True)

    # Status
    mastery_level = Column(Float, default=0.0)  # 0.0 to 1.0
    is_completed = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Document(Base):
    """Document model - stores curriculum content and documents for RAG"""
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Document content
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String, nullable=True)  # topic, subtopic, example, explanation

    # Curriculum metadata
    subject = Column(String, nullable=True, index=True)
    class_level = Column(String, nullable=True, index=True)  # SS1, SS2, SS3
    topic = Column(String, nullable=True, index=True)
    subtopic = Column(String, nullable=True)

    # Source tracking
    source = Column(String, nullable=True)  # curriculum, textbook, practice, etc.
    source_url = Column(String, nullable=True)

    # Vector search metadata
    is_indexed = Column(Boolean, default=False)  # Whether embedded in vector store
    vector_id = Column(Integer, nullable=True)  # ID in FAISS index
    embedding_model = Column(String, nullable=True)  # Model used for embedding

    # Usage stats
    retrieval_count = Column(Integer, default=0)  # How many times retrieved
    last_retrieved = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
