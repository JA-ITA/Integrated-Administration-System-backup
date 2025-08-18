"""
SQLAlchemy models for ITADIAS Test Engine Microservice
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, Float, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field, validator
import enum
from database import Base
from config import config

# Enums

class TestModule(str, enum.Enum):
    PROVISIONAL = "Provisional"
    CLASS_B = "Class-B"
    CLASS_C = "Class-C"
    PPV = "PPV"
    HAZMAT = "HAZMAT"

class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"

class QuestionDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class TestStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"

# SQLAlchemy Models

class Question(Base):
    """Question model for test_engine schema"""
    __tablename__ = "questions"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module = Column(Enum(TestModule), nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # For multiple choice: ["A", "B", "C", "D"]
    correct_answer = Column(String(10), nullable=False)  # "A", "B", "C", "D" or "true", "false"
    difficulty = Column(Enum(QuestionDifficulty), default=QuestionDifficulty.MEDIUM, nullable=False)
    explanation = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Test(Base):
    """Test model for test_engine schema"""
    __tablename__ = "tests"
    __table_args__ = {"schema": config.db.schema}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_record_id = Column(UUID(as_uuid=True), nullable=False)  # Links to booking/candidate
    module = Column(Enum(TestModule), nullable=False)
    questions = Column(JSON, nullable=False)  # List of question IDs
    answers = Column(JSON, nullable=True)  # User submitted answers
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    time_limit_minutes = Column(Integer, default=25, nullable=False)
    status = Column(Enum(TestStatus), default=TestStatus.IN_PROGRESS, nullable=False)
    score = Column(Float, nullable=True)  # Score as percentage
    passed = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

# Pydantic Models for API

class QuestionBase(BaseModel):
    """Base question schema"""
    module: TestModule
    question_type: QuestionType
    text: str = Field(..., min_length=10)
    options: Optional[List[str]] = Field(None, description="Options for multiple choice questions")
    correct_answer: str = Field(..., description="Correct answer (A/B/C/D for MC, true/false for TF)")
    difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM
    explanation: Optional[str] = None
    
    @validator('options')
    def validate_options(cls, v, values):
        question_type = values.get('question_type')
        if question_type == QuestionType.MULTIPLE_CHOICE:
            if not v or len(v) != 4:
                raise ValueError('Multiple choice questions must have exactly 4 options')
        elif question_type == QuestionType.TRUE_FALSE:
            if v is not None:
                raise ValueError('True/false questions should not have options')
        return v
    
    @validator('correct_answer')
    def validate_correct_answer(cls, v, values):
        question_type = values.get('question_type')
        if question_type == QuestionType.MULTIPLE_CHOICE:
            if v not in ['A', 'B', 'C', 'D']:
                raise ValueError('Multiple choice answer must be A, B, C, or D')
        elif question_type == QuestionType.TRUE_FALSE:
            if v.lower() not in ['true', 'false']:
                raise ValueError('True/false answer must be true or false')
        return v

class QuestionCreate(QuestionBase):
    """Schema for creating a question"""
    pass

class QuestionResponse(QuestionBase):
    """Schema for question response"""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class QuestionForTest(BaseModel):
    """Question schema for test (without correct answer)"""
    id: uuid.UUID
    question_type: QuestionType
    text: str
    options: Optional[List[str]]
    
    class Config:
        from_attributes = True

class TestStartRequest(BaseModel):
    """Schema for starting a test"""
    driver_record_id: uuid.UUID
    module: TestModule

class TestStartResponse(BaseModel):
    """Schema for test start response"""
    test_id: uuid.UUID
    questions: List[QuestionForTest]
    time_limit_minutes: int
    start_time: datetime
    expires_at: datetime

class AnswerSubmission(BaseModel):
    """Schema for individual answer submission"""
    question_id: uuid.UUID
    answer: str = Field(..., description="Answer: A/B/C/D for MC, true/false for TF")

class TestSubmitRequest(BaseModel):
    """Schema for test submission"""
    answers: List[AnswerSubmission]

class TestSubmitResponse(BaseModel):
    """Schema for test submission response"""
    test_id: uuid.UUID
    score: float
    passed: bool
    correct_answers: int
    total_questions: int
    submitted_at: datetime

class TestResult(BaseModel):
    """Schema for test result"""
    id: uuid.UUID
    driver_record_id: uuid.UUID
    module: TestModule
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime]
    score: Optional[float]
    passed: Optional[bool]
    time_limit_minutes: int
    
    class Config:
        from_attributes = True

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

# Utility functions
def generate_test_questions(questions_pool: List[Question], count: int = 20) -> List[Question]:
    """Generate a random selection of questions for a test"""
    import random
    
    # Ensure we have enough questions
    if len(questions_pool) < count:
        raise ValueError(f"Not enough questions available. Need {count}, have {len(questions_pool)}")
    
    # For now, simple random selection
    # In production, you might want more sophisticated selection (difficulty distribution, etc.)
    return random.sample(questions_pool, count)

def calculate_score(submitted_answers: Dict[str, str], questions: List[Question]) -> tuple[float, int, int]:
    """Calculate test score based on submitted answers"""
    correct_count = 0
    total_questions = len(questions)
    
    # Create a lookup for questions by ID
    question_lookup = {str(q.id): q for q in questions}
    
    for question_id, submitted_answer in submitted_answers.items():
        if question_id in question_lookup:
            question = question_lookup[question_id]
            
            # Normalize answers for comparison
            correct_answer = question.correct_answer.lower()
            submitted_answer = submitted_answer.lower()
            
            if correct_answer == submitted_answer:
                correct_count += 1
    
    # Calculate percentage score
    score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    return score_percentage, correct_count, total_questions