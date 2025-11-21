"""
API Request/Response Models
Pydantic models for API validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# User Models
# ============================================================================

class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    PARENT = "parent"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    role: UserRole
    school_id: Optional[str] = None
    class_level: Optional[str] = None  # SS1, SS2, SS3


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    school_id: Optional[str] = None
    class_level: Optional[str] = None
    created_at: datetime
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ============================================================================
# AI Tutor Models
# ============================================================================

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    subject: Optional[str] = None
    topic: Optional[str] = None
    class_level: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class QuestionResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    response_time_ms: float
    retrieval_time_ms: float
    num_sources: int
    question_id: Optional[str] = None  # NEW: For feedback tracking
    feedback_url: Optional[str] = None  # NEW: Direct link to provide feedback


class PracticeRequest(BaseModel):
    subject: str
    topic: Optional[str] = None
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    num_questions: int = Field(default=10, ge=1, le=50)
    question_type: Optional[str] = None  # mcq, theory, calculation


class DiagnosticTestRequest(BaseModel):
    subjects: List[str]
    class_level: str
    duration_minutes: Optional[int] = 60


# ============================================================================
# Subscription Models
# ============================================================================

class SubscriptionPlanResponse(BaseModel):
    tier: str
    name: str
    price_monthly: float
    price_annual: float
    features: Dict[str, Any]
    limits: Dict[str, int]


class SubscribeRequest(BaseModel):
    plan_tier: str
    billing_cycle: str  # monthly, annual
    num_students: int = Field(..., ge=1)
    school_id: str


class SubscriptionResponse(BaseModel):
    subscription_id: str
    plan_tier: str
    status: str
    start_date: datetime
    end_date: datetime
    auto_renew: bool


# ============================================================================
# Payment Models
# ============================================================================

class PaymentInitRequest(BaseModel):
    amount: float
    email: EmailStr
    subscription_id: str
    callback_url: Optional[str] = None


class PaymentInitResponse(BaseModel):
    authorization_url: str
    access_code: str
    reference: str


class PaymentVerifyResponse(BaseModel):
    status: str
    amount: float
    paid_at: Optional[datetime] = None
    reference: str
    subscription_id: str


# ============================================================================
# Learning Models
# ============================================================================

class SubjectResponse(BaseModel):
    id: str
    name: str
    description: str
    topics: List[str]
    class_levels: List[str]


class TopicResponse(BaseModel):
    id: str
    name: str
    subject: str
    subtopics: List[str]
    difficulty: str
    curriculum_coverage: str


class ProgressResponse(BaseModel):
    student_id: str
    subject: str
    topics_completed: int
    total_topics: int
    questions_answered: int
    accuracy_rate: float
    study_time_hours: float
    last_activity: datetime


# ============================================================================
# Analytics Models
# ============================================================================

class AnalyticsRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    metric_types: Optional[List[str]] = None


class AnalyticsResponse(BaseModel):
    total_students: int
    active_students: int
    questions_answered: int
    avg_session_duration: float
    engagement_rate: float
    performance_metrics: Dict[str, Any]


# ============================================================================
# Feedback Models
# ============================================================================

class FeedbackCategory(str, Enum):
    CLARITY = "clarity"
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    RELEVANCE = "relevance"
    TONE = "tone"
    NEEDS_EXAMPLES = "needs_examples"


class FeedbackSubmitRequest(BaseModel):
    was_helpful: bool
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None
    categories: Optional[List[FeedbackCategory]] = []
    time_to_feedback_sec: Optional[float] = None


class FeedbackSubmitResponse(BaseModel):
    message: str
    feedback_id: str
    processed: bool = False


class FeedbackAnalyticsResponse(BaseModel):
    total_responses: int
    feedback_received: int
    feedback_rate: float
    average_rating: float
    helpfulness_rate: float
    sentiment_distribution: Dict[str, float]
    top_issues: List[Dict[str, Any]]
    by_subject: Optional[List[Dict[str, Any]]] = None


class FeedbackTrendingResponse(BaseModel):
    trending_positive: List[Dict[str, Any]]
    trending_negative: List[Dict[str, Any]]
    action_required: List[Dict[str, Any]]
