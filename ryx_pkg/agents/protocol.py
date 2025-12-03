"""
Ryx AI - Agent Communication Protocol

Defines the message format and protocol for agent-to-agent communication.
Inspired by Claude Code's structured agent communication patterns.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import uuid


class MessageType(Enum):
    """Types of messages agents can exchange"""
    # Task lifecycle
    TASK_ASSIGN = "task_assign"         # Supervisor → Operator
    TASK_ACCEPT = "task_accept"         # Operator → Supervisor
    TASK_REJECT = "task_reject"         # Operator → Supervisor (can't handle)
    TASK_COMPLETE = "task_complete"     # Operator → Supervisor
    TASK_FAILED = "task_failed"         # Operator → Supervisor
    
    # Progress updates
    PROGRESS = "progress"               # Operator → Supervisor
    STATUS_REQUEST = "status_request"   # Supervisor → Operator
    STATUS_RESPONSE = "status_response" # Operator → Supervisor
    
    # Resource coordination
    RESOURCE_REQUEST = "resource_request"   # Any → Orchestrator
    RESOURCE_GRANTED = "resource_granted"   # Orchestrator → Any
    RESOURCE_DENIED = "resource_denied"     # Orchestrator → Any
    
    # Tool execution
    TOOL_REQUEST = "tool_request"       # Operator → Tool Layer
    TOOL_RESULT = "tool_result"         # Tool Layer → Operator
    
    # Errors and recovery
    ERROR = "error"                     # Any → Any
    RESCUE_REQUEST = "rescue_request"   # Operator → Supervisor
    RESCUE_RESPONSE = "rescue_response" # Supervisor → Operator
    
    # Council coordination
    COUNCIL_VOTE_REQUEST = "council_vote_request"
    COUNCIL_VOTE_RESPONSE = "council_vote_response"
    COUNCIL_CONSENSUS = "council_consensus"


@dataclass
class AgentMessage:
    """
    Message passed between agents.
    
    Immutable message format for reliable communication.
    """
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: MessageType = MessageType.TASK_ASSIGN
    
    # Routing
    sender: str = "unknown"
    receiver: str = "unknown"
    
    # Content
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: Optional[str] = None  # Links related messages
    priority: int = 5  # 1=highest, 10=lowest
    
    # Tracking
    attempts: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "priority": self.priority,
            "attempts": self.attempts,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Deserialize from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            type=MessageType(data.get("type", "task_assign")),
            sender=data.get("sender", "unknown"),
            receiver=data.get("receiver", "unknown"),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            correlation_id=data.get("correlation_id"),
            priority=data.get("priority", 5),
            attempts=data.get("attempts", 0),
        )
    
    def create_response(
        self, 
        type: MessageType, 
        payload: Dict[str, Any]
    ) -> 'AgentMessage':
        """Create a response message to this message"""
        return AgentMessage(
            type=type,
            sender=self.receiver,
            receiver=self.sender,
            payload=payload,
            correlation_id=self.id,
        )


class AgentProtocol:
    """
    Protocol handler for agent communication.
    
    Manages message routing, delivery, and acknowledgment.
    """
    
    def __init__(self):
        self._handlers: Dict[MessageType, List[callable]] = {}
        self._message_log: List[AgentMessage] = []
        self._pending: Dict[str, AgentMessage] = {}  # Awaiting response
    
    def register_handler(
        self, 
        msg_type: MessageType, 
        handler: callable
    ) -> None:
        """Register a handler for a message type"""
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)
    
    def send(self, message: AgentMessage) -> bool:
        """
        Send a message to registered handlers.
        
        Returns True if at least one handler processed it.
        """
        self._message_log.append(message)
        
        handlers = self._handlers.get(message.type, [])
        if not handlers:
            return False
        
        success = False
        for handler in handlers:
            try:
                handler(message)
                success = True
            except Exception as e:
                # Log but don't fail
                pass
        
        return success
    
    def send_and_wait(
        self, 
        message: AgentMessage, 
        timeout_ms: int = 30000
    ) -> Optional[AgentMessage]:
        """
        Send message and wait for response.
        
        This is a simplified sync version. In production,
        would use async/await or callbacks.
        """
        self._pending[message.id] = message
        self.send(message)
        
        # In real impl, would wait for response
        # For now, return None (caller should poll)
        return None
    
    def handle_response(self, response: AgentMessage) -> bool:
        """Handle a response to a pending message"""
        if response.correlation_id in self._pending:
            del self._pending[response.correlation_id]
            return True
        return False
    
    def get_pending(self) -> List[AgentMessage]:
        """Get all pending messages awaiting response"""
        return list(self._pending.values())
    
    def get_message_log(
        self, 
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        msg_type: Optional[MessageType] = None,
        limit: int = 100
    ) -> List[AgentMessage]:
        """Get filtered message log"""
        messages = self._message_log
        
        if sender:
            messages = [m for m in messages if m.sender == sender]
        if receiver:
            messages = [m for m in messages if m.receiver == receiver]
        if msg_type:
            messages = [m for m in messages if m.type == msg_type]
        
        return messages[-limit:]


# Message factory functions for common patterns
def create_task_assignment(
    supervisor: str,
    operator: str,
    task: str,
    context: Dict[str, Any],
    priority: int = 5
) -> AgentMessage:
    """Create a task assignment message"""
    return AgentMessage(
        type=MessageType.TASK_ASSIGN,
        sender=supervisor,
        receiver=operator,
        payload={
            "task": task,
            "context": context,
        },
        priority=priority,
    )


def create_task_result(
    operator: str,
    supervisor: str,
    success: bool,
    result: Any,
    correlation_id: str,
    errors: Optional[List[str]] = None
) -> AgentMessage:
    """Create a task completion message"""
    msg_type = MessageType.TASK_COMPLETE if success else MessageType.TASK_FAILED
    return AgentMessage(
        type=msg_type,
        sender=operator,
        receiver=supervisor,
        payload={
            "success": success,
            "result": result,
            "errors": errors or [],
        },
        correlation_id=correlation_id,
    )


def create_progress_update(
    operator: str,
    supervisor: str,
    step: int,
    total_steps: int,
    status: str,
    details: Optional[str] = None
) -> AgentMessage:
    """Create a progress update message"""
    return AgentMessage(
        type=MessageType.PROGRESS,
        sender=operator,
        receiver=supervisor,
        payload={
            "step": step,
            "total_steps": total_steps,
            "progress_pct": int((step / total_steps) * 100) if total_steps > 0 else 0,
            "status": status,
            "details": details,
        },
        priority=7,  # Lower priority than task messages
    )


def create_rescue_request(
    operator: str,
    supervisor: str,
    task_id: str,
    errors: List[str],
    attempts: int
) -> AgentMessage:
    """Create a rescue request when operator fails repeatedly"""
    return AgentMessage(
        type=MessageType.RESCUE_REQUEST,
        sender=operator,
        receiver=supervisor,
        payload={
            "task_id": task_id,
            "errors": errors,
            "attempts": attempts,
        },
        priority=2,  # High priority
    )
