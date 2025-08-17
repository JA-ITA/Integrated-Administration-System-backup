"""
Hubs API routes for ITADIAS Calendar Microservice
"""
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import HubCreate, HubResponse
from services.hub_service import HubService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/hubs", response_model=List[HubResponse])
async def list_hubs(
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    List all hubs with pagination
    
    - **active_only**: Filter for active hubs only (default: true)
    - **skip**: Number of hubs to skip (default: 0)
    - **limit**: Maximum number of hubs to return (default: 100, max: 1000)
    """
    try:
        if limit > 1000:
            limit = 1000
            
        logger.info(f"Listing hubs: skip={skip}, limit={limit}, active_only={active_only}")
        
        # Check if database is available
        if db is None:
            # Return mock hubs for testing without database
            mock_hubs = [
                {
                    "id": uuid.uuid4(),
                    "name": "Main Testing Hub",
                    "location": "Hamilton, Bermuda",
                    "address": "123 Front Street, Hamilton HM 11, Bermuda",
                    "timezone": "Atlantic/Bermuda",
                    "is_active": True,
                    "operating_hours_start": "09:00",
                    "operating_hours_end": "17:00",
                    "operating_days": "1,2,3,4,5",
                    "capacity": 3,
                    "description": "Main hub for testing and assessments",
                    "contact_info": "Phone: +1-441-555-0123, Email: hub@example.com",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": uuid.uuid4(),
                    "name": "Secondary Hub",
                    "location": "St. George's, Bermuda",
                    "address": "456 King's Square, St. George's GE 05, Bermuda",
                    "timezone": "Atlantic/Bermuda",
                    "is_active": True,
                    "operating_hours_start": "10:00",
                    "operating_hours_end": "16:00",
                    "operating_days": "1,2,3,4,5",
                    "capacity": 2,
                    "description": "Secondary hub for overflow testing",
                    "contact_info": "Phone: +1-441-555-0124, Email: stgeorge@example.com",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                }
            ]
            
            logger.info(f"Returning {len(mock_hubs)} mock hubs")
            return [HubResponse(**hub) for hub in mock_hubs]
        
        hub_service = HubService(db)
        hubs = await hub_service.list_hubs(skip=skip, limit=limit, active_only=active_only)
        
        return [HubResponse.from_orm(hub) for hub in hubs]
        
    except Exception as e:
        logger.error(f"Error listing hubs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/hubs/{hub_id}", response_model=HubResponse)
async def get_hub(
    hub_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific hub by ID
    
    - **hub_id**: UUID of the hub to retrieve
    """
    try:
        logger.info(f"Getting hub with ID: {hub_id}")
        
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Database not available"
            )
        
        hub_service = HubService(db)
        hub = await hub_service.get_hub_by_id(hub_id)
        
        if not hub:
            raise HTTPException(
                status_code=404,
                detail=f"Hub with ID {hub_id} not found"
            )
        
        return HubResponse.from_orm(hub)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hub {hub_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/hubs", response_model=HubResponse, status_code=201)
async def create_hub(
    hub_data: HubCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new hub
    
    - **name**: Hub name (required)
    - **location**: Hub location/city (required)
    - **address**: Full address (optional)
    - **timezone**: Timezone identifier (default: UTC)
    - **operating_hours_start**: Operating start time in HH:MM format
    - **operating_hours_end**: Operating end time in HH:MM format
    - **operating_days**: Comma-separated operating days (1=Mon, 7=Sun)
    - **capacity**: Maximum concurrent capacity (default: 1)
    - **description**: Hub description (optional)
    - **contact_info**: Contact information (optional)
    """
    try:
        logger.info(f"Creating hub: {hub_data.name}")
        
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Database not available"
            )
        
        hub_service = HubService(db)
        
        # Check if hub with same name already exists
        existing_hub = await hub_service.get_hub_by_name(hub_data.name)
        if existing_hub:
            raise HTTPException(
                status_code=409,
                detail=f"Hub with name '{hub_data.name}' already exists"
            )
        
        # Create hub
        hub = await hub_service.create_hub(hub_data)
        logger.info(f"Hub created with ID: {hub.id}")
        
        return HubResponse.from_orm(hub)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating hub: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/hubs/{hub_id}", response_model=HubResponse)
async def update_hub(
    hub_id: uuid.UUID,
    hub_data: HubCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing hub
    
    - **hub_id**: UUID of the hub to update
    - **hub_data**: Updated hub information
    """
    try:
        logger.info(f"Updating hub: {hub_id}")
        
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Database not available"
            )
        
        hub_service = HubService(db)
        
        # Check if hub exists
        existing_hub = await hub_service.get_hub_by_id(hub_id)
        if not existing_hub:
            raise HTTPException(
                status_code=404,
                detail=f"Hub with ID {hub_id} not found"
            )
        
        # Update hub
        hub = await hub_service.update_hub(hub_id, hub_data)
        logger.info(f"Hub updated: {hub_id}")
        
        return HubResponse.from_orm(hub)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating hub {hub_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/hubs/{hub_id}")
async def delete_hub(
    hub_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a hub (soft delete by setting is_active to false)
    
    - **hub_id**: UUID of the hub to delete
    """
    try:
        logger.info(f"Deleting hub: {hub_id}")
        
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Database not available"
            )
        
        hub_service = HubService(db)
        
        # Check if hub exists
        existing_hub = await hub_service.get_hub_by_id(hub_id)
        if not existing_hub:
            raise HTTPException(
                status_code=404,
                detail=f"Hub with ID {hub_id} not found"
            )
        
        # Soft delete hub
        await hub_service.delete_hub(hub_id)
        logger.info(f"Hub deleted: {hub_id}")
        
        return {"message": "Hub deleted successfully", "hub_id": hub_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting hub {hub_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")