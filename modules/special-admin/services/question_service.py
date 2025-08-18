"""
Question service for CSV upload and processing
Integrates with test-engine microservice
"""
import csv
import io
import base64
import uuid
import logging
import httpx
from typing import Dict, Any, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import QuestionModule
from config import config

logger = logging.getLogger(__name__)

class QuestionService:
    """Service for managing questions and CSV uploads"""
    
    def __init__(self):
        self.test_engine_url = "http://localhost:8005"
        
    async def process_csv_upload(self, db: AsyncSession, module_code: str, 
                                csv_data: str, created_by: str) -> Dict[str, Any]:
        """Process CSV upload and create/update questions in test-engine"""
        try:
            # Parse CSV data
            questions = await self._parse_csv_data(csv_data)
            if not questions:
                return {
                    "success": False,
                    "error": "No valid questions found in CSV",
                    "questions_processed": 0,
                    "questions_created": 0,
                    "questions_updated": 0,
                    "errors": ["CSV parsing failed or no questions found"]
                }
            
            # Verify module exists
            module = await self._get_or_create_module(db, module_code, created_by)
            if not module:
                return {
                    "success": False,
                    "error": f"Failed to create or find module: {module_code}",
                    "questions_processed": 0,
                    "questions_created": 0,
                    "questions_updated": 0,
                    "errors": [f"Module {module_code} could not be created"]
                }
            
            # Process questions in test-engine
            result = await self._upload_questions_to_test_engine(questions, module_code)
            
            # Update module question count
            if result["success"]:
                await self._update_module_question_count(db, module.id, result["questions_created"])
            
            return result
            
        except Exception as e:
            logger.error(f"CSV upload processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "questions_processed": 0,
                "questions_created": 0,
                "questions_updated": 0,
                "errors": [str(e)]
            }
    
    async def _parse_csv_data(self, csv_data: str) -> List[Dict[str, Any]]:
        """Parse CSV data and extract questions"""
        questions = []
        
        try:
            # Handle base64 encoded data
            if csv_data.startswith('data:'):
                # Extract base64 part
                base64_data = csv_data.split(',')[1]
                csv_content = base64.b64decode(base64_data).decode('utf-8')
            else:
                csv_content = csv_data
            
            # Parse CSV
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            for row_num, row in enumerate(reader, start=1):
                try:
                    question = self._parse_question_row(row, row_num)
                    if question:
                        questions.append(question)
                except Exception as e:
                    logger.warning(f"Failed to parse row {row_num}: {e}")
                    continue
            
            return questions
            
        except Exception as e:
            logger.error(f"CSV parsing failed: {e}")
            return []
    
    def _parse_question_row(self, row: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
        """Parse a single CSV row into question format"""
        try:
            # Expected CSV columns: question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty, explanation
            question_text = row.get('question_text', '').strip()
            if not question_text:
                return None
            
            # Determine question type based on options
            option_a = row.get('option_a', '').strip()
            option_b = row.get('option_b', '').strip()
            option_c = row.get('option_c', '').strip()
            option_d = row.get('option_d', '').strip()
            
            # Check if it's a true/false question
            if (not option_c and not option_d and 
                option_a.lower() in ['true', 'false'] and 
                option_b.lower() in ['true', 'false']):
                question_type = "true_false"
                options = None
            elif option_a and option_b and option_c and option_d:
                question_type = "multiple_choice"
                options = [option_a, option_b, option_c, option_d]
            else:
                return None
            
            correct_answer = row.get('correct_answer', '').strip()
            if not correct_answer:
                return None
            
            difficulty = row.get('difficulty', 'medium').strip().lower()
            if difficulty not in ['easy', 'medium', 'hard']:
                difficulty = 'medium'
            
            explanation = row.get('explanation', '').strip()
            
            return {
                "question_type": question_type,
                "text": question_text,
                "options": options,
                "correct_answer": correct_answer,
                "difficulty": difficulty,
                "explanation": explanation if explanation else None
            }
            
        except Exception as e:
            logger.error(f"Error parsing question row {row_num}: {e}")
            return None
    
    async def _get_or_create_module(self, db: AsyncSession, module_code: str, 
                                  created_by: str) -> Optional[QuestionModule]:
        """Get existing module or create new one"""
        try:
            # Check if module exists
            stmt = select(QuestionModule).where(QuestionModule.code == module_code)
            result = await db.execute(stmt)
            module = result.scalars().first()
            
            if module:
                return module
            
            # Create new module
            new_module = QuestionModule(
                code=module_code,
                description=f"Module for {module_code} questions",
                category="Special",
                created_by=created_by
            )
            
            db.add(new_module)
            await db.commit()
            await db.refresh(new_module)
            
            logger.info(f"Created new question module: {module_code}")
            return new_module
            
        except Exception as e:
            logger.error(f"Error getting/creating module {module_code}: {e}")
            await db.rollback()
            return None
    
    async def _upload_questions_to_test_engine(self, questions: List[Dict[str, Any]], 
                                             module_code: str) -> Dict[str, Any]:
        """Upload questions to test-engine microservice"""
        try:
            created_count = 0
            updated_count = 0
            errors = []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for question in questions:
                    try:
                        # Prepare question data for test-engine
                        question_data = {
                            "module": module_code,
                            "question_type": question["question_type"],
                            "text": question["text"],
                            "options": question["options"],
                            "correct_answer": question["correct_answer"],
                            "difficulty": question["difficulty"],
                            "explanation": question.get("explanation")
                        }
                        
                        # Send to test-engine (assuming it has a questions endpoint)
                        response = await client.post(
                            f"{self.test_engine_url}/api/v1/questions",
                            json=question_data,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if response.status_code == 201:
                            created_count += 1
                        elif response.status_code == 200:
                            updated_count += 1
                        else:
                            errors.append(f"Failed to create question: {response.text}")
                            
                    except Exception as e:
                        errors.append(f"Error processing question: {str(e)}")
                        continue
            
            return {
                "success": True,
                "module_code": module_code,
                "questions_processed": len(questions),
                "questions_created": created_count,
                "questions_updated": updated_count,
                "errors": errors,
                "message": f"Successfully processed {created_count + updated_count} questions for module {module_code}"
            }
            
        except Exception as e:
            logger.error(f"Error uploading questions to test-engine: {e}")
            return {
                "success": False,
                "error": str(e),
                "module_code": module_code,
                "questions_processed": len(questions),
                "questions_created": 0,
                "questions_updated": 0,
                "errors": [str(e)],
                "message": f"Failed to upload questions: {str(e)}"
            }
    
    async def _update_module_question_count(self, db: AsyncSession, module_id: uuid.UUID, 
                                          count_increment: int):
        """Update question count for module"""
        try:
            stmt = (
                update(QuestionModule)
                .where(QuestionModule.id == module_id)
                .values(question_count=QuestionModule.question_count + count_increment)
            )
            await db.execute(stmt)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error updating module question count: {e}")
            await db.rollback()
    
    async def get_available_modules(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all available question modules"""
        try:
            stmt = select(QuestionModule).where(QuestionModule.status == "active")
            result = await db.execute(stmt)
            modules = result.scalars().all()
            
            return [
                {
                    "id": str(module.id),
                    "code": module.code,
                    "description": module.description,
                    "category": module.category,
                    "question_count": module.question_count,
                    "status": module.status,
                    "created_at": module.created_at.isoformat(),
                    "created_by": module.created_by
                }
                for module in modules
            ]
            
        except Exception as e:
            logger.error(f"Error getting modules: {e}")
            return []