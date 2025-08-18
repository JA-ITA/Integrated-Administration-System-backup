"""
Special test types routes for Special Admin Microservice
"""
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_session
from models import (
    SpecialTestType, SpecialTestTypeCreate, SpecialTestTypeUpdate, 
    SpecialTestTypeResponse, ErrorResponse
)
from services.event_service import EventService

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_event_service():
    """Dependency to get event service"""
    # This will be injected from the main app
    from main import app
    return app.state.event_service

@router.post("/special-types", response_model=SpecialTestTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_special_type(
    special_type_data: SpecialTestTypeCreate,
    event_service: EventService = Depends(get_event_service)
):
    """Create a new special test type"""
    try:
        async with get_db_session() as db:
            # Check if name already exists
            stmt = select(SpecialTestType).where(SpecialTestType.name == special_type_data.name)
            existing = await db.execute(stmt)
            if existing.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Special test type with name '{special_type_data.name}' already exists"
                )
            
            # Create new special test type
            special_type = SpecialTestType(**special_type_data.model_dump())
            db.add(special_type)
            await db.commit()
            await db.refresh(special_type)
            
            # Publish event
            await event_service.publish_special_type_created({
                "id": special_type.id,
                "name": special_type.name,
                "fee": special_type.fee,
                "validity_months": special_type.validity_months,
                "required_docs": special_type.required_docs,
                "created_by": special_type.created_by
            })
            
            logger.info(f"Created special test type: {special_type.name} (ID: {special_type.id})")
            return SpecialTestTypeResponse.model_validate(special_type)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating special test type: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create special test type: {str(e)}"
        )

@router.get("/special-types", response_model=List[SpecialTestTypeResponse])
async def get_special_types(skip: int = 0, limit: int = 100):
    """Get all special test types"""
    try:
        async with get_db_session() as db:
            stmt = select(SpecialTestType).offset(skip).limit(limit)
            result = await db.execute(stmt)
            special_types = result.scalars().all()
            
            return [SpecialTestTypeResponse.model_validate(st) for st in special_types]
            
    except Exception as e:
        logger.error(f"Error getting special test types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get special test types: {str(e)}"
        )

@router.get("/special-types/{type_id}", response_model=SpecialTestTypeResponse)
async def get_special_type(type_id: uuid.UUID):
    """Get a specific special test type"""
    try:
        async with get_db_session() as db:
            stmt = select(SpecialTestType).where(SpecialTestType.id == type_id)
            result = await db.execute(stmt)
            special_type = result.scalars().first()
            
            if not special_type:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Special test type not found"
                )
            
            return SpecialTestTypeResponse.model_validate(special_type)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting special test type {type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get special test type: {str(e)}"
        )

@router.put("/special-types/{type_id}", response_model=SpecialTestTypeResponse)
async def update_special_type(
    type_id: uuid.UUID,
    update_data: SpecialTestTypeUpdate,
    event_service: EventService = Depends(get_event_service)
):
    """Update a special test type"""
    try:
        async with get_db_session() as db:
            # Get existing special test type
            stmt = select(SpecialTestType).where(SpecialTestType.id == type_id)
            result = await db.execute(stmt)
            special_type = result.scalars().first()
            
            if not special_type:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Special test type not found"
                )
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            if update_dict:
                stmt = (
                    update(SpecialTestType)
                    .where(SpecialTestType.id == type_id)
                    .values(**update_dict)
                )
                await db.execute(stmt)
                await db.commit()
                await db.refresh(special_type)
            
            # Publish event if status changed to active
            if update_dict.get("status") == "active":
                await event_service.publish_special_type_created({
                    "id": special_type.id,
                    "name": special_type.name,
                    "fee": special_type.fee,
                    "validity_months": special_type.validity_months,
                    "required_docs": special_type.required_docs,
                    "created_by": special_type.created_by
                })
            
            logger.info(f"Updated special test type: {special_type.name} (ID: {special_type.id})")
            return SpecialTestTypeResponse.model_validate(special_type)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating special test type {type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update special test type: {str(e)}"
        )

@router.delete("/special-types/{type_id}")
async def delete_special_type(type_id: uuid.UUID):
    """Delete a special test type"""
    try:
        async with get_db_session() as db:
            # Check if special test type exists
            stmt = select(SpecialTestType).where(SpecialTestType.id == type_id)
            result = await db.execute(stmt)
            special_type = result.scalars().first()
            
            if not special_type:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Special test type not found"
                )
            
            # Delete special test type
            stmt = delete(SpecialTestType).where(SpecialTestType.id == type_id)
            await db.execute(stmt)
            await db.commit()
            
            logger.info(f"Deleted special test type: {special_type.name} (ID: {type_id})")
            return {"message": "Special test type deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting special test type {type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete special test type: {str(e)}"
        )