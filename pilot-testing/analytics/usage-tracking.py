"""
Usage Analytics Tracking for Pilot Testing
Phase 4: Epic 4.2 - Beta Testing with Pilot Schools
Tracks student/teacher usage, engagement, and learning outcomes
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import pandas as pd
from dataclasses import dataclass, asdict
import json

from src.core.logger import logger


class UserRole(str, Enum):
    """User roles in the system."""
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    PARENT = "parent"


class EventType(str, Enum):
    """Types of user events to track."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"

    # Student Activities
    QUESTION_ASKED = "question_asked"
    FOLLOW_UP_QUESTION = "follow_up_question"
    PRACTICE_STARTED = "practice_started"
    PRACTICE_COMPLETED = "practice_completed"
    DIAGNOSTIC_STARTED = "diagnostic_started"
    DIAGNOSTIC_COMPLETED = "diagnostic_completed"
    LEARNING_PLAN_VIEWED = "learning_plan_viewed"
    PROGRESS_VIEWED = "progress_viewed"

    # Teacher Activities
    DASHBOARD_VIEWED = "dashboard_viewed"
    STUDENT_PROGRESS_VIEWED = "student_progress_viewed"
    REPORT_GENERATED = "report_generated"
    QUIZ_GENERATED = "quiz_generated"
    FEEDBACK_PROVIDED = "feedback_provided"

    # System Events
    ERROR_OCCURRED = "error_occurred"
    OFFLINE_MODE_ACTIVATED = "offline_mode_activated"
    SYNC_COMPLETED = "sync_completed"


@dataclass
class UsageEvent:
    """Represents a single usage event."""
    event_id: str
    user_id: str
    user_role: UserRole
    event_type: EventType
    timestamp: datetime

    # Context
    school_id: Optional[str] = None
    class_id: Optional[str] = None
    subject: Optional[str] = None

    # Event-specific data
    session_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    # Technical details
    device_type: Optional[str] = None  # desktop, mobile, tablet
    os: Optional[str] = None
    browser: Optional[str] = None
    connection_type: Optional[str] = None  # online, offline

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['user_role'] = self.user_role.value
        data['event_type'] = self.event_type.value
        return data


class PilotAnalytics:
    """
    Analytics system for pilot testing.
    Tracks and analyzes user behavior, engagement, and learning outcomes.
    """

    def __init__(self, database_connection=None):
        """
        Initialize analytics tracker.

        Args:
            database_connection: Database connection for persisting events
        """
        self.db = database_connection
        self.events: List[UsageEvent] = []

    async def track_event(
        self,
        user_id: str,
        user_role: UserRole,
        event_type: EventType,
        school_id: Optional[str] = None,
        subject: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        Track a user event.

        Args:
            user_id: Unique user identifier
            user_role: User's role (student, teacher, admin)
            event_type: Type of event
            school_id: School identifier (for pilot tracking)
            subject: Subject (if applicable)
            duration_seconds: Event duration
            metadata: Additional event data
            **kwargs: Additional context fields
        """
        event = UsageEvent(
            event_id=self._generate_event_id(),
            user_id=user_id,
            user_role=user_role,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            school_id=school_id,
            subject=subject,
            duration_seconds=duration_seconds,
            metadata=metadata or {},
            **kwargs
        )

        # Store event
        self.events.append(event)

        # Persist to database
        if self.db:
            await self._persist_event(event)

        logger.info(
            f"Event tracked: {event_type.value}",
            extra={
                "user_id": user_id,
                "user_role": user_role.value,
                "school_id": school_id,
                "event_id": event.event_id
            }
        )

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid
        return f"evt_{uuid.uuid4().hex[:12]}"

    async def _persist_event(self, event: UsageEvent) -> None:
        """Persist event to database."""
        # TODO: Implement database persistence
        pass

    # ============================================
    # STUDENT ANALYTICS
    # ============================================

    def get_student_engagement(
        self,
        student_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get student engagement metrics.

        Returns:
            Dictionary with engagement metrics
        """
        student_events = self._filter_events(
            user_id=student_id,
            user_role=UserRole.STUDENT,
            start_date=start_date,
            end_date=end_date
        )

        # Calculate metrics
        total_logins = len([e for e in student_events if e.event_type == EventType.LOGIN])
        questions_asked = len([e for e in student_events if e.event_type == EventType.QUESTION_ASKED])
        practice_sessions = len([e for e in student_events if e.event_type == EventType.PRACTICE_STARTED])

        # Calculate total time spent
        session_durations = [
            e.duration_seconds for e in student_events
            if e.duration_seconds is not None
        ]
        total_time_seconds = sum(session_durations)
        avg_session_seconds = total_time_seconds / len(session_durations) if session_durations else 0

        # Active days
        active_days = len(set(e.timestamp.date() for e in student_events))

        # Questions by subject
        questions_by_subject = {}
        for event in student_events:
            if event.event_type == EventType.QUESTION_ASKED and event.subject:
                questions_by_subject[event.subject] = questions_by_subject.get(event.subject, 0) + 1

        return {
            "student_id": student_id,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "engagement": {
                "total_logins": total_logins,
                "active_days": active_days,
                "questions_asked": questions_asked,
                "practice_sessions": practice_sessions,
                "diagnostics_completed": len([e for e in student_events if e.event_type == EventType.DIAGNOSTIC_COMPLETED])
            },
            "time_spent": {
                "total_seconds": total_time_seconds,
                "total_minutes": total_time_seconds / 60,
                "total_hours": total_time_seconds / 3600,
                "avg_session_seconds": avg_session_seconds,
                "avg_session_minutes": avg_session_seconds / 60
            },
            "subject_breakdown": questions_by_subject,
            "offline_usage_percent": self._calculate_offline_percentage(student_events)
        }

    def get_class_engagement(
        self,
        class_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get class-wide engagement metrics.

        Returns:
            Dictionary with class metrics
        """
        class_events = self._filter_events(
            class_id=class_id,
            start_date=start_date,
            end_date=end_date
        )

        # Get unique students
        students = set(e.user_id for e in class_events if e.user_role == UserRole.STUDENT)

        # Calculate aggregate metrics
        total_questions = len([e for e in class_events if e.event_type == EventType.QUESTION_ASKED])
        avg_questions_per_student = total_questions / len(students) if students else 0

        # Active user percentage
        total_students = len(students)  # Should get from database
        active_percentage = (len([s for s in students if self._is_active_user(s, class_events)]) / total_students * 100) if total_students > 0 else 0

        return {
            "class_id": class_id,
            "total_students": total_students,
            "active_students": len(students),
            "active_percentage": active_percentage,
            "total_questions": total_questions,
            "avg_questions_per_student": avg_questions_per_student,
            "subject_distribution": self._get_subject_distribution(class_events),
            "daily_active_users": self._get_daily_active_users(class_events)
        }

    def get_school_engagement(
        self,
        school_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get school-wide engagement metrics.

        Returns:
            Dictionary with school metrics
        """
        school_events = self._filter_events(
            school_id=school_id,
            start_date=start_date,
            end_date=end_date
        )

        # Get unique users by role
        students = set(e.user_id for e in school_events if e.user_role == UserRole.STUDENT)
        teachers = set(e.user_id for e in school_events if e.user_role == UserRole.TEACHER)

        # Overall metrics
        total_logins = len([e for e in school_events if e.event_type == EventType.LOGIN])
        total_questions = len([e for e in school_events if e.event_type == EventType.QUESTION_ASKED])

        return {
            "school_id": school_id,
            "users": {
                "total_students": len(students),
                "total_teachers": len(teachers),
                "active_students": len([s for s in students if self._is_active_user(s, school_events)]),
                "active_teachers": len([t for t in teachers if self._is_active_user(t, school_events)])
            },
            "activity": {
                "total_logins": total_logins,
                "total_questions": total_questions,
                "avg_questions_per_student": total_questions / len(students) if students else 0
            },
            "technical": {
                "offline_usage_events": len([e for e in school_events if e.connection_type == "offline"]),
                "sync_events": len([e for e in school_events if e.event_type == EventType.SYNC_COMPLETED]),
                "error_rate": len([e for e in school_events if e.event_type == EventType.ERROR_OCCURRED]) / len(school_events) if school_events else 0
            }
        }

    # ============================================
    # TEACHER ANALYTICS
    # ============================================

    def get_teacher_usage(
        self,
        teacher_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get teacher usage metrics.

        Returns:
            Dictionary with teacher metrics
        """
        teacher_events = self._filter_events(
            user_id=teacher_id,
            user_role=UserRole.TEACHER,
            start_date=start_date,
            end_date=end_date
        )

        dashboard_views = len([e for e in teacher_events if e.event_type == EventType.DASHBOARD_VIEWED])
        student_progress_views = len([e for e in teacher_events if e.event_type == EventType.STUDENT_PROGRESS_VIEWED])
        reports_generated = len([e for e in teacher_events if e.event_type == EventType.REPORT_GENERATED])

        return {
            "teacher_id": teacher_id,
            "engagement": {
                "dashboard_views": dashboard_views,
                "student_progress_views": student_progress_views,
                "reports_generated": reports_generated,
                "quizzes_generated": len([e for e in teacher_events if e.event_type == EventType.QUIZ_GENERATED]),
                "feedback_provided": len([e for e in teacher_events if e.event_type == EventType.FEEDBACK_PROVIDED])
            },
            "avg_weekly_usage": len(teacher_events) / 4  # Assuming 4-week pilot
        }

    # ============================================
    # LEARNING OUTCOMES
    # ============================================

    def get_learning_outcomes(
        self,
        student_id: str,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get student learning outcome metrics.

        Returns:
            Dictionary with learning metrics
        """
        # TODO: Integrate with actual assessment data
        return {
            "student_id": student_id,
            "subject": subject,
            "baseline_score": None,  # From initial diagnostic
            "current_score": None,  # From latest assessment
            "improvement_percent": None,
            "topics_mastered": [],
            "topics_in_progress": [],
            "topics_struggling": []
        }

    # ============================================
    # PILOT-SPECIFIC METRICS
    # ============================================

    def get_pilot_success_metrics(
        self,
        school_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Calculate pilot success metrics against targets.

        Targets:
        - >70% weekly active users
        - Average 30+ minutes per session
        - Average 20+ questions per student
        - >15% improvement in post-test

        Returns:
            Dictionary with success metrics and target comparison
        """
        school_events = self._filter_events(
            school_id=school_id,
            start_date=start_date,
            end_date=end_date
        )

        students = set(e.user_id for e in school_events if e.user_role == UserRole.STUDENT)
        total_enrolled = len(students)  # Should get from database

        # Weekly active users
        weekly_active = self._get_weekly_active_users(school_events, start_date, end_date)
        avg_weekly_active_percent = sum(weekly_active.values()) / len(weekly_active) if weekly_active else 0

        # Session duration
        session_durations = [
            e.duration_seconds / 60  # Convert to minutes
            for e in school_events
            if e.duration_seconds is not None and e.user_role == UserRole.STUDENT
        ]
        avg_session_minutes = sum(session_durations) / len(session_durations) if session_durations else 0

        # Questions per student
        questions_by_student = {}
        for event in school_events:
            if event.event_type == EventType.QUESTION_ASKED:
                questions_by_student[event.user_id] = questions_by_student.get(event.user_id, 0) + 1
        avg_questions_per_student = sum(questions_by_student.values()) / len(questions_by_student) if questions_by_student else 0

        return {
            "school_id": school_id,
            "pilot_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "duration_weeks": (end_date - start_date).days / 7
            },
            "targets_vs_actual": {
                "weekly_active_users": {
                    "target": 70,  # percent
                    "actual": avg_weekly_active_percent,
                    "met": avg_weekly_active_percent >= 70
                },
                "avg_session_duration": {
                    "target": 30,  # minutes
                    "actual": avg_session_minutes,
                    "met": avg_session_minutes >= 30
                },
                "avg_questions_per_student": {
                    "target": 20,
                    "actual": avg_questions_per_student,
                    "met": avg_questions_per_student >= 20
                },
                "score_improvement": {
                    "target": 15,  # percent
                    "actual": None,  # TODO: Get from assessment data
                    "met": None
                }
            },
            "overall_success": self._calculate_overall_success_score(
                avg_weekly_active_percent,
                avg_session_minutes,
                avg_questions_per_student
            )
        }

    # ============================================
    # UTILITY METHODS
    # ============================================

    def _filter_events(
        self,
        user_id: Optional[str] = None,
        user_role: Optional[UserRole] = None,
        event_type: Optional[EventType] = None,
        school_id: Optional[str] = None,
        class_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[UsageEvent]:
        """Filter events by various criteria."""
        filtered = self.events

        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]
        if user_role:
            filtered = [e for e in filtered if e.user_role == user_role]
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        if school_id:
            filtered = [e for e in filtered if e.school_id == school_id]
        if class_id:
            filtered = [e for e in filtered if e.class_id == class_id]
        if start_date:
            filtered = [e for e in filtered if e.timestamp >= start_date]
        if end_date:
            filtered = [e for e in filtered if e.timestamp <= end_date]

        return filtered

    def _is_active_user(self, user_id: str, events: List[UsageEvent]) -> bool:
        """Determine if user is active (logged in at least once per week)."""
        user_events = [e for e in events if e.user_id == user_id and e.event_type == EventType.LOGIN]
        if not user_events:
            return False

        # Check if logged in within last 7 days
        latest_login = max(e.timestamp for e in user_events)
        return (datetime.utcnow() - latest_login).days <= 7

    def _calculate_offline_percentage(self, events: List[UsageEvent]) -> float:
        """Calculate percentage of events that occurred offline."""
        if not events:
            return 0.0
        offline_events = len([e for e in events if e.connection_type == "offline"])
        return (offline_events / len(events)) * 100

    def _get_subject_distribution(self, events: List[UsageEvent]) -> Dict[str, int]:
        """Get distribution of events by subject."""
        distribution = {}
        for event in events:
            if event.subject:
                distribution[event.subject] = distribution.get(event.subject, 0) + 1
        return distribution

    def _get_daily_active_users(self, events: List[UsageEvent]) -> Dict[str, int]:
        """Get daily active user counts."""
        daily_users = {}
        for event in events:
            date_str = event.timestamp.date().isoformat()
            if date_str not in daily_users:
                daily_users[date_str] = set()
            daily_users[date_str].add(event.user_id)

        return {date: len(users) for date, users in daily_users.items()}

    def _get_weekly_active_users(
        self,
        events: List[UsageEvent],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[int, float]:
        """Get weekly active user percentages."""
        total_users = len(set(e.user_id for e in events if e.user_role == UserRole.STUDENT))
        if total_users == 0:
            return {}

        weeks = {}
        current_date = start_date
        week_num = 1

        while current_date < end_date:
            week_end = min(current_date + timedelta(days=7), end_date)
            week_events = [e for e in events if current_date <= e.timestamp < week_end]
            week_users = len(set(e.user_id for e in week_events if e.user_role == UserRole.STUDENT))
            weeks[week_num] = (week_users / total_users) * 100

            current_date = week_end
            week_num += 1

        return weeks

    def _calculate_overall_success_score(
        self,
        weekly_active: float,
        session_duration: float,
        questions_per_student: float
    ) -> Dict[str, Any]:
        """Calculate overall pilot success score."""
        # Weight each metric
        weights = {
            "weekly_active": 0.4,
            "session_duration": 0.3,
            "questions": 0.3
        }

        # Calculate scores (0-100)
        scores = {
            "weekly_active": min(100, (weekly_active / 70) * 100),
            "session_duration": min(100, (session_duration / 30) * 100),
            "questions": min(100, (questions_per_student / 20) * 100)
        }

        # Weighted average
        overall_score = sum(scores[k] * weights[k] for k in scores)

        return {
            "score": overall_score,
            "rating": self._get_success_rating(overall_score),
            "component_scores": scores
        }

    def _get_success_rating(self, score: float) -> str:
        """Get qualitative rating based on score."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Satisfactory"
        elif score >= 50:
            return "Needs Improvement"
        else:
            return "Poor"

    # ============================================
    # REPORTING
    # ============================================

    def generate_pilot_report(
        self,
        school_id: str,
        start_date: datetime,
        end_date: datetime,
        output_format: str = "json"
    ) -> Any:
        """
        Generate comprehensive pilot report.

        Args:
            school_id: School identifier
            start_date: Pilot start date
            end_date: Pilot end date
            output_format: "json", "pdf", or "excel"

        Returns:
            Report in specified format
        """
        report = {
            "school_id": school_id,
            "pilot_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "engagement": self.get_school_engagement(school_id, start_date, end_date),
            "success_metrics": self.get_pilot_success_metrics(school_id, start_date, end_date),
            "generated_at": datetime.utcnow().isoformat()
        }

        if output_format == "json":
            return json.dumps(report, indent=2)
        elif output_format == "pdf":
            # TODO: Implement PDF generation
            pass
        elif output_format == "excel":
            # TODO: Implement Excel generation
            pass

        return report


# Global analytics instance
pilot_analytics = PilotAnalytics()


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def main():
        analytics = PilotAnalytics()

        # Track some example events
        await analytics.track_event(
            user_id="student_001",
            user_role=UserRole.STUDENT,
            event_type=EventType.QUESTION_ASKED,
            school_id="school_001",
            subject="Mathematics",
            duration_seconds=120,
            metadata={"question": "What is quadratic equation?"}
        )

        # Get engagement metrics
        engagement = analytics.get_student_engagement("student_001")
        print(json.dumps(engagement, indent=2))

    asyncio.run(main())
