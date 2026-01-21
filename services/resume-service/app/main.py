"""
Resume parsing service main application.

FastAPI application for processing resumes and extracting structured data.
Requirements: 2.1, 2.2, 2.3, 2.6, 2.7
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import logging

from .services.nlp_service import NLPService
from .services.document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Resume Parsing Service",
    description="Service for parsing resumes and extracting structured data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
nlp_service = None
document_processor = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global nlp_service, document_processor
    
    try:
        logger.info("Initializing resume parsing services...")
        nlp_service = NLPService()
        document_processor = DocumentProcessor()
        logger.info("Resume parsing services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "resume-parsing",
        "nlp_ready": nlp_service is not None,
        "processor_ready": document_processor is not None
    }

@app.post("/parse", response_model=Dict[str, Any])
async def parse_resume(file: UploadFile = File(...)):
    """Parse resume file and extract structured data"""
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Process document to extract text
        doc_result = document_processor.process_document(file_content, file.filename)
        
        if not doc_result["metadata"]["success"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to process document: {doc_result['metadata'].get('error', 'Unknown error')}"
            )
        
        # Extract entities using NLP
        extracted_data = nlp_service.extract_entities(doc_result["text"])
        
        # Normalize skills
        if extracted_data.get("skills"):
            extracted_data["skills"] = nlp_service.normalize_skills(extracted_data["skills"])
        
        # Calculate confidence score
        confidence_score = nlp_service.calculate_confidence_score(extracted_data)
        
        # Assess document quality
        quality_assessment = document_processor.assess_quality(doc_result)
        
        return {
            "filename": file.filename,
            "extracted_data": extracted_data,
            "confidence_score": confidence_score,
            "quality_assessment": quality_assessment,
            "document_metadata": doc_result["metadata"],
            "raw_text": doc_result["text"][:1000] + "..." if len(doc_result["text"]) > 1000 else doc_result["text"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing resume {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/extract-skills", response_model=Dict[str, Any])
async def extract_skills_only(file: UploadFile = File(...)):
    """Extract only skills from resume file"""
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )
    
    try:
        # Read and process file
        file_content = await file.read()
        doc_result = document_processor.process_document(file_content, file.filename)
        
        if not doc_result["metadata"]["success"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to process document: {doc_result['metadata'].get('error', 'Unknown error')}"
            )
        
        # Extract and normalize skills
        skills = nlp_service._extract_skills(doc_result["text"])
        normalized_skills = nlp_service.normalize_skills(skills)
        
        return {
            "filename": file.filename,
            "skills": normalized_skills,
            "skill_count": len(normalized_skills),
            "categories": list(set(skill["category"] for skill in normalized_skills))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting skills from {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "formats": list(document_processor.supported_formats),
        "description": {
            ".pdf": "PDF documents (text and scanned)",
            ".docx": "Microsoft Word documents",
            ".txt": "Plain text files",
            ".png": "PNG images (OCR)",
            ".jpg": "JPEG images (OCR)",
            ".jpeg": "JPEG images (OCR)",
            ".tiff": "TIFF images (OCR)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)