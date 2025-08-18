"""
Test routes for ITADIAS Test Engine Microservice
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import random

from database import get_db
from models import (
    Question, Test, TestModule, TestStatus, QuestionType,
    TestStartRequest, TestStartResponse, TestSubmitRequest, TestSubmitResponse,
    QuestionForTest, AnswerSubmission, calculate_score
)
from services.test_service import TestService
from services.event_service import EventService
from config import config

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/tests/start", response_model=TestStartResponse)
async def start_test(
    request: TestStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start a new test"""
    try:
        if not db:
            raise HTTPException(
                status_code=503,
                detail="Database service unavailable"
            )
        
        # Check if user already has an active test for this module
        existing_test_query = select(Test).where(
            and_(
                Test.driver_record_id == request.driver_record_id,
                Test.module == request.module,
                Test.status == TestStatus.IN_PROGRESS
            )
        )
        result = await db.execute(existing_test_query)
        existing_test = result.scalar_one_or_none()
        
        if existing_test:
            raise HTTPException(
                status_code=409,
                detail="An active test already exists for this module"
            )
        
        # Check if user has already completed a test for this module (one attempt only)
        completed_test_query = select(Test).where(
            and_(
                Test.driver_record_id == request.driver_record_id,
                Test.module == request.module,
                Test.status == TestStatus.COMPLETED
            )
        )
        result = await db.execute(completed_test_query)
        completed_test = result.scalar_one_or_none()
        
        if completed_test:
            raise HTTPException(
                status_code=409,
                detail="Test already completed for this module. Only one attempt allowed per booking."
            )
        
        # Get questions for the specified module
        questions_query = select(Question).where(
            and_(
                Question.module == request.module,
                Question.is_active == True
            )
        )
        result = await db.execute(questions_query)
        available_questions = result.scalars().all()
        
        if len(available_questions) < config.test.questions_per_test:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough questions available for {request.module}. Need {config.test.questions_per_test}, have {len(available_questions)}"
            )
        
        # Select random questions
        selected_questions = random.sample(available_questions, config.test.questions_per_test)
        
        # Create test record
        start_time = datetime.now(timezone.utc)
        test = Test(
            driver_record_id=request.driver_record_id,
            module=request.module,
            questions=[str(q.id) for q in selected_questions],
            start_time=start_time,
            time_limit_minutes=config.test.time_limit_minutes,
            status=TestStatus.IN_PROGRESS
        )
        
        db.add(test)
        await db.commit()
        await db.refresh(test)
        
        # Prepare questions for response (without correct answers)
        questions_for_test = [
            QuestionForTest(
                id=q.id,
                question_type=q.question_type,
                text=q.text,
                options=q.options if q.question_type == QuestionType.MULTIPLE_CHOICE else None
            )
            for q in selected_questions
        ]
        
        expires_at = start_time + timedelta(minutes=config.test.time_limit_minutes)
        
        logger.info(f"Started test {test.id} for driver {request.driver_record_id}, module {request.module}")
        
        return TestStartResponse(
            test_id=test.id,
            questions=questions_for_test,
            time_limit_minutes=config.test.time_limit_minutes,
            start_time=start_time,
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting test: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to start test"
        )

@router.post("/tests/{test_id}/submit", response_model=TestSubmitResponse)
async def submit_test(
    test_id: uuid.UUID,
    request: TestSubmitRequest,
    db: AsyncSession = Depends(get_db),
    event_service: EventService = Depends(lambda: EventService())
):
    """Submit test answers"""
    try:
        if not db:
            raise HTTPException(
                status_code=503,
                detail="Database service unavailable"
            )
        
        # Get the test
        test_query = select(Test).where(Test.id == test_id)
        result = await db.execute(test_query)
        test = result.scalar_one_or_none()
        
        if not test:
            raise HTTPException(
                status_code=404,
                detail="Test not found"
            )
        
        if test.status != TestStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=400,
                detail="Test is not in progress"
            )
        
        # Check if test has expired
        now = datetime.now(timezone.utc)
        expires_at = test.start_time + timedelta(minutes=test.time_limit_minutes)
        
        if now > expires_at:
            # Mark test as expired
            test.status = TestStatus.EXPIRED
            test.end_time = expires_at
            await db.commit()
            raise HTTPException(
                status_code=410,
                detail="Test has expired"
            )
        
        # Get the questions for this test
        question_ids = [uuid.UUID(qid) for qid in test.questions]
        questions_query = select(Question).where(Question.id.in_(question_ids))
        result = await db.execute(questions_query)
        questions = result.scalars().all()
        
        # Convert submitted answers to dict
        submitted_answers = {str(answer.question_id): answer.answer for answer in request.answers}
        
        # Calculate score
        score_percentage, correct_count, total_questions = calculate_score(submitted_answers, questions)
        passed = score_percentage >= config.test.passing_score_percent
        
        # Update test with results
        test.answers = submitted_answers
        test.end_time = now
        test.score = score_percentage
        test.passed = passed
        test.status = TestStatus.COMPLETED
        
        await db.commit()
        
        # Publish TestCompleted event
        try:
            await event_service.publish_test_completed(
                driver_record_id=test.driver_record_id,
                test_id=test.id,
                score=score_percentage,
                passed=passed,
                timestamp=now
            )
        except Exception as e:
            logger.warning(f"Failed to publish TestCompleted event: {e}")
        
        logger.info(f"Test {test_id} completed: score={score_percentage:.1f}%, passed={passed}")
        
        return TestSubmitResponse(
            test_id=test.id,
            score=score_percentage,
            passed=passed,
            correct_answers=correct_count,
            total_questions=total_questions,
            submitted_at=now
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting test: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to submit test"
        )

@router.get("/tests/{test_id}/status")
async def get_test_status(
    test_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get test status and time remaining"""
    try:
        if not db:
            raise HTTPException(
                status_code=503,
                detail="Database service unavailable"
            )
        
        test_query = select(Test).where(Test.id == test_id)
        result = await db.execute(test_query)
        test = result.scalar_one_or_none()
        
        if not test:
            raise HTTPException(
                status_code=404,
                detail="Test not found"
            )
        
        now = datetime.now(timezone.utc)
        expires_at = test.start_time + timedelta(minutes=test.time_limit_minutes)
        time_remaining_seconds = max(0, int((expires_at - now).total_seconds()))
        
        return {
            "test_id": test.id,
            "status": test.status,
            "start_time": test.start_time,
            "expires_at": expires_at,
            "time_remaining_seconds": time_remaining_seconds,
            "score": test.score,
            "passed": test.passed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get test status"
        )