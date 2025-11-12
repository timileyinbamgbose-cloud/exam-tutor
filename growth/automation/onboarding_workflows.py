"""
Automated Onboarding Workflows
ExamsTutor AI - Phase 5: Scale & Growth

Automate school, teacher, and student onboarding to scale efficiently.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import asyncio


class OnboardingStage(str, Enum):
    """Onboarding workflow stages"""
    NOT_STARTED = "not_started"
    ACCOUNT_SETUP = "account_setup"
    TRAINING_SCHEDULED = "training_scheduled"
    TRAINING_COMPLETED = "training_completed"
    STUDENT_ONBOARDING = "student_onboarding"
    GO_LIVE = "go_live"
    POST_LAUNCH_SUPPORT = "post_launch_support"
    COMPLETE = "complete"


class TaskStatus(str, Enum):
    """Status of individual onboarding tasks"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class OnboardingTask:
    """Individual onboarding task"""
    task_id: str
    title: str
    description: str
    assigned_to: str  # "system", "school", "examstutor_team"
    status: TaskStatus
    due_date: datetime
    completed_at: Optional[datetime] = None
    notes: str = ""


@dataclass
class SchoolOnboarding:
    """School onboarding workflow"""
    school_id: str
    school_name: str
    current_stage: OnboardingStage
    tasks: List[OnboardingTask]

    # Key dates
    contract_signed_date: datetime
    target_go_live_date: datetime
    actual_go_live_date: Optional[datetime] = None

    # Contacts
    principal_email: str
    lead_teacher_email: str
    it_contact_email: Optional[str] = None

    # Configuration
    num_students: int
    num_teachers: int
    subjects: List[str]
    classes: List[str]  # SS1, SS2, SS3

    # Progress tracking
    setup_progress: int = 0  # 0-100%
    training_progress: int = 0
    student_activation_progress: int = 0

    created_at: datetime = None
    updated_at: datetime = None


class OnboardingWorkflowEngine:
    """Automated onboarding workflow engine"""

    def __init__(self, db_connection=None, email_service=None, calendar_service=None):
        self.db = db_connection
        self.email = email_service
        self.calendar = calendar_service

    async def initiate_school_onboarding(
        self,
        school_id: str,
        school_name: str,
        contract_signed_date: datetime,
        principal_email: str,
        lead_teacher_email: str,
        num_students: int,
        num_teachers: int,
        subjects: List[str],
        classes: List[str],
    ) -> SchoolOnboarding:
        """
        Initiate automated onboarding workflow for a new school

        Returns SchoolOnboarding object with all tasks pre-populated
        """

        # Calculate timeline
        target_go_live = contract_signed_date + timedelta(days=14)  # 2 weeks

        # Generate onboarding tasks
        tasks = self._generate_onboarding_tasks(
            school_id=school_id,
            start_date=contract_signed_date,
            num_students=num_students,
            num_teachers=num_teachers,
        )

        onboarding = SchoolOnboarding(
            school_id=school_id,
            school_name=school_name,
            current_stage=OnboardingStage.ACCOUNT_SETUP,
            tasks=tasks,
            contract_signed_date=contract_signed_date,
            target_go_live_date=target_go_live,
            principal_email=principal_email,
            lead_teacher_email=lead_teacher_email,
            num_students=num_students,
            num_teachers=num_teachers,
            subjects=subjects,
            classes=classes,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Save to database
        await self._save_onboarding(onboarding)

        # Trigger automated actions
        await self._execute_stage_actions(onboarding, OnboardingStage.ACCOUNT_SETUP)

        # Send welcome email
        await self._send_welcome_email(onboarding)

        return onboarding

    def _generate_onboarding_tasks(
        self,
        school_id: str,
        start_date: datetime,
        num_students: int,
        num_teachers: int,
    ) -> List[OnboardingTask]:
        """Generate complete list of onboarding tasks"""

        tasks = []

        # Week 1: Account Setup & Training Preparation (Days 1-3)
        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_001",
            title="Create school account in system",
            description="Set up school profile, configure settings, generate access credentials",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(hours=2),  # Within 2 hours
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_002",
            title="Bulk upload teacher accounts",
            description=f"Create {num_teachers} teacher accounts with proper roles and permissions",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(hours=4),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_003",
            title="Generate student account credentials",
            description=f"Create {num_students} student accounts with login credentials",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=1),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_004",
            title="Schedule teacher training session",
            description="Coordinate with school to schedule 2-day teacher training workshop",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=2),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_005",
            title="Send training materials to teachers",
            description="Email pre-training materials, agenda, and system access credentials",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=3),
        ))

        # Week 1-2: Teacher Training (Days 4-5)
        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_006",
            title="Conduct Day 1 teacher training",
            description="System overview, student experience walkthrough, hands-on practice",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=5),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_007",
            title="Conduct Day 2 teacher training",
            description="Dashboard deep dive, classroom integration, advanced features",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=6),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_008",
            title="Teacher training assessment",
            description="Verify all teachers can use dashboard and understand key features",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=6),
        ))

        # Week 2: Student Onboarding (Days 7-10)
        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_009",
            title="Distribute student credentials",
            description="Provide printed credential sheets to school for distribution",
            assigned_to="school",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=7),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_010",
            title="Class-by-class student orientation",
            description="30-min onboarding session for each class (SS1, SS2, SS3)",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=9),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_011",
            title="Students complete first diagnostic test",
            description="All students take diagnostic test in their primary subject",
            assigned_to="school",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=10),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_012",
            title="Students ask first question",
            description="Every student successfully asks at least one question to AI tutor",
            assigned_to="school",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=10),
        ))

        # Week 2: Go-Live (Days 11-14)
        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_013",
            title="Go-live readiness check",
            description="Verify all systems functional, teachers trained, students activated",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=12),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_014",
            title="Official go-live",
            description="School transitions from onboarding to production usage",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=14),
        ))

        # Ongoing: Post-Launch Support (Weeks 3-4)
        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_015",
            title="Week 1 post-launch check-in",
            description="Call with principal and lead teacher to address early issues",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=21),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_016",
            title="Week 2 post-launch check-in",
            description="Review usage analytics, identify drop-off students",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=28),
        ))

        tasks.append(OnboardingTask(
            task_id=f"{school_id}_task_017",
            title="Month 1 progress report",
            description="Generate and share detailed progress report with school",
            assigned_to="examstutor_team",
            status=TaskStatus.PENDING,
            due_date=start_date + timedelta(days=35),
        ))

        return tasks

    async def _execute_stage_actions(
        self,
        onboarding: SchoolOnboarding,
        stage: OnboardingStage,
    ) -> None:
        """Execute automated actions for a stage"""

        if stage == OnboardingStage.ACCOUNT_SETUP:
            # Automatically create school account
            await self._create_school_account(onboarding)

            # Generate teacher accounts
            await self._generate_teacher_accounts(onboarding)

            # Generate student credentials
            await self._generate_student_credentials(onboarding)

            # Create WhatsApp support group
            await self._create_support_channel(onboarding)

        elif stage == OnboardingStage.TRAINING_SCHEDULED:
            # Send calendar invites
            await self._send_calendar_invites(onboarding)

            # Send pre-training materials
            await self._send_training_materials(onboarding)

        elif stage == OnboardingStage.GO_LIVE:
            # Enable production access
            await self._enable_production_access(onboarding)

            # Send congratulations email
            await self._send_go_live_email(onboarding)

            # Schedule post-launch check-ins
            await self._schedule_check_ins(onboarding)

    async def update_task_status(
        self,
        school_id: str,
        task_id: str,
        status: TaskStatus,
        notes: str = "",
    ) -> None:
        """Update task status and trigger next actions"""

        onboarding = await self._load_onboarding(school_id)
        if not onboarding:
            return

        # Find and update task
        for task in onboarding.tasks:
            if task.task_id == task_id:
                task.status = status
                if status == TaskStatus.COMPLETED:
                    task.completed_at = datetime.now()
                if notes:
                    task.notes = notes
                break

        # Update progress percentages
        self._update_progress_metrics(onboarding)

        # Check if stage is complete
        if self._is_stage_complete(onboarding, onboarding.current_stage):
            # Move to next stage
            next_stage = self._get_next_stage(onboarding.current_stage)
            if next_stage:
                onboarding.current_stage = next_stage
                await self._execute_stage_actions(onboarding, next_stage)

        # Save updated onboarding
        await self._save_onboarding(onboarding)

        # Send notifications if needed
        await self._check_and_send_notifications(onboarding)

    async def get_onboarding_status(self, school_id: str) -> Dict[str, Any]:
        """Get current onboarding status for a school"""

        onboarding = await self._load_onboarding(school_id)
        if not onboarding:
            return {}

        return {
            "school_id": school_id,
            "school_name": onboarding.school_name,
            "current_stage": onboarding.current_stage.value,
            "overall_progress": self._calculate_overall_progress(onboarding),

            "progress": {
                "setup": onboarding.setup_progress,
                "training": onboarding.training_progress,
                "student_activation": onboarding.student_activation_progress,
            },

            "timeline": {
                "contract_signed": onboarding.contract_signed_date.isoformat(),
                "target_go_live": onboarding.target_go_live_date.isoformat(),
                "actual_go_live": onboarding.actual_go_live_date.isoformat() if onboarding.actual_go_live_date else None,
                "days_since_contract": (datetime.now() - onboarding.contract_signed_date).days,
                "days_to_go_live": (onboarding.target_go_live_date - datetime.now()).days,
            },

            "tasks": {
                "total": len(onboarding.tasks),
                "completed": len([t for t in onboarding.tasks if t.status == TaskStatus.COMPLETED]),
                "pending": len([t for t in onboarding.tasks if t.status == TaskStatus.PENDING]),
                "in_progress": len([t for t in onboarding.tasks if t.status == TaskStatus.IN_PROGRESS]),
                "overdue": len([t for t in onboarding.tasks if t.status == TaskStatus.PENDING and t.due_date < datetime.now()]),
            },

            "next_actions": self._get_next_actions(onboarding),
        }

    def _update_progress_metrics(self, onboarding: SchoolOnboarding) -> None:
        """Update progress percentages"""

        # Setup progress (tasks 1-3)
        setup_tasks = [t for t in onboarding.tasks if t.task_id.endswith(('001', '002', '003'))]
        onboarding.setup_progress = self._calculate_progress(setup_tasks)

        # Training progress (tasks 6-8)
        training_tasks = [t for t in onboarding.tasks if t.task_id.endswith(('006', '007', '008'))]
        onboarding.training_progress = self._calculate_progress(training_tasks)

        # Student activation progress (tasks 9-12)
        activation_tasks = [t for t in onboarding.tasks if t.task_id.endswith(('009', '010', '011', '012'))]
        onboarding.student_activation_progress = self._calculate_progress(activation_tasks)

    def _calculate_progress(self, tasks: List[OnboardingTask]) -> int:
        """Calculate progress percentage for a set of tasks"""
        if not tasks:
            return 0
        completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        return int((completed / len(tasks)) * 100)

    def _calculate_overall_progress(self, onboarding: SchoolOnboarding) -> int:
        """Calculate overall onboarding progress"""
        total_tasks = len(onboarding.tasks)
        if total_tasks == 0:
            return 0
        completed = len([t for t in onboarding.tasks if t.status == TaskStatus.COMPLETED])
        return int((completed / total_tasks) * 100)

    def _is_stage_complete(self, onboarding: SchoolOnboarding, stage: OnboardingStage) -> bool:
        """Check if all tasks for a stage are complete"""
        stage_tasks = self._get_stage_tasks(onboarding, stage)
        return all(t.status == TaskStatus.COMPLETED for t in stage_tasks)

    def _get_stage_tasks(self, onboarding: SchoolOnboarding, stage: OnboardingStage) -> List[OnboardingTask]:
        """Get all tasks for a specific stage"""
        # Map stages to task IDs
        stage_map = {
            OnboardingStage.ACCOUNT_SETUP: ['001', '002', '003'],
            OnboardingStage.TRAINING_SCHEDULED: ['004', '005'],
            OnboardingStage.TRAINING_COMPLETED: ['006', '007', '008'],
            OnboardingStage.STUDENT_ONBOARDING: ['009', '010', '011', '012'],
            OnboardingStage.GO_LIVE: ['013', '014'],
            OnboardingStage.POST_LAUNCH_SUPPORT: ['015', '016', '017'],
        }

        task_suffixes = stage_map.get(stage, [])
        return [t for t in onboarding.tasks if any(t.task_id.endswith(suffix) for suffix in task_suffixes)]

    def _get_next_stage(self, current_stage: OnboardingStage) -> Optional[OnboardingStage]:
        """Get next stage in workflow"""
        stages = list(OnboardingStage)
        try:
            current_index = stages.index(current_stage)
            if current_index < len(stages) - 1:
                return stages[current_index + 1]
        except ValueError:
            pass
        return None

    def _get_next_actions(self, onboarding: SchoolOnboarding) -> List[Dict[str, str]]:
        """Get next actions that need to be taken"""
        next_actions = []

        # Get pending tasks ordered by due date
        pending_tasks = [t for t in onboarding.tasks if t.status == TaskStatus.PENDING]
        pending_tasks.sort(key=lambda t: t.due_date)

        for task in pending_tasks[:5]:  # Next 5 tasks
            next_actions.append({
                "task_id": task.task_id,
                "title": task.title,
                "assigned_to": task.assigned_to,
                "due_date": task.due_date.isoformat(),
                "overdue": task.due_date < datetime.now(),
            })

        return next_actions

    # Email and communication methods (placeholders)

    async def _send_welcome_email(self, onboarding: SchoolOnboarding) -> None:
        """Send welcome email to school"""
        # Would integrate with email service
        pass

    async def _send_calendar_invites(self, onboarding: SchoolOnboarding) -> None:
        """Send calendar invites for training"""
        pass

    async def _send_training_materials(self, onboarding: SchoolOnboarding) -> None:
        """Send pre-training materials"""
        pass

    async def _send_go_live_email(self, onboarding: SchoolOnboarding) -> None:
        """Send go-live congratulations email"""
        pass

    async def _check_and_send_notifications(self, onboarding: SchoolOnboarding) -> None:
        """Check for overdue tasks and send notifications"""
        pass

    # System integration methods (placeholders)

    async def _create_school_account(self, onboarding: SchoolOnboarding) -> None:
        """Create school account in system"""
        pass

    async def _generate_teacher_accounts(self, onboarding: SchoolOnboarding) -> None:
        """Generate teacher accounts"""
        pass

    async def _generate_student_credentials(self, onboarding: SchoolOnboarding) -> None:
        """Generate student login credentials"""
        pass

    async def _create_support_channel(self, onboarding: SchoolOnboarding) -> None:
        """Create WhatsApp support group"""
        pass

    async def _enable_production_access(self, onboarding: SchoolOnboarding) -> None:
        """Enable full production access"""
        pass

    async def _schedule_check_ins(self, onboarding: SchoolOnboarding) -> None:
        """Schedule post-launch check-in calls"""
        pass

    # Database methods (placeholders)

    async def _save_onboarding(self, onboarding: SchoolOnboarding) -> None:
        """Save onboarding to database"""
        pass

    async def _load_onboarding(self, school_id: str) -> Optional[SchoolOnboarding]:
        """Load onboarding from database"""
        # Would query database
        return None


# Example usage
if __name__ == "__main__":
    import json

    engine = OnboardingWorkflowEngine()

    # Initiate onboarding for a new school
    onboarding = asyncio.run(
        engine.initiate_school_onboarding(
            school_id="SCH001",
            school_name="Greenfield International School",
            contract_signed_date=datetime.now(),
            principal_email="principal@greenfield.ng",
            lead_teacher_email="lead.teacher@greenfield.ng",
            num_students=200,
            num_teachers=15,
            subjects=["Mathematics", "English", "Physics", "Chemistry", "Biology"],
            classes=["SS1", "SS2", "SS3"],
        )
    )

    print("Onboarding initiated for Greenfield International School")
    print(f"  Total tasks: {len(onboarding.tasks)}")
    print(f"  Target go-live: {onboarding.target_go_live_date.strftime('%Y-%m-%d')}")
    print("\nFirst 5 tasks:")
    for task in onboarding.tasks[:5]:
        print(f"  - {task.title}")
        print(f"    Assigned to: {task.assigned_to}")
        print(f"    Due: {task.due_date.strftime('%Y-%m-%d')}")
