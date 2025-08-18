"""
Questions management routes for Test Engine Microservice
Allows creation and management of questions from special-admin service
"""
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_session
from models import Question, QuestionCreate, QuestionResponse, TestModule, QuestionType, QuestionDifficulty

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(question_data: QuestionCreate):
    """Create a new question"""
    try:
        async with get_db_session() as db:
            # Create new question
            question = Question(**question_data.model_dump())
            db.add(question)
            await db.commit()
            await db.refresh(question)
            
            logger.info(f"Created question for module {question.module}: {question.id}")
            return QuestionResponse.model_validate(question)
            
    except Exception as e:
        logger.error(f"Error creating question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question: {str(e)}"
        )

@router.get("/questions", response_model=List[QuestionResponse])
async def get_questions(
    module: TestModule = None,
    skip: int = 0,
    limit: int = 100,
    include_answers: bool = False
):
    """Get questions, optionally filtered by module"""
    try:
        async with get_db_session() as db:
            stmt = select(Question)
            
            if module:
                stmt = stmt.where(Question.module == module)
            
            stmt = stmt.where(Question.is_active == True).offset(skip).limit(limit)
            result = await db.execute(stmt)
            questions = result.scalars().all()
            
            # If not including answers (for admin use), return full data
            # If including answers is False (for test use), this would need different handling
            return [QuestionResponse.model_validate(q) for q in questions]
            
    except Exception as e:
        logger.error(f"Error getting questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get questions: {str(e)}"
        )

@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: uuid.UUID):
    """Get a specific question"""
    try:
        async with get_db_session() as db:
            stmt = select(Question).where(Question.id == question_id)
            result = await db.execute(stmt)
            question = result.scalars().first()
            
            if not question:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Question not found"
                )
            
            return QuestionResponse.model_validate(question)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting question {question_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get question: {str(e)}"
        )

@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(question_id: uuid.UUID, question_data: QuestionCreate):
    """Update a question"""
    try:
        async with get_db_session() as db:
            # Check if question exists
            stmt = select(Question).where(Question.id == question_id)
            result = await db.execute(stmt)
            question = result.scalars().first()
            
            if not question:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Question not found"
                )
            
            # Update question
            update_dict = question_data.model_dump()
            stmt = (
                update(Question)
                .where(Question.id == question_id)
                .values(**update_dict)
            )
            await db.execute(stmt)
            await db.commit()
            await db.refresh(question)
            
            logger.info(f"Updated question: {question_id}")
            return QuestionResponse.model_validate(question)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating question {question_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update question: {str(e)}"
        )

@router.delete("/questions/{question_id}")
async def delete_question(question_id: uuid.UUID):
    """Delete a question (mark as inactive)"""
    try:
        async with get_db_session() as db:
            # Check if question exists
            stmt = select(Question).where(Question.id == question_id)
            result = await db.execute(stmt)
            question = result.scalars().first()
            
            if not question:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Question not found"
                )
            
            # Mark as inactive instead of deleting
            stmt = (
                update(Question)
                .where(Question.id == question_id)
                .values(is_active=False)
            )
            await db.execute(stmt)
            await db.commit()
            
            logger.info(f"Deactivated question: {question_id}")
            return {"message": "Question deactivated successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting question {question_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete question: {str(e)}"
        )

@router.get("/questions/count/{module}")
async def get_question_count(module: TestModule):
    """Get question count for a specific module"""
    try:
        async with get_db_session() as db:
            from sqlalchemy import func
            stmt = select(func.count(Question.id)).where(
                Question.module == module,
                Question.is_active == True
            )
            result = await db.execute(stmt)
            count = result.scalar() or 0
            
            return {
                "module": module,
                "count": count,
                "min_required": 20  # Assuming minimum 20 questions needed for a test
            }
            
    except Exception as e:
        logger.error(f"Error getting question count for {module}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get question count: {str(e)}"
        )

@router.get("/modules/supported")
async def get_supported_modules():
    """Get list of supported test modules"""
    return {
        "modules": [
            {
                "code": module.value,
                "name": module.value,
                "description": f"Questions for {module.value} module"
            }
            for module in TestModule
        ]
    }