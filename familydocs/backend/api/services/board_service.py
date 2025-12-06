"""
Board Service - Business logic for board operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from database.models import Board, BoardDocument, BoardLink, Document


class BoardService:
    """Service class for board operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_board(self, board_data) -> Board:
        """Create a new board"""
        board = Board(
            name=board_data.name,
            type=board_data.type,
            parent_id=board_data.parent_id,
            description=board_data.description,
            icon=board_data.icon,
            color=board_data.color,
            is_synced_to_pc=board_data.is_synced_to_pc,
            canvas_x=board_data.canvas_x,
            canvas_y=board_data.canvas_y,
        )

        self.db.add(board)
        await self.db.commit()
        await self.db.refresh(board)

        return board

    async def get_board(self, board_id: UUID) -> Optional[Board]:
        """Get a board by ID"""
        result = await self.db.execute(
            select(Board).where(Board.id == board_id)
        )
        return result.scalar_one_or_none()

    async def get_board_with_counts(self, board_id: UUID) -> Optional[dict]:
        """Get board with document and child counts"""
        # Get board
        result = await self.db.execute(
            select(Board).where(Board.id == board_id)
        )
        board = result.scalar_one_or_none()

        if not board:
            return None

        # Count documents
        doc_result = await self.db.execute(
            select(func.count(BoardDocument.id)).where(BoardDocument.board_id == board_id)
        )
        document_count = doc_result.scalar() or 0

        # Count children
        child_result = await self.db.execute(
            select(func.count(Board.id)).where(Board.parent_id == board_id)
        )
        child_count = child_result.scalar() or 0

        # Convert to dict and add counts
        board_dict = {
            "id": board.id,
            "name": board.name,
            "type": board.type,
            "parent_id": board.parent_id,
            "workspace_id": board.workspace_id,
            "is_synced_to_pc": board.is_synced_to_pc,
            "pc_path": board.pc_path,
            "sync_status": board.sync_status,
            "canvas_x": board.canvas_x,
            "canvas_y": board.canvas_y,
            "canvas_zoom": board.canvas_zoom,
            "canvas_width": board.canvas_width,
            "canvas_height": board.canvas_height,
            "description": board.description,
            "ai_description": board.ai_description,
            "icon": board.icon,
            "color": board.color,
            "created_by": board.created_by,
            "auto_created": board.auto_created,
            "created_at": board.created_at,
            "updated_at": board.updated_at,
            "document_count": document_count,
            "child_count": child_count,
        }

        return board_dict

    async def list_boards(
        self,
        parent_id: Optional[UUID] = None,
        workspace_id: str = "default"
    ) -> List[dict]:
        """List boards with counts"""
        query = select(Board).where(Board.workspace_id == workspace_id)

        if parent_id is not None:
            query = query.where(Board.parent_id == parent_id)
        else:
            # Only root boards if no parent specified
            query = query.where(Board.parent_id.is_(None))

        result = await self.db.execute(query.order_by(Board.created_at.desc()))
        boards = result.scalars().all()

        # Add counts for each board
        boards_with_counts = []
        for board in boards:
            board_data = await self.get_board_with_counts(board.id)
            boards_with_counts.append(board_data)

        return boards_with_counts

    async def update_board(self, board_id: UUID, board_data) -> Optional[Board]:
        """Update a board"""
        result = await self.db.execute(
            select(Board).where(Board.id == board_id)
        )
        board = result.scalar_one_or_none()

        if not board:
            return None

        # Update fields if provided
        if board_data.name is not None:
            board.name = board_data.name
        if board_data.description is not None:
            board.description = board_data.description
        if board_data.icon is not None:
            board.icon = board_data.icon
        if board_data.color is not None:
            board.color = board_data.color
        if board_data.canvas_x is not None:
            board.canvas_x = board_data.canvas_x
        if board_data.canvas_y is not None:
            board.canvas_y = board_data.canvas_y
        if board_data.canvas_zoom is not None:
            board.canvas_zoom = board_data.canvas_zoom

        await self.db.commit()
        await self.db.refresh(board)

        return board

    async def delete_board(self, board_id: UUID):
        """Delete a board"""
        result = await self.db.execute(
            select(Board).where(Board.id == board_id)
        )
        board = result.scalar_one_or_none()

        if board:
            await self.db.delete(board)
            await self.db.commit()

    async def create_link(self, board_id_from: UUID, link_data) -> BoardLink:
        """Create a link between boards"""
        link = BoardLink(
            board_id_from=board_id_from,
            board_id_to=link_data.board_id_to,
            link_type=link_data.link_type,
            reason=link_data.reason,
            created_by="user",
        )

        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)

        return link

    async def get_links(self, board_id: UUID) -> List[BoardLink]:
        """Get all links for a board (incoming and outgoing)"""
        result = await self.db.execute(
            select(BoardLink).where(
                or_(
                    BoardLink.board_id_from == board_id,
                    BoardLink.board_id_to == board_id
                )
            )
        )
        return result.scalars().all()

    async def delete_link(self, link_id: UUID):
        """Delete a board link"""
        result = await self.db.execute(
            select(BoardLink).where(BoardLink.id == link_id)
        )
        link = result.scalar_one_or_none()

        if link:
            await self.db.delete(link)
            await self.db.commit()

    async def add_document(
        self,
        board_id: UUID,
        document_id: UUID,
        relevance_score: float = 1.0
    ):
        """Add a document to a board"""
        # Check if already exists
        result = await self.db.execute(
            select(BoardDocument).where(
                BoardDocument.board_id == board_id,
                BoardDocument.document_id == document_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update relevance score
            existing.relevance_score = relevance_score
        else:
            # Create new relationship
            board_doc = BoardDocument(
                board_id=board_id,
                document_id=document_id,
                relevance_score=relevance_score,
                added_by="user"
            )
            self.db.add(board_doc)

        await self.db.commit()

    async def remove_document(self, board_id: UUID, document_id: UUID):
        """Remove a document from a board"""
        result = await self.db.execute(
            select(BoardDocument).where(
                BoardDocument.board_id == board_id,
                BoardDocument.document_id == document_id
            )
        )
        board_doc = result.scalar_one_or_none()

        if board_doc:
            await self.db.delete(board_doc)
            await self.db.commit()

    async def get_children(self, board_id: UUID) -> List[dict]:
        """Get all child boards"""
        result = await self.db.execute(
            select(Board).where(Board.parent_id == board_id).order_by(Board.created_at.desc())
        )
        boards = result.scalars().all()

        # Add counts
        children_with_counts = []
        for board in boards:
            board_data = await self.get_board_with_counts(board.id)
            children_with_counts.append(board_data)

        return children_with_counts

    async def get_ancestors(self, board_id: UUID) -> List[dict]:
        """Get all ancestor boards (breadcrumb trail)"""
        ancestors = []
        current_board = await self.get_board(board_id)

        while current_board and current_board.parent_id:
            parent = await self.get_board(current_board.parent_id)
            if parent:
                parent_data = await self.get_board_with_counts(parent.id)
                ancestors.insert(0, parent_data)  # Insert at beginning
                current_board = parent
            else:
                break

        return ancestors
