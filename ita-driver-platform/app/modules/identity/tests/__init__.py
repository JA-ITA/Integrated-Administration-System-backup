"""
Test package for Identity Module.

This package contains comprehensive test suites for the Identity module including:
- Unit tests for services and business logic
- Integration tests for API endpoints
- Model validation tests
- OTP functionality tests
- Event publishing tests

Test Structure:
- test_candidate_service.py: Tests for CandidateService business logic
- test_otp_service.py: Tests for OTP generation, sending, and verification
- test_api.py: Integration tests for REST API endpoints
- test_models.py: Tests for database models and validation
- test_events.py: Tests for event publishing and consumption

Running Tests:
- All tests: pytest app/modules/identity/tests/
- Specific test file: pytest app/modules/identity/tests/test_candidate_service.py
- With coverage: pytest app/modules/identity/tests/ --cov=modules.identity
"""