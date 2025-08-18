"""
Test business logic service for ITADIAS Test Engine Microservice
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import random

from models import Question, Test, TestModule, TestStatus, QuestionType
from config import config

logger = logging.getLogger(__name__)

class TestService:
    """Service for test business logic"""
    
    def __init__(self):
        self.questions_per_test = config.test.questions_per_test
        self.time_limit_minutes = config.test.time_limit_minutes
        self.passing_score_percent = config.test.passing_score_percent
    
    async def can_start_test(self, db: AsyncSession, driver_record_id: uuid.UUID, module: TestModule) -> tuple[bool, Optional[str]]:
        """Check if a user can start a test for the given module"""
        try:
            # Check for active tests
            active_test_query = select(Test).where(
                and_(
                    Test.driver_record_id == driver_record_id,
                    Test.module == module,
                    Test.status == TestStatus.IN_PROGRESS
                )
            )
            result = await db.execute(active_test_query)
            active_test = result.scalar_one_or_none()
            
            if active_test:
                return False, "An active test already exists for this module"
            
            # Check for completed tests (one attempt only)
            completed_test_query = select(Test).where(
                and_(
                    Test.driver_record_id == driver_record_id,
                    Test.module == module,
                    Test.status == TestStatus.COMPLETED
                )
            )
            result = await db.execute(completed_test_query)
            completed_test = result.scalar_one_or_none()
            
            if completed_test:
                return False, "Test already completed for this module. Only one attempt allowed per booking."
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking test eligibility: {e}")
            return False, "Error checking test eligibility"
    
    async def get_available_questions(self, db: AsyncSession, module: TestModule) -> List[Question]:
        """Get all available questions for a module"""
        try:
            questions_query = select(Question).where(
                and_(
                    Question.module == module,
                    Question.is_active == True
                )
            )
            result = await db.execute(questions_query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting questions for module {module}: {e}")
            return []
    
    def select_test_questions(self, questions: List[Question], count: Optional[int] = None) -> List[Question]:
        """Select questions for a test with balanced difficulty distribution"""
        if count is None:
            count = self.questions_per_test
        
        if len(questions) < count:
            raise ValueError(f"Not enough questions available. Need {count}, have {len(questions)}")
        
        # For MVP, simple random selection
        # In production, you might want more sophisticated selection:
        # - Difficulty distribution (e.g., 30% easy, 50% medium, 20% hard)
        # - Topic coverage
        # - Question type distribution
        
        return random.sample(questions, count)
    
    async def calculate_test_score(self, db: AsyncSession, test: Test) -> tuple[float, int, int, bool]:
        """Calculate test score and determine pass/fail"""
        try:
            # Get the questions for this test
            question_ids = [uuid.UUID(qid) for qid in test.questions]
            questions_query = select(Question).where(Question.id.in_(question_ids))
            result = await db.execute(questions_query)
            questions = result.scalars().all()
            
            # Create a lookup for questions by ID
            question_lookup = {str(q.id): q for q in questions}
            
            correct_count = 0
            total_questions = len(questions)
            
            # Check each submitted answer
            if test.answers:
                for question_id, submitted_answer in test.answers.items():
                    if question_id in question_lookup:
                        question = question_lookup[question_id]
                        
                        # Normalize answers for comparison
                        correct_answer = question.correct_answer.lower()
                        submitted_answer = submitted_answer.lower()
                        
                        if correct_answer == submitted_answer:
                            correct_count += 1
            
            # Calculate percentage score
            score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
            passed = score_percentage >= self.passing_score_percent
            
            return score_percentage, correct_count, total_questions, passed
            
        except Exception as e:
            logger.error(f"Error calculating test score: {e}")
            return 0.0, 0, 0, False
    
    async def expire_old_tests(self, db: AsyncSession) -> int:
        """Mark old in-progress tests as expired"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=self.time_limit_minutes)
            
            # Find tests that should be expired
            expired_tests_query = select(Test).where(
                and_(
                    Test.status == TestStatus.IN_PROGRESS,
                    Test.start_time <= cutoff_time
                )
            )
            result = await db.execute(expired_tests_query)
            expired_tests = result.scalars().all()
            
            count = 0
            for test in expired_tests:
                test.status = TestStatus.EXPIRED
                test.end_time = test.start_time + timedelta(minutes=test.time_limit_minutes)
                count += 1
            
            if count > 0:
                await db.commit()
                logger.info(f"Expired {count} old tests")
            
            return count
            
        except Exception as e:
            logger.error(f"Error expiring old tests: {e}")
            return 0
    
    async def get_test_statistics(self, db: AsyncSession, module: Optional[TestModule] = None) -> Dict:
        """Get test statistics"""
        try:
            query = select(Test).where(Test.status == TestStatus.COMPLETED)
            if module:
                query = query.where(Test.module == module)
            
            result = await db.execute(query)
            completed_tests = result.scalars().all()
            
            if not completed_tests:
                return {
                    "total_tests": 0,
                    "pass_rate": 0.0,
                    "average_score": 0.0,
                    "module": module.value if module else "All"
                }
            
            total_tests = len(completed_tests)
            passed_tests = sum(1 for test in completed_tests if test.passed)
            total_score = sum(test.score or 0 for test in completed_tests)
            
            return {
                "total_tests": total_tests,
                "pass_rate": (passed_tests / total_tests) * 100,
                "average_score": total_score / total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "module": module.value if module else "All"
            }
            
        except Exception as e:
            logger.error(f"Error getting test statistics: {e}")
            return {
                "total_tests": 0,
                "pass_rate": 0.0,
                "average_score": 0.0,
                "error": str(e)
            }