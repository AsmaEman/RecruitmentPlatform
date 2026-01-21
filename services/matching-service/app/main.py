from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Candidate Matching Service",
    description="AI-powered candidate-job matching and scoring service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "matching-service",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    return {"message": "Candidate Matching Service", "version": "1.0.0"}