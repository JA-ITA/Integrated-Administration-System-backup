# Island Traffic Authority Driver Integrated Administration System

A comprehensive digital platform for managing driver licensing, testing, and administrative operations for island traffic authorities.

## 🏗️ Architecture

**Monolith-First Approach**: Clean modular boundaries designed for future microservices extraction.

### Core Modules
- **Identity**: User authentication, authorization, and profile management
- **Calendar**: Test scheduling, appointment management, and availability
- **Receipt**: Payment processing, fee collection, and financial records
- **Registration**: Driver registration, application processing, and data management
- **Test Engine**: Driving tests, theory exams, and assessment workflows
- **Certificate**: License generation, validation, and digital certificates
- **Special Admin**: Super-admin functions, system configuration, and oversight
- **Audit**: Activity logging, compliance tracking, and audit trails
- **Checklist**: Process workflows, document verification, and requirement tracking

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python) - High-performance async API
- **Frontend**: React - Multi-SPA architecture
- **Database**: PostgreSQL - Enterprise-grade relational database
- **Message Queue**: RabbitMQ - Async task processing
- **Monitoring**: Jaeger - Distributed tracing and observability
- **Infrastructure**: Docker Compose - Local development environment

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Yarn package manager

### Development Setup
```bash
# Start all services
docker-compose up -d

# Install Python dependencies
cd app && pip install -r requirements.txt

# Install UI dependencies
cd ui && yarn install

# Run database migrations
cd app && alembic upgrade head

# Start development servers
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# PostgreSQL: localhost:5432
# RabbitMQ Management: http://localhost:15672
# Jaeger UI: http://localhost:16686
```

## 📁 Project Structure

```
ita-driver-platform/
├── app/                       # FastAPI monolith
│   ├── modules/               # Business domain modules
│   │   ├── identity/         # Authentication & user management
│   │   ├── calendar/         # Scheduling & appointments
│   │   ├── receipt/          # Payments & financial records
│   │   ├── registration/     # Driver applications & processing
│   │   ├── test_engine/      # Testing & assessment workflows
│   │   ├── certificate/      # License generation & validation
│   │   ├── special_admin/    # Super-admin functions
│   │   ├── audit/           # Activity logging & compliance
│   │   └── checklist/       # Process workflows & verification
│   ├── db/                   # Database migrations (Alembic)
│   ├── core/                 # Shared configuration & utilities
│   └── main.py              # FastAPI application entry point
├── ui/                       # React frontend (multi-SPA)
│   ├── src/
│   │   ├── apps/            # Individual SPA applications
│   │   ├── shared/          # Shared components & utilities
│   │   └── lib/             # Core libraries & configurations
├── docs/                     # Project documentation
├── .github/workflows/        # CI/CD pipelines
├── docker-compose.yml        # Local development environment
└── README.md                # This file
```

## 🧪 Testing

```bash
# Backend tests
cd app && python -m pytest

# Frontend tests
cd ui && yarn test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📖 Documentation

- [Architecture Decision Records (ADRs)](./docs/adrs/)
- [API Documentation](./docs/api.md)
- [Development Guide](./docs/development.md)
- [Deployment Guide](./docs/deployment.md)

## 🔄 CI/CD Pipeline

GitHub Actions workflow includes:
1. **Lint**: Code quality and style checks
2. **Test**: Automated test suites
3. **Build**: Application build verification
4. **Deploy**: Automated deployment (staging/production)

## 📄 License

Island Traffic Authority proprietary system. All rights reserved.

## 🤝 Contributing

See [CONTRIBUTING.md](./docs/contributing.md) for development guidelines and contribution process.