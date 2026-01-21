# Recruitment & Testing Platform

A comprehensive AI-powered recruitment automation system with microservices architecture.

## Architecture Overview

The platform consists of the following microservices:

- **API Gateway** (Node.js) - Central routing and authentication
- **ATS Service** (FastAPI) - Applicant tracking system
- **Resume Service** (Python) - AI-powered resume parsing
- **Matching Service** (Python) - Intelligent candidate matching
- **Testing Service** (Node.js) - Secure online testing platform
- **Notification Service** (Python) - Email and SMS communications

## Infrastructure Components

- **PostgreSQL** - Primary database for structured data
- **MongoDB** - Document storage for test sessions
- **Redis** - Caching and session management
- **Elasticsearch** - Full-text search capabilities
- **MinIO** - S3-compatible object storage

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd recruitment-platform
   ```

2. **Set up environment**
   ```bash
   make dev-setup
   # Edit .env file with your configuration
   ```

3. **Build and start services**
   ```bash
   make build
   make up
   ```

4. **Check service health**
   ```bash
   make health
   ```

## Service Endpoints

- API Gateway: http://localhost:8000
- ATS Service: http://localhost:8001
- Resume Service: http://localhost:8002
- Matching Service: http://localhost:8003
- Testing Service: http://localhost:8004
- Notification Service: http://localhost:8005

## Database Access

- PostgreSQL: localhost:5432
- MongoDB: localhost:27017
- Redis: localhost:6379
- Elasticsearch: localhost:9200
- MinIO Console: http://localhost:9001

## Development

### Prerequisites

- Docker and Docker Compose
- Make (optional, for convenience commands)

### Available Commands

```bash
make build      # Build all Docker images
make up         # Start all services
make down       # Stop all services
make logs       # View service logs
make clean      # Clean up containers and volumes
make test       # Run tests
make health     # Check service health
```

### Service Development

Each service is containerized and can be developed independently:

1. **API Gateway** (services/api-gateway)
   - Node.js with Express
   - Handles routing, authentication, rate limiting

2. **ATS Service** (services/ats-service)
   - FastAPI with SQLAlchemy
   - Manages candidates, jobs, applications

3. **Resume Service** (services/resume-service)
   - Python with spaCy for NLP
   - Parses resumes and extracts structured data

4. **Matching Service** (services/matching-service)
   - Python with scikit-learn
   - AI-powered candidate-job matching

5. **Testing Service** (services/testing-service)
   - Node.js with Socket.io
   - Secure online testing platform

6. **Notification Service** (services/notification-service)
   - FastAPI with SendGrid/Twilio
   - Email and SMS notifications

## Security Features

- JWT-based authentication
- Role-based access control
- Rate limiting
- Data encryption at rest and in transit
- Audit logging
- CORS protection

## Monitoring and Logging

- Centralized logging with Winston
- Health check endpoints for all services
- Redis-based rate limiting
- Audit trails for compliance

## API Documentation

Once services are running, API documentation is available at:
- API Gateway: http://localhost:8000/api/v1/docs
- Individual services: http://localhost:800X/docs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Your License Here]