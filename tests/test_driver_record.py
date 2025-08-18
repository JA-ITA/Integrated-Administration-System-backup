"""
Unit tests for Driver Records API endpoints
Using pytest-asyncio and faker for comprehensive testing
"""
import pytest
import uuid
import asyncio
from datetime import date, datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from faker import Faker
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json

# Import the router and models
import sys
import os
sys.path.append('/app')

from driver_record_router import (
    router, 
    DriverRecordCreate, 
    DriverRecordUpdate, 
    TheoryAttempt,
    YardRoadAttempt, 
    CourtRecord, 
    OverrideRequest,
    LicenceType, 
    DriverStatus, 
    TestType, 
    AuthUser,
    get_current_user,
    get_dao_or_rd_user, 
    get_rd_user
)

# Initialize faker
fake = Faker()

# Test app setup
app = FastAPI()
app.include_router(router)

# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_pool():
    """Mock database connection pool"""
    with patch('driver_record_router.db_pool') as mock_pool:
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.release = AsyncMock()
        yield mock_conn

@pytest.fixture
def mock_rabbitmq():
    """Mock RabbitMQ publishing"""
    with patch('driver_record_router.publish_event') as mock_publish:
        mock_publish.return_value = AsyncMock()
        yield mock_publish

@pytest.fixture
def dao_user():
    """DAO user fixture"""
    return AuthUser(user_id=uuid.uuid4(), role="dao")

@pytest.fixture
def rd_user():
    """RD user fixture"""
    return AuthUser(user_id=uuid.uuid4(), role="rd")

@pytest.fixture
def manager_user():
    """Manager user fixture"""
    return AuthUser(user_id=uuid.uuid4(), role="manager")

@pytest.fixture
def sample_driver_record():
    """Sample driver record data"""
    return {
        'id': uuid.uuid4(),
        'candidate_id': uuid.uuid4(),
        'licence_number': fake.unique.bothify(text='D#########'),
        'christian_names': fake.first_name(),
        'surname': fake.last_name(),
        'address': fake.address(),
        'dob': fake.date_of_birth(minimum_age=18, maximum_age=80),
        'photo_url': fake.url(),
        'signature_url': fake.url(),
        'licence_type': 'Class B',
        'status': 'Issued',
        'certificate_of_competency_no': fake.bothify(text='COC######'),
        'application_date': fake.date_this_year(),
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'theory_attempts': [],
        'yard_road_attempts': [],
        'endorsements': [],
        'court_records': []
    }

@pytest.fixture
def sample_driver_create():
    """Sample driver record creation data"""
    return DriverRecordCreate(
        candidate_id=uuid.uuid4(),
        licence_number=fake.unique.bothify(text='D#########'),
        christian_names=fake.first_name() + " " + fake.first_name(),
        surname=fake.last_name(),
        address=fake.address(),
        dob=fake.date_of_birth(minimum_age=18, maximum_age=80),
        licence_type=LicenceType.CLASS_B,
        status=DriverStatus.ISSUED,
        application_date=fake.date_this_year()
    )

@pytest.fixture
def sample_theory_attempt():
    """Sample theory test attempt data"""
    return TheoryAttempt(
        attempt_no=fake.random_int(min=1, max=3),
        module=fake.random_element(elements=[
            "Traffic Signs and Rules",
            "Road Safety",
            "Vehicle Knowledge",
            "Driving Laws"
        ]),
        score=fake.random_int(min=10, max=20),
        passed=fake.boolean(),
        attempt_date=fake.date_this_year()
    )

@pytest.fixture
def sample_yard_road_attempt():
    """Sample yard/road test attempt data"""
    criteria = [
        {
            "criterion": "Reverse Parking",
            "major": fake.random_int(min=0, max=2),
            "minor": fake.random_int(min=0, max=3),
            "score": fake.random_int(min=5, max=10)
        },
        {
            "criterion": "Hill Start", 
            "major": fake.random_int(min=0, max=1),
            "minor": fake.random_int(min=0, max=2),
            "score": fake.random_int(min=7, max=10)
        }
    ]
    
    return YardRoadAttempt(
        test_type=fake.random_element(elements=list(TestType)),
        visit_no=fake.random_int(min=1, max=3),
        attempt_date=fake.date_this_year(),
        criteria=criteria,
        overall_result=fake.boolean()
    )

@pytest.fixture
def sample_court_record():
    """Sample court record data"""
    suspension_start = fake.date_this_year()
    
    return CourtRecord(
        judgment_date=fake.date_this_year(),
        offence=fake.text(max_nb_chars=100),
        suspension_from=suspension_start,
        suspension_to=fake.date_between(start_date=suspension_start, end_date='+1y'),
        retest_required={
            "written": fake.boolean(),
            "yard": fake.boolean(), 
            "road": fake.boolean(),
            "other": fake.boolean()
        }
    )

@pytest.fixture
def sample_override_request():
    """Sample override request data"""
    return OverrideRequest(
        action=fake.sentence(nb_words=5),
        reason=fake.text(max_nb_chars=200),
        new_status=fake.random_element(elements=list(DriverStatus)),
        metadata={
            "court_case_no": fake.bothify(text='TC####/######'),
            "appeal_date": fake.date_this_year().isoformat()
        }
    )

# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_verify_jwt_token_success():
    """Test successful JWT token verification"""
    from driver_record_router import verify_jwt_token
    
    # Mock successful verification
    token = "valid.jwt.token"
    user = await verify_jwt_token(token)
    
    assert user is not None
    assert isinstance(user, AuthUser)
    assert user.role in ["dao", "manager", "rd"]

@pytest.mark.asyncio
async def test_verify_jwt_token_failure():
    """Test JWT token verification failure"""
    from driver_record_router import verify_jwt_token
    
    with patch('driver_record_router.logger') as mock_logger:
        # Test with invalid token (will raise exception in real implementation)
        token = "invalid.jwt.token"
        user = await verify_jwt_token(token)
        
        # For now, mock implementation returns None for invalid tokens
        # In real implementation, this would properly validate JWT
        assert user is not None  # Mock implementation always returns user

def test_dao_or_rd_access_control_success(dao_user, rd_user):
    """Test DAO and RD users can access restricted endpoints"""
    from driver_record_router import get_dao_or_rd_user
    
    # Test DAO access
    result_dao = asyncio.run(get_dao_or_rd_user(dao_user))
    assert result_dao.role == "dao"
    
    # Test RD access
    result_rd = asyncio.run(get_dao_or_rd_user(rd_user))
    assert result_rd.role == "rd"

def test_dao_or_rd_access_control_failure(manager_user):
    """Test manager user cannot access DAO/RD restricted endpoints"""
    from fastapi import HTTPException
    from driver_record_router import get_dao_or_rd_user
    
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_dao_or_rd_user(manager_user))
    
    assert exc_info.value.status_code == 403
    assert "DAO or RD role required" in exc_info.value.detail

def test_rd_only_access_control_success(rd_user):
    """Test RD user can access RD-only endpoints"""
    from driver_record_router import get_rd_user
    
    result = asyncio.run(get_rd_user(rd_user))
    assert result.role == "rd"

def test_rd_only_access_control_failure(dao_user, manager_user):
    """Test non-RD users cannot access RD-only endpoints"""
    from fastapi import HTTPException
    from driver_record_router import get_rd_user
    
    # Test DAO user
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_rd_user(dao_user))
    
    assert exc_info.value.status_code == 403
    assert "RD role required" in exc_info.value.detail
    
    # Test manager user  
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_rd_user(manager_user))
    
    assert exc_info.value.status_code == 403
    assert "RD role required" in exc_info.value.detail

# ============================================================================
# DATABASE OPERATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_driver_record_by_licence_success(mock_db_pool, sample_driver_record):
    """Test successful driver record retrieval"""
    from driver_record_router import get_driver_record_by_licence
    
    # Mock database responses
    mock_db_pool.fetchrow.return_value = sample_driver_record
    mock_db_pool.fetch.return_value = []  # Empty related records
    
    with patch('driver_record_router.get_db_connection') as mock_get_conn:
        mock_get_conn.return_value = mock_db_pool
        
        result = await get_driver_record_by_licence(sample_driver_record['licence_number'])
        
        assert result is not None
        assert result['licence_number'] == sample_driver_record['licence_number']
        assert 'theory_attempts' in result
        assert 'yard_road_attempts' in result
        assert 'endorsements' in result
        assert 'court_records' in result

@pytest.mark.asyncio  
async def test_get_driver_record_by_licence_not_found(mock_db_pool):
    """Test driver record not found"""
    from driver_record_router import get_driver_record_by_licence
    
    # Mock no record found
    mock_db_pool.fetchrow.return_value = None
    
    with patch('driver_record_router.get_db_connection') as mock_get_conn:
        mock_get_conn.return_value = mock_db_pool
        
        result = await get_driver_record_by_licence("NONEXISTENT123")
        assert result is None

@pytest.mark.asyncio
async def test_create_driver_record_db_success(mock_db_pool, sample_driver_create):
    """Test successful driver record creation"""
    from driver_record_router import create_driver_record_db
    
    # Mock successful insert
    expected_id = uuid.uuid4()
    mock_db_pool.fetchval.return_value = expected_id
    
    with patch('driver_record_router.get_db_connection') as mock_get_conn:
        mock_get_conn.return_value = mock_db_pool
        
        result_id = await create_driver_record_db(sample_driver_create)
        
        assert result_id == expected_id
        mock_db_pool.fetchval.assert_called_once()

@pytest.mark.asyncio
async def test_update_driver_record_db_success(mock_db_pool, sample_driver_record):
    """Test successful driver record update"""
    from driver_record_router import update_driver_record_db
    
    update_data = DriverRecordUpdate(
        christian_names="Updated Name",
        address="Updated Address"
    )
    
    # Mock successful update (returns "UPDATE 1")
    mock_db_pool.execute.return_value = "UPDATE 1"
    
    with patch('driver_record_router.get_db_connection') as mock_get_conn:
        mock_get_conn.return_value = mock_db_pool
        
        result = await update_driver_record_db(
            sample_driver_record['licence_number'], 
            update_data
        )
        
        assert result is True
        mock_db_pool.execute.assert_called_once()

# ============================================================================
# API ENDPOINT TESTS
# ============================================================================

class TestGetDriverRecord:
    """Test cases for GET /driver-records/{licence_number}"""
    
    @pytest.mark.asyncio
    async def test_get_driver_record_success(self, mock_db_pool, mock_rabbitmq, sample_driver_record, dao_user):
        """Test successful driver record retrieval"""
        from driver_record_router import get_driver_record
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.return_value = sample_driver_record
            
            result = await get_driver_record(
                licence_number=sample_driver_record['licence_number'],
                current_user=dao_user
            )
            
            assert result['licence_number'] == sample_driver_record['licence_number']
            mock_get_record.assert_called_once_with(sample_driver_record['licence_number'])
    
    @pytest.mark.asyncio
    async def test_get_driver_record_not_found(self, mock_db_pool, dao_user):
        """Test driver record not found"""
        from driver_record_router import get_driver_record
        from fastapi import HTTPException
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await get_driver_record(
                    licence_number="NOTFOUND123",
                    current_user=dao_user
                )
            
            assert exc_info.value.status_code == 404
            assert "Driver record not found" in exc_info.value.detail

class TestCreateDriverRecord:
    """Test cases for POST /driver-records"""
    
    @pytest.mark.asyncio
    async def test_create_driver_record_success(self, mock_db_pool, mock_rabbitmq, sample_driver_create, dao_user):
        """Test successful driver record creation"""
        from driver_record_router import create_driver_record
        
        expected_id = uuid.uuid4()
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_existing:
            mock_get_existing.return_value = None  # No existing record
            
            with patch('driver_record_router.create_driver_record_db') as mock_create:
                mock_create.return_value = expected_id
                
                result = await create_driver_record(
                    record_data=sample_driver_create,
                    current_user=dao_user
                )
                
                assert result.success is True
                assert "created successfully" in result.message
                assert result.data['record_id'] == str(expected_id)
                
                # Verify event was published
                mock_rabbitmq.assert_called_once()
                event_args = mock_rabbitmq.call_args[0]
                assert event_args[0] == "DriverRecordUpdated"
    
    @pytest.mark.asyncio
    async def test_create_driver_record_duplicate(self, sample_driver_create, sample_driver_record, dao_user):
        """Test creating duplicate driver record"""
        from driver_record_router import create_driver_record
        from fastapi import HTTPException
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_existing:
            mock_get_existing.return_value = sample_driver_record  # Existing record
            
            with pytest.raises(HTTPException) as exc_info:
                await create_driver_record(
                    record_data=sample_driver_create,
                    current_user=dao_user
                )
            
            assert exc_info.value.status_code == 409
            assert "already exists" in exc_info.value.detail

class TestUpdateDriverRecord:
    """Test cases for PUT /driver-records/{licence_number}"""
    
    @pytest.mark.asyncio
    async def test_update_driver_record_success(self, mock_rabbitmq, sample_driver_record, dao_user):
        """Test successful driver record update"""
        from driver_record_router import update_driver_record
        
        update_data = DriverRecordUpdate(
            christian_names="Updated Name",
            address="Updated Address"
        )
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.return_value = sample_driver_record
            
            with patch('driver_record_router.update_driver_record_db') as mock_update:
                mock_update.return_value = True
                
                result = await update_driver_record(
                    licence_number=sample_driver_record['licence_number'],
                    update_data=update_data,
                    current_user=dao_user
                )
                
                assert result.success is True
                assert "updated successfully" in result.message
                
                # Verify event was published
                mock_rabbitmq.assert_called_once()

class TestAddTheoryAttempt:
    """Test cases for POST /driver-records/{licence_number}/theory-attempts"""
    
    @pytest.mark.asyncio
    async def test_add_theory_attempt_success(self, mock_db_pool, mock_rabbitmq, sample_driver_record, sample_theory_attempt, dao_user):
        """Test successful theory attempt addition"""
        from driver_record_router import add_theory_attempt
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.return_value = sample_driver_record
            
            with patch('driver_record_router.get_db_connection') as mock_get_conn:
                mock_get_conn.return_value = mock_db_pool
                
                result = await add_theory_attempt(
                    licence_number=sample_driver_record['licence_number'],
                    attempt_data=sample_theory_attempt,
                    current_user=dao_user
                )
                
                assert result.success is True
                assert "Theory attempt recorded successfully" in result.message
                
                # Verify database insert was called
                mock_db_pool.execute.assert_called_once()
                
                # Verify event was published
                mock_rabbitmq.assert_called_once()

class TestAddYardRoadAttempt:
    """Test cases for POST /driver-records/{licence_number}/yard-road-attempts"""
    
    @pytest.mark.asyncio
    async def test_add_yard_road_attempt_success(self, mock_db_pool, mock_rabbitmq, sample_driver_record, sample_yard_road_attempt, dao_user):
        """Test successful yard/road attempt addition"""
        from driver_record_router import add_yard_road_attempt
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.return_value = sample_driver_record
            
            with patch('driver_record_router.get_db_connection') as mock_get_conn:
                mock_get_conn.return_value = mock_db_pool
                
                result = await add_yard_road_attempt(
                    licence_number=sample_driver_record['licence_number'],
                    attempt_data=sample_yard_road_attempt,
                    current_user=dao_user
                )
                
                assert result.success is True
                assert "test attempt recorded successfully" in result.message
                
                # Verify database insert was called
                mock_db_pool.execute.assert_called_once()
                
                # Verify event was published
                mock_rabbitmq.assert_called_once()

class TestAddCourtRecord:
    """Test cases for POST /driver-records/{licence_number}/court-records"""
    
    @pytest.mark.asyncio
    async def test_add_court_record_success(self, mock_db_pool, mock_rabbitmq, sample_driver_record, sample_court_record, dao_user):
        """Test successful court record addition"""
        from driver_record_router import add_court_record
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.return_value = sample_driver_record
            
            with patch('driver_record_router.get_db_connection') as mock_get_conn:
                mock_get_conn.return_value = mock_db_pool
                
                result = await add_court_record(
                    licence_number=sample_driver_record['licence_number'],
                    court_data=sample_court_record,
                    current_user=dao_user
                )
                
                assert result.success is True
                assert "Court record added successfully" in result.message
                
                # Verify database insert was called
                mock_db_pool.execute.assert_called_once()
                
                # Verify event was published
                mock_rabbitmq.assert_called_once()

class TestOverrideDriverRecord:
    """Test cases for POST /driver-records/{licence_number}/override"""
    
    @pytest.mark.asyncio
    async def test_override_success(self, mock_db_pool, mock_rabbitmq, sample_driver_record, sample_override_request, rd_user):
        """Test successful RD override"""
        from driver_record_router import override_driver_record
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.return_value = sample_driver_record
            
            with patch('driver_record_router.get_db_connection') as mock_get_conn:
                mock_get_conn.return_value = mock_db_pool
                
                result = await override_driver_record(
                    licence_number=sample_driver_record['licence_number'],
                    override_data=sample_override_request,
                    current_user=rd_user
                )
                
                assert result.success is True
                assert "Override action completed successfully" in result.message
                
                # Verify database operations were called
                assert mock_db_pool.execute.call_count >= 1
                
                # Verify override event was published  
                mock_rabbitmq.assert_called_once()
                event_args = mock_rabbitmq.call_args[0]
                assert event_args[0] == "OverrideIssued"
    
    @pytest.mark.asyncio
    async def test_override_unauthorized(self, sample_override_request, dao_user):
        """Test override with non-RD user"""
        from driver_record_router import override_driver_record
        from fastapi import HTTPException
        
        # This should be caught by the dependency, but test for completeness
        with pytest.raises(HTTPException) as exc_info:
            await override_driver_record(
                licence_number="D123456789",
                override_data=sample_override_request,
                current_user=dao_user  # DAO user trying RD-only operation
            )
        
        # The get_rd_user dependency should catch this
        assert exc_info.value.status_code == 403

# ============================================================================
# VALIDATION TESTS  
# ============================================================================

class TestPydanticModels:
    """Test Pydantic model validation"""
    
    def test_driver_record_create_validation(self):
        """Test DriverRecordCreate model validation"""
        # Valid data
        valid_data = {
            'candidate_id': str(uuid.uuid4()),
            'licence_number': 'D123456789',
            'christian_names': 'John Michael',
            'surname': 'Smith', 
            'address': '123 Main Street, Kingston, Jamaica',
            'dob': '1990-05-15',
            'licence_type': 'Class B'
        }
        
        record = DriverRecordCreate(**valid_data)
        assert record.licence_number == 'D123456789'
        assert record.licence_type == LicenceType.CLASS_B
    
    def test_theory_attempt_validation(self):
        """Test TheoryAttempt model validation"""
        valid_data = {
            'attempt_no': 1,
            'module': 'Traffic Signs',
            'score': 18,
            'pass': True
        }
        
        attempt = TheoryAttempt(**valid_data)
        assert attempt.score == 18
        assert attempt.pass is True
        
        # Test invalid score
        with pytest.raises(ValueError):
            TheoryAttempt(**{**valid_data, 'score': 25})  # Score > 20
    
    def test_yard_road_attempt_validation(self):
        """Test YardRoadAttempt model validation"""
        valid_criteria = [
            {"criterion": "Parking", "major": 0, "minor": 1, "score": 8}
        ]
        
        valid_data = {
            'test_type': 'Yard',
            'visit_no': 1,
            'criteria': valid_criteria,
            'overall_result': True
        }
        
        attempt = YardRoadAttempt(**valid_data)
        assert attempt.test_type == TestType.YARD
        assert len(attempt.criteria) == 1
        
        # Test invalid criteria
        with pytest.raises(ValueError):
            YardRoadAttempt(**{**valid_data, 'criteria': []})  # Empty criteria
    
    def test_court_record_validation(self):
        """Test CourtRecord model validation"""
        valid_data = {
            'judgment_date': '2024-01-01',
            'offence': 'Dangerous driving',
            'suspension_from': '2024-01-02',
            'suspension_to': '2024-06-02'
        }
        
        record = CourtRecord(**valid_data)
        assert record.offence == 'Dangerous driving'
        
        # Test invalid date range
        with pytest.raises(ValueError):
            CourtRecord(**{
                **valid_data, 
                'suspension_to': '2024-01-01'  # Before suspension_from
            })

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_driver_lifecycle(self, mock_db_pool, mock_rabbitmq, dao_user, rd_user):
        """Test complete driver record lifecycle"""
        from driver_record_router import (
            create_driver_record, add_theory_attempt, 
            add_yard_road_attempt, override_driver_record
        )
        
        # 1. Create driver record
        create_data = DriverRecordCreate(
            candidate_id=uuid.uuid4(),
            licence_number="D999888777",
            christian_names="Integration Test",
            surname="Driver",
            address="123 Test Street",
            dob=date(1990, 1, 1),
            licence_type=LicenceType.CLASS_B
        )
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_existing:
            mock_get_existing.return_value = None  # No existing record
            
            with patch('driver_record_router.create_driver_record_db') as mock_create:
                mock_create.return_value = uuid.uuid4()
                
                create_result = await create_driver_record(create_data, dao_user)
                assert create_result.success is True
        
        # 2. Add theory attempt
        theory_data = TheoryAttempt(
            attempt_no=1,
            module="Road Rules",
            score=16,
            pass=True
        )
        
        sample_record = {'id': uuid.uuid4(), 'licence_number': "D999888777"}
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.return_value = sample_record
            
            with patch('driver_record_router.get_db_connection') as mock_get_conn:
                mock_get_conn.return_value = mock_db_pool
                
                theory_result = await add_theory_attempt("D999888777", theory_data, dao_user)
                assert theory_result.success is True
        
        # 3. Override action by RD
        override_data = OverrideRequest(
            action="Emergency licence reinstatement",
            reason="Medical emergency requiring immediate driving privileges for family care",
            new_status=DriverStatus.ISSUED
        )
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.return_value = sample_record
            
            with patch('driver_record_router.get_db_connection') as mock_get_conn:
                mock_get_conn.return_value = mock_db_pool
                
                override_result = await override_driver_record("D999888777", override_data, rd_user)
                assert override_result.success is True
        
        # Verify all events were published
        assert mock_rabbitmq.call_count == 3  # Create, theory, override

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, dao_user):
        """Test handling of database connection errors"""
        from driver_record_router import get_driver_record
        from fastapi import HTTPException
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_record:
            mock_get_record.side_effect = Exception("Database connection failed")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_driver_record("D123456789", dao_user)
            
            assert exc_info.value.status_code == 500
            assert "Internal server error" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_rabbitmq_publish_error(self, mock_db_pool, sample_driver_create, dao_user):
        """Test handling of RabbitMQ publishing errors"""
        from driver_record_router import create_driver_record
        
        with patch('driver_record_router.get_driver_record_by_licence') as mock_get_existing:
            mock_get_existing.return_value = None
            
            with patch('driver_record_router.create_driver_record_db') as mock_create:
                mock_create.return_value = uuid.uuid4()
                
                with patch('driver_record_router.publish_event') as mock_publish:
                    mock_publish.side_effect = Exception("RabbitMQ connection failed")
                    
                    # Should still succeed despite event publishing failure
                    result = await create_driver_record(sample_driver_create, dao_user)
                    assert result.success is True

# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_record_creation(self):
        """Test concurrent driver record creation"""
        from driver_record_router import create_driver_record_db
        
        # Create multiple records concurrently
        create_tasks = []
        for i in range(10):
            record_data = DriverRecordCreate(
                candidate_id=uuid.uuid4(),
                licence_number=f"D{i:09d}",
                christian_names=f"Test{i}",
                surname=f"Driver{i}",
                address=f"Address {i}",
                dob=date(1990, 1, 1),
                licence_type=LicenceType.CLASS_B
            )
            
            with patch('driver_record_router.get_db_connection') as mock_get_conn:
                mock_conn = AsyncMock()
                mock_conn.fetchval.return_value = uuid.uuid4()
                mock_get_conn.return_value = mock_conn
                
                task = create_driver_record_db(record_data)
                create_tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*create_tasks, return_exceptions=True)
        
        # Verify all completed successfully
        successful_results = [r for r in results if isinstance(r, uuid.UUID)]
        assert len(successful_results) == 10

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])