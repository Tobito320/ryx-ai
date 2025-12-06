"""
Agent Router - Intelligent routing to specialized agents
Uses lightweight intent classification to route user messages
"""
import re
from typing import Tuple, Optional
import logging

from ai.agents import AgentType, Agent, get_agent

logger = logging.getLogger(__name__)


class AgentRouter:
    """Routes user messages to the appropriate specialized agent"""

    # Intent patterns for routing
    INTENT_PATTERNS = {
        AgentType.DOC_ANALYST: [
            r"analysier.*dokument",
            r"was steht.*brief",
            r"extrahier.*information",
            r"klassifizier.*dokument",
            r"welche.*kategorie",
            r"dokument.*upload",
            r"pdf.*analys",
            r"was.*bedeutet.*brief",
        ],
        AgentType.BOARD_PLANNER: [
            r"erstell.*board",
            r"neues.*board",
            r"organis.*dokument",
            r"wo.*speicher",
            r"board.*für",
            r"ordner.*erstell",
            r"struktur.*voschlag",
            r"wie.*organisier",
        ],
        AgentType.BRIEF_WRITER: [
            r"schreib.*brief",
            r"schreib.*email",
            r"schreib.*antwort",
            r"brief.*an",
            r"email.*an",
            r"antwort.*auf",
            r"generier.*brief",
            r"verfass.*schreiben",
        ],
    }

    # Keywords for quick routing
    KEYWORDS = {
        AgentType.DOC_ANALYST: [
            "dokument", "analysieren", "extrahieren", "klassifizieren",
            "pdf", "brief", "scan", "ocr", "inhalt"
        ],
        AgentType.BOARD_PLANNER: [
            "board", "erstellen", "organisieren", "ordner", "struktur",
            "speichern", "ablegen", "kategorisieren"
        ],
        AgentType.BRIEF_WRITER: [
            "schreiben", "brief", "email", "antwort", "verfassen",
            "generieren", "formulieren", "schreiben"
        ],
    }

    def __init__(self):
        """Initialize router"""
        pass

    def route(self, user_message: str, context: Optional[dict] = None) -> Tuple[AgentType, float]:
        """
        Route user message to appropriate agent

        Args:
            user_message: User's message
            context: Optional context (board_id, document_id, etc.)

        Returns:
            Tuple of (AgentType, confidence_score)
        """
        message_lower = user_message.lower()

        # Context-based routing (highest priority)
        if context:
            if context.get("document_upload"):
                logger.info("Routing to DOC_ANALYST (document upload context)")
                return AgentType.DOC_ANALYST, 1.0

            if context.get("board_creation"):
                logger.info("Routing to BOARD_PLANNER (board creation context)")
                return AgentType.BOARD_PLANNER, 1.0

            if context.get("letter_writing"):
                logger.info("Routing to BRIEF_WRITER (letter writing context)")
                return AgentType.BRIEF_WRITER, 1.0

        # Pattern-based routing
        for agent_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    logger.info(f"Routing to {agent_type.value} (pattern match: {pattern})")
                    return agent_type, 0.9

        # Keyword-based routing (lower priority)
        scores = {}
        for agent_type, keywords in self.KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                scores[agent_type] = score

        if scores:
            best_agent = max(scores.items(), key=lambda x: x[1])
            confidence = min(best_agent[1] / 3.0, 0.8)  # Cap at 0.8 for keyword matching
            logger.info(f"Routing to {best_agent[0].value} (keyword score: {best_agent[1]})")
            return best_agent[0], confidence

        # Default to CHAT agent for general conversation
        logger.info("Routing to CHAT (default)")
        return AgentType.CHAT, 0.5

    def get_agent_for_message(self, user_message: str, context: Optional[dict] = None) -> Tuple[Agent, float]:
        """
        Get the appropriate agent for a message

        Returns:
            Tuple of (Agent, confidence_score)
        """
        agent_type, confidence = self.route(user_message, context)
        agent = get_agent(agent_type)
        return agent, confidence

    def explain_routing(self, user_message: str, context: Optional[dict] = None) -> dict:
        """
        Explain why a particular agent was chosen (for debugging)

        Returns:
            Dict with routing explanation
        """
        agent_type, confidence = self.route(user_message, context)
        agent = get_agent(agent_type)

        return {
            "message": user_message,
            "routed_to": agent_type.value,
            "agent_name": agent.name,
            "confidence": confidence,
            "context": context,
            "reasoning": self._get_reasoning(user_message, agent_type, context)
        }

    def _get_reasoning(self, message: str, agent_type: AgentType, context: Optional[dict]) -> str:
        """Generate human-readable reasoning for routing decision"""
        if context:
            if context.get("document_upload"):
                return "Document upload detected in context → DOC_ANALYST"
            if context.get("board_creation"):
                return "Board creation detected in context → BOARD_PLANNER"
            if context.get("letter_writing"):
                return "Letter writing detected in context → BRIEF_WRITER"

        message_lower = message.lower()

        # Check patterns
        for agent, patterns in self.INTENT_PATTERNS.items():
            if agent == agent_type:
                for pattern in patterns:
                    if re.search(pattern, message_lower):
                        return f"Pattern match: '{pattern}' → {agent_type.value}"

        # Check keywords
        if agent_type in self.KEYWORDS:
            matched_keywords = [kw for kw in self.KEYWORDS[agent_type] if kw in message_lower]
            if matched_keywords:
                return f"Keywords found: {', '.join(matched_keywords)} → {agent_type.value}"

        return "No strong match, using CHAT as default"


# Global router instance
router = AgentRouter()
