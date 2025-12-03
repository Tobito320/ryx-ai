"""
Ryx AI - Model Performance Metrics

Tracks model performance over time:
- Response quality (rated by supervisor)
- Latency
- Error rate
- Task completion rate

Models that consistently underperform get "fired" (deprioritized).
Best performing models get promoted (used more often).
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ModelStats:
    """Statistics for a single model"""
    model_name: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_latency_ms: float = 0.0
    quality_scores: List[float] = field(default_factory=list)
    last_used: str = ""
    fired: bool = False
    promoted: bool = False
    
    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks
    
    @property
    def avg_latency_ms(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.total_latency_ms / self.total_tasks
    
    @property
    def avg_quality(self) -> float:
        if not self.quality_scores:
            return 0.0
        return sum(self.quality_scores[-20:]) / len(self.quality_scores[-20:])  # Last 20
    
    @property
    def overall_score(self) -> float:
        """Combined score: 60% quality, 30% success rate, 10% speed"""
        quality = self.avg_quality / 10  # Normalize to 0-1
        success = self.success_rate
        # Faster is better, cap at 5000ms
        speed = max(0, 1 - (self.avg_latency_ms / 5000))
        return (quality * 0.6) + (success * 0.3) + (speed * 0.1)


class ModelMetrics:
    """
    Tracks and manages model performance metrics.
    
    Used by the supervisor to:
    - Select best models for tasks
    - Fire underperforming models
    - Promote high performers
    """
    
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            from core.paths import get_data_dir
            data_dir = get_data_dir()
        
        self.data_dir = data_dir
        self.metrics_file = data_dir / "model_metrics.json"
        self.stats: Dict[str, ModelStats] = {}
        self._load()
    
    def _load(self):
        """Load metrics from disk"""
        if self.metrics_file.exists():
            try:
                data = json.loads(self.metrics_file.read_text())
                for name, stats in data.items():
                    self.stats[name] = ModelStats(
                        model_name=name,
                        total_tasks=stats.get("total_tasks", 0),
                        successful_tasks=stats.get("successful_tasks", 0),
                        failed_tasks=stats.get("failed_tasks", 0),
                        total_latency_ms=stats.get("total_latency_ms", 0.0),
                        quality_scores=stats.get("quality_scores", []),
                        last_used=stats.get("last_used", ""),
                        fired=stats.get("fired", False),
                        promoted=stats.get("promoted", False)
                    )
            except Exception as e:
                logger.error(f"Failed to load metrics: {e}")
    
    def _save(self):
        """Save metrics to disk"""
        try:
            data = {}
            for name, stats in self.stats.items():
                data[name] = {
                    "model_name": stats.model_name,
                    "total_tasks": stats.total_tasks,
                    "successful_tasks": stats.successful_tasks,
                    "failed_tasks": stats.failed_tasks,
                    "total_latency_ms": stats.total_latency_ms,
                    "quality_scores": stats.quality_scores[-50:],  # Keep last 50
                    "last_used": stats.last_used,
                    "fired": stats.fired,
                    "promoted": stats.promoted
                }
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            self.metrics_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def get_or_create(self, model_name: str) -> ModelStats:
        """Get stats for a model, create if not exists"""
        if model_name not in self.stats:
            self.stats[model_name] = ModelStats(model_name=model_name)
        return self.stats[model_name]
    
    def record_task(
        self,
        model_name: str,
        success: bool,
        latency_ms: float,
        quality_score: float = None
    ):
        """
        Record a completed task.
        
        Args:
            model_name: Name of the model
            success: Whether task succeeded
            latency_ms: Time taken in ms
            quality_score: Optional quality rating (0-10)
        """
        stats = self.get_or_create(model_name)
        stats.total_tasks += 1
        stats.total_latency_ms += latency_ms
        stats.last_used = datetime.now().isoformat()
        
        if success:
            stats.successful_tasks += 1
        else:
            stats.failed_tasks += 1
        
        if quality_score is not None:
            stats.quality_scores.append(quality_score)
        
        # Check if model should be fired
        if stats.total_tasks >= 10:
            if stats.success_rate < 0.5 or stats.avg_quality < 3:
                stats.fired = True
                logger.warning(f"Model {model_name} fired due to poor performance")
        
        # Check if model should be promoted
        if stats.total_tasks >= 20:
            if stats.success_rate > 0.9 and stats.avg_quality > 7:
                stats.promoted = True
                logger.info(f"Model {model_name} promoted for excellent performance")
        
        self._save()
    
    def get_best_models(
        self,
        task_type: str = "general",
        count: int = 3,
        exclude_fired: bool = True
    ) -> List[str]:
        """
        Get the best performing models for a task type.
        
        Args:
            task_type: Type of task (general, search, coding, etc.)
            count: Number of models to return
            exclude_fired: Whether to exclude fired models
            
        Returns:
            List of model names sorted by performance
        """
        candidates = []
        for name, stats in self.stats.items():
            if exclude_fired and stats.fired:
                continue
            candidates.append((name, stats.overall_score))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [name for name, _ in candidates[:count]]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary for display"""
        summary = {
            "total_models": len(self.stats),
            "active_models": len([s for s in self.stats.values() if not s.fired]),
            "fired_models": len([s for s in self.stats.values() if s.fired]),
            "promoted_models": len([s for s in self.stats.values() if s.promoted]),
            "models": {}
        }
        
        for name, stats in self.stats.items():
            summary["models"][name] = {
                "success_rate": f"{stats.success_rate:.1%}",
                "avg_quality": f"{stats.avg_quality:.1f}/10",
                "avg_latency": f"{stats.avg_latency_ms:.0f}ms",
                "tasks": stats.total_tasks,
                "status": "🔥 fired" if stats.fired else ("⭐ promoted" if stats.promoted else "active")
            }
        
        return summary
    
    def reset_model(self, model_name: str):
        """Reset a model's stats (unfire it)"""
        if model_name in self.stats:
            self.stats[model_name].fired = False
            self.stats[model_name].promoted = False
            self._save()
    
    def clear_all(self):
        """Clear all metrics"""
        self.stats = {}
        if self.metrics_file.exists():
            self.metrics_file.unlink()
