"""
Unit tests for candidate API endpoints.

Tests successful candidate creation and retrieval, validation errors and edge cases,
and pagination functionality.

Requirements: 1.1, 1.6
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app.models import Candidate
from app.schemas import CandidateCreate


class TestCandidateAPI:
    """Unit tests for candidate API endpoints"""
    
    def test_create_candidate_success(self, client: TestClient, db_session: Session):
        """Test successful candidate creation"""
        candidate_data = {
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "1234567890",
            "location": "New York, NY"
        }
        
        response = client.post("/candidates/", json=candidate_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == candidate_data["email"]
        assert data["first_name"] == candidate_data["first_name"]
        assert data["last_name"] == candidate_data["last_name"]
        assert data["phone"] == candidate_data["phone"]
        assert data["location"] == candidate_data["location"]
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_candidate_duplicate_email(self, client: TestClient, db_session: Session):
        """Test creating candidate with duplicate email fails"""
        # Create first candidate
        candidate_data = {
            "email": "duplicate@example.com",
            "first_name": "First",
            "last_name": "User"
        }
        
        response1 = client.post("/candidates/", json=candidate_data)
        assert response1.status_code == 201
        
        # Try to create second candidate with same email
        candidate_data["first_name"] = "Second"
        response2 = client.post("/candidates/", json=candidate_data)
        
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]
    
    def test_create_candidate_invalid_email(self, client: TestClient):
        """Test creating candidate with invalid email fails"""
        candidate_data = {
            "email": "invalid-email",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = client.post("/candidates/", json=candidate_data)
        assert response.status_code == 422  # Validation error
    
    def test_create_candidate_missing_required_fields(self, client: TestClient):
        """Test creating candidate with missing required fields fails"""
        candidate_data = {
            "email": "test@example.com"
            # Missing first_name and last_name
        }
        
        response = client.post("/candidates/", json=candidate_data)
        assert response.status_code == 422  # Validation error
    
    def test_get_candidate_success(self, client: TestClient, db_session: Session):
        """Test successful candidate retrieval"""
        # Create a candidate first
        candidate = Candidate(
            email="get.test@example.com",
            first_name="Get",
            last_name="Test",
            phone="9876543210"
        )
        db_session.add(candidate)
        db_session.commit()
        db_session.refresh(candidate)
        
        response = client.get(f"/candidates/{candidate.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(candidate.id)
        assert data["email"] == candidate.email
        assert data["first_name"] == candidate.first_name
        assert data["last_name"] == candidate.last_name
    
    def test_get_candidate_not_found(self, client: TestClient):
        """Test getting non-existent candidate returns 404"""
        fake_id = str(uuid4())
        response = client.get(f"/candidates/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_candidate_invalid_uuid(self, client: TestClient):
        """Test getting candidate with invalid UUID format"""
        response = client.get("/candidates/invalid-uuid")
        
        assert response.status_code == 422  # Validation error
    
    def test_update_candidate_success(self, client: TestClient, db_session: Session):
        """Test successful candidate update"""
        # Create a candidate first
        candidate = Candidate(
            email="update.test@example.com",
            first_name="Update",
            last_name="Test"
        )
        db_session.add(candidate)
        db_session.commit()
        db_session.refresh(candidate)
        
        update_data = {
            "first_name": "Updated",
            "phone": "5555555555",
            "location": "Updated Location"
        }
        
        response = client.put(f"/candidates/{candidate.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["phone"] == "5555555555"
        assert data["location"] == "Updated Location"
        assert data["last_name"] == "Test"  # Unchanged
        assert data["email"] == "update.test@example.com"  # Unchanged
    
    def test_update_candidate_not_found(self, client: TestClient):
        """Test updating non-existent candidate returns 404"""
        fake_id = str(uuid4())
        update_data = {"first_name": "Updated"}
        
        response = client.put(f"/candidates/{fake_id}", json=update_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_delete_candidate_success(self, client: TestClient, db_session: Session):
        """Test successful candidate deletion"""
        # Create a candidate first
        candidate = Candidate(
            email="delete.test@example.com",
            first_name="Delete",
            last_name="Test"
        )
        db_session.add(candidate)
        db_session.commit()
        db_session.refresh(candidate)
        candidate_id = candidate.id
        
        response = client.delete(f"/candidates/{candidate_id}")
        
        assert response.status_code == 204
        
        # Verify candidate is deleted
        deleted_candidate = db_session.query(Candidate).filter(Candidate.id == candidate_id).first()
        assert deleted_candidate is None
    
    def test_delete_candidate_not_found(self, client: TestClient):
        """Test deleting non-existent candidate returns 404"""
        fake_id = str(uuid4())
        response = client.delete(f"/candidates/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_list_candidates_pagination(self, client: TestClient, db_session: Session):
        """Test candidate listing with pagination"""
        # Create multiple candidates
        candidates = []
        for i in range(15):
            candidate = Candidate(
                email=f"candidate{i}@example.com",
                first_name=f"First{i}",
                last_name=f"Last{i}"
            )
            candidates.append(candidate)
            db_session.add(candidate)
        
        db_session.commit()
        
        # Test first page
        response = client.get("/candidates/?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        # Test second page
        response = client.get("/candidates/?skip=10&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5  # Remaining candidates
        
        # Test with limit
        response = client.get("/candidates/?skip=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
    
    def test_list_candidates_status_filter(self, client: TestClient, db_session: Session):
        """Test candidate listing with status filtering"""
        # Create candidates with different statuses
        active_candidate = Candidate(
            email="active@example.com",
            first_name="Active",
            last_name="User",
            status="active"
        )
        inactive_candidate = Candidate(
            email="inactive@example.com",
            first_name="Inactive",
            last_name="User",
            status="inactive"
        )
        
        db_session.add(active_candidate)
        db_session.add(inactive_candidate)
        db_session.commit()
        
        # Test filtering by active status
        response = client.get("/candidates/?status=active")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "active"
        
        # Test filtering by inactive status
        response = client.get("/candidates/?status=inactive")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "inactive"
    
    def test_list_candidates_invalid_status(self, client: TestClient):
        """Test candidate listing with invalid status filter"""
        response = client.get("/candidates/?status=invalid_status")
        
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]
    
    def test_search_candidates_success(self, client: TestClient, db_session: Session):
        """Test successful candidate search"""
        # Create test candidates
        candidates = [
            Candidate(email="john.smith@example.com", first_name="John", last_name="Smith"),
            Candidate(email="jane.doe@example.com", first_name="Jane", last_name="Doe"),
            Candidate(email="bob.johnson@example.com", first_name="Bob", last_name="Johnson"),
        ]
        
        for candidate in candidates:
            db_session.add(candidate)
        db_session.commit()
        
        # Search by first name
        response = client.get("/candidates/search/?q=John")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(candidate["first_name"] == "John" for candidate in data)
        
        # Search by last name
        response = client.get("/candidates/search/?q=Smith")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(candidate["last_name"] == "Smith" for candidate in data)
        
        # Search by email
        response = client.get("/candidates/search/?q=jane.doe")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("jane.doe" in candidate["email"] for candidate in data)
    
    def test_search_candidates_no_results(self, client: TestClient):
        """Test candidate search with no results"""
        response = client.get("/candidates/search/?q=nonexistent")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_search_candidates_empty_query(self, client: TestClient):
        """Test candidate search with empty query fails"""
        response = client.get("/candidates/search/?q=")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_candidates_pagination(self, client: TestClient, db_session: Session):
        """Test candidate search with pagination"""
        # Create multiple candidates with similar names
        for i in range(15):
            candidate = Candidate(
                email=f"search{i}@example.com",
                first_name="Search",
                last_name=f"User{i}"
            )
            db_session.add(candidate)
        
        db_session.commit()
        
        # Test first page
        response = client.get("/candidates/search/?q=Search&skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        # Test second page
        response = client.get("/candidates/search/?q=Search&skip=10&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5  # Remaining candidates
    
    def test_count_candidates_success(self, client: TestClient, db_session: Session):
        """Test candidate count endpoint"""
        # Create test candidates
        for i in range(5):
            candidate = Candidate(
                email=f"count{i}@example.com",
                first_name=f"Count{i}",
                last_name="User",
                status="active" if i < 3 else "inactive"
            )
            db_session.add(candidate)
        
        db_session.commit()
        
        # Test total count
        response = client.get("/candidates/count")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 5
        
        # Test count with status filter
        response = client.get("/candidates/count?status=active")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        
        response = client.get("/candidates/count?status=inactive")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2