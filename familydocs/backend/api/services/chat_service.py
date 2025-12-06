"""
Chat Service - Multi-Agent Chat System
Handles chat sessions, routing, and multi-agent orchestration
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Optional, AsyncGenerator
from uuid import UUID
import logging
from datetime import datetime

from database.models import ChatSession, ChatMessage
from ai.agent_router import router
from ai.multi_agent_client import client
from ai.agents import AgentType

logger = logging.getLogger(__name__)


class ChatService:
    """Service for multi-agent chat operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self,
        session_name: Optional[str] = None,
        board_id: Optional[UUID] = None,
        user_id: str = "default_user",
        is_persistent: bool = False
    ) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            session_name=session_name or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            board_id=board_id,
            user_id=user_id,
            is_persistent=is_persistent,
            is_active=True
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info(f"✅ Created chat session {session.id}")
        return session

    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, user_id: str = "default_user", active_only: bool = True) -> List[ChatSession]:
        """List chat sessions"""
        query = select(ChatSession).where(ChatSession.user_id == user_id)

        if active_only:
            query = query.where(ChatSession.is_active == True)

        query = query.order_by(ChatSession.last_activity.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_messages(self, session_id: UUID, limit: int = 50) -> List[ChatMessage]:
        """Get messages for a session"""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def send_message(
        self,
        session_id: UUID,
        user_message: str,
        context: Optional[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> ChatMessage:
        """
        Send a message and get AI response

        Args:
            session_id: Chat session ID
            user_message: User's message
            context: Optional context for routing (board_id, document_id, etc.)
            temperature: LLM temperature
            max_tokens: Max tokens to generate

        Returns:
            AI response message
        """
        # Verify session exists
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Store user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_message
        )
        self.db.add(user_msg)

        # Route to appropriate agent
        agent, confidence = router.get_agent_for_message(user_message, context)

        logger.info(f"🤖 Routing to {agent.type.value} (confidence: {confidence:.2f})")

        # Get conversation history
        history = await self.get_messages(session_id)
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in history[-10:]  # Last 10 messages for context
        ]
        messages.append({"role": "user", "content": user_message})

        # Generate response
        start_time = datetime.now()

        response = await client.generate(
            agent=agent,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        end_time = datetime.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Extract response text
        ai_content = response["choices"][0]["message"]["content"]
        tokens_used = response.get("usage", {}).get("total_tokens", 0)

        # Store AI response
        ai_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=ai_content,
            agent_used=agent.type.value,
            model_used=agent.model_name,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms
        )
        self.db.add(ai_msg)

        await self.db.commit()
        await self.db.refresh(ai_msg)

        logger.info(f"✅ Response generated ({tokens_used} tokens, {response_time_ms}ms)")

        return ai_msg

    async def send_message_stream(
        self,
        session_id: UUID,
        user_message: str,
        context: Optional[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """
        Send message and get streaming AI response

        Args:
            session_id: Chat session ID
            user_message: User's message
            context: Optional context
            temperature: LLM temperature
            max_tokens: Max tokens

        Yields:
            Chunks of AI response
        """
        # Verify session
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Store user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_message
        )
        self.db.add(user_msg)
        await self.db.commit()

        # Route to agent
        agent, confidence = router.get_agent_for_message(user_message, context)

        logger.info(f"🤖 Streaming from {agent.type.value} (confidence: {confidence:.2f})")

        # Get history
        history = await self.get_messages(session_id)
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in history[-10:]
        ]
        messages.append({"role": "user", "content": user_message})

        # Stream response
        full_response = ""
        start_time = datetime.now()

        async for chunk in client.generate_stream(
            agent=agent,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        ):
            full_response += chunk
            yield chunk

        end_time = datetime.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Store complete AI response
        ai_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_response,
            agent_used=agent.type.value,
            model_used=agent.model_name,
            response_time_ms=response_time_ms
        )
        self.db.add(ai_msg)
        await self.db.commit()

        logger.info(f"✅ Streaming complete ({len(full_response)} chars, {response_time_ms}ms)")

    async def delete_session(self, session_id: UUID):
        """Delete a chat session"""
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            await self.db.delete(session)
            await self.db.commit()
            logger.info(f"✅ Deleted session {session_id}")

    async def get_agent_stats(self, session_id: UUID) -> Dict:
        """Get statistics about which agents were used in a session"""
        messages = await self.get_messages(session_id)

        agent_counts = {}
        total_tokens = 0
        total_time_ms = 0

        for msg in messages:
            if msg.agent_used:
                agent_counts[msg.agent_used] = agent_counts.get(msg.agent_used, 0) + 1
                total_tokens += msg.tokens_used or 0
                total_time_ms += msg.response_time_ms or 0

        return {
            "total_messages": len([m for m in messages if m.role == "assistant"]),
            "agent_usage": agent_counts,
            "total_tokens": total_tokens,
            "avg_response_time_ms": total_time_ms / len(messages) if messages else 0
        }
