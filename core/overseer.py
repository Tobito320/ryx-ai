"""
Ryx AI - Overseer System

Inspired by: self_improving_coding_agent/oversight/overseer.py

The Overseer monitors running agents and:
1. Detects if an agent is stuck in a loop
2. Detects if an agent is making no progress
3. Can inject notifications to redirect agents
4. Can force-cancel stuck agents
5. Provides dynamic scheduling for next check

This is critical for the RSI loop - we need to detect
when self-improvement attempts are failing and need intervention.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Status of a monitored agent"""
    IDLE = "idle"
    RUNNING = "running"
    STUCK = "stuck"
    LOOPING = "looping"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentState:
    """State of a monitored agent"""
    agent_id: str
    task_description: str
    status: AgentStatus = AgentStatus.IDLE
    started_at: Optional[str] = None
    last_activity: Optional[str] = None
    
    # Progress tracking
    steps_completed: int = 0
    last_output: Optional[str] = None
    output_history: deque = field(default_factory=lambda: deque(maxlen=10))
    
    # Loop detection
    repeated_outputs: int = 0
    
    # Metrics
    tokens_used: int = 0
    elapsed_seconds: float = 0.0
    
    def update_activity(self, output: Optional[str] = None):
        """Update last activity timestamp"""
        self.last_activity = datetime.now().isoformat()
        if output:
            # Check for repeated output (loop detection)
            if self.output_history and output == self.output_history[-1]:
                self.repeated_outputs += 1
            else:
                self.repeated_outputs = 0
            self.output_history.append(output)
            self.last_output = output


@dataclass
class OverseerJudgement:
    """Judgement about an agent's state"""
    agent_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Assessment
    making_progress: bool = True
    is_looping: bool = False
    is_stuck: bool = False
    needs_intervention: bool = False
    
    # Actions
    send_notification: bool = False
    notification_message: Optional[str] = None
    force_cancel: bool = False
    
    # Next check
    next_check_seconds: int = 30
    
    # Reasoning
    reasoning: str = ""


class Overseer:
    """
    Monitors agents and intervenes when necessary.
    
    Usage:
        overseer = Overseer()
        
        # Register an agent
        overseer.register_agent("agent_1", "Fix the bug in utils.py")
        
        # Start monitoring
        await overseer.start_monitoring()
        
        # Update agent state periodically
        overseer.update_agent("agent_1", output="Working on line 42...")
        
        # Get judgement
        judgement = await overseer.judge_agent("agent_1")
        
        # Stop monitoring
        overseer.stop_monitoring()
    """
    
    def __init__(
        self,
        check_interval: int = 30,
        stuck_threshold: int = 120,  # seconds without activity
        loop_threshold: int = 3,      # repeated outputs before loop detected
        llm_client: Any = None,       # For AI-based judgement
    ):
        self.check_interval = check_interval
        self.stuck_threshold = stuck_threshold
        self.loop_threshold = loop_threshold
        self.llm_client = llm_client
        
        self._agents: Dict[str, AgentState] = {}
        self._judgements: Dict[str, OverseerJudgement] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Callbacks
        self._on_stuck: Optional[Callable] = None
        self._on_loop: Optional[Callable] = None
        self._on_intervention: Optional[Callable] = None
    
    def register_agent(
        self,
        agent_id: str,
        task_description: str,
    ) -> AgentState:
        """Register a new agent for monitoring"""
        state = AgentState(
            agent_id=agent_id,
            task_description=task_description,
            status=AgentStatus.RUNNING,
            started_at=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
        )
        self._agents[agent_id] = state
        logger.info(f"Registered agent for monitoring: {agent_id}")
        return state
    
    def unregister_agent(self, agent_id: str):
        """Remove agent from monitoring"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
    
    def update_agent(
        self,
        agent_id: str,
        output: Optional[str] = None,
        steps_completed: Optional[int] = None,
        tokens_used: Optional[int] = None,
        status: Optional[AgentStatus] = None,
    ):
        """Update an agent's state"""
        if agent_id not in self._agents:
            logger.warning(f"Unknown agent: {agent_id}")
            return
        
        state = self._agents[agent_id]
        state.update_activity(output)
        
        if steps_completed is not None:
            state.steps_completed = steps_completed
        if tokens_used is not None:
            state.tokens_used = tokens_used
        if status is not None:
            state.status = status
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get current state of an agent"""
        return self._agents.get(agent_id)
    
    async def judge_agent(self, agent_id: str) -> OverseerJudgement:
        """
        Make a judgement about an agent's current state.
        
        This checks:
        1. Is the agent making progress?
        2. Is the agent stuck in a loop?
        3. Does it need intervention?
        """
        state = self._agents.get(agent_id)
        
        if not state:
            return OverseerJudgement(
                agent_id=agent_id,
                making_progress=False,
                is_stuck=True,
                reasoning="Agent not found"
            )
        
        judgement = OverseerJudgement(agent_id=agent_id)
        
        # Check for stuck (no activity)
        if state.last_activity:
            last_activity = datetime.fromisoformat(state.last_activity)
            elapsed = (datetime.now() - last_activity).total_seconds()
            state.elapsed_seconds = elapsed
            
            if elapsed > self.stuck_threshold:
                judgement.is_stuck = True
                judgement.making_progress = False
                judgement.needs_intervention = True
                judgement.reasoning = f"No activity for {elapsed:.0f} seconds"
        
        # Check for loop (repeated outputs)
        if state.repeated_outputs >= self.loop_threshold:
            judgement.is_looping = True
            judgement.making_progress = False
            judgement.needs_intervention = True
            judgement.reasoning = f"Repeated same output {state.repeated_outputs} times"
        
        # Determine action
        if judgement.is_stuck or judgement.is_looping:
            if state.repeated_outputs >= self.loop_threshold * 2:
                # Severe loop - force cancel
                judgement.force_cancel = True
                judgement.reasoning += " - Force cancelling"
            else:
                # Try notification first
                judgement.send_notification = True
                judgement.notification_message = self._generate_notification(state, judgement)
        
        # Use LLM for smarter judgement if available
        if self.llm_client and judgement.needs_intervention:
            judgement = await self._ai_enhanced_judgement(state, judgement)
        
        # Dynamic next check timing
        if judgement.making_progress:
            judgement.next_check_seconds = self.check_interval
        else:
            judgement.next_check_seconds = self.check_interval // 2
        
        self._judgements[agent_id] = judgement
        return judgement
    
    def _generate_notification(
        self,
        state: AgentState,
        judgement: OverseerJudgement
    ) -> str:
        """Generate a notification message to send to the agent"""
        if judgement.is_looping:
            return (
                "OVERSEER NOTICE: You appear to be in a loop. "
                "Please try a different approach or ask for help."
            )
        elif judgement.is_stuck:
            return (
                "OVERSEER NOTICE: No progress detected for a while. "
                "Please continue with your task or report if you're blocked."
            )
        return "OVERSEER NOTICE: Please check your progress."
    
    async def _ai_enhanced_judgement(
        self,
        state: AgentState,
        judgement: OverseerJudgement
    ) -> OverseerJudgement:
        """Use LLM to make smarter intervention decisions"""
        
        if not self.llm_client:
            return judgement
        
        prompt = f"""Analyze this agent's state and determine if intervention is needed.

Agent ID: {state.agent_id}
Task: {state.task_description}
Status: {state.status.value}
Steps completed: {state.steps_completed}
Time elapsed: {state.elapsed_seconds:.0f} seconds
Repeated outputs: {state.repeated_outputs}

Recent outputs:
{chr(10).join(list(state.output_history)[-3:])}

Current assessment:
- Making progress: {judgement.making_progress}
- Is looping: {judgement.is_looping}
- Is stuck: {judgement.is_stuck}

Should we:
1. Let the agent continue (it might be making progress we can't see)
2. Send a gentle notification to redirect
3. Force cancel and restart

Respond with: CONTINUE, NOTIFY, or CANCEL
And a brief reason.
"""
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                system="You are an agent supervisor. Be conservative about intervention.",
                temperature=0.3,
                max_tokens=100
            )
            
            if response.error:
                return judgement
            
            text = response.response.upper()
            
            if "CANCEL" in text:
                judgement.force_cancel = True
                judgement.send_notification = False
            elif "NOTIFY" in text:
                judgement.send_notification = True
                judgement.force_cancel = False
            else:  # CONTINUE
                judgement.needs_intervention = False
                judgement.send_notification = False
                judgement.force_cancel = False
            
            # Extract reasoning
            lines = response.response.strip().split('\n')
            if len(lines) > 1:
                judgement.reasoning = lines[-1][:200]
                
        except Exception as e:
            logger.error(f"AI judgement failed: {e}")
        
        return judgement
    
    async def start_monitoring(self):
        """Start the monitoring loop"""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("Overseer monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        logger.info("Overseer monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                for agent_id in list(self._agents.keys()):
                    state = self._agents.get(agent_id)
                    if not state or state.status in [
                        AgentStatus.COMPLETED,
                        AgentStatus.FAILED,
                        AgentStatus.CANCELLED
                    ]:
                        continue
                    
                    judgement = await self.judge_agent(agent_id)
                    
                    # Execute callbacks
                    if judgement.is_stuck and self._on_stuck:
                        await self._on_stuck(agent_id, judgement)
                    
                    if judgement.is_looping and self._on_loop:
                        await self._on_loop(agent_id, judgement)
                    
                    if judgement.needs_intervention and self._on_intervention:
                        await self._on_intervention(agent_id, judgement)
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Overseer error: {e}")
                await asyncio.sleep(5)
    
    def on_stuck(self, callback: Callable):
        """Register callback for stuck agents"""
        self._on_stuck = callback
    
    def on_loop(self, callback: Callable):
        """Register callback for looping agents"""
        self._on_loop = callback
    
    def on_intervention(self, callback: Callable):
        """Register callback for any intervention"""
        self._on_intervention = callback
    
    def get_all_judgements(self) -> Dict[str, OverseerJudgement]:
        """Get all current judgements"""
        return self._judgements.copy()
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of all monitored agents"""
        summary = {
            "total_agents": len(self._agents),
            "running": 0,
            "stuck": 0,
            "looping": 0,
            "completed": 0,
            "agents": {}
        }
        
        for agent_id, state in self._agents.items():
            summary["agents"][agent_id] = {
                "status": state.status.value,
                "steps": state.steps_completed,
                "elapsed": state.elapsed_seconds,
            }
            
            if state.status == AgentStatus.RUNNING:
                summary["running"] += 1
            elif state.status == AgentStatus.STUCK:
                summary["stuck"] += 1
            elif state.status == AgentStatus.COMPLETED:
                summary["completed"] += 1
        
        return summary


# Global instance
_overseer: Optional[Overseer] = None


def get_overseer(
    check_interval: int = 30,
    llm_client: Any = None
) -> Overseer:
    """Get or create the global overseer instance"""
    global _overseer
    if _overseer is None:
        _overseer = Overseer(
            check_interval=check_interval,
            llm_client=llm_client
        )
    return _overseer
