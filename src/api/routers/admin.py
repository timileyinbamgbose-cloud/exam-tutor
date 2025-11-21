"""
Admin Router
Handles administrative functions and system management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.api.auth import get_current_admin
from typing import List, Dict, Any
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get("/dashboard")
async def get_admin_dashboard(current_user: dict = Depends(get_current_admin)):
    """Get admin dashboard overview"""
    return {
        "total_users": 1250,
        "total_students": 1000,
        "total_teachers": 200,
        "total_schools": 50,
        "active_subscriptions": 45,
        "revenue_this_month": 2500000,  # Naira
        "system_health": "healthy",
        "api_uptime": 99.7,
        "storage_used_gb": 150.5,
        "daily_active_users": 650
    }


@router.get("/users")
async def get_all_users(
    role: str = None,
    status: str = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_admin)
):
    """Get list of all users with filters"""
    # Mock users
    users = [
        {
            "id": f"user_{i}",
            "email": f"user{i}@example.com",
            "full_name": f"User {i}",
            "role": "student" if i % 5 != 0 else "teacher",
            "status": "active",
            "created_at": datetime.utcnow() - timedelta(days=i*10),
            "last_login": datetime.utcnow() - timedelta(hours=i)
        }
        for i in range(1, 21)
    ]

    if role:
        users = [u for u in users if u["role"] == role]

    if status:
        users = [u for u in users if u["status"] == status]

    return {
        "users": users,
        "total": len(users),
        "page": page,
        "page_size": page_size
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    updates: Dict[str, Any],
    current_user: dict = Depends(get_current_admin)
):
    """Update user information"""
    return {
        "message": "User updated successfully",
        "user_id": user_id,
        "updated_fields": list(updates.keys())
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Delete a user account"""
    return {
        "message": "User deleted successfully",
        "user_id": user_id,
        "deleted_at": datetime.utcnow()
    }


@router.get("/schools")
async def get_all_schools(current_user: dict = Depends(get_current_admin)):
    """Get list of all registered schools"""
    schools = [
        {
            "id": f"school_{i}",
            "name": f"School {i}",
            "type": "public" if i % 2 == 0 else "private",
            "location": f"Lagos",
            "total_students": 100 + i*10,
            "total_teachers": 10 + i,
            "subscription_tier": "free" if i % 3 == 0 else "premium",
            "status": "active"
        }
        for i in range(1, 11)
    ]

    return {"schools": schools, "total": len(schools)}


@router.post("/schools")
async def create_school(
    name: str,
    type: str,
    location: str,
    contact_email: str,
    current_user: dict = Depends(get_current_admin)
):
    """Register a new school"""
    import uuid

    school_id = str(uuid.uuid4())

    return {
        "school_id": school_id,
        "name": name,
        "type": type,
        "location": location,
        "contact_email": contact_email,
        "status": "active",
        "created_at": datetime.utcnow()
    }


@router.get("/subscriptions")
async def get_all_subscriptions(
    status: str = None,
    current_user: dict = Depends(get_current_admin)
):
    """Get list of all subscriptions"""
    subscriptions = [
        {
            "id": f"sub_{i}",
            "school_id": f"school_{i}",
            "school_name": f"School {i}",
            "tier": "premium" if i % 2 == 0 else "free",
            "status": "active",
            "num_students": 100 + i*10,
            "monthly_revenue": 50000 if i % 2 == 0 else 0,
            "start_date": datetime.utcnow() - timedelta(days=i*30),
            "next_billing_date": datetime.utcnow() + timedelta(days=30)
        }
        for i in range(1, 11)
    ]

    if status:
        subscriptions = [s for s in subscriptions if s["status"] == status]

    return {"subscriptions": subscriptions, "total": len(subscriptions)}


@router.get("/analytics")
async def get_system_analytics(
    start_date: datetime = None,
    end_date: datetime = None,
    current_user: dict = Depends(get_current_admin)
):
    """Get comprehensive system analytics"""
    return {
        "period": {
            "start": start_date or datetime.utcnow() - timedelta(days=30),
            "end": end_date or datetime.utcnow()
        },
        "users": {
            "new_registrations": 150,
            "active_users": 850,
            "churn_rate": 0.05
        },
        "engagement": {
            "total_questions": 25000,
            "total_practice_sessions": 15000,
            "avg_session_duration": 38.5,
            "daily_active_users": 650
        },
        "revenue": {
            "total_revenue": 7500000,
            "mrr": 2500000,
            "arr": 30000000,
            "paying_schools": 35
        },
        "performance": {
            "avg_score_improvement": 0.18,
            "topics_covered": 450,
            "completion_rate": 0.65
        }
    }


@router.get("/system/health")
async def get_system_health(current_user: dict = Depends(get_current_admin)):
    """Get detailed system health metrics"""
    return {
        "status": "healthy",
        "api": {
            "uptime_percentage": 99.7,
            "avg_response_time_ms": 150,
            "requests_per_minute": 250,
            "error_rate": 0.002
        },
        "database": {
            "status": "connected",
            "connections": 15,
            "query_time_ms": 25
        },
        "storage": {
            "used_gb": 150.5,
            "total_gb": 500,
            "usage_percentage": 30.1
        },
        "cache": {
            "status": "operational",
            "hit_rate": 0.85,
            "memory_mb": 512
        }
    }


@router.post("/system/maintenance")
async def toggle_maintenance_mode(
    enabled: bool,
    message: str = None,
    current_user: dict = Depends(get_current_admin)
):
    """Enable or disable maintenance mode"""
    return {
        "maintenance_mode": enabled,
        "message": message or "System is under maintenance",
        "updated_at": datetime.utcnow()
    }


@router.get("/logs")
async def get_system_logs(
    level: str = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_admin)
):
    """Get system logs"""
    # Mock logs
    logs = [
        {
            "timestamp": datetime.utcnow() - timedelta(minutes=i),
            "level": "INFO" if i % 3 != 0 else "WARNING",
            "message": f"Log message {i}",
            "source": "api.main"
        }
        for i in range(1, min(limit+1, 101))
    ]

    if level:
        logs = [l for l in logs if l["level"] == level]

    return {"logs": logs, "total": len(logs)}


@router.get("/export/data")
async def export_data(
    data_type: str,
    format: str = "csv",
    current_user: dict = Depends(get_current_admin)
):
    """Export system data (users, analytics, etc.)"""
    return {
        "export_id": "export_001",
        "data_type": data_type,
        "format": format,
        "status": "processing",
        "download_url": f"/api/v1/admin/downloads/export_001.{format}",
        "estimated_completion": datetime.utcnow() + timedelta(minutes=5)
    }
