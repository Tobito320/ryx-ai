"""
Board API Routes
CRUD operations + PC folder sync
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from database.models import Board, BoardDocument, BoardLink
from api.services.board_service import BoardService
from api.services.pc_sync_service import PCSyncService

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class BoardCreate(BaseModel):
    name: str
    type: str = "board"  # 'board' or 'folder'
    parent_id: Optional[UUID] = None
    description: Optional[str] = None
    icon: str = "📁"
    color: str = "#8b5cf6"
    is_synced_to_pc: bool = False
    canvas_x: float = 0
    canvas_y: float = 0


class BoardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    canvas_x: Optional[float] = None
    canvas_y: Optional[float] = None
    canvas_zoom: Optional[float] = None


class BoardResponse(BaseModel):
    id: UUID
    name: str
    type: str
    parent_id: Optional[UUID]
    workspace_id: str
    is_synced_to_pc: bool
    pc_path: Optional[str]
    sync_status: str
    canvas_x: float
    canvas_y: float
    canvas_zoom: float
    canvas_width: float
    canvas_height: float
    description: Optional[str]
    ai_description: Optional[str]
    icon: str
    color: str
    created_by: str
    auto_created: bool
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    child_count: int = 0

    class Config:
        from_attributes = True


class BoardLinkCreate(BaseModel):
    board_id_to: UUID
    link_type: str = "related"  # 'related', 'depends_on', 'affects', 'references'
    reason: Optional[str] = None


class BoardLinkResponse(BaseModel):
    id: UUID
    board_id_from: UUID
    board_id_to: UUID
    link_type: str
    reason: Optional[str]
    created_by: str
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Board CRUD Endpoints
# ============================================================================


@router.post("/", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
async def create_board(
    board_data: BoardCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new board"""
    service = BoardService(db)
    sync_service = PCSyncService()

    # Create board in database
    board = await service.create_board(board_data)

    # If PC sync enabled, create folder
    if board_data.is_synced_to_pc:
        pc_path = await sync_service.create_folder(board)
        board.pc_path = pc_path
        board.sync_status = "synced"
        board.last_synced_at = datetime.utcnow()
        await db.commit()
        await db.refresh(board)

    # Get counts
    response = await service.get_board_with_counts(board.id)
    return response


@router.get("/", response_model=List[BoardResponse])
async def list_boards(
    parent_id: Optional[UUID] = None,
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """List all boards (optionally filter by parent)"""
    service = BoardService(db)
    boards = await service.list_boards(parent_id=parent_id, workspace_id=workspace_id)
    return boards


@router.get("/{board_id}", response_model=BoardResponse)
async def get_board(
    board_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a single board by ID"""
    service = BoardService(db)
    board = await service.get_board_with_counts(board_id)

    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    return board


@router.patch("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: UUID,
    board_data: BoardUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a board"""
    service = BoardService(db)
    board = await service.update_board(board_id, board_data)

    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    return await service.get_board_with_counts(board_id)


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(
    board_id: UUID,
    archive_pc_folder: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Delete a board (with optional PC folder archiving)"""
    service = BoardService(db)
    sync_service = PCSyncService()

    # Get board first
    result = await db.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()

    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    # Archive PC folder if needed
    if board.is_synced_to_pc and board.pc_path and archive_pc_folder:
        await sync_service.archive_folder(board.pc_path)

    # Delete from database
    await service.delete_board(board_id)


# ============================================================================
# PC Sync Endpoints
# ============================================================================


@router.post("/{board_id}/sync", response_model=BoardResponse)
async def sync_board_to_pc(
    board_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Manually sync a board to PC"""
    service = BoardService(db)
    sync_service = PCSyncService()

    # Get board
    result = await db.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()

    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    # Create or update PC folder
    try:
        pc_path = await sync_service.create_folder(board)
        board.pc_path = pc_path
        board.is_synced_to_pc = True
        board.sync_status = "synced"
        board.sync_error = None
        board.last_synced_at = datetime.utcnow()

        await db.commit()
        await db.refresh(board)

        return await service.get_board_with_counts(board_id)

    except Exception as e:
        board.sync_status = "error"
        board.sync_error = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


# ============================================================================
# Board Link Endpoints
# ============================================================================


@router.post("/{board_id}/links", response_model=BoardLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_board_link(
    board_id: UUID,
    link_data: BoardLinkCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a link between two boards"""
    service = BoardService(db)
    link = await service.create_link(board_id, link_data)
    return link


@router.get("/{board_id}/links", response_model=List[BoardLinkResponse])
async def get_board_links(
    board_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all links for a board"""
    service = BoardService(db)
    links = await service.get_links(board_id)
    return links


@router.delete("/{board_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board_link(
    board_id: UUID,
    link_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a board link"""
    service = BoardService(db)
    await service.delete_link(link_id)


# ============================================================================
# Document Management
# ============================================================================


@router.post("/{board_id}/documents/{document_id}", status_code=status.HTTP_201_CREATED)
async def add_document_to_board(
    board_id: UUID,
    document_id: UUID,
    relevance_score: float = 1.0,
    db: AsyncSession = Depends(get_db)
):
    """Add a document to a board"""
    service = BoardService(db)
    await service.add_document(board_id, document_id, relevance_score)
    return {"status": "success", "message": "Document added to board"}


@router.delete("/{board_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document_from_board(
    board_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Remove a document from a board"""
    service = BoardService(db)
    await service.remove_document(board_id, document_id)


# ============================================================================
# Hierarchy & Graph Endpoints
# ============================================================================


@router.get("/{board_id}/children", response_model=List[BoardResponse])
async def get_board_children(
    board_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all child boards"""
    service = BoardService(db)
    children = await service.get_children(board_id)
    return children


@router.get("/{board_id}/ancestors", response_model=List[BoardResponse])
async def get_board_ancestors(
    board_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all ancestor boards (breadcrumb trail)"""
    service = BoardService(db)
    ancestors = await service.get_ancestors(board_id)
    return ancestors


# ============================================================================
# Statistics & Analytics
# ============================================================================


@router.get("/stats/overview")
async def get_board_stats(
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Get overall board statistics"""
    # Total boards
    result = await db.execute(
        select(func.count(Board.id)).where(Board.workspace_id == workspace_id)
    )
    total_boards = result.scalar()

    # Total synced
    result = await db.execute(
        select(func.count(Board.id)).where(
            Board.workspace_id == workspace_id,
            Board.is_synced_to_pc == True
        )
    )
    synced_boards = result.scalar()

    # Total links
    result = await db.execute(select(func.count(BoardLink.id)))
    total_links = result.scalar()

    return {
        "total_boards": total_boards,
        "synced_boards": synced_boards,
        "total_links": total_links,
    }
