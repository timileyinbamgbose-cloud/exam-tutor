"""
Fine-Tuning Service
Manages model fine-tuning on OpenAI platform
"""
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime
from pathlib import Path
import asyncio

from openai import OpenAI, AsyncOpenAI
from pydantic import BaseModel


class FineTuningExample(BaseModel):
    """Single training example for fine-tuning"""
    messages: List[Dict[str, str]]


class FineTuningDataset(BaseModel):
    """Complete fine-tuning dataset"""
    examples: List[FineTuningExample]
    validation_split: float = 0.1


class FineTuningJob(BaseModel):
    """Fine-tuning job details"""
    job_id: str
    model: str
    status: str
    created_at: datetime
    finished_at: Optional[datetime] = None
    fine_tuned_model: Optional[str] = None
    training_file: str
    validation_file: Optional[str] = None
    hyperparameters: Dict[str, Any] = {}
    result_files: List[str] = []
    trained_tokens: Optional[int] = None
    error: Optional[str] = None


class FineTuningService:
    """
    Service for fine-tuning OpenAI models on curriculum data
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize fine-tuning service

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            print("⚠️  OPENAI_API_KEY not set - fine-tuning disabled")
            self.client = None
            self.async_client = None
            self.enabled = False
        else:
            self.client = OpenAI(api_key=self.api_key)
            self.async_client = AsyncOpenAI(api_key=self.api_key)
            self.enabled = True

        # Storage paths
        self.data_dir = Path("data/finetuning")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.datasets_dir = self.data_dir / "datasets"
        self.datasets_dir.mkdir(exist_ok=True)

        self.jobs_dir = self.data_dir / "jobs"
        self.jobs_dir.mkdir(exist_ok=True)

    def prepare_training_data(
        self,
        questions_and_answers: List[Dict[str, str]],
        system_prompt: str = "You are an expert AI tutor for Nigerian secondary school students preparing for WAEC and JAMB examinations.",
        format_for: str = "chat"
    ) -> FineTuningDataset:
        """
        Prepare training data in OpenAI fine-tuning format

        Args:
            questions_and_answers: List of dicts with 'question', 'answer', 'subject', 'class_level'
            system_prompt: System prompt for the model
            format_for: 'chat' or 'completion'

        Returns:
            FineTuningDataset with formatted examples
        """
        examples = []

        for qa in questions_and_answers:
            question = qa.get("question", "")
            answer = qa.get("answer", "")
            subject = qa.get("subject", "")
            class_level = qa.get("class_level", "")

            if not question or not answer:
                continue

            # Format as chat messages
            if format_for == "chat":
                # Build context-aware user message
                user_message = question
                if subject or class_level:
                    context_parts = []
                    if subject:
                        context_parts.append(f"Subject: {subject}")
                    if class_level:
                        context_parts.append(f"Class: {class_level}")
                    context = ", ".join(context_parts)
                    user_message = f"[{context}] {question}"

                example = FineTuningExample(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": answer}
                    ]
                )
                examples.append(example)

        return FineTuningDataset(examples=examples)

    def save_dataset(
        self,
        dataset: FineTuningDataset,
        name: str,
        split: bool = True
    ) -> Dict[str, Path]:
        """
        Save dataset to JSONL format

        Args:
            dataset: FineTuningDataset to save
            name: Dataset name
            split: Whether to split into train/validation

        Returns:
            Dict with paths to saved files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{name}_{timestamp}"

        # Split dataset if requested
        if split and dataset.validation_split > 0:
            split_idx = int(len(dataset.examples) * (1 - dataset.validation_split))
            train_examples = dataset.examples[:split_idx]
            val_examples = dataset.examples[split_idx:]
        else:
            train_examples = dataset.examples
            val_examples = []

        # Save training data
        train_path = self.datasets_dir / f"{base_name}_train.jsonl"
        with open(train_path, "w") as f:
            for example in train_examples:
                f.write(json.dumps(example.dict()) + "\n")

        result = {"train": train_path}

        # Save validation data if split
        if val_examples:
            val_path = self.datasets_dir / f"{base_name}_val.jsonl"
            with open(val_path, "w") as f:
                for example in val_examples:
                    f.write(json.dumps(example.dict()) + "\n")
            result["validation"] = val_path

        print(f"✅ Saved dataset: {len(train_examples)} train, {len(val_examples)} validation examples")

        return result

    async def upload_training_file(self, file_path: Path) -> str:
        """
        Upload training file to OpenAI

        Args:
            file_path: Path to JSONL file

        Returns:
            File ID
        """
        if not self.enabled:
            raise ValueError("Fine-tuning not enabled (no API key)")

        with open(file_path, "rb") as f:
            response = await self.async_client.files.create(
                file=f,
                purpose="fine-tune"
            )

        print(f"✅ Uploaded file: {response.id}")
        return response.id

    async def create_fine_tuning_job(
        self,
        training_file_id: str,
        model: str = "gpt-4o-mini-2024-07-18",
        validation_file_id: Optional[str] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        suffix: Optional[str] = None
    ) -> FineTuningJob:
        """
        Create a fine-tuning job

        Args:
            training_file_id: ID of uploaded training file
            model: Base model to fine-tune
            validation_file_id: Optional validation file ID
            hyperparameters: Training hyperparameters (epochs, batch_size, learning_rate_multiplier)
            suffix: Custom suffix for fine-tuned model name

        Returns:
            FineTuningJob with job details
        """
        if not self.enabled:
            raise ValueError("Fine-tuning not enabled (no API key)")

        # Default hyperparameters
        if hyperparameters is None:
            hyperparameters = {
                "n_epochs": 3,
                "batch_size": "auto",
                "learning_rate_multiplier": "auto"
            }

        # Create job
        job_params = {
            "training_file": training_file_id,
            "model": model,
            "hyperparameters": hyperparameters
        }

        if validation_file_id:
            job_params["validation_file"] = validation_file_id

        if suffix:
            job_params["suffix"] = suffix

        response = await self.async_client.fine_tuning.jobs.create(**job_params)

        # Convert to our model
        job = FineTuningJob(
            job_id=response.id,
            model=response.model,
            status=response.status,
            created_at=datetime.fromtimestamp(response.created_at),
            training_file=response.training_file,
            validation_file=response.validation_file,
            hyperparameters=response.hyperparameters.dict() if response.hyperparameters else {},
            fine_tuned_model=response.fine_tuned_model
        )

        # Save job details
        self._save_job(job)

        print(f"✅ Created fine-tuning job: {job.job_id}")
        return job

    async def get_job_status(self, job_id: str) -> FineTuningJob:
        """
        Get status of fine-tuning job

        Args:
            job_id: Job ID

        Returns:
            Updated FineTuningJob
        """
        if not self.enabled:
            raise ValueError("Fine-tuning not enabled (no API key)")

        response = await self.async_client.fine_tuning.jobs.retrieve(job_id)

        job = FineTuningJob(
            job_id=response.id,
            model=response.model,
            status=response.status,
            created_at=datetime.fromtimestamp(response.created_at),
            finished_at=datetime.fromtimestamp(response.finished_at) if response.finished_at else None,
            training_file=response.training_file,
            validation_file=response.validation_file,
            hyperparameters=response.hyperparameters.dict() if response.hyperparameters else {},
            fine_tuned_model=response.fine_tuned_model,
            result_files=response.result_files or [],
            trained_tokens=response.trained_tokens,
            error=response.error.message if response.error else None
        )

        # Save updated job details
        self._save_job(job)

        return job

    async def list_jobs(self, limit: int = 10) -> List[FineTuningJob]:
        """
        List fine-tuning jobs

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of FineTuningJob objects
        """
        if not self.enabled:
            raise ValueError("Fine-tuning not enabled (no API key)")

        response = await self.async_client.fine_tuning.jobs.list(limit=limit)

        jobs = []
        for job_data in response.data:
            job = FineTuningJob(
                job_id=job_data.id,
                model=job_data.model,
                status=job_data.status,
                created_at=datetime.fromtimestamp(job_data.created_at),
                finished_at=datetime.fromtimestamp(job_data.finished_at) if job_data.finished_at else None,
                training_file=job_data.training_file,
                validation_file=job_data.validation_file,
                hyperparameters=job_data.hyperparameters.dict() if job_data.hyperparameters else {},
                fine_tuned_model=job_data.fine_tuned_model,
                result_files=job_data.result_files or [],
                trained_tokens=job_data.trained_tokens
            )
            jobs.append(job)

        return jobs

    async def cancel_job(self, job_id: str) -> FineTuningJob:
        """
        Cancel a running fine-tuning job

        Args:
            job_id: Job ID

        Returns:
            Updated FineTuningJob
        """
        if not self.enabled:
            raise ValueError("Fine-tuning not enabled (no API key)")

        response = await self.async_client.fine_tuning.jobs.cancel(job_id)

        job = FineTuningJob(
            job_id=response.id,
            model=response.model,
            status=response.status,
            created_at=datetime.fromtimestamp(response.created_at),
            training_file=response.training_file,
            fine_tuned_model=response.fine_tuned_model
        )

        self._save_job(job)

        print(f"✅ Cancelled job: {job_id}")
        return job

    def _save_job(self, job: FineTuningJob):
        """Save job details to disk"""
        job_path = self.jobs_dir / f"{job.job_id}.json"
        with open(job_path, "w") as f:
            json.dump(job.dict(), f, indent=2, default=str)

    def load_job(self, job_id: str) -> Optional[FineTuningJob]:
        """Load job details from disk"""
        job_path = self.jobs_dir / f"{job_id}.json"
        if not job_path.exists():
            return None

        with open(job_path, "r") as f:
            data = json.load(f)

        return FineTuningJob(**data)

    async def wait_for_completion(
        self,
        job_id: str,
        check_interval: int = 60,
        timeout: int = 7200
    ) -> FineTuningJob:
        """
        Wait for fine-tuning job to complete

        Args:
            job_id: Job ID
            check_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Completed FineTuningJob
        """
        if not self.enabled:
            raise ValueError("Fine-tuning not enabled (no API key)")

        start_time = datetime.now()

        while True:
            job = await self.get_job_status(job_id)

            if job.status in ["succeeded", "failed", "cancelled"]:
                return job

            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                raise TimeoutError(f"Fine-tuning job {job_id} timed out after {timeout}s")

            print(f"⏳ Job {job_id} status: {job.status}, waiting {check_interval}s...")
            await asyncio.sleep(check_interval)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get fine-tuning service statistics

        Returns:
            Dict with stats
        """
        # Count datasets
        dataset_files = list(self.datasets_dir.glob("*.jsonl"))

        # Count jobs
        job_files = list(self.jobs_dir.glob("*.json"))

        return {
            "enabled": self.enabled,
            "datasets_created": len(dataset_files),
            "jobs_created": len(job_files),
            "data_directory": str(self.data_dir)
        }


# Global instance
finetuning_service = FineTuningService()
