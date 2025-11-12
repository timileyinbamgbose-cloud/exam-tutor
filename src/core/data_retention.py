"""
Data Retention Policy Implementation
Epic 3.4: Kubernetes Deployment & Security
NDPR Compliance - Data Retention and Right to Erasure
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio

from src.core.logger import logger
from src.core.audit import audit_logger, AuditEventType, AuditSeverity


class DataCategory(str, Enum):
    """Categories of data with different retention periods."""
    # User Data
    USER_PROFILE = "user_profile"  # 2 years after account deletion
    USER_CREDENTIALS = "user_credentials"  # 2 years after account deletion
    USER_PREFERENCES = "user_preferences"  # 1 year after last activity

    # Student Activity Data
    STUDENT_QUESTIONS = "student_questions"  # 3 years
    STUDENT_PRACTICE = "student_practice"  # 3 years
    STUDENT_PROGRESS = "student_progress"  # 3 years
    STUDENT_PERFORMANCE = "student_performance"  # 5 years (analytics)

    # System Data
    AUDIT_LOGS = "audit_logs"  # 7 years (legal requirement)
    SECURITY_LOGS = "security_logs"  # 5 years
    ERROR_LOGS = "error_logs"  # 1 year
    ACCESS_LOGS = "access_logs"  # 6 months

    # Temporary Data
    SESSIONS = "sessions"  # 30 days
    CACHE = "cache"  # 7 days
    TEMP_FILES = "temp_files"  # 24 hours


class RetentionPolicy:
    """Defines retention period for a data category."""

    def __init__(
        self,
        category: DataCategory,
        retention_days: int,
        description: str,
        legal_basis: str
    ):
        """
        Initialize retention policy.

        Args:
            category: Data category
            retention_days: Number of days to retain data
            description: Policy description
            legal_basis: Legal basis for retention
        """
        self.category = category
        self.retention_days = retention_days
        self.description = description
        self.legal_basis = legal_basis


# Default retention policies (NDPR compliant)
DEFAULT_RETENTION_POLICIES = {
    DataCategory.USER_PROFILE: RetentionPolicy(
        category=DataCategory.USER_PROFILE,
        retention_days=730,  # 2 years
        description="User profile data retained for 2 years after account deletion",
        legal_basis="Contract fulfillment and legal obligations"
    ),
    DataCategory.USER_CREDENTIALS: RetentionPolicy(
        category=DataCategory.USER_CREDENTIALS,
        retention_days=730,  # 2 years
        description="Authentication credentials retained for security audit",
        legal_basis="Security and fraud prevention"
    ),
    DataCategory.USER_PREFERENCES: RetentionPolicy(
        category=DataCategory.USER_PREFERENCES,
        retention_days=365,  # 1 year
        description="User preferences retained for 1 year after last activity",
        legal_basis="Legitimate interest"
    ),
    DataCategory.STUDENT_QUESTIONS: RetentionPolicy(
        category=DataCategory.STUDENT_QUESTIONS,
        retention_days=1095,  # 3 years
        description="Student questions retained for education quality improvement",
        legal_basis="Contract fulfillment and legitimate interest"
    ),
    DataCategory.STUDENT_PRACTICE: RetentionPolicy(
        category=DataCategory.STUDENT_PRACTICE,
        retention_days=1095,  # 3 years
        description="Practice data retained for progress tracking",
        legal_basis="Contract fulfillment"
    ),
    DataCategory.STUDENT_PROGRESS: RetentionPolicy(
        category=DataCategory.STUDENT_PROGRESS,
        retention_days=1095,  # 3 years
        description="Progress data retained for analytics and improvement",
        legal_basis="Contract fulfillment and legitimate interest"
    ),
    DataCategory.STUDENT_PERFORMANCE: RetentionPolicy(
        category=DataCategory.STUDENT_PERFORMANCE,
        retention_days=1825,  # 5 years
        description="Performance analytics retained for research",
        legal_basis="Legitimate interest (anonymized after 2 years)"
    ),
    DataCategory.AUDIT_LOGS: RetentionPolicy(
        category=DataCategory.AUDIT_LOGS,
        retention_days=2555,  # 7 years
        description="Audit logs retained for legal compliance",
        legal_basis="Legal obligation"
    ),
    DataCategory.SECURITY_LOGS: RetentionPolicy(
        category=DataCategory.SECURITY_LOGS,
        retention_days=1825,  # 5 years
        description="Security logs retained for threat analysis",
        legal_basis="Legal obligation and security"
    ),
    DataCategory.ERROR_LOGS: RetentionPolicy(
        category=DataCategory.ERROR_LOGS,
        retention_days=365,  # 1 year
        description="Error logs retained for system improvement",
        legal_basis="Legitimate interest"
    ),
    DataCategory.ACCESS_LOGS: RetentionPolicy(
        category=DataCategory.ACCESS_LOGS,
        retention_days=180,  # 6 months
        description="Access logs retained for security monitoring",
        legal_basis="Security and legitimate interest"
    ),
    DataCategory.SESSIONS: RetentionPolicy(
        category=DataCategory.SESSIONS,
        retention_days=30,
        description="Session data retained for 30 days",
        legal_basis="Technical necessity"
    ),
    DataCategory.CACHE: RetentionPolicy(
        category=DataCategory.CACHE,
        retention_days=7,
        description="Cached data retained for performance",
        legal_basis="Technical necessity"
    ),
    DataCategory.TEMP_FILES: RetentionPolicy(
        category=DataCategory.TEMP_FILES,
        retention_days=1,
        description="Temporary files deleted daily",
        legal_basis="Technical necessity"
    ),
}


class DataRetentionManager:
    """
    Manages data retention and deletion according to NDPR compliance.
    """

    def __init__(self, retention_policies: Optional[Dict[DataCategory, RetentionPolicy]] = None):
        """
        Initialize data retention manager.

        Args:
            retention_policies: Custom retention policies. Uses defaults if None.
        """
        self.retention_policies = retention_policies or DEFAULT_RETENTION_POLICIES
        self.deletion_queue: List[Dict[str, Any]] = []

    def get_retention_period(self, category: DataCategory) -> int:
        """
        Get retention period in days for a data category.

        Args:
            category: Data category

        Returns:
            Retention period in days
        """
        policy = self.retention_policies.get(category)
        if policy:
            return policy.retention_days
        else:
            logger.warning(f"No retention policy for category: {category}")
            return 365  # Default 1 year

    def is_expired(self, created_at: datetime, category: DataCategory) -> bool:
        """
        Check if data has exceeded retention period.

        Args:
            created_at: Data creation timestamp
            category: Data category

        Returns:
            True if data is expired, False otherwise
        """
        retention_days = self.get_retention_period(category)
        expiry_date = created_at + timedelta(days=retention_days)
        return datetime.utcnow() > expiry_date

    async def schedule_deletion(
        self,
        data_id: str,
        category: DataCategory,
        created_at: datetime,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Schedule data for deletion after retention period.

        Args:
            data_id: Unique identifier for data
            category: Data category
            created_at: Data creation timestamp
            user_id: Associated user ID
            metadata: Additional metadata
        """
        retention_days = self.get_retention_period(category)
        deletion_date = created_at + timedelta(days=retention_days)

        deletion_item = {
            "data_id": data_id,
            "category": category.value,
            "created_at": created_at.isoformat(),
            "deletion_date": deletion_date.isoformat(),
            "user_id": user_id,
            "metadata": metadata or {},
            "status": "scheduled"
        }

        self.deletion_queue.append(deletion_item)

        logger.info(
            f"Scheduled deletion for {category.value}",
            extra={
                "data_id": data_id,
                "deletion_date": deletion_date.isoformat()
            }
        )

    async def process_deletions(self) -> Dict[str, int]:
        """
        Process scheduled deletions for expired data.

        Returns:
            Statistics on deletions performed
        """
        stats = {
            "processed": 0,
            "deleted": 0,
            "failed": 0,
            "skipped": 0
        }

        current_time = datetime.utcnow()

        for item in self.deletion_queue[:]:
            stats["processed"] += 1

            try:
                deletion_date = datetime.fromisoformat(item["deletion_date"].replace('Z', '+00:00'))

                if current_time >= deletion_date:
                    # Perform deletion
                    success = await self._delete_data(item)

                    if success:
                        stats["deleted"] += 1
                        self.deletion_queue.remove(item)

                        # Log deletion in audit
                        await audit_logger.log_event(
                            event_type=AuditEventType.DATA_DELETE,
                            user_id=item.get("user_id"),
                            resource=item["category"],
                            action="automatic_deletion",
                            result="success",
                            severity=AuditSeverity.MEDIUM,
                            details={
                                "data_id": item["data_id"],
                                "reason": "retention_policy",
                                "retention_days": self.get_retention_period(DataCategory(item["category"]))
                            }
                        )
                    else:
                        stats["failed"] += 1
                else:
                    stats["skipped"] += 1

            except Exception as e:
                logger.error(f"Failed to process deletion: {e}", extra={"item": item})
                stats["failed"] += 1

        logger.info(f"Deletion processing complete", extra=stats)
        return stats

    async def _delete_data(self, item: Dict[str, Any]) -> bool:
        """
        Perform actual data deletion.

        Args:
            item: Deletion item with data details

        Returns:
            True if deletion successful, False otherwise
        """
        # TODO: Implement actual deletion logic for different data categories
        # This should interact with the database and remove the data

        logger.info(
            f"Deleting data: {item['data_id']} ({item['category']})",
            extra=item
        )

        # Placeholder for actual deletion
        # Example: await database.delete(item['category'], item['data_id'])

        return True

    async def handle_erasure_request(
        self,
        user_id: str,
        categories: Optional[List[DataCategory]] = None
    ) -> Dict[str, Any]:
        """
        Handle NDPR Right to Erasure (Right to be Forgotten) request.

        Args:
            user_id: User requesting data erasure
            categories: Specific data categories to erase. If None, erases all user data.

        Returns:
            Erasure result summary
        """
        if categories is None:
            # Erase all user data categories
            categories = [
                DataCategory.USER_PROFILE,
                DataCategory.USER_PREFERENCES,
                DataCategory.STUDENT_QUESTIONS,
                DataCategory.STUDENT_PRACTICE,
                DataCategory.STUDENT_PROGRESS
            ]

        result = {
            "user_id": user_id,
            "request_time": datetime.utcnow().isoformat(),
            "categories": [cat.value for cat in categories],
            "status": "processing",
            "deleted_count": 0,
            "anonymized_count": 0,
            "retained_count": 0
        }

        for category in categories:
            try:
                # Check if data can be deleted or must be anonymized
                policy = self.retention_policies.get(category)

                if policy and "legal" in policy.legal_basis.lower():
                    # Data must be retained for legal reasons - anonymize instead
                    await self._anonymize_data(user_id, category)
                    result["anonymized_count"] += 1
                else:
                    # Data can be deleted
                    await self._delete_user_data(user_id, category)
                    result["deleted_count"] += 1

            except Exception as e:
                logger.error(f"Failed to erase {category.value} for user {user_id}: {e}")
                result["retained_count"] += 1

        result["status"] = "completed"

        # Log NDPR erasure event
        await audit_logger.log_event(
            event_type=AuditEventType.DATA_ERASURE_REQUEST,
            user_id=user_id,
            action="erasure_completed",
            result="success",
            severity=AuditSeverity.HIGH,
            details=result
        )

        return result

    async def _delete_user_data(self, user_id: str, category: DataCategory) -> None:
        """Delete all user data for a specific category."""
        # TODO: Implement actual user data deletion
        logger.info(f"Deleting {category.value} for user {user_id}")
        pass

    async def _anonymize_data(self, user_id: str, category: DataCategory) -> None:
        """Anonymize user data instead of deletion (for legally required retention)."""
        # TODO: Implement data anonymization
        logger.info(f"Anonymizing {category.value} for user {user_id}")
        pass

    def get_policy_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary of all retention policies.

        Returns:
            List of retention policy summaries
        """
        return [
            {
                "category": policy.category.value,
                "retention_days": policy.retention_days,
                "retention_years": round(policy.retention_days / 365, 2),
                "description": policy.description,
                "legal_basis": policy.legal_basis
            }
            for policy in self.retention_policies.values()
        ]


# Global retention manager instance
retention_manager = DataRetentionManager()


if __name__ == "__main__":
    # Example usage
    async def main():
        # Get policy summary
        policies = retention_manager.get_policy_summary()
        print("Retention Policies:")
        for policy in policies:
            print(f"  {policy['category']}: {policy['retention_years']} years - {policy['description']}")

        # Schedule deletion
        await retention_manager.schedule_deletion(
            data_id="question_12345",
            category=DataCategory.STUDENT_QUESTIONS,
            created_at=datetime.utcnow() - timedelta(days=1100),  # 3+ years old
            user_id="student@examstutor.ng"
        )

        # Process deletions
        stats = await retention_manager.process_deletions()
        print(f"\nDeletion Stats: {stats}")

        # Handle erasure request
        result = await retention_manager.handle_erasure_request(
            user_id="student@examstutor.ng"
        )
        print(f"\nErasure Result: {result}")

    asyncio.run(main())
