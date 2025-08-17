# ITADIAS Identity Microservice

A FastAPI-based microservice for candidate identity and profile management.

## Features

- **Candidate Management**: Create and manage candidate profiles
- **Multi-channel OTP**: Email and SMS verification support
- **Event Publishing**: RabbitMQ-based event system with fallback
- **Database**: PostgreSQL with dedicated identity schema
- **Containerization**: Full Docker support with Docker Compose
- **Testing**: Comprehensive unit test suite
- **API Documentation**: OpenAPI 3.0 specification

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   FastAPI App   │    │ PostgreSQL   │    │  RabbitMQ   │
│   (Port 8001)   │◄──►│   Database   │    │   Events    │
└─────────────────┘    └──────────────┘    └─────────────┘
         │                       │                    │
         ▼                       ▼                    ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   REST APIs     │    │   Identity   │    │ Domain      │
│   /api/v1/*     │    │   Schema     │    │ Events      │
└─────────────────┘    └──────────────┘    └─────────────┘
```

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the identity module:**
   ```bash
   cd /app/modules/identity
   ```

2. **Configure environment (optional):**
   ```bash
   cp .env .env.local
   # Edit .env.local with your API keys
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Verify services are running:**
   ```bash
   curl http://localhost:8001/health
   ```

5. **Access management UIs:**
   - API Documentation: http://localhost:8001/docs
   - RabbitMQ Management: http://localhost:15672 (guest/guest)

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL and RabbitMQ:**
   ```bash
   docker-compose up -d postgres rabbitmq
   ```

3. **Set environment variables:**
   ```bash
   export DB_HOST=localhost
   export RABBITMQ_HOST=localhost
   # ... other variables from .env
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | Service information |
| POST | `/api/v1/candidates` | Create candidate |
| GET | `/api/v1/candidates/{id}` | Get candidate |
| GET | `/api/v1/candidates` | List candidates |

### Example Usage

**Create a candidate:**
```bash
curl -X POST http://localhost:8001/api/v1/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "first_name": "John",
    "last_name": "Doe",
    "send_otp": true,
    "otp_channel": "email"
  }'
```

**Get a candidate:**
```bash
curl http://localhost:8001/api/v1/candidates/{candidate_id}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_PORT` | PostgreSQL port | 5432 |
| `DB_NAME` | Database name | identity_db |
| `DB_USER` | Database user | identity_user |
| `DB_PASSWORD` | Database password | identity_pass |
| `EMAIL_OTP_ENABLED` | Enable email OTP | true |
| `SMS_OTP_ENABLED` | Enable SMS OTP | false |
| `SENDGRID_API_KEY` | SendGrid API key | - |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | - |
| `RABBITMQ_HOST` | RabbitMQ host | localhost |

### OTP Configuration

The service supports both email and SMS OTP with the following features:

- **Email OTP**: Powered by SendGrid
- **SMS OTP**: Powered by Twilio (disabled by default)
- **Configurable**: OTP length, expiry time, max attempts
- **Fallback**: Graceful degradation when services are unavailable

## Events

### Published Events

The service publishes the following domain events:

| Event | Trigger | Routing Key |
|-------|---------|-------------|
| `CandidateCreated` | New candidate registration | `identity.candidate.created` |
| `CandidateVerified` | OTP verification success | `identity.candidate.verified` |

### Event Structure

```json
{
  "event_type": "CandidateCreated",
  "event_data": {
    "candidate_id": "uuid",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "created_at": "iso-datetime"
  },
  "entity_id": "uuid",
  "entity_type": "candidate",
  "timestamp": "iso-datetime",
  "service": "identity-service",
  "version": "1.0.0"
}
```

## Database Schema

### Tables

- **candidates**: Core candidate profiles
- **otp_verifications**: OTP tracking and verification
- **event_logs**: Event publishing audit trail

### Schema: `identity`

All tables are created within the `identity` schema for namespace isolation.

## Testing

### Run Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

### Test Coverage

The test suite covers:
- ✅ API endpoints (routes)
- ✅ Database models
- ✅ Service layer logic
- ✅ Event publishing
- ✅ OTP functionality
- ✅ Error handling

## Production Deployment

### Security Considerations

1. **API Keys**: Store in secure environment variables
2. **Database**: Use strong passwords and SSL connections
3. **Rate Limiting**: Implement API rate limiting
4. **Authentication**: Add API authentication layer
5. **Monitoring**: Set up logging and monitoring

### Performance Tuning

1. **Database**: Configure connection pooling
2. **RabbitMQ**: Tune message acknowledgments
3. **Caching**: Consider Redis for session management
4. **Load Balancing**: Use multiple service instances

### Monitoring

The service provides:
- Health check endpoint for load balancers
- Structured logging
- Event audit trail
- Database connection monitoring

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL container
   docker-compose logs postgres
   
   # Verify database connectivity
   psql -h localhost -U identity_user -d identity_db
   ```

2. **RabbitMQ Connection Failed**
   ```bash
   # Check RabbitMQ container
   docker-compose logs rabbitmq
   
   # Access management UI
   http://localhost:15672
   ```

3. **OTP Not Sending**
   ```bash
   # Check logs for SendGrid/Twilio errors
   docker-compose logs identity-service
   
   # Verify API keys in environment
   ```

### Logs

```bash
# View service logs
docker-compose logs -f identity-service

# View all logs
docker-compose logs -f
```

## API Documentation

Full API documentation is available at:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
- OpenAPI Spec: `openapi.yaml`

## License

Proprietary - ITADIAS Platform