"""
Smart Modules API Routes
Müllabfuhr, Gmail Reader, Brief Generator, etc.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================


class ModuleCreate(BaseModel):
    board_id: UUID
    module_type: str  # 'muellabfuhr', 'gmail_reader', 'brief_generator'
    name: str
    config: dict


class ModuleResponse(BaseModel):
    id: UUID
    board_id: UUID
    module_type: str
    name: str
    description: str | None
    config: dict
    data: dict
    is_active: bool
    last_refreshed: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Module Endpoints (Placeholder)
# ============================================================================


@router.post("/", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
async def create_module(
    module_data: ModuleCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new smart module"""
    # TODO: Implement module creation
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/", response_model=List[ModuleResponse])
async def list_modules(
    board_id: UUID | None = None,
    db: AsyncSession = Depends(get_db)
):
    """List all modules"""
    # TODO: Implement module listing
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/{module_id}/refresh")
async def refresh_module(
    module_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Manually refresh a module's data"""
    # TODO: Implement module refresh
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(
    module_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a module"""
    # TODO: Implement module deletion
    raise HTTPException(status_code=501, detail="Not implemented yet")
