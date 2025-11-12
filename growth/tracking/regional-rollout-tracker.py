"""
Regional Rollout Tracker
ExamsTutor AI - Phase 5: Scale & Growth

Track progress of regional expansion across 5 Nigerian regions.
Monitors school onboarding, student enrollment, and key metrics.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json


class Region(str, Enum):
    """Nigerian regions for expansion"""
    LAGOS_OGUN = "lagos_ogun"
    ABUJA_FCT = "abuja_fct"
    RIVERS_DELTA = "rivers_delta"
    KANO_KADUNA = "kano_kaduna"
    OYO_OSUN = "oyo_osun"


class RolloutStatus(str, Enum):
    """Status of regional rollout"""
    NOT_STARTED = "not_started"
    PLANNING = "planning"
    RECRUITMENT = "recruitment"
    ONBOARDING = "onboarding"
    TRAINING = "training"
    LIVE = "live"
    STABILIZING = "stabilizing"
    COMPLETE = "complete"


class SchoolStatus(str, Enum):
    """Status of individual school onboarding"""
    LEAD = "lead"
    QUALIFIED = "qualified"
    PITCHED = "pitched"
    PROPOSAL_SENT = "proposal_sent"
    MOU_SIGNED = "mou_signed"
    TRAINING_SCHEDULED = "training_scheduled"
    TRAINING_COMPLETE = "training_complete"
    LIVE = "live"
    CHURNED = "churned"


@dataclass
class RegionalTarget:
    """Regional rollout targets"""
    region: Region
    target_schools: int
    target_students: int
    target_teachers: int
    start_week: int  # Week number (21-26)
    duration_weeks: int
    budget_ngn: int

    # Calculated fields
    @property
    def end_week(self) -> int:
        return self.start_week + self.duration_weeks - 1

    @property
    def is_active(self) -> bool:
        current_week = self._get_current_week()
        return self.start_week <= current_week <= self.end_week

    @property
    def is_complete(self) -> bool:
        return self._get_current_week() > self.end_week

    def _get_current_week(self) -> int:
        # Calculate current week number (simplified)
        # In production, this would be based on actual project start date
        phase_5_start = datetime(2025, 5, 1)  # Example start date
        days_elapsed = (datetime.now() - phase_5_start).days
        return 21 + (days_elapsed // 7)


# Regional targets for Phase 5
REGIONAL_TARGETS = {
    Region.LAGOS_OGUN: RegionalTarget(
        region=Region.LAGOS_OGUN,
        target_schools=15,
        target_students=3000,
        target_teachers=120,
        start_week=21,
        duration_weeks=2,
        budget_ngn=9_375_000,  # 15 schools × ₦625k
    ),
    Region.ABUJA_FCT: RegionalTarget(
        region=Region.ABUJA_FCT,
        target_schools=10,
        target_students=2000,
        target_teachers=80,
        start_week=23,
        duration_weeks=2,
        budget_ngn=6_250_000,  # 10 schools × ₦625k
    ),
    Region.RIVERS_DELTA: RegionalTarget(
        region=Region.RIVERS_DELTA,
        target_schools=8,
        target_students=1600,
        target_teachers=64,
        start_week=25,
        duration_weeks=1,
        budget_ngn=5_000_000,  # 8 schools × ₦625k
    ),
    Region.KANO_KADUNA: RegionalTarget(
        region=Region.KANO_KADUNA,
        target_schools=10,
        target_students=2000,
        target_teachers=80,
        start_week=26,
        duration_weeks=1,
        budget_ngn=6_250_000,  # 10 schools × ₦625k
    ),
    Region.OYO_OSUN: RegionalTarget(
        region=Region.OYO_OSUN,
        target_schools=7,
        target_students=1400,
        target_teachers=56,
        start_week=26,
        duration_weeks=1,
        budget_ngn=4_375_000,  # 7 schools × ₦625k
    ),
}


@dataclass
class School:
    """School record for tracking"""
    school_id: str
    name: str
    region: Region
    location: str  # City/LGA
    school_type: str  # public, private, mission

    # Contact information
    principal_name: str
    principal_email: str
    principal_phone: str

    # Enrollment
    num_students: int
    num_teachers: int
    classes: List[str]  # e.g., ["SS1", "SS2", "SS3"]
    subjects: List[str]

    # Status tracking
    status: SchoolStatus
    lead_source: str
    assigned_to: str  # Sales rep name

    # Key dates
    first_contact_date: Optional[datetime] = None
    pitch_date: Optional[datetime] = None
    mou_signed_date: Optional[datetime] = None
    training_date: Optional[datetime] = None
    go_live_date: Optional[datetime] = None

    # Financial
    subscription_tier: Optional[str] = None
    mrr: float = 0.0  # Monthly Recurring Revenue

    # Notes
    notes: str = ""

    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class RegionalProgress:
    """Track progress for a region"""
    region: Region
    status: RolloutStatus

    # Schools
    schools_targeted: int
    schools_qualified: int
    schools_pitched: int
    schools_signed: int
    schools_live: int

    # Students & Teachers
    students_targeted: int
    students_enrolled: int
    students_active: int
    teachers_targeted: int
    teachers_trained: int

    # Engagement
    weekly_active_rate: float = 0.0  # %
    avg_session_duration_min: float = 0.0
    questions_per_student: float = 0.0

    # Financial
    mrr: float = 0.0  # Monthly Recurring Revenue
    budget_spent: float = 0.0

    # Dates
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

    updated_at: datetime = None

    def completion_percentage(self) -> float:
        """Calculate overall completion percentage"""
        if self.schools_targeted == 0:
            return 0.0
        return (self.schools_live / self.schools_targeted) * 100

    def is_on_track(self) -> bool:
        """Check if region is on track to meet targets"""
        if not self.target_completion_date:
            return True

        days_total = (self.target_completion_date - self.start_date).days
        days_elapsed = (datetime.now() - self.start_date).days

        if days_total == 0:
            return True

        expected_progress = (days_elapsed / days_total) * 100
        actual_progress = self.completion_percentage()

        # On track if within 15% of expected progress
        return actual_progress >= (expected_progress - 15)


class RegionalRolloutTracker:
    """Track and manage regional rollout progress"""

    def __init__(self, db_connection=None):
        self.db = db_connection
        self.regions: Dict[Region, RegionalProgress] = {}
        self.schools: List[School] = []

        # Initialize regional progress tracking
        for region, target in REGIONAL_TARGETS.items():
            self.regions[region] = RegionalProgress(
                region=region,
                status=RolloutStatus.NOT_STARTED,
                schools_targeted=target.target_schools,
                schools_qualified=0,
                schools_pitched=0,
                schools_signed=0,
                schools_live=0,
                students_targeted=target.target_students,
                students_enrolled=0,
                students_active=0,
                teachers_targeted=target.target_teachers,
                teachers_trained=0,
                updated_at=datetime.now(),
            )

    def add_school(self, school: School) -> None:
        """Add a school to tracking"""
        self.schools.append(school)
        self._update_regional_stats(school.region)

    def update_school_status(
        self,
        school_id: str,
        new_status: SchoolStatus,
        notes: str = "",
    ) -> None:
        """Update school status"""
        school = self._get_school(school_id)
        if not school:
            return

        old_status = school.status
        school.status = new_status
        school.updated_at = datetime.now()

        if notes:
            school.notes = f"{school.notes}\n[{datetime.now()}] {notes}"

        # Update key dates based on status
        if new_status == SchoolStatus.PITCHED and not school.pitch_date:
            school.pitch_date = datetime.now()
        elif new_status == SchoolStatus.MOU_SIGNED and not school.mou_signed_date:
            school.mou_signed_date = datetime.now()
        elif new_status == SchoolStatus.TRAINING_COMPLETE and not school.training_date:
            school.training_date = datetime.now()
        elif new_status == SchoolStatus.LIVE and not school.go_live_date:
            school.go_live_date = datetime.now()

        # Update regional stats
        self._update_regional_stats(school.region)

    def update_engagement_metrics(
        self,
        region: Region,
        weekly_active_rate: float,
        avg_session_duration: float,
        questions_per_student: float,
    ) -> None:
        """Update engagement metrics for a region"""
        if region in self.regions:
            progress = self.regions[region]
            progress.weekly_active_rate = weekly_active_rate
            progress.avg_session_duration_min = avg_session_duration
            progress.questions_per_student = questions_per_student
            progress.updated_at = datetime.now()

    def get_regional_dashboard(self, region: Region) -> Dict[str, Any]:
        """Get comprehensive dashboard for a region"""
        if region not in self.regions:
            return {}

        progress = self.regions[region]
        target = REGIONAL_TARGETS[region]
        regional_schools = [s for s in self.schools if s.region == region]

        return {
            "region": region.value,
            "status": progress.status.value,
            "on_track": progress.is_on_track(),
            "completion_percentage": progress.completion_percentage(),

            "timeline": {
                "start_week": target.start_week,
                "end_week": target.end_week,
                "start_date": progress.start_date,
                "target_completion": progress.target_completion_date,
                "actual_completion": progress.actual_completion_date,
            },

            "schools": {
                "targeted": progress.schools_targeted,
                "qualified": progress.schools_qualified,
                "pitched": progress.schools_pitched,
                "signed": progress.schools_signed,
                "live": progress.schools_live,
                "conversion_rate": (
                    (progress.schools_signed / progress.schools_qualified * 100)
                    if progress.schools_qualified > 0 else 0
                ),
            },

            "students": {
                "targeted": progress.students_targeted,
                "enrolled": progress.students_enrolled,
                "active": progress.students_active,
                "enrollment_rate": (
                    (progress.students_enrolled / progress.students_targeted * 100)
                    if progress.students_targeted > 0 else 0
                ),
                "activation_rate": (
                    (progress.students_active / progress.students_enrolled * 100)
                    if progress.students_enrolled > 0 else 0
                ),
            },

            "teachers": {
                "targeted": progress.teachers_targeted,
                "trained": progress.teachers_trained,
                "training_completion": (
                    (progress.teachers_trained / progress.teachers_targeted * 100)
                    if progress.teachers_targeted > 0 else 0
                ),
            },

            "engagement": {
                "weekly_active_rate": progress.weekly_active_rate,
                "avg_session_duration_min": progress.avg_session_duration_min,
                "questions_per_student": progress.questions_per_student,
                "target_weekly_active": 70.0,  # Target from Phase 4
                "target_session_duration": 35.0,
                "target_questions": 25.0,
            },

            "financial": {
                "mrr": progress.mrr,
                "budget_allocated": target.budget_ngn,
                "budget_spent": progress.budget_spent,
                "budget_remaining": target.budget_ngn - progress.budget_spent,
                "burn_rate": (
                    (progress.budget_spent / target.budget_ngn * 100)
                    if target.budget_ngn > 0 else 0
                ),
            },

            "schools_detail": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "students": s.num_students,
                    "mrr": s.mrr,
                }
                for s in regional_schools
            ],
        }

    def get_phase_5_overview(self) -> Dict[str, Any]:
        """Get overall Phase 5 progress overview"""
        total_schools_targeted = sum(t.target_schools for t in REGIONAL_TARGETS.values())
        total_students_targeted = sum(t.target_students for t in REGIONAL_TARGETS.values())

        total_schools_signed = sum(p.schools_signed for p in self.regions.values())
        total_schools_live = sum(p.schools_live for p in self.regions.values())
        total_students_enrolled = sum(p.students_enrolled for p in self.regions.values())
        total_students_active = sum(p.students_active for p in self.regions.values())
        total_mrr = sum(p.mrr for p in self.regions.values())

        return {
            "phase": "Phase 5: Scale & Growth",
            "week_range": "21-30",
            "overall_progress": (total_schools_live / total_schools_targeted * 100) if total_schools_targeted > 0 else 0,

            "summary": {
                "schools": {
                    "targeted": total_schools_targeted,
                    "signed": total_schools_signed,
                    "live": total_schools_live,
                },
                "students": {
                    "targeted": total_students_targeted,
                    "enrolled": total_students_enrolled,
                    "active": total_students_active,
                },
                "financial": {
                    "mrr": total_mrr,
                    "arr_projected": total_mrr * 12,
                    "target_arr": 50_000_000,  # ₦50M target
                },
            },

            "regions": {
                region.value: {
                    "status": progress.status.value,
                    "completion": progress.completion_percentage(),
                    "on_track": progress.is_on_track(),
                    "schools_live": progress.schools_live,
                    "students_active": progress.students_active,
                }
                for region, progress in self.regions.items()
            },

            "timeline": {
                "regions_active": len([p for p in self.regions.values() if p.status == RolloutStatus.LIVE]),
                "regions_complete": len([p for p in self.regions.values() if p.status == RolloutStatus.COMPLETE]),
                "regions_remaining": 5 - len([p for p in self.regions.values() if p.status in [RolloutStatus.COMPLETE, RolloutStatus.STABILIZING]]),
            },
        }

    def get_sales_funnel(self, region: Optional[Region] = None) -> Dict[str, Any]:
        """Get sales funnel metrics"""
        schools = self.schools if not region else [s for s in self.schools if s.region == region]

        funnel = {
            "leads": len([s for s in schools if s.status == SchoolStatus.LEAD]),
            "qualified": len([s for s in schools if s.status in [SchoolStatus.QUALIFIED, SchoolStatus.PITCHED, SchoolStatus.PROPOSAL_SENT, SchoolStatus.MOU_SIGNED, SchoolStatus.TRAINING_SCHEDULED, SchoolStatus.TRAINING_COMPLETE, SchoolStatus.LIVE]]),
            "pitched": len([s for s in schools if s.status in [SchoolStatus.PITCHED, SchoolStatus.PROPOSAL_SENT, SchoolStatus.MOU_SIGNED, SchoolStatus.TRAINING_SCHEDULED, SchoolStatus.TRAINING_COMPLETE, SchoolStatus.LIVE]]),
            "proposal_sent": len([s for s in schools if s.status in [SchoolStatus.PROPOSAL_SENT, SchoolStatus.MOU_SIGNED, SchoolStatus.TRAINING_SCHEDULED, SchoolStatus.TRAINING_COMPLETE, SchoolStatus.LIVE]]),
            "closed": len([s for s in schools if s.status in [SchoolStatus.MOU_SIGNED, SchoolStatus.TRAINING_SCHEDULED, SchoolStatus.TRAINING_COMPLETE, SchoolStatus.LIVE]]),
            "live": len([s for s in schools if s.status == SchoolStatus.LIVE]),
        }

        # Calculate conversion rates
        funnel["conversion_rates"] = {
            "lead_to_qualified": (funnel["qualified"] / funnel["leads"] * 100) if funnel["leads"] > 0 else 0,
            "qualified_to_pitch": (funnel["pitched"] / funnel["qualified"] * 100) if funnel["qualified"] > 0 else 0,
            "pitch_to_proposal": (funnel["proposal_sent"] / funnel["pitched"] * 100) if funnel["pitched"] > 0 else 0,
            "proposal_to_close": (funnel["closed"] / funnel["proposal_sent"] * 100) if funnel["proposal_sent"] > 0 else 0,
            "overall": (funnel["closed"] / funnel["leads"] * 100) if funnel["leads"] > 0 else 0,
        }

        return funnel

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts for regions at risk"""
        alerts = []

        for region, progress in self.regions.items():
            # Alert if region is not on track
            if not progress.is_on_track() and progress.status in [RolloutStatus.RECRUITMENT, RolloutStatus.ONBOARDING, RolloutStatus.TRAINING]:
                alerts.append({
                    "severity": "warning",
                    "region": region.value,
                    "message": f"{region.value} is {progress.completion_percentage():.1f}% complete but should be further along",
                    "recommendation": "Accelerate school recruitment or extend timeline",
                })

            # Alert if engagement below target
            if progress.status == RolloutStatus.LIVE and progress.weekly_active_rate < 70:
                alerts.append({
                    "severity": "warning",
                    "region": region.value,
                    "message": f"{region.value} weekly active rate is {progress.weekly_active_rate:.1f}% (target: 70%)",
                    "recommendation": "Increase teacher engagement, send re-activation campaigns",
                })

            # Alert if budget overrun
            target = REGIONAL_TARGETS[region]
            if progress.budget_spent > target.budget_ngn:
                alerts.append({
                    "severity": "critical",
                    "region": region.value,
                    "message": f"{region.value} budget exceeded: ₦{progress.budget_spent:,.0f} / ₦{target.budget_ngn:,.0f}",
                    "recommendation": "Review spending, optimize CAC",
                })

        return alerts

    def export_report(self, format: str = "json") -> str:
        """Export comprehensive report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "phase_5_overview": self.get_phase_5_overview(),
            "regional_dashboards": {
                region.value: self.get_regional_dashboard(region)
                for region in Region
            },
            "sales_funnel": self.get_sales_funnel(),
            "alerts": self.get_alerts(),
        }

        if format == "json":
            return json.dumps(report, indent=2, default=str)
        # Add other formats (CSV, PDF) as needed

        return json.dumps(report, indent=2, default=str)

    # Helper methods

    def _get_school(self, school_id: str) -> Optional[School]:
        """Get school by ID"""
        for school in self.schools:
            if school.school_id == school_id:
                return school
        return None

    def _update_regional_stats(self, region: Region) -> None:
        """Update regional statistics based on schools"""
        regional_schools = [s for s in self.schools if s.region == region]
        progress = self.regions[region]

        progress.schools_qualified = len([s for s in regional_schools if s.status != SchoolStatus.LEAD])
        progress.schools_pitched = len([s for s in regional_schools if s.status in [SchoolStatus.PITCHED, SchoolStatus.PROPOSAL_SENT, SchoolStatus.MOU_SIGNED, SchoolStatus.TRAINING_SCHEDULED, SchoolStatus.TRAINING_COMPLETE, SchoolStatus.LIVE]])
        progress.schools_signed = len([s for s in regional_schools if s.status in [SchoolStatus.MOU_SIGNED, SchoolStatus.TRAINING_SCHEDULED, SchoolStatus.TRAINING_COMPLETE, SchoolStatus.LIVE]])
        progress.schools_live = len([s for s in regional_schools if s.status == SchoolStatus.LIVE])

        progress.students_enrolled = sum(s.num_students for s in regional_schools if s.status in [SchoolStatus.MOU_SIGNED, SchoolStatus.TRAINING_SCHEDULED, SchoolStatus.TRAINING_COMPLETE, SchoolStatus.LIVE])
        progress.teachers_trained = sum(s.num_teachers for s in regional_schools if s.status in [SchoolStatus.TRAINING_COMPLETE, SchoolStatus.LIVE])

        progress.mrr = sum(s.mrr for s in regional_schools if s.status == SchoolStatus.LIVE)

        progress.updated_at = datetime.now()


# Example usage
if __name__ == "__main__":
    # Initialize tracker
    tracker = RegionalRolloutTracker()

    # Example: Add a school in Lagos
    school = School(
        school_id="SCH001",
        name="Greenfield International School",
        region=Region.LAGOS_OGUN,
        location="Ikeja, Lagos",
        school_type="private",
        principal_name="Mrs. Adebayo",
        principal_email="principal@greenfield.ng",
        principal_phone="+234 80X XXX XXXX",
        num_students=200,
        num_teachers=15,
        classes=["SS1", "SS2", "SS3"],
        subjects=["Mathematics", "English", "Physics", "Chemistry", "Biology"],
        status=SchoolStatus.LEAD,
        lead_source="referral",
        assigned_to="Sales Rep Lagos",
        subscription_tier="premium",
        mrr=100_000,  # 200 students × ₦500
        created_at=datetime.now(),
    )

    tracker.add_school(school)

    # Update school status progression
    tracker.update_school_status("SCH001", SchoolStatus.QUALIFIED, "Met BANT criteria")
    tracker.update_school_status("SCH001", SchoolStatus.PITCHED, "Demo went well")
    tracker.update_school_status("SCH001", SchoolStatus.MOU_SIGNED, "Contract signed!")
    tracker.update_school_status("SCH001", SchoolStatus.LIVE, "Successfully onboarded")

    # Get Lagos dashboard
    lagos_dashboard = tracker.get_regional_dashboard(Region.LAGOS_OGUN)
    print("Lagos/Ogun Dashboard:")
    print(json.dumps(lagos_dashboard, indent=2, default=str))

    # Get Phase 5 overview
    overview = tracker.get_phase_5_overview()
    print("\nPhase 5 Overview:")
    print(json.dumps(overview, indent=2, default=str))

    # Export full report
    report = tracker.export_report()
    print("\nFull Report:")
    print(report)
