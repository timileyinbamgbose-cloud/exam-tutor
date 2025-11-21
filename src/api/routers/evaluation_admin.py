"""
Evaluation & A/B Testing Administration Router
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.ai.evaluation_service import evaluation_service
from src.api.routers.auth_db import get_current_user
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/evaluation", tags=["Evaluation & A/B Testing"])


class RecordMetricRequest(BaseModel):
    model_id: str
    metric_name: str
    value: float
    metadata: Dict[str, Any] = {}


class CreateExperimentRequest(BaseModel):
    name: str
    description: str
    variants: List[str]
    traffic_split: Optional[Dict[str, float]] = None


class RecordExperimentMetricRequest(BaseModel):
    experiment_id: str
    variant: str
    metric_name: str
    value: float


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.post("/metrics/record")
async def record_metric(request: RecordMetricRequest, current_user: dict = Depends(require_admin)):
    """Record a model metric"""
    try:
        evaluation_service.record_metric(
            model_id=request.model_id,
            metric_name=request.metric_name,
            value=request.value,
            metadata=request.metadata
        )
        return {"success": True, "message": f"Recorded {request.metric_name} for {request.model_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/create")
async def create_experiment(request: CreateExperimentRequest, current_user: dict = Depends(require_admin)):
    """Create A/B test experiment"""
    try:
        experiment = evaluation_service.create_ab_experiment(
            name=request.name,
            description=request.description,
            variants=request.variants,
            traffic_split=request.traffic_split
        )
        return {"success": True, "experiment": experiment.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/list")
async def list_experiments(status_filter: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List all experiments"""
    try:
        experiments = evaluation_service.list_experiments(status=status_filter)
        return {"success": True, "experiments": [exp.dict() for exp in experiments], "count": len(experiments)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/results")
async def get_experiment_results(experiment_id: str, current_user: dict = Depends(get_current_user)):
    """Get experiment results"""
    try:
        results = evaluation_service.get_experiment_results(experiment_id)
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/{experiment_id}/assign")
async def assign_variant(experiment_id: str, user_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Assign user to experiment variant"""
    try:
        variant = evaluation_service.assign_variant(experiment_id, user_id or current_user.get("id"))
        return {"success": True, "variant": variant}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/{experiment_id}/complete")
async def complete_experiment(experiment_id: str, current_user: dict = Depends(require_admin)):
    """Mark experiment as completed"""
    try:
        experiment = evaluation_service.complete_experiment(experiment_id)
        return {"success": True, "experiment": experiment.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/metric/record")
async def record_experiment_metric(request: RecordExperimentMetricRequest, current_user: dict = Depends(get_current_user)):
    """Record metric for experiment variant"""
    try:
        evaluation_service.record_experiment_metric(
            experiment_id=request.experiment_id,
            variant=request.variant,
            metric_name=request.metric_name,
            value=request.value
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_evaluation_stats(current_user: dict = Depends(get_current_user)):
    """Get evaluation service statistics"""
    stats = evaluation_service.get_stats()
    return {"success": True, "stats": stats}


@router.get("/health")
async def evaluation_health_check():
    """Check evaluation service health"""
    stats = evaluation_service.get_stats()
    return {"evaluation_service": "operational", "stats": stats}
