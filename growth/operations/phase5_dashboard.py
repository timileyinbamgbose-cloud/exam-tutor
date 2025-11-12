"""
Phase 5 Operational Dashboard
ExamsTutor AI - Scale & Growth

Real-time dashboard for monitoring Phase 5 rollout progress across all dimensions.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum


class HealthStatus(str, Enum):
    """Health status indicators"""
    HEALTHY = "healthy"      # On track, no issues
    WARNING = "warning"       # Minor issues, attention needed
    CRITICAL = "critical"     # Major issues, immediate action required
    UNKNOWN = "unknown"       # Insufficient data


@dataclass
class MetricStatus:
    """Status of a specific metric"""
    name: str
    current_value: float
    target_value: float
    unit: str
    status: HealthStatus
    trend: str  # "up", "down", "stable"
    last_updated: datetime

    def percentage_of_target(self) -> float:
        """Calculate percentage of target achieved"""
        if self.target_value == 0:
            return 0.0
        return (self.current_value / self.target_value) * 100

    def is_on_track(self) -> bool:
        """Check if metric is on track"""
        return self.percentage_of_target() >= 80.0  # 80% threshold


class Phase5Dashboard:
    """
    Comprehensive dashboard for Phase 5 monitoring

    Integrates data from:
    - Regional rollout tracker
    - Business model metrics
    - Partnership manager
    - Infrastructure monitoring
    - Support systems
    """

    def __init__(
        self,
        rollout_tracker=None,
        subscription_manager=None,
        partnership_manager=None,
        infrastructure_monitor=None,
    ):
        self.rollout_tracker = rollout_tracker
        self.subscription_manager = subscription_manager
        self.partnership_manager = partnership_manager
        self.infrastructure_monitor = infrastructure_monitor

    def get_executive_summary(self) -> Dict[str, Any]:
        """
        High-level executive summary

        Returns key metrics for CEO/Board
        """
        now = datetime.now()
        phase_5_start = datetime(2025, 5, 1)  # Example start date
        weeks_elapsed = (now - phase_5_start).days // 7

        # Growth metrics
        growth = self._get_growth_metrics()

        # Financial metrics
        financial = self._get_financial_metrics()

        # Operational metrics
        operational = self._get_operational_metrics()

        # Calculate overall health
        health = self._calculate_overall_health()

        return {
            "as_of": now.isoformat(),
            "phase": "Phase 5: Scale & Growth",
            "week": f"Week {21 + weeks_elapsed}",
            "overall_health": health.value,

            "growth": {
                "schools": {
                    "current": growth["schools_live"],
                    "target": 50,
                    "percentage": (growth["schools_live"] / 50) * 100,
                },
                "students": {
                    "current": growth["students_active"],
                    "target": 10000,
                    "percentage": (growth["students_active"] / 10000) * 100,
                },
            },

            "financial": {
                "mrr": {
                    "current": financial["mrr"],
                    "target": Decimal('3900000'),
                    "percentage": (financial["mrr"] / Decimal('3900000')) * 100,
                },
                "arr_projected": financial["mrr"] * 12,
            },

            "operational": {
                "uptime": operational["uptime_percentage"],
                "response_time_ms": operational["avg_response_time_ms"],
                "active_users_now": operational["current_concurrent_users"],
            },

            "top_wins": self._get_top_wins(),
            "top_risks": self._get_top_risks(),
            "action_items": self._get_priority_actions(),
        }

    def get_growth_dashboard(self) -> Dict[str, Any]:
        """Detailed growth metrics dashboard"""

        metrics = []

        # Schools
        metrics.append(MetricStatus(
            name="Schools Onboarded",
            current_value=self._get_schools_live(),
            target_value=50.0,
            unit="schools",
            status=self._determine_status(self._get_schools_live(), 50.0),
            trend=self._calculate_trend("schools", 7),
            last_updated=datetime.now(),
        ))

        # Students
        metrics.append(MetricStatus(
            name="Active Students",
            current_value=self._get_active_students(),
            target_value=10000.0,
            unit="students",
            status=self._determine_status(self._get_active_students(), 10000.0),
            trend=self._calculate_trend("students", 7),
            last_updated=datetime.now(),
        ))

        # Teachers
        metrics.append(MetricStatus(
            name="Teachers Trained",
            current_value=self._get_teachers_trained(),
            target_value=400.0,
            unit="teachers",
            status=self._determine_status(self._get_teachers_trained(), 400.0),
            trend=self._calculate_trend("teachers", 7),
            last_updated=datetime.now(),
        ))

        # Weekly Active Rate
        weekly_active_rate = self._get_weekly_active_rate()
        metrics.append(MetricStatus(
            name="Weekly Active Rate",
            current_value=weekly_active_rate,
            target_value=70.0,
            unit="%",
            status=HealthStatus.HEALTHY if weekly_active_rate >= 70 else HealthStatus.WARNING,
            trend=self._calculate_trend("weekly_active_rate", 7),
            last_updated=datetime.now(),
        ))

        return {
            "metrics": [
                {
                    "name": m.name,
                    "current": m.current_value,
                    "target": m.target_value,
                    "percentage": m.percentage_of_target(),
                    "status": m.status.value,
                    "trend": m.trend,
                    "unit": m.unit,
                }
                for m in metrics
            ],

            "regional_breakdown": self._get_regional_breakdown(),

            "funnel": self._get_growth_funnel(),
        }

    def get_financial_dashboard(self) -> Dict[str, Any]:
        """Financial metrics dashboard"""

        current_mrr = self._get_current_mrr()
        target_mrr = Decimal('3900000')

        return {
            "revenue": {
                "mrr": {
                    "current": float(current_mrr),
                    "target": float(target_mrr),
                    "percentage": float((current_mrr / target_mrr) * 100),
                    "trend": self._calculate_trend("mrr", 30),
                },
                "arr_projected": float(current_mrr * 12),
                "target_arr": 50000000.0,

                "breakdown": {
                    "premium_subscriptions": float(self._get_premium_revenue()),
                    "government_contracts": float(self._get_government_revenue()),
                    "sponsorships": float(self._get_sponsorship_revenue()),
                },
            },

            "unit_economics": {
                "arpu": float(self._calculate_arpu()),  # Average Revenue Per User
                "cac": float(self._calculate_cac()),    # Customer Acquisition Cost
                "ltv": float(self._calculate_ltv()),    # Lifetime Value
                "ltv_cac_ratio": float(self._calculate_ltv() / max(self._calculate_cac(), 1)),
                "gross_margin_percent": self._calculate_gross_margin(),
            },

            "churn": {
                "monthly_churn_rate": self._get_churn_rate(),
                "target": 5.0,
                "status": "healthy" if self._get_churn_rate() < 5.0 else "warning",
                "churned_schools_this_month": self._get_churned_schools_count(),
                "churned_mrr_this_month": float(self._get_churned_mrr()),
            },

            "budget": {
                "allocated": 72000000.0,
                "spent": float(self._get_budget_spent()),
                "remaining": float(72000000.0 - self._get_budget_spent()),
                "burn_rate_monthly": float(self._calculate_burn_rate()),
                "runway_months": self._calculate_runway_months(),
            },

            "projections": {
                "break_even_week": 26,
                "weeks_to_break_even": max(0, 26 - self._get_current_week()),
                "end_of_phase_mrr": float(self._project_mrr(weeks=10)),
                "end_of_phase_arr": float(self._project_mrr(weeks=10) * 12),
            },
        }

    def get_operational_dashboard(self) -> Dict[str, Any]:
        """Operational metrics dashboard"""

        return {
            "system_health": {
                "uptime_percentage": self._get_uptime_percentage(),
                "target": 99.9,
                "status": "healthy" if self._get_uptime_percentage() >= 99.9 else "warning",

                "performance": {
                    "avg_response_time_ms": self._get_avg_response_time(),
                    "target_ms": 2000,
                    "p95_response_time_ms": self._get_p95_response_time(),
                    "p99_response_time_ms": self._get_p99_response_time(),
                },

                "capacity": {
                    "current_concurrent_users": self._get_concurrent_users(),
                    "max_capacity": 10000,
                    "utilization_percent": (self._get_concurrent_users() / 10000) * 100,
                },

                "infrastructure": {
                    "api_pods_running": self._get_api_pods_count(),
                    "api_pods_target": "10-100 (auto-scaling)",
                    "database_connections": self._get_db_connections(),
                    "redis_hit_rate_percent": self._get_redis_hit_rate(),
                    "cdn_hit_rate_percent": self._get_cdn_hit_rate(),
                },
            },

            "support": {
                "open_tickets": self._get_open_tickets_count(),
                "avg_response_time_hours": self._get_avg_ticket_response_time(),
                "sla_compliance_percent": self._get_sla_compliance(),
                "csat_score": self._get_csat_score(),  # Customer Satisfaction (1-5)
            },

            "engagement": {
                "daily_active_users": self._get_dau(),
                "weekly_active_users": self._get_wau(),
                "monthly_active_users": self._get_mau(),
                "dau_mau_ratio": self._get_dau() / max(self._get_mau(), 1),  # Stickiness

                "avg_session_duration_min": self._get_avg_session_duration(),
                "questions_per_student_weekly": self._get_questions_per_student(),
                "practice_completion_rate": self._get_practice_completion_rate(),
            },

            "content": {
                "total_questions_library": self._get_question_count(),
                "questions_answered_today": self._get_questions_answered_today(),
                "ai_response_accuracy": self._get_ai_accuracy(),
                "avg_explanation_rating": self._get_avg_explanation_rating(),
            },
        }

    def get_regional_dashboard(self, region: str) -> Dict[str, Any]:
        """Detailed dashboard for a specific region"""

        if not self.rollout_tracker:
            return {}

        return self.rollout_tracker.get_regional_dashboard(region)

    def get_partnership_dashboard(self) -> Dict[str, Any]:
        """Partnership metrics dashboard"""

        if not self.partnership_manager:
            return {}

        return self.partnership_manager.get_partnership_dashboard()

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts across the system"""

        alerts = []

        # Growth alerts
        if self._get_schools_live() < self._get_expected_schools():
            alerts.append({
                "severity": "warning",
                "category": "growth",
                "title": "School onboarding behind target",
                "message": f"{self._get_schools_live()} schools live vs {self._get_expected_schools()} expected",
                "action": "Accelerate recruitment in lagging regions",
            })

        # Financial alerts
        churn_rate = self._get_churn_rate()
        if churn_rate > 5.0:
            alerts.append({
                "severity": "critical",
                "category": "financial",
                "title": "Churn rate above target",
                "message": f"{churn_rate:.1f}% monthly churn (target: <5%)",
                "action": "Investigate churned schools, improve retention",
            })

        # Operational alerts
        if self._get_uptime_percentage() < 99.9:
            alerts.append({
                "severity": "critical",
                "category": "operational",
                "title": "Uptime below SLA",
                "message": f"{self._get_uptime_percentage():.2f}% uptime (SLA: 99.9%)",
                "action": "Review incidents, implement fixes",
            })

        if self._get_avg_response_time() > 2000:
            alerts.append({
                "severity": "warning",
                "category": "operational",
                "title": "Response time degraded",
                "message": f"{self._get_avg_response_time()}ms avg response (target: <2000ms)",
                "action": "Investigate performance, consider scaling",
            })

        # Engagement alerts
        weekly_active_rate = self._get_weekly_active_rate()
        if weekly_active_rate < 70.0:
            alerts.append({
                "severity": "warning",
                "category": "engagement",
                "title": "Weekly active rate below target",
                "message": f"{weekly_active_rate:.1f}% weekly active (target: >70%)",
                "action": "Launch re-engagement campaign, check with teachers",
            })

        # Budget alerts
        budget_utilization = (self._get_budget_spent() / 72000000.0) * 100
        time_elapsed_percent = ((datetime.now() - datetime(2025, 5, 1)).days / 70) * 100  # 10 weeks = 70 days
        if budget_utilization > time_elapsed_percent + 15:
            alerts.append({
                "severity": "warning",
                "category": "financial",
                "title": "Budget burn rate high",
                "message": f"{budget_utilization:.1f}% budget spent vs {time_elapsed_percent:.1f}% time elapsed",
                "action": "Review spending, optimize CAC",
            })

        # Regional alerts
        if self.rollout_tracker:
            regional_alerts = self.rollout_tracker.get_alerts()
            alerts.extend(regional_alerts)

        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda x: severity_order.get(x["severity"], 3))

        return alerts

    def get_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly progress report"""

        current_week = self._get_current_week()

        return {
            "week": f"Week {current_week}",
            "generated_at": datetime.now().isoformat(),

            "executive_summary": self.get_executive_summary(),

            "week_over_week_growth": {
                "schools_added": self._get_wow_metric("schools"),
                "students_added": self._get_wow_metric("students"),
                "mrr_growth": self._get_wow_metric("mrr"),
            },

            "key_wins": self._get_top_wins(),
            "challenges": self._get_top_risks(),
            "next_week_priorities": self._get_next_week_priorities(),

            "detailed_metrics": {
                "growth": self.get_growth_dashboard(),
                "financial": self.get_financial_dashboard(),
                "operational": self.get_operational_dashboard(),
                "partnerships": self.get_partnership_dashboard(),
            },

            "alerts": self.get_alerts(),
        }

    # Internal helper methods (placeholders - would integrate with actual systems)

    def _get_growth_metrics(self) -> Dict[str, Any]:
        """Get current growth metrics"""
        return {
            "schools_live": self._get_schools_live(),
            "students_active": self._get_active_students(),
            "teachers_trained": self._get_teachers_trained(),
        }

    def _get_financial_metrics(self) -> Dict[str, Any]:
        """Get current financial metrics"""
        return {
            "mrr": self._get_current_mrr(),
            "arr": self._get_current_mrr() * 12,
            "churn_rate": self._get_churn_rate(),
        }

    def _get_operational_metrics(self) -> Dict[str, Any]:
        """Get current operational metrics"""
        return {
            "uptime_percentage": self._get_uptime_percentage(),
            "avg_response_time_ms": self._get_avg_response_time(),
            "current_concurrent_users": self._get_concurrent_users(),
        }

    def _calculate_overall_health(self) -> HealthStatus:
        """Calculate overall system health"""
        critical_count = len([a for a in self.get_alerts() if a["severity"] == "critical"])
        warning_count = len([a for a in self.get_alerts() if a["severity"] == "warning"])

        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 3:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY

    def _get_top_wins(self) -> List[str]:
        """Get top wins for the week"""
        # Would query from database/tracking system
        return [
            "Signed 3 new schools in Lagos region",
            "MTN data partnership went live",
            "Average weekly active rate increased to 75%",
        ]

    def _get_top_risks(self) -> List[str]:
        """Get top risks/challenges"""
        # Would analyze current state
        return [
            "Abuja recruitment 20% behind schedule",
            "Churn rate ticked up to 6.2% this month",
            "Payment collection delays with 2 schools",
        ]

    def _get_priority_actions(self) -> List[str]:
        """Get priority action items"""
        return [
            "Accelerate Abuja outreach - add 2nd sales rep",
            "Call churned schools to understand issues",
            "Follow up on overdue invoices",
        ]

    def _get_next_week_priorities(self) -> List[str]:
        """Get priorities for next week"""
        return [
            "Launch Rivers/Delta region recruitment",
            "Complete Abuja teacher training",
            "Close Lagos sponsorship deal with Shell",
        ]

    # Metric calculation methods (would integrate with actual data sources)

    def _get_schools_live(self) -> float:
        if self.rollout_tracker:
            overview = self.rollout_tracker.get_phase_5_overview()
            return overview["summary"]["schools"]["live"]
        return 0.0

    def _get_active_students(self) -> float:
        if self.rollout_tracker:
            overview = self.rollout_tracker.get_phase_5_overview()
            return overview["summary"]["students"]["active"]
        return 0.0

    def _get_teachers_trained(self) -> float:
        # Would query from database
        return 0.0

    def _get_weekly_active_rate(self) -> float:
        # Would calculate from usage data
        return 75.0  # Example

    def _get_current_mrr(self) -> Decimal:
        if self.rollout_tracker:
            overview = self.rollout_tracker.get_phase_5_overview()
            return Decimal(str(overview["summary"]["financial"]["mrr"]))
        return Decimal('0')

    def _get_premium_revenue(self) -> Decimal:
        # Would query from subscription manager
        return Decimal('0')

    def _get_government_revenue(self) -> Decimal:
        if self.partnership_manager:
            return self.partnership_manager.calculate_government_revenue()
        return Decimal('0')

    def _get_sponsorship_revenue(self) -> Decimal:
        # Would query from partnership manager
        return Decimal('0')

    def _calculate_arpu(self) -> Decimal:
        students = self._get_active_students()
        if students == 0:
            return Decimal('0')
        return self._get_current_mrr() / Decimal(str(students))

    def _calculate_cac(self) -> Decimal:
        # Customer Acquisition Cost
        return Decimal('50000')  # Example: ₦50k per school

    def _calculate_ltv(self) -> Decimal:
        # Lifetime Value
        return Decimal('500000')  # Example: ₦500k per school

    def _calculate_gross_margin(self) -> float:
        # Gross margin percentage
        return 72.0  # Example: 72%

    def _get_churn_rate(self) -> float:
        # Monthly churn rate
        return 4.5  # Example: 4.5%

    def _get_churned_schools_count(self) -> int:
        return 0

    def _get_churned_mrr(self) -> Decimal:
        return Decimal('0')

    def _get_budget_spent(self) -> Decimal:
        return Decimal('20000000')  # Example: ₦20M spent

    def _calculate_burn_rate(self) -> Decimal:
        # Monthly burn rate
        return Decimal('8000000')  # Example: ₦8M/month

    def _calculate_runway_months(self) -> float:
        burn_rate = self._calculate_burn_rate()
        if burn_rate == 0:
            return float('inf')
        remaining = Decimal('72000000') - self._get_budget_spent()
        return float(remaining / burn_rate)

    def _project_mrr(self, weeks: int) -> Decimal:
        # Project MRR based on current growth rate
        current = self._get_current_mrr()
        # Simple linear projection - would use more sophisticated model
        weekly_growth = Decimal('200000')  # ₦200k/week average
        return current + (weekly_growth * weeks)

    def _get_uptime_percentage(self) -> float:
        # Would query from monitoring system
        return 99.85  # Example

    def _get_avg_response_time(self) -> float:
        # Would query from monitoring system
        return 1400.0  # Example: 1.4s

    def _get_p95_response_time(self) -> float:
        return 2100.0

    def _get_p99_response_time(self) -> float:
        return 3500.0

    def _get_concurrent_users(self) -> int:
        return 2500  # Example

    def _get_api_pods_count(self) -> int:
        return 25  # Example: 25 pods running

    def _get_db_connections(self) -> int:
        return 85  # Example: 85 active connections

    def _get_redis_hit_rate(self) -> float:
        return 88.5  # Example: 88.5%

    def _get_cdn_hit_rate(self) -> float:
        return 92.3  # Example: 92.3%

    def _get_open_tickets_count(self) -> int:
        return 15

    def _get_avg_ticket_response_time(self) -> float:
        return 2.5  # hours

    def _get_sla_compliance(self) -> float:
        return 96.5  # Example: 96.5%

    def _get_csat_score(self) -> float:
        return 4.2  # Example: 4.2/5

    def _get_dau(self) -> int:
        return 4500

    def _get_wau(self) -> int:
        return 7500

    def _get_mau(self) -> int:
        return 9500

    def _get_avg_session_duration(self) -> float:
        return 38.0  # minutes

    def _get_questions_per_student(self) -> float:
        return 27.0

    def _get_practice_completion_rate(self) -> float:
        return 68.0  # %

    def _get_question_count(self) -> int:
        return 25000

    def _get_questions_answered_today(self) -> int:
        return 12500

    def _get_ai_accuracy(self) -> float:
        return 96.5  # %

    def _get_avg_explanation_rating(self) -> float:
        return 4.3  # out of 5

    def _get_expected_schools(self) -> int:
        # Based on timeline
        week = self._get_current_week()
        if week < 23:
            return 15  # Lagos target
        elif week < 25:
            return 25  # Lagos + Abuja
        elif week < 26:
            return 33  # + Rivers
        else:
            return 50  # All regions

    def _get_current_week(self) -> int:
        # Calculate current week (21-30)
        phase_5_start = datetime(2025, 5, 1)
        weeks_elapsed = (datetime.now() - phase_5_start).days // 7
        return 21 + weeks_elapsed

    def _get_regional_breakdown(self) -> List[Dict[str, Any]]:
        if self.rollout_tracker:
            overview = self.rollout_tracker.get_phase_5_overview()
            return [
                {
                    "region": region,
                    "status": data["status"],
                    "schools_live": data["schools_live"],
                    "students_active": data["students_active"],
                    "on_track": data["on_track"],
                }
                for region, data in overview["regions"].items()
            ]
        return []

    def _get_growth_funnel(self) -> Dict[str, int]:
        if self.rollout_tracker:
            return self.rollout_tracker.get_sales_funnel()
        return {}

    def _determine_status(self, current: float, target: float) -> HealthStatus:
        percentage = (current / target) * 100 if target > 0 else 0
        if percentage >= 90:
            return HealthStatus.HEALTHY
        elif percentage >= 70:
            return HealthStatus.WARNING
        else:
            return HealthStatus.CRITICAL

    def _calculate_trend(self, metric: str, days: int) -> str:
        # Would calculate actual trend from historical data
        return "up"  # Example

    def _get_wow_metric(self, metric: str) -> float:
        # Week-over-week growth
        return 0.0  # Would calculate from historical data


# Example usage
if __name__ == "__main__":
    import json

    dashboard = Phase5Dashboard()

    # Get executive summary
    summary = dashboard.get_executive_summary()
    print("Executive Summary:")
    print(json.dumps(summary, indent=2, default=str))

    # Get alerts
    alerts = dashboard.get_alerts()
    print(f"\nActive Alerts: {len(alerts)}")
    for alert in alerts[:5]:  # Top 5
        print(f"  [{alert['severity'].upper()}] {alert['title']}")
        print(f"    {alert['message']}")

    # Get weekly report
    report = dashboard.get_weekly_report()
    print("\nWeekly Report generated")
    print(f"  Overall health: {report['executive_summary']['overall_health']}")
    print(f"  Schools: {report['executive_summary']['growth']['schools']['current']}/50")
    print(f"  Students: {report['executive_summary']['growth']['students']['current']}/10000")
