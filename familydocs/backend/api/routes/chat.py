"""
Chat API Routes
Multi-agent chat system with intelligent routing
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from api.services.chat_service import ChatService
from ai.agents import get_all_agents
from ai.multi_agent_client import client

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class ChatSessionCreate(BaseModel):
    session_name: Optional[str] = None
    board_id: Optional[UUID] = None
    is_persistent: bool = False


class ChatMessageCreate(BaseModel):
    content: str
    context: Optional[dict] = None  # For routing hints


class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    agent_used: str | None
    model_used: str | None
    tokens_used: int | None
    response_time_ms: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    id: UUID
    session_name: str | None
    board_id: UUID | None
    is_persistent: bool
    is_active: bool
    created_at: datetime
    last_activity: datetime

    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSessionResponse):
    messages: List[ChatMessageResponse]
    stats: dict


# ============================================================================
# Chat Endpoints
# ============================================================================


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session"""
    service = ChatService(db)
    session = await service.create_session(
        session_name=session_data.session_name,
        board_id=session_data.board_id,
        is_persistent=session_data.is_persistent
    )
    return session


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List all chat sessions"""
    service = ChatService(db)
    sessions = await service.list_sessions(active_only=active_only)
    return sessions


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a chat session with messages and stats"""
    service = ChatService(db)

    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await service.get_messages(session_id)
    stats = await service.get_agent_stats(session_id)

    return {
        **ChatSessionResponse.from_orm(session).dict(),
        "messages": messages,
        "stats": stats
    }


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: UUID,
    message: ChatMessageCreate,
    stream: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get AI response"""
    service = ChatService(db)

    # Check if session exists
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Handle streaming separately
    if stream:
        async def generate():
            async for chunk in service.send_message_stream(
                session_id=session_id,
                user_message=message.content,
                context=message.context
            ):
                yield chunk

        return StreamingResponse(generate(), media_type="text/plain")

    # Non-streaming response
    ai_message = await service.send_message(
        session_id=session_id,
        user_message=message.content,
        context=message.context
    )

    return ai_message


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get all messages in a chat session"""
    service = ChatService(db)

    # Check if session exists
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await service.get_messages(session_id, limit=limit)
    return messages


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session"""
    service = ChatService(db)

    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await service.delete_session(session_id)


@router.get("/sessions/{session_id}/stats")
async def get_session_stats(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about a chat session"""
    service = ChatService(db)

    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    stats = await service.get_agent_stats(session_id)
    return stats


# ============================================================================
# Agent Info Endpoints
# ============================================================================


@router.get("/agents")
async def list_agents():
    """List all available agents"""
    return get_all_agents()


@router.get("/agents/health")
async def check_agents_health():
    """Check health of all agent endpoints"""
    health = await client.health_check_all()
    all_healthy = all(health.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "agents": health
    }


@router.get("/agents/info")
async def get_agents_info():
    """Get detailed information about all agents"""
    return client.get_agent_info()
