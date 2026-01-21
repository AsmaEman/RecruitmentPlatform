from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import redis
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv

from .database import engine, get_db
from .models import Base
from .routers import candidates, jobs, applications, auth
from .core.security import verify_token

load_dotenv()

# Create database tables only if not in test environment
if os.getenv("DATABASE_URL", "").find("test.db") == -1:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Recruitment ATS Service",
    description="Applicant Tracking System for Recruitment Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis connection
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

# Initialize Elasticsearch connection
es_client = Elasticsearch([os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")])

# Security
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user information"""
    try:
        payload = verify_token(credentials.credentials)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db = next(get_db())
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    try:
        # Check Redis connection
        redis_client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"
    
    try:
        # Check Elasticsearch connection
        es_client.ping()
        es_status = "healthy"
    except Exception:
        es_status = "unhealthy"
    
    return {
        "status": "healthy" if all(s == "healthy" for s in [db_status, redis_status, es_status]) else "degraded",
        "services": {
            "database": db_status,
            "redis": redis_status,
            "elasticsearch": es_status
        }
    }

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/applications", tags=["applications"])

@app.get("/")
async def root():
    return {"message": "Recruitment ATS Service", "version": "1.0.0"}

# Dependency injection for services
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    app.state.redis = redis_client
    app.state.elasticsearch = es_client

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    redis_client.close()
    es_client.close()