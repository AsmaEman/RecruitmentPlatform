from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from uuid import UUID
import logging

from ..database import get_db
from ..models import JobPosting
from ..schemas import JobCreate, JobResponse, JobUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """Create a new job posting"""
    try:
        # Validate custom pipeline stages if provided
        if hasattr(job_data, 'custom_pipeline_stages') and job_data.custom_pipeline_stages:
            valid_stages = ['applied', 'screening', 'interview', 'technical_test', 'final_interview', 'offer', 'hired', 'rejected']
            for stage in job_data.custom_pipeline_stages:
                if stage not in valid_stages:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid pipeline stage: {stage}. Valid stages: {', '.join(valid_stages)}"
                    )
        
        db_job = JobPosting(**job_data.dict())
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        
        logger.info(f"Created job posting with ID: {db_job.id}")
        return db_job
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error creating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database constraint violation"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    department: Optional[str] = Query(None, description="Filter by department"),
    employment_type: Optional[str] = Query(None, description="Filter by employment type"),
    db: Session = Depends(get_db)
):
    """List job postings with pagination and filtering"""
    try:
        query = db.query(JobPosting)
        
        if status:
            # Validate status value
            valid_statuses = ['active', 'inactive', 'closed', 'draft']
            if status not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                )
            query = query.filter(JobPosting.status == status)
        
        if department:
            query = query.filter(JobPosting.department.ilike(f"%{department}%"))
        
        if employment_type:
            # Validate employment type
            valid_types = ['full-time', 'part-time', 'contract', 'internship', 'temporary']
            if employment_type not in valid_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid employment type. Must be one of: {', '.join(valid_types)}"
                )
            query = query.filter(JobPosting.employment_type == employment_type)
        
        # Order by creation date (newest first)
        query = query.order_by(JobPosting.created_at.desc())
        
        jobs = query.offset(skip).limit(limit).all()
        return jobs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/search/", response_model=List[JobResponse])
async def search_jobs(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Search job postings by title, description, or department"""
    try:
        search_term = f"%{q.strip()}%"
        query = db.query(JobPosting).filter(
            (JobPosting.title.ilike(search_term)) |
            (JobPosting.description.ilike(search_term)) |
            (JobPosting.department.ilike(search_term))
        ).order_by(JobPosting.created_at.desc())
        
        jobs = query.offset(skip).limit(limit).all()
        return jobs
        
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/count", response_model=dict)
async def count_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    department: Optional[str] = Query(None, description="Filter by department"),
    db: Session = Depends(get_db)
):
    """Get total count of job postings with optional filtering"""
    try:
        query = db.query(JobPosting)
        
        if status:
            # Validate status value
            valid_statuses = ['active', 'inactive', 'closed', 'draft']
            if status not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                )
            query = query.filter(JobPosting.status == status)
        
        if department:
            query = query.filter(JobPosting.department.ilike(f"%{department}%"))
        
        total_count = query.count()
        return {"total": total_count}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error counting jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, db: Session = Depends(get_db)):
    """Get a specific job posting by ID"""
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found"
        )
    return job

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    job_data: JobUpdate,
    db: Session = Depends(get_db)
):
    """Update a job posting"""
    try:
        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job posting not found"
            )
        
        update_data = job_data.dict(exclude_unset=True)
        
        # Validate employment type if being updated
        if 'employment_type' in update_data:
            valid_types = ['full-time', 'part-time', 'contract', 'internship', 'temporary']
            if update_data['employment_type'] not in valid_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid employment type. Must be one of: {', '.join(valid_types)}"
                )
        
        # Validate status if being updated
        if 'status' in update_data:
            valid_statuses = ['active', 'inactive', 'closed', 'draft']
            if update_data['status'] not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                )
        
        for field, value in update_data.items():
            setattr(job, field, value)
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Updated job posting with ID: {job_id}")
        return job
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error updating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database constraint violation"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{job_id}/pipeline-stages", response_model=dict)
async def get_job_pipeline_stages(job_id: UUID, db: Session = Depends(get_db)):
    """Get custom recruitment pipeline stages for a job"""
    try:
        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job posting not found"
            )
        
        # Get custom pipeline stages from job requirements or use default
        default_stages = ['applied', 'screening', 'interview', 'technical_test', 'final_interview', 'offer', 'hired', 'rejected']
        custom_stages = job.requirements.get('custom_pipeline_stages', default_stages) if job.requirements else default_stages
        
        return {
            "job_id": str(job_id),
            "pipeline_stages": custom_stages,
            "default_stages": default_stages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pipeline stages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{job_id}/pipeline-stages", response_model=JobResponse)
async def update_job_pipeline_stages(
    job_id: UUID,
    pipeline_data: dict,
    db: Session = Depends(get_db)
):
    """Update custom recruitment pipeline stages for a job"""
    try:
        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job posting not found"
            )
        
        # Validate pipeline stages
        stages = pipeline_data.get('pipeline_stages', [])
        if not stages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pipeline stages cannot be empty"
            )
        
        valid_stages = ['applied', 'screening', 'interview', 'technical_test', 'final_interview', 'offer', 'hired', 'rejected']
        for stage in stages:
            if stage not in valid_stages:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid pipeline stage: {stage}. Valid stages: {', '.join(valid_stages)}"
                )
        
        # Update job requirements with custom pipeline stages
        if not job.requirements:
            job.requirements = {}
        job.requirements['custom_pipeline_stages'] = stages
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Updated pipeline stages for job ID: {job_id}")
        return job
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error updating pipeline stages: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database constraint violation"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating pipeline stages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: UUID, db: Session = Depends(get_db)):
    """Delete a job posting"""
    try:
        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job posting not found"
            )
        
        # Check if job has active applications
        from ..models import Application
        active_applications = db.query(Application).filter(
            Application.job_id == job_id,
            Application.status.in_(['applied', 'screening', 'interview', 'technical_test', 'final_interview'])
        ).count()
        
        if active_applications > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete job with {active_applications} active applications. Please close the job instead."
            )
        
        db.delete(job)
        db.commit()
        
        logger.info(f"Deleted job posting with ID: {job_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error deleting job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )