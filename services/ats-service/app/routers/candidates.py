from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from uuid import UUID
import logging

from ..database import get_db
from ..models import Candidate
from ..schemas import CandidateCreate, CandidateResponse, CandidateUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(candidate_data: CandidateCreate, db: Session = Depends(get_db)):
    """Create a new candidate"""
    try:
        # Check if candidate already exists
        existing_candidate = db.query(Candidate).filter(Candidate.email == candidate_data.email).first()
        if existing_candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Candidate with this email already exists"
            )
        
        db_candidate = Candidate(**candidate_data.dict())
        db.add(db_candidate)
        db.commit()
        db.refresh(db_candidate)
        
        logger.info(f"Created candidate with ID: {db_candidate.id}")
        return db_candidate
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error creating candidate: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database constraint violation"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating candidate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/count", response_model=dict)
async def count_candidates(
    status: Optional[str] = Query(None, description="Filter by candidate status"),
    db: Session = Depends(get_db)
):
    """Get total count of candidates with optional filtering"""
    try:
        query = db.query(Candidate)
        
        if status:
            # Validate status value
            valid_statuses = ['active', 'inactive', 'hired', 'rejected']
            if status not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                )
            query = query.filter(Candidate.status == status)
        
        total_count = query.count()
        return {"total": total_count}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error counting candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/", response_model=List[CandidateResponse])
async def list_candidates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by candidate status"),
    db: Session = Depends(get_db)
):
    """List candidates with pagination and filtering"""
    try:
        query = db.query(Candidate)
        
        if status:
            # Validate status value
            valid_statuses = ['active', 'inactive', 'hired', 'rejected']
            if status not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                )
            query = query.filter(Candidate.status == status)
        
        # Order by creation date (newest first)
        query = query.order_by(Candidate.created_at.desc())
        
        candidates = query.offset(skip).limit(limit).all()
        return candidates
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(candidate_id: UUID, db: Session = Depends(get_db)):
    """Get a specific candidate by ID"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    return candidate

@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: UUID,
    candidate_data: CandidateUpdate,
    db: Session = Depends(get_db)
):
    """Update a candidate"""
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Check for email uniqueness if email is being updated
        if candidate_data.email and candidate_data.email != candidate.email:
            existing_candidate = db.query(Candidate).filter(
                Candidate.email == candidate_data.email,
                Candidate.id != candidate_id
            ).first()
            if existing_candidate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists for another candidate"
                )
        
        update_data = candidate_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(candidate, field, value)
        
        db.commit()
        db.refresh(candidate)
        
        logger.info(f"Updated candidate with ID: {candidate_id}")
        return candidate
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error updating candidate: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database constraint violation"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating candidate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(candidate_id: UUID, db: Session = Depends(get_db)):
    """Delete a candidate"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    db.delete(candidate)
    db.commit()

@router.get("/search/", response_model=List[CandidateResponse])
async def search_candidates(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Search candidates by name, email, or skills"""
    try:
        # Basic text search - can be enhanced with Elasticsearch later
        search_term = f"%{q.strip()}%"
        query = db.query(Candidate).filter(
            (Candidate.first_name.ilike(search_term)) |
            (Candidate.last_name.ilike(search_term)) |
            (Candidate.email.ilike(search_term))
        ).order_by(Candidate.created_at.desc())
        
        candidates = query.offset(skip).limit(limit).all()
        return candidates
        
    except Exception as e:
        logger.error(f"Error searching candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )