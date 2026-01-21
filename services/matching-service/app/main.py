"""
Matching service main application.

FastAPI application for intelligent candidate matching.
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any
import logging

from .services.matching_engine import MatchingEngine
from .services.semantic_matcher import SemanticMatcher
from .services.decision_engine import DecisionEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Candidate Matching Service",
    description="Intelligent candidate matching and screening service",
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
matching_engine = MatchingEngine()
semantic_matcher = SemanticMatcher()
decision_engine = DecisionEngine()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "candidate-matching",
        "components": {
            "matching_engine": True,
            "semantic_matcher": True,
            "decision_engine": True
        }
    }

@app.post("/match/calculate")
async def calculate_match(request: Dict[str, Any]):
    """Calculate match score between candidate and job"""
    try:
        candidate = request.get('candidate')
        job = request.get('job')
        
        if not candidate or not job:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both candidate and job data are required"
            )
        
        # Calculate basic match score
        match_result = matching_engine.calculate_match_score(candidate, job)
        
        # Enhance with semantic matching
        if candidate.get('skills') and job.get('required_skills'):
            candidate_skills = [skill.get('skill', '') for skill in candidate['skills']]
            semantic_result = semantic_matcher.calculate_enhanced_skill_match(
                candidate_skills, job['required_skills']
            )
            match_result['semantic_skill_match'] = semantic_result
        
        return {
            "candidate_id": candidate.get('id'),
            "job_id": job.get('id'),
            "match_result": match_result
        }
        
    except Exception as e:
        logger.error(f"Error calculating match: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating match: {str(e)}"
        )

@app.post("/match/rank")
async def rank_candidates(request: Dict[str, Any]):
    """Rank candidates for a job position"""
    try:
        candidates = request.get('candidates', [])
        job = request.get('job')
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job data is required"
            )
        
        if not candidates:
            return {"ranked_candidates": []}
        
        # Rank candidates
        ranked_candidates = matching_engine.rank_candidates(candidates, job)
        
        return {
            "job_id": job.get('id'),
            "total_candidates": len(candidates),
            "ranked_candidates": ranked_candidates
        }
        
    except Exception as e:
        logger.error(f"Error ranking candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ranking candidates: {str(e)}"
        )

@app.post("/match/screen")
async def screen_candidates(request: Dict[str, Any]):
    """Automated screening of candidates"""
    try:
        scored_candidates = request.get('scored_candidates', [])
        job_requirements = request.get('job_requirements', {})
        
        if not scored_candidates:
            return {
                "decisions": {
                    "auto_shortlisted": [],
                    "auto_rejected": [],
                    "manual_review": [],
                    "summary": {"total_candidates": 0}
                }
            }
        
        # Make screening decisions
        decisions = decision_engine.make_screening_decisions(scored_candidates, job_requirements)
        
        return {
            "job_id": job_requirements.get('job_id'),
            "decisions": decisions
        }
        
    except Exception as e:
        logger.error(f"Error screening candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error screening candidates: {str(e)}"
        )

@app.post("/semantic/similarity")
async def calculate_semantic_similarity(request: Dict[str, Any]):
    """Calculate semantic similarity between skills"""
    try:
        skill1 = request.get('skill1')
        skill2 = request.get('skill2')
        
        if not skill1 or not skill2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both skill1 and skill2 are required"
            )
        
        similarity = semantic_matcher.calculate_semantic_similarity(skill1, skill2)
        
        return {
            "skill1": skill1,
            "skill2": skill2,
            "similarity": similarity
        }
        
    except Exception as e:
        logger.error(f"Error calculating semantic similarity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating semantic similarity: {str(e)}"
        )

@app.post("/semantic/expand")
async def expand_skills(request: Dict[str, Any]):
    """Expand skill requirements with similar skills"""
    try:
        required_skills = request.get('required_skills', [])
        
        if not required_skills:
            return {"expanded_skills": {}}
        
        expanded = semantic_matcher.expand_skill_requirements(required_skills)
        
        return {
            "original_skills": required_skills,
            "expanded_skills": expanded
        }
        
    except Exception as e:
        logger.error(f"Error expanding skills: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error expanding skills: {str(e)}"
        )

@app.get("/semantic/context/{skill}")
async def get_skill_context(skill: str):
    """Get contextual information about a skill"""
    try:
        context = semantic_matcher.get_skill_context(skill)
        return context
        
    except Exception as e:
        logger.error(f"Error getting skill context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting skill context: {str(e)}"
        )

@app.post("/decision/explain")
async def explain_decision(request: Dict[str, Any]):
    """Get explanation for a candidate decision"""
    try:
        candidate_data = request.get('candidate_data')
        job_requirements = request.get('job_requirements')
        
        if not candidate_data or not job_requirements:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both candidate_data and job_requirements are required"
            )
        
        explanation = decision_engine.get_decision_explanation(candidate_data, job_requirements)
        
        return explanation
        
    except Exception as e:
        logger.error(f"Error explaining decision: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error explaining decision: {str(e)}"
        )

@app.post("/config/update")
async def update_config(request: Dict[str, Any]):
    """Update decision engine configuration"""
    try:
        new_config = request.get('config', {})
        
        if not new_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Configuration data is required"
            )
        
        decision_engine.update_thresholds(new_config)
        
        return {
            "message": "Configuration updated successfully",
            "updated_config": new_config
        }
        
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating configuration: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)