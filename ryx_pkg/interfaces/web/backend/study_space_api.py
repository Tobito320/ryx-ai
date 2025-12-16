"""
RyxHub Study Space API - Phase 1 MVP
REST API endpoints for StudySpace, Chat, Message, Snippet

Based on ryx_study_space_spec.json
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from .database.connection import get_db
from .database.models import (
    StudySpace, StudySpaceChat, StudySpaceMessage, StudySpaceSnippet, Summary
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/study-spaces", tags=["study-spaces"])


# ============================================================================
# Pydantic Models
# ============================================================================

class StudySpaceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=255)
    color: Optional[str] = None
    description: Optional[str] = None


class StudySpaceResponse(BaseModel):
    id: str
    userId: str
    title: str
    subject: str
    color: Optional[str]
    description: Optional[str]
    createdAt: str
    updatedAt: str
    archivedAt: Optional[str] = None

    class Config:
        from_attributes = True


class StudySpaceListItem(BaseModel):
    id: str
    title: str
    subject: str
    snippetCount: int = 0
    chatCount: int = 0
    lastUpdated: str


class ChatCreate(BaseModel):
    title: Optional[str] = None


class ChatResponse(BaseModel):
    id: str
    spaceId: str
    title: str
    createdAt: str
    updatedAt: str
    archivedAt: Optional[str] = None


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    model: Optional[str] = "claude-opus-4.5"


class MessageResponse(BaseModel):
    id: str
    chatId: str
    role: str
    content: str
    metadata: Dict[str, Any] = {}
    createdAt: str


class SnippetCreate(BaseModel):
    type: str = Field(..., regex="^(definition|code|example|image|phrase|formula)$")
    title: Optional[str] = None
    content: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    sourceMessageId: Optional[str] = None


class SnippetResponse(BaseModel):
    id: str
    spaceId: str
    sourceMessageId: Optional[str]
    type: str
    title: str
    content: str
    tags: List[str]
    source: Dict[str, Any]
    createdAt: str
    isFavorite: bool


class SnippetUpdate(BaseModel):
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    isFavorite: Optional[bool] = None


# ============================================================================
# Helper Functions
# ============================================================================

def get_user_id() -> str:
    """Get current user ID (placeholder - implement auth later)"""
    return str(uuid.uuid4())


def get_space_or_404(db: Session, space_id: str, user_id: str) -> StudySpace:
    space = db.query(StudySpace).filter(
        StudySpace.id == space_id,
        StudySpace.user_id == user_id,
        StudySpace.archived_at.is_(None)
    ).first()
    if not space:
        raise HTTPException(status_code=404, detail="Study space not found")
    return space


def get_chat_or_404(db: Session, chat_id: str, space_id: str) -> StudySpaceChat:
    chat = db.query(StudySpaceChat).filter(
        StudySpaceChat.id == chat_id,
        StudySpaceChat.space_id == space_id,
        StudySpaceChat.archived_at.is_(None)
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


# ============================================================================
# Study Spaces Endpoints
# ============================================================================

@router.post("", response_model=StudySpaceResponse, status_code=201)
async def create_study_space(data: StudySpaceCreate, db: Session = Depends(get_db)):
    try:
        user_id = get_user_id()
        space = StudySpace(
            user_id=user_id,
            title=data.title,
            subject=data.subject,
            color=data.color,
            description=data.description
        )
        db.add(space)
        db.commit()
        db.refresh(space)
        logger.info(f"Created study space: {space.id}")
        return StudySpaceResponse(**space.to_dict())
    except Exception as e:
        logger.error(f"Error creating study space: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[StudySpaceListItem])
async def list_study_spaces(db: Session = Depends(get_db)):
    try:
        user_id = get_user_id()
        spaces = db.query(StudySpace).filter(
            StudySpace.user_id == user_id,
            StudySpace.archived_at.is_(None)
        ).order_by(StudySpace.updated_at.desc()).all()
        
        result = []
        for space in spaces:
            snippet_count = db.query(func.count(StudySpaceSnippet.id)).filter(
                StudySpaceSnippet.space_id == space.id
            ).scalar() or 0
            chat_count = db.query(func.count(StudySpaceChat.id)).filter(
                StudySpaceChat.space_id == space.id,
                StudySpaceChat.archived_at.is_(None)
            ).scalar() or 0
            result.append(StudySpaceListItem(
                id=str(space.id),
                title=space.title,
                subject=space.subject,
                snippetCount=snippet_count,
                chatCount=chat_count,
                lastUpdated=space.updated_at.isoformat() if space.updated_at else space.created_at.isoformat()
            ))
        return result
    except Exception as e:
        logger.error(f"Error listing study spaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{space_id}")
async def get_study_space(space_id: str, db: Session = Depends(get_db)):
    try:
        user_id = get_user_id()
        space = get_space_or_404(db, space_id, user_id)
        snippets = db.query(StudySpaceSnippet).filter(
            StudySpaceSnippet.space_id == space_id
        ).all()
        chats = db.query(StudySpaceChat).filter(
            StudySpaceChat.space_id == space_id,
            StudySpaceChat.archived_at.is_(None)
        ).all()
        summary = db.query(Summary).filter(Summary.space_id == space_id).first()
        total_messages = db.query(func.count(StudySpaceMessage.id)).join(
            StudySpaceChat
        ).filter(StudySpaceChat.space_id == space_id).scalar() or 0
        types_count = {}
        for snippet in snippets:
            types_count[snippet.type] = types_count.get(snippet.type, 0) + 1
        return {
            "space": space.to_dict(),
            "snippets": [s.to_dict() for s in snippets],
            "summary": summary.to_dict() if summary else None,
            "chats": [c.to_dict() for c in chats],
            "stats": {
                "totalMessages": total_messages,
                "totalSnippets": len(snippets),
                "types": types_count
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting study space: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{space_id}", status_code=204)
async def delete_study_space(space_id: str, db: Session = Depends(get_db)):
    try:
        user_id = get_user_id()
        space = get_space_or_404(db, space_id, user_id)
        space.archived_at = datetime.utcnow()
        db.commit()
        return JSONResponse(status_code=204, content=None)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Chats Endpoints
# ============================================================================

@router.post("/{space_id}/chats", response_model=ChatResponse, status_code=201)
async def create_chat(space_id: str, data: ChatCreate, db: Session = Depends(get_db)):
    try:
        user_id = get_user_id()
        space = get_space_or_404(db, space_id, user_id)
        title = data.title or f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        chat = StudySpaceChat(space_id=space.id, title=title)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return ChatResponse(**chat.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{space_id}/chats/{chat_id}/messages", response_model=List[MessageResponse])
async def get_chat_messages(space_id: str, chat_id: str, db: Session = Depends(get_db)):
    try:
        user_id = get_user_id()
        space = get_space_or_404(db, space_id, user_id)
        chat = get_chat_or_404(db, chat_id, space_id)
        messages = db.query(StudySpaceMessage).filter(
            StudySpaceMessage.chat_id == chat_id
        ).order_by(StudySpaceMessage.created_at.asc()).all()
        return [MessageResponse(**m.to_dict()) for m in messages]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Snippets Endpoints
# ============================================================================

@router.post("/{space_id}/snippets", response_model=SnippetResponse, status_code=201)
async def create_snippet(space_id: str, data: SnippetCreate, db: Session = Depends(get_db)):
    try:
        user_id = get_user_id()
        space = get_space_or_404(db, space_id, user_id)
        title = data.title or data.content.split("\n")[0][:50]
        source = {}
        if data.sourceMessageId:
            message = db.query(StudySpaceMessage).filter(
                StudySpaceMessage.id == data.sourceMessageId
            ).first()
            if message:
                source = {"messageId": str(message.id), "chatId": str(message.chat_id)}
        snippet = StudySpaceSnippet(
            space_id=space.id,
            source_message_id=UUID(data.sourceMessageId) if data.sourceMessageId else None,
            type=data.type,
            title=title,
            content=data.content,
            tags=data.tags,
            source=source
        )
        db.add(snippet)
        db.commit()
        db.refresh(snippet)
        return SnippetResponse(**snippet.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{space_id}/snippets", response_model=List[SnippetResponse])
async def list_snippets(
    space_id: str,
    type: Optional[str] = Query(None),
    tag: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        user_id = get_user_id()
        space = get_space_or_404(db, space_id, user_id)
        query = db.query(StudySpaceSnippet).filter(StudySpaceSnippet.space_id == space_id)
        if type:
            query = query.filter(StudySpaceSnippet.type == type)
        if tag:
            query = query.filter(StudySpaceSnippet.tags.contains([tag]))
        if search:
            query = query.filter(or_(
                StudySpaceSnippet.content.ilike(f"%{search}%"),
                StudySpaceSnippet.title.ilike(f"%{search}%")
            ))
        snippets = query.order_by(StudySpaceSnippet.created_at.desc()).all()
        result = []
        for snippet in snippets:
            snippet_dict = snippet.to_dict()
            if len(snippet_dict["content"]) > 200:
                snippet_dict["content"] = snippet_dict["content"][:200] + "..."
            result.append(SnippetResponse(**snippet_dict))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{space_id}/snippets/{snippet_id}", status_code=204)
async def delete_snippet(space_id: str, snippet_id: str, db: Session = Depends(get_db)):
    try:
        user_id = get_user_id()
        space = get_space_or_404(db, space_id, user_id)
        snippet = db.query(StudySpaceSnippet).filter(
            StudySpaceSnippet.id == snippet_id,
            StudySpaceSnippet.space_id == space_id
        ).first()
        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")
        db.delete(snippet)
        db.commit()
        return JSONResponse(status_code=204, content=None)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{space_id}/snippets/{snippet_id}", response_model=SnippetResponse)
async def update_snippet(
    space_id: str, snippet_id: str, data: SnippetUpdate, db: Session = Depends(get_db)
):
    try:
        user_id = get_user_id()
        space = get_space_or_404(db, space_id, user_id)
        snippet = db.query(StudySpaceSnippet).filter(
            StudySpaceSnippet.id == snippet_id,
            StudySpaceSnippet.space_id == space_id
        ).first()
        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")
        if data.content is not None:
            snippet.content = data.content
        if data.tags is not None:
            snippet.tags = data.tags
        if data.isFavorite is not None:
            snippet.is_favorite = data.isFavorite
        db.commit()
        db.refresh(snippet)
        return SnippetResponse(**snippet.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
