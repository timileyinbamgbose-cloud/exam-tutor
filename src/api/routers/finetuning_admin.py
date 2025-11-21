"""
Fine-Tuning Administration Router
Manage model fine-tuning jobs
"""
from fastapi import APIRouter, HTTPException, status, Depends, Body
from sqlalchemy.orm import Session
from src.database.config import get_db
from src.database import crud
from src.ai.finetuning_service import finetuning_service, FineTuningDataset
from src.api.routers.auth_db import get_current_user
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/finetuning", tags=["Fine-Tuning"])


class PrepareDataRequest(BaseModel):
    """Request to prepare training data"""
    min_questions: int = 10
    subjects: Optional[List[str]] = None
    class_levels: Optional[List[str]] = None
    system_prompt: Optional[str] = None


class CreateJobRequest(BaseModel):
    """Request to create fine-tuning job"""
    dataset_name: str
    model: str = "gpt-4o-mini-2024-07-18"
    hyperparameters: Optional[Dict[str, Any]] = None
    suffix: Optional[str] = None


def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure user is admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for fine-tuning operations"
        )
    return current_user


@router.post("/data/prepare")
async def prepare_training_data(
    request: PrepareDataRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Prepare training data from existing questions/answers

    Fetches Q&A pairs from database and formats for fine-tuning.
    Requires admin access.
    """
    try:
        # Fetch questions from database
        # Filter by subject and class level if provided
        questions = db.query(crud.models.Question).filter(
            crud.models.Question.answer_text.isnot(None)
        )

        if request.subjects:
            questions = questions.filter(crud.models.Question.subject.in_(request.subjects))

        if request.class_levels:
            questions = questions.filter(crud.models.Question.class_level.in_(request.class_levels))

        questions = questions.all()

        if len(questions) < request.min_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough questions (found {len(questions)}, need {request.min_questions})"
            )

        # Format for fine-tuning
        qa_data = []
        for q in questions:
            qa_data.append({
                "question": q.question_text,
                "answer": q.answer_text,
                "subject": q.subject or "",
                "class_level": q.class_level or ""
            })

        # Prepare dataset
        system_prompt = request.system_prompt or "You are an expert AI tutor for Nigerian secondary school students preparing for WAEC and JAMB examinations."

        dataset = finetuning_service.prepare_training_data(
            questions_and_answers=qa_data,
            system_prompt=system_prompt
        )

        # Save dataset
        dataset_name = f"curriculum_{'_'.join(request.subjects or ['all'])}"
        file_paths = finetuning_service.save_dataset(
            dataset=dataset,
            name=dataset_name,
            split=True
        )

        return {
            "success": True,
            "dataset_name": dataset_name,
            "num_examples": len(dataset.examples),
            "train_examples": len(dataset.examples) - int(len(dataset.examples) * dataset.validation_split),
            "val_examples": int(len(dataset.examples) * dataset.validation_split),
            "files": {k: str(v) for k, v in file_paths.items()}
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare training data: {str(e)}"
        )


@router.post("/jobs/create")
async def create_finetuning_job(
    request: CreateJobRequest,
    current_user: dict = Depends(require_admin)
):
    """
    Create a fine-tuning job on OpenAI

    Uploads training data and starts fine-tuning.
    Requires admin access and valid OpenAI API key.
    """
    if not finetuning_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fine-tuning service not available (OPENAI_API_KEY not set)"
        )

    try:
        # Find dataset files
        import glob
        train_files = glob.glob(str(finetuning_service.datasets_dir / f"{request.dataset_name}*_train.jsonl"))
        val_files = glob.glob(str(finetuning_service.datasets_dir / f"{request.dataset_name}*_val.jsonl"))

        if not train_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset '{request.dataset_name}' not found"
            )

        train_file = train_files[0]
        val_file = val_files[0] if val_files else None

        # Upload files to OpenAI
        from pathlib import Path
        training_file_id = await finetuning_service.upload_training_file(Path(train_file))

        validation_file_id = None
        if val_file:
            validation_file_id = await finetuning_service.upload_training_file(Path(val_file))

        # Create fine-tuning job
        job = await finetuning_service.create_fine_tuning_job(
            training_file_id=training_file_id,
            model=request.model,
            validation_file_id=validation_file_id,
            hyperparameters=request.hyperparameters,
            suffix=request.suffix
        )

        return {
            "success": True,
            "job": job.dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create fine-tuning job: {str(e)}"
        )


@router.get("/jobs/list")
async def list_finetuning_jobs(
    limit: int = 10,
    current_user: dict = Depends(require_admin)
):
    """
    List fine-tuning jobs

    Returns list of all fine-tuning jobs.
    Requires admin access.
    """
    if not finetuning_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fine-tuning service not available (OPENAI_API_KEY not set)"
        )

    try:
        jobs = await finetuning_service.list_jobs(limit=limit)

        return {
            "success": True,
            "jobs": [job.dict() for job in jobs],
            "count": len(jobs)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(require_admin)
):
    """
    Get status of fine-tuning job

    Returns current status and details of job.
    Requires admin access.
    """
    if not finetuning_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fine-tuning service not available (OPENAI_API_KEY not set)"
        )

    try:
        job = await finetuning_service.get_job_status(job_id)

        return {
            "success": True,
            "job": job.dict()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.post("/jobs/{job_id}/cancel")
async def cancel_finetuning_job(
    job_id: str,
    current_user: dict = Depends(require_admin)
):
    """
    Cancel a running fine-tuning job

    Stops job execution.
    Requires admin access.
    """
    if not finetuning_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fine-tuning service not available (OPENAI_API_KEY not set)"
        )

    try:
        job = await finetuning_service.cancel_job(job_id)

        return {
            "success": True,
            "message": f"Job {job_id} cancelled",
            "job": job.dict()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/stats")
async def get_finetuning_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get fine-tuning service statistics

    Returns stats about datasets and jobs.
    """
    try:
        stats = finetuning_service.get_stats()

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.get("/health")
async def finetuning_health_check():
    """
    Check fine-tuning service health

    Public endpoint to check service availability.
    """
    health = {
        "finetuning_service": "operational" if finetuning_service.enabled else "disabled",
        "openai_api_available": finetuning_service.enabled,
        "stats": finetuning_service.get_stats()
    }

    return health
