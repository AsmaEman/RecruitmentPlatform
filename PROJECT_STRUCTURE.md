# Project Structure

```
recruitment-platform/
├── .env.example                    # Environment variables template
├── docker-compose.yml              # Docker services configuration
├── Makefile                        # Development commands
├── README.md                       # Project documentation
├── PROJECT_STRUCTURE.md            # This file
│
├── database/
│   └── init.sql                    # PostgreSQL schema initialization
│
├── services/
│   ├── api-gateway/                # API Gateway Service (Node.js)
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── src/
│   │   │   └── server.js           # Main gateway server
│   │   └── logs/
│   │
│   ├── ats-service/                # ATS Service (FastAPI)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py             # FastAPI application
│   │       ├── database.py         # Database configuration
│   │       ├── models.py           # SQLAlchemy models
│   │       ├── schemas.py          # Pydantic schemas
│   │       ├── core/
│   │       │   ├── __init__.py
│   │       │   └── security.py     # JWT and password handling
│   │       └── routers/
│   │           ├── __init__.py
│   │           ├── auth.py         # Authentication endpoints
│   │           ├── candidates.py   # Candidate management
│   │           ├── jobs.py         # Job posting management
│   │           └── applications.py # Application management
│   │
│   ├── resume-service/             # Resume Parser Service (Python)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       └── main.py             # Basic service setup
│   │
│   ├── matching-service/           # Matching Service (Python)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       └── main.py             # Basic service setup
│   │
│   ├── testing-service/            # Testing Service (Node.js)
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── src/
│   │   │   └── server.js           # Basic service setup
│   │   └── logs/
│   │
│   └── notification-service/       # Notification Service (Python)
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app/
│           └── main.py             # Basic service setup
│
└── .kiro/
    └── specs/
        └── recruitment-testing-platform/
            ├── requirements.md      # Feature requirements
            ├── design.md           # System design
            └── tasks.md            # Implementation tasks
```

## Service Responsibilities

### API Gateway (Port 8000)
- Central entry point for all client requests
- JWT authentication and authorization
- Rate limiting and request logging
- Service discovery and load balancing
- CORS handling

### ATS Service (Port 8001)
- Candidate profile management
- Job posting management
- Application tracking and workflow
- User authentication and authorization
- Audit logging

### Resume Service (Port 8002)
- Resume parsing (PDF, DOCX, TXT)
- OCR for scanned documents
- Named Entity Recognition (NER)
- Skill extraction and normalization
- File storage integration

### Matching Service (Port 8003)
- Candidate-job compatibility scoring
- Skill matching algorithms
- Experience and education matching
- Automated decision making
- ML model serving

### Testing Service (Port 8004)
- Online test delivery
- Code execution environment
- Session management
- Real-time communication
- Anti-cheating measures

### Notification Service (Port 8005)
- Email notifications (SendGrid)
- SMS notifications (Twilio)
- Template management
- Communication logging
- Calendar integration

## Infrastructure Components

### PostgreSQL (Port 5432)
- Primary relational database
- Stores candidates, jobs, applications
- User management and authentication
- Audit logs and compliance data

### MongoDB (Port 27017)
- Document storage for test sessions
- Flexible schema for test responses
- Proctoring data and violations
- Session recordings metadata

### Redis (Port 6379)
- Session management
- Caching frequently accessed data
- Rate limiting storage
- Real-time data sharing

### Elasticsearch (Port 9200)
- Full-text search for candidates
- Resume content indexing
- Advanced search capabilities
- Analytics and reporting

### MinIO (Port 9000/9001)
- S3-compatible object storage
- Resume file storage
- Test materials and submissions
- Screen recordings and media files

## Development Workflow

1. **Setup**: Copy `.env.example` to `.env` and configure
2. **Build**: `make build` to build all Docker images
3. **Start**: `make up` to start all services
4. **Develop**: Modify service code, containers auto-reload
5. **Test**: `make test` to run all test suites
6. **Monitor**: `make logs` to view service logs
7. **Health**: `make health` to check service status

## Security Considerations

- All services run as non-root users
- JWT tokens for authentication
- Rate limiting on API Gateway
- CORS protection
- Input validation and sanitization
- Audit logging for compliance
- Encrypted data storage