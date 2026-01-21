from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..database import get_db
from ..models import Candidate
from ..schemas import CandidateCreate, CandidateResponse, CandidateUpdate

router = APIRouter()

@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(candidate_data: CandidateCreate, db: Session = Depends(get_db)):
    """Create a new candidate"""
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
    
    return db_candidate

@router.get("/", response_model=List[CandidateResponse])
async def list_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List candidates with pagination and filtering"""
    query = db.query(Candidate)
    
    if status:
        query = query.filter(Candidate.status == status)
    
    candidates = query.offset(skip).limit(limit).all()
    return candidates

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
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    update_data = candidate_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)
    
    db.commit()
    db.refresh(candidate)
    
    return candidate

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
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Search candidates by name, email, or skills"""
    # Basic text search - can be enhanced with Elasticsearch later
    query = db.query(Candidate).filter(
        (Candidate.first_name.ilike(f"%{q}%")) |
        (Candidate.last_name.ilike(f"%{q}%")) |
        (Candidate.email.ilike(f"%{q}%"))
    )
    
    candidates = query.offset(skip).limit(limit).all()
    return candidates