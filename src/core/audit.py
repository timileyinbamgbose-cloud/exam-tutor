"""
Audit Logging System
Epic 3.4: Kubernetes Deployment & Security
NDPR Compliance - Audit Trails and Activity Logging
"""

import json
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio
from collections import deque

from src.core.logger import logger
from src.core.encryption import pii_masker


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Authentication & Authorization
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_CHANGE = "auth.password_change"
    TOKEN_REFRESH = "auth.token_refresh"

    # Data Access
    DATA_READ = "data.read"
    DATA_CREATE = "data.create"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"

    # Student Activities
    STUDENT_REGISTER = "student.register"
    STUDENT_QUESTION = "student.question"
    STUDENT_PRACTICE = "student.practice"
    STUDENT_PROGRESS_VIEW = "student.progress_view"

    # Administrative
    ADMIN_ACCESS = "admin.access"
    CONFIG_CHANGE = "admin.config_change"
    USER_ROLE_CHANGE = "admin.role_change"

    # NDPR Compliance
    CONSENT_GIVEN = "ndpr.consent_given"
    CONSENT_WITHDRAWN = "ndpr.consent_withdrawn"
    DATA_ERASURE_REQUEST = "ndpr.data_erasure_request"
    DATA_ACCESS_REQUEST = "ndpr.data_access_request"
    DATA_PORTABILITY_REQUEST = "ndpr.data_portability_request"

    # Security
    SECURITY_ALERT = "security.alert"
    RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "security.suspicious_activity"

    # System
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLog:
    """
    Audit logging system for NDPR compliance.
    Logs all significant user and system activities.
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        enable_console: bool = False,
        enable_remote: bool = False,
        buffer_size: int = 1000
    ):
        """
        Initialize audit logging system.

        Args:
            log_file: Path to audit log file
            enable_console: Enable console logging
            enable_remote: Enable remote logging (e.g., to SIEM)
            buffer_size: Size of in-memory buffer before flushing
        """
        self.log_file = Path(log_file) if log_file else Path("logs/audit.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self.enable_console = enable_console
        self.enable_remote = enable_remote
        self.buffer: deque = deque(maxlen=buffer_size)

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        severity: AuditSeverity = AuditSeverity.LOW,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        mask_pii: bool = True
    ) -> None:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            user_id: ID of user performing action
            resource: Resource being accessed/modified
            action: Specific action performed
            result: Result of action (success, failure, denied)
            severity: Severity level
            details: Additional event details
            ip_address: User's IP address
            user_agent: User's browser/client info
            mask_pii: Whether to mask PII in logs
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'

        audit_entry = {
            "timestamp": timestamp,
            "event_type": event_type.value,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "result": result,
            "severity": severity.value,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {}
        }

        # Mask PII if enabled
        if mask_pii and user_id:
            audit_entry["user_id"] = pii_masker.mask_email(user_id) if '@' in user_id else user_id

        # Add to buffer
        self.buffer.append(audit_entry)

        # Log to various destinations
        await self._write_to_file(audit_entry)

        if self.enable_console:
            self._log_to_console(audit_entry)

        if self.enable_remote:
            await self._send_to_remote(audit_entry)

        # Log using application logger
        logger.info(f"AUDIT: {event_type.value}", extra=audit_entry)

    async def _write_to_file(self, entry: Dict[str, Any]) -> None:
        """Write audit entry to file."""
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _log_to_console(self, entry: Dict[str, Any]) -> None:
        """Log audit entry to console."""
        print(f"[AUDIT] {json.dumps(entry, indent=2)}")

    async def _send_to_remote(self, entry: Dict[str, Any]) -> None:
        """Send audit entry to remote SIEM/logging system."""
        # TODO: Implement remote logging (e.g., to Elasticsearch, Splunk)
        pass

    async def flush_buffer(self) -> None:
        """Flush buffered audit logs to storage."""
        if not self.buffer:
            return

        try:
            with open(self.log_file, 'a') as f:
                while self.buffer:
                    entry = self.buffer.popleft()
                    f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to flush audit buffer: {e}")

    async def query_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """
        Query audit logs with filters.

        Args:
            start_time: Start of time range
            end_time: End of time range
            event_type: Filter by event type
            user_id: Filter by user ID
            limit: Maximum number of results

        Returns:
            List of matching audit log entries
        """
        results = []

        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)

                        # Apply filters
                        if start_time and datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')) < start_time:
                            continue
                        if end_time and datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')) > end_time:
                            continue
                        if event_type and entry['event_type'] != event_type.value:
                            continue
                        if user_id and entry['user_id'] != user_id:
                            continue

                        results.append(entry)

                        if len(results) >= limit:
                            break

                    except json.JSONDecodeError:
                        continue

        except FileNotFoundError:
            logger.warning(f"Audit log file not found: {self.log_file}")

        return results

    async def generate_report(
        self,
        start_time: datetime,
        end_time: datetime,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate audit report for a time period.

        Args:
            start_time: Report start time
            end_time: Report end time
            output_file: Optional file to save report

        Returns:
            Report summary
        """
        logs = await self.query_logs(start_time=start_time, end_time=end_time, limit=10000)

        report = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_events": len(logs),
            "events_by_type": {},
            "events_by_severity": {},
            "users_active": set(),
            "failed_actions": 0,
            "security_alerts": 0
        }

        for log in logs:
            # Count by type
            event_type = log['event_type']
            report['events_by_type'][event_type] = report['events_by_type'].get(event_type, 0) + 1

            # Count by severity
            severity = log['severity']
            report['events_by_severity'][severity] = report['events_by_severity'].get(severity, 0) + 1

            # Track active users
            if log['user_id']:
                report['users_active'].add(log['user_id'])

            # Count failures
            if log['result'] != 'success':
                report['failed_actions'] += 1

            # Count security alerts
            if 'security' in event_type:
                report['security_alerts'] += 1

        report['users_active'] = len(report['users_active'])

        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)

        return report


# Global audit logger instance
audit_logger = AuditLog(
    log_file="logs/audit.log",
    enable_console=False,
    enable_remote=False
)


# Convenience functions
async def log_auth_event(user_id: str, event_type: AuditEventType, result: str = "success", **kwargs):
    """Log authentication event."""
    await audit_logger.log_event(
        event_type=event_type,
        user_id=user_id,
        result=result,
        severity=AuditSeverity.MEDIUM if result != "success" else AuditSeverity.LOW,
        **kwargs
    )


async def log_data_access(user_id: str, resource: str, action: str, result: str = "success", **kwargs):
    """Log data access event."""
    event_type = {
        "read": AuditEventType.DATA_READ,
        "create": AuditEventType.DATA_CREATE,
        "update": AuditEventType.DATA_UPDATE,
        "delete": AuditEventType.DATA_DELETE,
        "export": AuditEventType.DATA_EXPORT
    }.get(action.lower(), AuditEventType.DATA_READ)

    await audit_logger.log_event(
        event_type=event_type,
        user_id=user_id,
        resource=resource,
        action=action,
        result=result,
        severity=AuditSeverity.MEDIUM,
        **kwargs
    )


async def log_ndpr_event(user_id: str, event_type: AuditEventType, details: Dict[str, Any], **kwargs):
    """Log NDPR compliance event."""
    await audit_logger.log_event(
        event_type=event_type,
        user_id=user_id,
        details=details,
        severity=AuditSeverity.HIGH,
        **kwargs
    )


if __name__ == "__main__":
    # Example usage
    async def main():
        # Log authentication
        await log_auth_event(
            user_id="student@examstutor.ng",
            event_type=AuditEventType.LOGIN,
            ip_address="192.168.1.100"
        )

        # Log data access
        await log_data_access(
            user_id="student@examstutor.ng",
            resource="student_profile",
            action="read"
        )

        # Log NDPR event
        await log_ndpr_event(
            user_id="student@examstutor.ng",
            event_type=AuditEventType.CONSENT_GIVEN,
            details={"consent_type": "data_processing", "version": "1.0"}
        )

        # Generate report
        from datetime import timedelta
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        report = await audit_logger.generate_report(start_time, end_time)
        print(json.dumps(report, indent=2))

    asyncio.run(main())
