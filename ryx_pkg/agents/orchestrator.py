"""
Ryx AI - Agent Orchestrator

Central coordinator for the multi-agent system.
Manages Supervisor-Operator hierarchy and task distribution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import asyncio
import logging

from .protocol import (
    AgentMessage, MessageType, AgentProtocol,
    create_task_assignment, create_progress_update
)

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Roles agents can have in the system"""
    SUPERVISOR = "supervisor"      # Strategic planning, task decomposition
    OPERATOR = "operator"          # Task execution
    SPECIALIST = "specialist"      # Domain-specific (code, web, file)
    VERIFIER = "verifier"         # Verification and testing
    COUNCIL_MEMBER = "council"    # Multi-model consensus


@dataclass
class AgentInfo:
    """Information about a registered agent"""
    id: str
    role: AgentRole
    model: str
    capabilities: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 1
    current_tasks: int = 0
    total_completed: int = 0
    total_failed: int = 0
    is_available: bool = True
    last_heartbeat: Optional[datetime] = None


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""
    # Supervisor settings
    supervisor_model: str = "qwen2.5-coder:14b"
    supervisor_timeout: int = 60
    
    # Operator settings
    default_operator_model: str = "qwen2.5-coder:7b"
    operator_timeout: int = 30
    
    # Task settings
    max_parallel_tasks: int = 3
    max_retries_per_task: int = 3
    rescue_on_failure: bool = True
    
    # Model settings
    code_model: str = "qwen2.5-coder:14b"
    fast_model: str = "qwen2.5:3b"
    reason_model: str = "deepseek-r1:14b"


class AgentOrchestrator:
    """
    Central orchestrator for the multi-agent system.
    
    Responsibilities:
    1. Agent lifecycle management (register, unregister, health check)
    2. Task routing and load balancing
    3. Supervisor-Operator coordination
    4. Failure recovery and escalation
    5. Resource management
    
    Architecture:
    ```
    User Request
         │
         ▼
    ┌─────────────────┐
    │   Orchestrator  │ ◄── Central control
    └────────┬────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
    ┌──────────┐  ┌──────────┐
    │Supervisor│  │ Council  │ ◄── Strategic layer
    └────┬─────┘  └──────────┘
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
    ┌────┐ ┌────┐  ┌────┐  ┌────┐
    │Op1 │ │Op2 │  │Op3 │  │Op4 │ ◄── Execution layer
    └────┘ └────┘  └────┘  └────┘
    (code) (file)  (web)  (shell)
    ```
    """
    
    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        ollama_client = None
    ):
        self.config = config or OrchestratorConfig()
        self.ollama = ollama_client
        
        self.protocol = AgentProtocol()
        self._agents: Dict[str, AgentInfo] = {}
        self._task_queue: List[AgentMessage] = []
        self._active_tasks: Dict[str, AgentMessage] = {}
        self._task_results: Dict[str, Any] = {}
        
        # Callbacks
        self._on_progress: Optional[Callable] = None
        self._on_complete: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        
        # Register message handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Register protocol handlers"""
        self.protocol.register_handler(
            MessageType.TASK_COMPLETE, 
            self._handle_task_complete
        )
        self.protocol.register_handler(
            MessageType.TASK_FAILED, 
            self._handle_task_failed
        )
        self.protocol.register_handler(
            MessageType.PROGRESS, 
            self._handle_progress
        )
        self.protocol.register_handler(
            MessageType.RESCUE_REQUEST, 
            self._handle_rescue_request
        )
    
    # ─────────────────────────────────────────────────────────────
    # Agent Management
    # ─────────────────────────────────────────────────────────────
    
    def register_agent(
        self,
        agent_id: str,
        role: AgentRole,
        model: str,
        capabilities: Optional[List[str]] = None
    ) -> bool:
        """Register an agent with the orchestrator"""
        if agent_id in self._agents:
            logger.warning(f"Agent {agent_id} already registered")
            return False
        
        self._agents[agent_id] = AgentInfo(
            id=agent_id,
            role=role,
            model=model,
            capabilities=capabilities or [],
            last_heartbeat=datetime.now()
        )
        
        logger.info(f"Registered agent: {agent_id} ({role.value})")
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        if agent_id not in self._agents:
            return False
        
        del self._agents[agent_id]
        logger.info(f"Unregistered agent: {agent_id}")
        return True
    
    def get_available_agents(
        self, 
        role: Optional[AgentRole] = None,
        capability: Optional[str] = None
    ) -> List[AgentInfo]:
        """Get available agents, optionally filtered"""
        agents = [a for a in self._agents.values() if a.is_available]
        
        if role:
            agents = [a for a in agents if a.role == role]
        
        if capability:
            agents = [a for a in agents if capability in a.capabilities]
        
        return agents
    
    def get_best_operator(
        self,
        task_type: str,
        capabilities_needed: Optional[List[str]] = None
    ) -> Optional[AgentInfo]:
        """
        Find the best available operator for a task.
        
        Selection criteria:
        1. Has required capabilities
        2. Not at max concurrent tasks
        3. Best success rate
        """
        operators = self.get_available_agents(role=AgentRole.OPERATOR)
        
        if not operators:
            # Fall back to specialists
            operators = self.get_available_agents(role=AgentRole.SPECIALIST)
        
        if capabilities_needed:
            operators = [
                o for o in operators 
                if all(c in o.capabilities for c in capabilities_needed)
            ]
        
        if not operators:
            return None
        
        # Sort by: 1) current load, 2) success rate
        def score(agent: AgentInfo) -> float:
            load_factor = 1 - (agent.current_tasks / max(agent.max_concurrent_tasks, 1))
            total = agent.total_completed + agent.total_failed
            success_rate = agent.total_completed / total if total > 0 else 0.5
            return load_factor * 0.6 + success_rate * 0.4
        
        operators.sort(key=score, reverse=True)
        return operators[0]
    
    # ─────────────────────────────────────────────────────────────
    # Task Execution
    # ─────────────────────────────────────────────────────────────
    
    def submit_task(
        self,
        task: str,
        context: Dict[str, Any],
        priority: int = 5,
        task_type: Optional[str] = None
    ) -> str:
        """
        Submit a task for execution.
        
        Returns task_id for tracking.
        """
        # Create task message
        supervisor = self._get_supervisor()
        if not supervisor:
            raise RuntimeError("No supervisor registered")
        
        msg = create_task_assignment(
            supervisor="orchestrator",
            operator=supervisor.id,
            task=task,
            context=context,
            priority=priority
        )
        
        msg.payload["task_type"] = task_type
        
        # Queue or execute immediately
        if len(self._active_tasks) >= self.config.max_parallel_tasks:
            self._task_queue.append(msg)
            logger.info(f"Task {msg.id} queued (position {len(self._task_queue)})")
        else:
            self._dispatch_task(msg)
        
        return msg.id
    
    def _dispatch_task(self, msg: AgentMessage):
        """Dispatch a task to appropriate agent"""
        self._active_tasks[msg.id] = msg
        self.protocol.send(msg)
        logger.info(f"Dispatched task {msg.id} to {msg.receiver}")
    
    def _get_supervisor(self) -> Optional[AgentInfo]:
        """Get the supervisor agent"""
        supervisors = self.get_available_agents(role=AgentRole.SUPERVISOR)
        return supervisors[0] if supervisors else None
    
    def execute_with_supervisor(
        self,
        task: str,
        context: Dict[str, Any],
        on_progress: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute a task using the full Supervisor-Operator pattern.
        
        Flow:
        1. Supervisor analyzes task and creates plan
        2. Orchestrator selects best operator
        3. Operator executes with progress updates
        4. On failure: retry or escalate to supervisor
        5. Return final result
        """
        self._on_progress = on_progress
        
        # Phase 1: Planning (Supervisor)
        plan = self._call_supervisor_plan(task, context)
        if not plan:
            return {"success": False, "error": "Failed to create plan"}
        
        # Phase 2: Execution (Operators)
        results = []
        for step in plan.get("steps", []):
            operator = self.get_best_operator(
                task_type=step.get("type", "general"),
                capabilities_needed=step.get("capabilities")
            )
            
            if not operator:
                # No operator available, try supervisor direct
                result = self._supervisor_execute_step(step, context)
            else:
                result = self._operator_execute_step(
                    operator, step, context
                )
            
            results.append(result)
            
            # Report progress
            if self._on_progress:
                progress = create_progress_update(
                    operator=operator.id if operator else "supervisor",
                    supervisor="orchestrator",
                    step=len(results),
                    total_steps=len(plan.get("steps", [])),
                    status="completed" if result.get("success") else "failed"
                )
                self._on_progress(progress)
            
            # Stop on critical failure
            if not result.get("success") and step.get("critical", False):
                break
        
        # Phase 3: Compile results
        success = all(r.get("success", False) for r in results)
        
        return {
            "success": success,
            "plan": plan,
            "results": results,
            "completed_steps": len([r for r in results if r.get("success")]),
            "total_steps": len(plan.get("steps", [])),
        }
    
    def _call_supervisor_plan(
        self, 
        task: str, 
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Call supervisor to create execution plan"""
        # This would call the actual SupervisorAgent
        # For now, return a simple plan structure
        return {
            "understanding": task,
            "steps": [
                {
                    "step": 1,
                    "type": "analyze",
                    "action": "understand_task",
                    "description": f"Analyze: {task[:50]}..."
                }
            ]
        }
    
    def _operator_execute_step(
        self,
        operator: AgentInfo,
        step: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a step using an operator"""
        operator.current_tasks += 1
        
        try:
            # Would call actual operator here
            result = {
                "success": True,
                "step": step.get("step"),
                "output": f"Executed: {step.get('action', 'unknown')}"
            }
            operator.total_completed += 1
            return result
            
        except Exception as e:
            operator.total_failed += 1
            return {
                "success": False,
                "step": step.get("step"),
                "error": str(e)
            }
        finally:
            operator.current_tasks -= 1
    
    def _supervisor_execute_step(
        self,
        step: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Supervisor directly executes a step (fallback)"""
        return {
            "success": True,
            "step": step.get("step"),
            "output": f"Supervisor executed: {step.get('action', 'unknown')}",
            "fallback": True
        }
    
    # ─────────────────────────────────────────────────────────────
    # Message Handlers
    # ─────────────────────────────────────────────────────────────
    
    def _handle_task_complete(self, msg: AgentMessage):
        """Handle task completion"""
        task_id = msg.correlation_id
        if task_id in self._active_tasks:
            del self._active_tasks[task_id]
            self._task_results[task_id] = msg.payload
            
            # Update agent stats
            agent = self._agents.get(msg.sender)
            if agent:
                agent.total_completed += 1
                agent.current_tasks = max(0, agent.current_tasks - 1)
            
            # Process queue
            self._process_queue()
            
            # Callback
            if self._on_complete:
                self._on_complete(task_id, msg.payload)
    
    def _handle_task_failed(self, msg: AgentMessage):
        """Handle task failure"""
        task_id = msg.correlation_id
        task = self._active_tasks.get(task_id)
        
        if not task:
            return
        
        # Update agent stats
        agent = self._agents.get(msg.sender)
        if agent:
            agent.total_failed += 1
            agent.current_tasks = max(0, agent.current_tasks - 1)
        
        # Retry or escalate
        if task.attempts < task.max_retries:
            task.attempts += 1
            self._dispatch_task(task)
            logger.info(f"Retrying task {task_id} (attempt {task.attempts})")
        elif self.config.rescue_on_failure:
            self._escalate_to_supervisor(task, msg.payload.get("errors", []))
        else:
            del self._active_tasks[task_id]
            self._task_results[task_id] = {"success": False, **msg.payload}
            
            if self._on_error:
                self._on_error(task_id, msg.payload)
    
    def _handle_progress(self, msg: AgentMessage):
        """Handle progress update"""
        if self._on_progress:
            self._on_progress(msg)
    
    def _handle_rescue_request(self, msg: AgentMessage):
        """Handle rescue request from operator"""
        task_id = msg.payload.get("task_id")
        task = self._active_tasks.get(task_id)
        
        if task:
            self._escalate_to_supervisor(
                task, 
                msg.payload.get("errors", [])
            )
    
    def _escalate_to_supervisor(
        self, 
        task: AgentMessage, 
        errors: List[str]
    ):
        """Escalate failed task to supervisor"""
        supervisor = self._get_supervisor()
        if not supervisor:
            logger.error(f"No supervisor for escalation of task {task.id}")
            return
        
        rescue_msg = AgentMessage(
            type=MessageType.RESCUE_REQUEST,
            sender="orchestrator",
            receiver=supervisor.id,
            payload={
                "original_task": task.payload,
                "errors": errors,
                "attempts": task.attempts,
            },
            correlation_id=task.id,
            priority=2
        )
        
        self.protocol.send(rescue_msg)
        logger.info(f"Escalated task {task.id} to supervisor")
    
    def _process_queue(self):
        """Process queued tasks"""
        while (
            self._task_queue and 
            len(self._active_tasks) < self.config.max_parallel_tasks
        ):
            task = self._task_queue.pop(0)
            self._dispatch_task(task)
    
    # ─────────────────────────────────────────────────────────────
    # Status & Monitoring
    # ─────────────────────────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "agents": {
                "total": len(self._agents),
                "available": len([a for a in self._agents.values() if a.is_available]),
                "by_role": {
                    role.value: len([
                        a for a in self._agents.values() 
                        if a.role == role
                    ])
                    for role in AgentRole
                }
            },
            "tasks": {
                "active": len(self._active_tasks),
                "queued": len(self._task_queue),
                "completed": len(self._task_results),
            },
            "config": {
                "max_parallel": self.config.max_parallel_tasks,
                "max_retries": self.config.max_retries_per_task,
            }
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        if task_id in self._task_results:
            return {"status": "completed", **self._task_results[task_id]}
        
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            return {
                "status": "active",
                "attempts": task.attempts,
                "receiver": task.receiver,
            }
        
        for i, task in enumerate(self._task_queue):
            if task.id == task_id:
                return {
                    "status": "queued",
                    "position": i + 1,
                }
        
        return None
    
    def set_callbacks(
        self,
        on_progress: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        """Set callback functions"""
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error
