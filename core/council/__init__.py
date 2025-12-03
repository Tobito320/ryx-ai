"""
Ryx AI - Council: Multi-Agent Orchestration System

The Council is a supervisor-worker pattern where:
- Supervisor (7B model): Evaluates tasks, assigns workers, aggregates results
- Workers (1.5B-3B models): Execute specific tasks async
- Metrics: Track performance, fire bad models, promote good ones
"""

from .supervisor import Supervisor
from .worker import Worker, WorkerPool
from .metrics import ModelMetrics
from .searxng import SearXNGClient

__all__ = ['Supervisor', 'Worker', 'WorkerPool', 'ModelMetrics', 'SearXNGClient']
