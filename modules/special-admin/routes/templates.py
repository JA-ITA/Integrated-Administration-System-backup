"""
Certificate template routes for Special Admin Microservice
"""
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_session
from models import (
    CertificateTemplate, CertificateTemplateCreate, CertificateTemplateUpdate,
    CertificateTemplateResponse, TemplatePreviewRequest, TemplatePreviewResponse, ErrorResponse
)
from services.event_service import EventService
from services.template_service import TemplateService

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_event_service():
    """Dependency to get event service"""
    from main import app
    return app.state.event_service

async def get_template_service():
    """Dependency to get template service"""
    from main import app
    return app.state.template_service

@router.post("/templates", response_model=CertificateTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: CertificateTemplateCreate,
    event_service: EventService = Depends(get_event_service),
    template_service: TemplateService = Depends(get_template_service)
):
    """Create a new certificate template"""
    try:
        async with get_db_session() as db:
            # Generate preview HTML if needed
            preview_result = await template_service.compile_template(
                template_data.hbs_content,
                template_data.css_content,
                {}
            )
            
            # Create new template
            template = CertificateTemplate(
                **template_data.model_dump(),
                preview_html=preview_result.get("preview_html") if preview_result.get("success") else None
            )
            db.add(template)
            await db.commit()
            await db.refresh(template)
            
            # Publish event
            await event_service.publish_template_updated({
                "id": template.id,
                "name": template.name,
                "type": template.type,
                "status": template.status,
                "is_default": template.is_default,
                "created_by": template.created_by
            })
            
            logger.info(f"Created certificate template: {template.name} (ID: {template.id})")
            return CertificateTemplateResponse.model_validate(template)
            
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )

@router.get("/templates", response_model=List[CertificateTemplateResponse])
async def get_templates(skip: int = 0, limit: int = 100, template_type: str = None):
    """Get all certificate templates"""
    try:
        async with get_db_session() as db:
            stmt = select(CertificateTemplate)
            
            if template_type:
                stmt = stmt.where(CertificateTemplate.type == template_type)
            
            stmt = stmt.offset(skip).limit(limit)
            result = await db.execute(stmt)
            templates = result.scalars().all()
            
            return [CertificateTemplateResponse.model_validate(t) for t in templates]
            
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get templates: {str(e)}"
        )

@router.get("/templates/{template_id}", response_model=CertificateTemplateResponse)
async def get_template(template_id: uuid.UUID):
    """Get a specific certificate template"""
    try:
        async with get_db_session() as db:
            stmt = select(CertificateTemplate).where(CertificateTemplate.id == template_id)
            result = await db.execute(stmt)
            template = result.scalars().first()
            
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )
            
            return CertificateTemplateResponse.model_validate(template)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}"
        )

@router.get("/templates/{template_id}/preview")
async def get_template_preview(
    template_id: uuid.UUID,
    template_service: TemplateService = Depends(get_template_service)
):
    """Get live preview HTML for a template"""
    try:
        async with get_db_session() as db:
            stmt = select(CertificateTemplate).where(CertificateTemplate.id == template_id)
            result = await db.execute(stmt)
            template = result.scalars().first()
            
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )
            
            # Generate preview
            preview_result = await template_service.compile_template(
                template.hbs_content,
                template.css_content,
                {}
            )
            
            if preview_result.get("success"):
                return {"preview_html": preview_result["preview_html"]}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to generate preview: {preview_result.get('error')}"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating template preview {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )

@router.post("/templates/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    preview_data: TemplatePreviewRequest,
    template_service: TemplateService = Depends(get_template_service)
):
    """Generate preview for template content without saving"""
    try:
        preview_result = await template_service.compile_template(
            preview_data.hbs_content,
            preview_data.css_content,
            preview_data.sample_data
        )
        
        if preview_result.get("success"):
            return TemplatePreviewResponse(
                preview_html=preview_result["preview_html"],
                compiled_template=preview_result["compiled_template"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Template compilation failed: {preview_result.get('error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )

@router.put("/templates/{template_id}", response_model=CertificateTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    update_data: CertificateTemplateUpdate,
    event_service: EventService = Depends(get_event_service),
    template_service: TemplateService = Depends(get_template_service)
):
    """Update a certificate template"""
    try:
        async with get_db_session() as db:
            # Get existing template
            stmt = select(CertificateTemplate).where(CertificateTemplate.id == template_id)
            result = await db.execute(stmt)
            template = result.scalars().first()
            
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            if update_dict:
                # Regenerate preview if content changed
                if "hbs_content" in update_dict or "css_content" in update_dict:
                    preview_result = await template_service.compile_template(
                        update_dict.get("hbs_content", template.hbs_content),
                        update_dict.get("css_content", template.css_content),
                        {}
                    )
                    if preview_result.get("success"):
                        update_dict["preview_html"] = preview_result["preview_html"]
                
                stmt = (
                    update(CertificateTemplate)
                    .where(CertificateTemplate.id == template_id)
                    .values(**update_dict)
                )
                await db.execute(stmt)
                await db.commit()
                await db.refresh(template)
            
            # Publish event
            await event_service.publish_template_updated({
                "id": template.id,
                "name": template.name,
                "type": template.type,
                "status": template.status,
                "is_default": template.is_default,
                "created_by": template.created_by
            })
            
            logger.info(f"Updated certificate template: {template.name} (ID: {template.id})")
            return CertificateTemplateResponse.model_validate(template)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update template: {str(e)}"
        )

@router.delete("/templates/{template_id}")
async def delete_template(template_id: uuid.UUID):
    """Delete a certificate template"""
    try:
        async with get_db_session() as db:
            # Check if template exists
            stmt = select(CertificateTemplate).where(CertificateTemplate.id == template_id)
            result = await db.execute(stmt)
            template = result.scalars().first()
            
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )
            
            # Delete template
            stmt = delete(CertificateTemplate).where(CertificateTemplate.id == template_id)
            await db.execute(stmt)
            await db.commit()
            
            logger.info(f"Deleted certificate template: {template.name} (ID: {template_id})")
            return {"message": "Template deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {str(e)}"
        )

@router.get("/templates/config/default")
async def get_default_template_config(
    template_service: TemplateService = Depends(get_template_service)
):
    """Get default template configuration for the designer"""
    try:
        config = await template_service.get_default_template_config()
        return config
    except Exception as e:
        logger.error(f"Error getting default template config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get default config: {str(e)}"
        )