"""
Question modules routes for Special Admin Microservice
"""
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_session
from models import (
    QuestionModule, QuestionModuleCreate, QuestionModuleUpdate, QuestionModuleResponse,
    QuestionUploadRequest, QuestionUploadResponse, ErrorResponse
)
from services.event_service import EventService
from services.question_service import QuestionService

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_event_service():
    """Dependency to get event service"""
    from app import app
    return app.state.event_service

async def get_question_service():
    """Dependency to get question service"""
    from app import app
    return app.state.question_service

@router.get("/modules", response_model=List[QuestionModuleResponse])
async def get_modules(skip: int = 0, limit: int = 100):
    """Get all available question modules"""
    try:
        async with get_db_session() as db:
            stmt = select(QuestionModule).offset(skip).limit(limit)
            result = await db.execute(stmt)
            modules = result.scalars().all()
            
            return [QuestionModuleResponse.model_validate(m) for m in modules]
            
    except Exception as e:
        logger.error(f"Error getting modules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get modules: {str(e)}"
        )

@router.post("/modules", response_model=QuestionModuleResponse, status_code=status.HTTP_201_CREATED)
async def create_module(
    module_data: QuestionModuleCreate,
    event_service: EventService = Depends(get_event_service)
):
    """Create a new question module"""
    try:
        async with get_db_session() as db:
            # Check if code already exists
            stmt = select(QuestionModule).where(QuestionModule.code == module_data.code)
            existing = await db.execute(stmt)
            if existing.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Module with code '{module_data.code}' already exists"
                )
            
            # Create new module
            module = QuestionModule(**module_data.model_dump())
            db.add(module)
            await db.commit()
            await db.refresh(module)
            
            # Publish event
            await event_service.publish_module_created({
                "id": module.id,
                "code": module.code,
                "description": module.description,
                "category": module.category,
                "created_by": module.created_by
            })
            
            logger.info(f"Created question module: {module.code} (ID: {module.id})")
            return QuestionModuleResponse.model_validate(module)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating module: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create module: {str(e)}"
        )

@router.get("/modules/{module_id}", response_model=QuestionModuleResponse)
async def get_module(module_id: uuid.UUID):
    """Get a specific question module"""
    try:
        async with get_db_session() as db:
            stmt = select(QuestionModule).where(QuestionModule.id == module_id)
            result = await db.execute(stmt)
            module = result.scalars().first()
            
            if not module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Module not found"
                )
            
            return QuestionModuleResponse.model_validate(module)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting module {module_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get module: {str(e)}"
        )

@router.put("/modules/{module_id}", response_model=QuestionModuleResponse)
async def update_module(
    module_id: uuid.UUID,
    update_data: QuestionModuleUpdate
):
    """Update a question module"""
    try:
        async with get_db_session() as db:
            # Get existing module
            stmt = select(QuestionModule).where(QuestionModule.id == module_id)
            result = await db.execute(stmt)
            module = result.scalars().first()
            
            if not module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Module not found"
                )
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            if update_dict:
                stmt = (
                    update(QuestionModule)
                    .where(QuestionModule.id == module_id)
                    .values(**update_dict)
                )
                await db.execute(stmt)
                await db.commit()
                await db.refresh(module)
            
            logger.info(f"Updated question module: {module.code} (ID: {module.id})")
            return QuestionModuleResponse.model_validate(module)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating module {module_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update module: {str(e)}"
        )

@router.delete("/modules/{module_id}")
async def delete_module(module_id: uuid.UUID):
    """Delete a question module"""
    try:
        async with get_db_session() as db:
            # Check if module exists
            stmt = select(QuestionModule).where(QuestionModule.id == module_id)
            result = await db.execute(stmt)
            module = result.scalars().first()
            
            if not module:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Module not found"
                )
            
            # Delete module
            stmt = delete(QuestionModule).where(QuestionModule.id == module_id)
            await db.execute(stmt)
            await db.commit()
            
            logger.info(f"Deleted question module: {module.code} (ID: {module_id})")
            return {"message": "Module deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting module {module_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete module: {str(e)}"
        )

@router.post("/questions/upload", response_model=QuestionUploadResponse)
async def upload_questions_csv(
    module_code: str = Form(..., description="Module code (e.g., SPECIAL-TEST)"),
    created_by: str = Form(..., description="User who is uploading"),
    file: UploadFile = File(..., description="CSV file with questions"),
    question_service: QuestionService = Depends(get_question_service)
):
    """Upload questions from CSV file and tag with module code"""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a CSV file"
            )
        
        # Read file content
        content = await file.read()
        csv_data = content.decode('utf-8')
        
        # Process upload
        async with get_db_session() as db:
            result = await question_service.process_csv_upload(
                db, module_code, csv_data, created_by
            )
            
        if result["success"]:
            logger.info(f"Successfully uploaded questions for module {module_code}: {result['questions_created']} created")
            return QuestionUploadResponse(**result)
        else:
            logger.warning(f"Question upload failed for module {module_code}: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload questions: {str(e)}"
        )

@router.post("/questions/upload-text", response_model=QuestionUploadResponse)
async def upload_questions_text(
    upload_data: QuestionUploadRequest,
    question_service: QuestionService = Depends(get_question_service)
):
    """Upload questions from text/base64 CSV data"""
    try:
        async with get_db_session() as db:
            result = await question_service.process_csv_upload(
                db, upload_data.module_code, upload_data.csv_data, upload_data.created_by
            )
            
        if result["success"]:
            logger.info(f"Successfully uploaded questions for module {upload_data.module_code}: {result['questions_created']} created")
            return QuestionUploadResponse(**result)
        else:
            logger.warning(f"Question upload failed for module {upload_data.module_code}: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload questions: {str(e)}"
        )

@router.get("/questions/template")
async def get_csv_template():
    """Get CSV template for question upload"""
    template_content = """question_text,option_a,option_b,option_c,option_d,correct_answer,difficulty,explanation
"What is the maximum speed limit in urban areas?","50 km/h","60 km/h","70 km/h","80 km/h","A","medium","Speed limits vary by jurisdiction but 50 km/h is common in urban areas"
"Is it mandatory to wear seatbelts while driving?","true","false","","","true","easy","Seatbelt use is mandatory for safety"
"What should you do at a red traffic light?","Stop","Slow down","Proceed with caution","Honk","A","easy","Red light means complete stop"
"""
    
    return {
        "template": template_content,
        "format": "CSV",
        "columns": [
            "question_text - The question text",
            "option_a - First option (for multiple choice) or 'true' (for true/false)",
            "option_b - Second option (for multiple choice) or 'false' (for true/false)",
            "option_c - Third option (for multiple choice only)",
            "option_d - Fourth option (for multiple choice only)",
            "correct_answer - A/B/C/D for multiple choice, true/false for true/false questions",
            "difficulty - easy/medium/hard",
            "explanation - Optional explanation for the answer"
        ],
        "notes": [
            "For true/false questions, leave option_c and option_d empty",
            "For multiple choice questions, provide all 4 options",
            "Correct answer should be A/B/C/D for multiple choice, true/false for true/false",
            "Difficulty levels: easy, medium, hard"
        ]
    }