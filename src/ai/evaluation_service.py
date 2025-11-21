"""
Model Evaluation & A/B Testing Service
Tracks metrics, runs experiments, and compares models
"""
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import random
import hashlib

from pydantic import BaseModel


class MetricValue(BaseModel):
    """Single metric measurement"""
    name: str
    value: float
    timestamp: datetime = datetime.utcnow()
    metadata: Dict[str, Any] = {}


class ModelEvaluation(BaseModel):
    """Evaluation results for a model"""
    model_id: str
    model_name: str
    evaluated_at: datetime
    metrics: Dict[str, float]
    sample_predictions: List[Dict[str, Any]] = []
    confusion_matrix: Optional[Dict[str, Any]] = None


class ABExperiment(BaseModel):
    """A/B test experiment"""
    experiment_id: str
    name: str
    description: str
    variants: List[str]  # e.g., ["control", "treatment"]
    traffic_split: Dict[str, float]  # e.g., {"control": 0.5, "treatment": 0.5}
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "running"  # running, completed, cancelled
    metrics: Dict[str, Dict[str, List[float]]] = {}  # {variant: {metric: [values]}}
    total_requests: Dict[str, int] = {}  # {variant: count}


class EvaluationService:
    """
    Service for model evaluation, metrics tracking, and A/B testing
    """

    def __init__(self):
        """Initialize evaluation service"""
        self.data_dir = Path("data/evaluation")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_dir = self.data_dir / "metrics"
        self.metrics_dir.mkdir(exist_ok=True)

        self.experiments_dir = self.data_dir / "experiments"
        self.experiments_dir.mkdir(exist_ok=True)

        self.evaluations_dir = self.data_dir / "evaluations"
        self.evaluations_dir.mkdir(exist_ok=True)

        # In-memory storage for active experiments
        self.active_experiments: Dict[str, ABExperiment] = {}
        self._load_active_experiments()

    def _load_active_experiments(self):
        """Load running experiments from disk"""
        for exp_file in self.experiments_dir.glob("*.json"):
            try:
                with open(exp_file, "r") as f:
                    data = json.load(f)
                exp = ABExperiment(**data)
                if exp.status == "running":
                    self.active_experiments[exp.experiment_id] = exp
            except Exception as e:
                print(f"⚠️  Failed to load experiment {exp_file}: {e}")

    def record_metric(
        self,
        model_id: str,
        metric_name: str,
        value: float,
        metadata: Dict[str, Any] = None
    ):
        """
        Record a metric value for a model

        Args:
            model_id: Model identifier
            metric_name: Metric name (e.g., 'accuracy', 'f1_score')
            value: Metric value
            metadata: Additional context
        """
        metric = MetricValue(
            name=metric_name,
            value=value,
            metadata=metadata or {}
        )

        # Save to file
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{model_id}_{metric_name}_{timestamp_str}.json"
        filepath = self.metrics_dir / filename

        with open(filepath, "w") as f:
            json.dump(metric.dict(), f, indent=2, default=str)

    def evaluate_model(
        self,
        model_id: str,
        model_name: str,
        predictions: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]]
    ) -> ModelEvaluation:
        """
        Evaluate model performance

        Args:
            model_id: Model identifier
            model_name: Human-readable model name
            predictions: List of predictions with 'text' and optional 'label'
            ground_truth: List of ground truth with 'text' and 'label'

        Returns:
            ModelEvaluation with calculated metrics
        """
        metrics = {}

        # Calculate accuracy if labels available
        if predictions and ground_truth and len(predictions) == len(ground_truth):
            correct = 0
            total = 0

            for pred, truth in zip(predictions, ground_truth):
                if "label" in pred and "label" in truth:
                    total += 1
                    if pred["label"] == truth["label"]:
                        correct += 1

            if total > 0:
                metrics["accuracy"] = correct / total

        # Calculate semantic similarity if embeddings available
        # (Placeholder - would use embedding service)

        # Response quality metrics
        if predictions:
            avg_length = sum(len(p.get("text", "")) for p in predictions) / len(predictions)
            metrics["avg_response_length"] = avg_length

        # Create evaluation
        evaluation = ModelEvaluation(
            model_id=model_id,
            model_name=model_name,
            evaluated_at=datetime.utcnow(),
            metrics=metrics,
            sample_predictions=predictions[:10]  # Store sample
        )

        # Save evaluation
        self._save_evaluation(evaluation)

        # Record metrics
        for metric_name, value in metrics.items():
            self.record_metric(model_id, metric_name, value)

        return evaluation

    def _save_evaluation(self, evaluation: ModelEvaluation):
        """Save evaluation to disk"""
        timestamp_str = evaluation.evaluated_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{evaluation.model_id}_{timestamp_str}.json"
        filepath = self.evaluations_dir / filename

        with open(filepath, "w") as f:
            json.dump(evaluation.dict(), f, indent=2, default=str)

    def create_ab_experiment(
        self,
        name: str,
        description: str,
        variants: List[str],
        traffic_split: Optional[Dict[str, float]] = None
    ) -> ABExperiment:
        """
        Create A/B test experiment

        Args:
            name: Experiment name
            description: Experiment description
            variants: List of variant names (e.g., ["control", "treatment"])
            traffic_split: Traffic allocation per variant (must sum to 1.0)

        Returns:
            ABExperiment object
        """
        # Generate experiment ID
        experiment_id = hashlib.md5(f"{name}_{datetime.utcnow()}".encode()).hexdigest()[:12]

        # Default equal split
        if traffic_split is None:
            split_value = 1.0 / len(variants)
            traffic_split = {v: split_value for v in variants}

        # Validate traffic split
        if abs(sum(traffic_split.values()) - 1.0) > 0.01:
            raise ValueError("Traffic split must sum to 1.0")

        # Create experiment
        experiment = ABExperiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variants=variants,
            traffic_split=traffic_split,
            start_date=datetime.utcnow(),
            status="running",
            metrics={v: {} for v in variants},
            total_requests={v: 0 for v in variants}
        )

        # Save and activate
        self._save_experiment(experiment)
        self.active_experiments[experiment_id] = experiment

        print(f"✅ Created A/B experiment: {experiment_id} ({name})")
        return experiment

    def assign_variant(self, experiment_id: str, user_id: Optional[str] = None) -> str:
        """
        Assign user to experiment variant

        Args:
            experiment_id: Experiment ID
            user_id: Optional user ID for consistent assignment

        Returns:
            Assigned variant name
        """
        if experiment_id not in self.active_experiments:
            raise ValueError(f"Experiment {experiment_id} not found or not active")

        experiment = self.active_experiments[experiment_id]

        # Consistent assignment based on user_id
        if user_id:
            hash_value = int(hashlib.md5(f"{experiment_id}_{user_id}".encode()).hexdigest(), 16)
            random_value = (hash_value % 10000) / 10000.0
        else:
            random_value = random.random()

        # Assign based on traffic split
        cumulative = 0.0
        for variant, probability in experiment.traffic_split.items():
            cumulative += probability
            if random_value < cumulative:
                return variant

        # Fallback to first variant
        return experiment.variants[0]

    def record_experiment_metric(
        self,
        experiment_id: str,
        variant: str,
        metric_name: str,
        value: float
    ):
        """
        Record metric for experiment variant

        Args:
            experiment_id: Experiment ID
            variant: Variant name
            metric_name: Metric name
            value: Metric value
        """
        if experiment_id not in self.active_experiments:
            raise ValueError(f"Experiment {experiment_id} not found or not active")

        experiment = self.active_experiments[experiment_id]

        if variant not in experiment.variants:
            raise ValueError(f"Variant {variant} not in experiment")

        # Initialize metric list if needed
        if metric_name not in experiment.metrics[variant]:
            experiment.metrics[variant][metric_name] = []

        # Append value
        experiment.metrics[variant][metric_name].append(value)

        # Increment request count
        experiment.total_requests[variant] = experiment.total_requests.get(variant, 0) + 1

        # Save updated experiment
        self._save_experiment(experiment)

    def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get experiment results with statistical analysis

        Args:
            experiment_id: Experiment ID

        Returns:
            Dict with results per variant
        """
        if experiment_id not in self.active_experiments:
            experiment = self._load_experiment(experiment_id)
            if not experiment:
                raise ValueError(f"Experiment {experiment_id} not found")
        else:
            experiment = self.active_experiments[experiment_id]

        results = {
            "experiment_id": experiment_id,
            "name": experiment.name,
            "status": experiment.status,
            "variants": {}
        }

        # Calculate stats for each variant
        for variant in experiment.variants:
            variant_metrics = experiment.metrics.get(variant, {})
            variant_results = {
                "total_requests": experiment.total_requests.get(variant, 0),
                "metrics": {}
            }

            for metric_name, values in variant_metrics.items():
                if values:
                    variant_results["metrics"][metric_name] = {
                        "mean": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values)
                    }

            results["variants"][variant] = variant_results

        return results

    def complete_experiment(self, experiment_id: str) -> ABExperiment:
        """
        Mark experiment as completed

        Args:
            experiment_id: Experiment ID

        Returns:
            Updated experiment
        """
        if experiment_id not in self.active_experiments:
            raise ValueError(f"Experiment {experiment_id} not active")

        experiment = self.active_experiments[experiment_id]
        experiment.status = "completed"
        experiment.end_date = datetime.utcnow()

        self._save_experiment(experiment)
        del self.active_experiments[experiment_id]

        print(f"✅ Completed experiment: {experiment_id}")
        return experiment

    def _save_experiment(self, experiment: ABExperiment):
        """Save experiment to disk"""
        filepath = self.experiments_dir / f"{experiment.experiment_id}.json"

        with open(filepath, "w") as f:
            json.dump(experiment.dict(), f, indent=2, default=str)

    def _load_experiment(self, experiment_id: str) -> Optional[ABExperiment]:
        """Load experiment from disk"""
        filepath = self.experiments_dir / f"{experiment_id}.json"

        if not filepath.exists():
            return None

        with open(filepath, "r") as f:
            data = json.load(f)

        return ABExperiment(**data)

    def list_experiments(self, status: Optional[str] = None) -> List[ABExperiment]:
        """
        List all experiments

        Args:
            status: Filter by status (running, completed, cancelled)

        Returns:
            List of experiments
        """
        experiments = []

        for exp_file in self.experiments_dir.glob("*.json"):
            try:
                with open(exp_file, "r") as f:
                    data = json.load(f)
                exp = ABExperiment(**data)

                if status is None or exp.status == status:
                    experiments.append(exp)
            except Exception as e:
                print(f"⚠️  Failed to load experiment {exp_file}: {e}")

        return experiments

    def get_stats(self) -> Dict[str, Any]:
        """
        Get evaluation service statistics

        Returns:
            Dict with stats
        """
        # Count metrics
        metric_files = list(self.metrics_dir.glob("*.json"))

        # Count evaluations
        evaluation_files = list(self.evaluations_dir.glob("*.json"))

        # Count experiments by status
        all_experiments = self.list_experiments()
        status_counts = defaultdict(int)
        for exp in all_experiments:
            status_counts[exp.status] += 1

        return {
            "total_metrics_recorded": len(metric_files),
            "total_evaluations": len(evaluation_files),
            "total_experiments": len(all_experiments),
            "active_experiments": len(self.active_experiments),
            "experiments_by_status": dict(status_counts)
        }


# Global instance
evaluation_service = EvaluationService()
