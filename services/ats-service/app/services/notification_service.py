from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import logging

from ..models import Application, Candidate, JobPosting, User, ApplicationStatusHistory

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling automated notifications on status changes"""
    
    def __init__(self, db: Session):
        self.db = db
        self.sent_notifications = []  # In-memory store for testing
    
    def send_status_change_notification(
        self, 
        application_id: UUID, 
        status_change: ApplicationStatusHistory
    ) -> Dict[str, Any]:
        """Send notification when application status changes"""
        
        # Get application details
        application = self.db.query(Application).filter(
            Application.id == application_id
        ).first()
        
        if not application:
            raise ValueError(f"Application {application_id} not found")
        
        candidate = application.candidate
        job = application.job
        changed_by_user = self.db.query(User).filter(
            User.id == status_change.changed_by
        ).first()
        
        # Determine notification recipients and content
        notification_data = {
            "notification_id": f"notif_{application_id}_{status_change.id}",
            "application_id": application_id,
            "candidate_email": candidate.email,
            "candidate_name": f"{candidate.first_name} {candidate.last_name}",
            "job_title": job.title,
            "previous_status": status_change.previous_status,
            "new_status": status_change.new_status,
            "changed_by": f"{changed_by_user.first_name} {changed_by_user.last_name}" if changed_by_user else "System",
            "change_reason": status_change.change_reason,
            "timestamp": status_change.created_at,
            "sent_at": datetime.utcnow()
        }
        
        # Determine notification type and recipients
        recipients = []
        
        # Always notify the candidate
        recipients.append({
            "type": "candidate",
            "email": candidate.email,
            "name": f"{candidate.first_name} {candidate.last_name}"
        })
        
        # Notify hiring manager for certain status changes
        if status_change.new_status in ['interview', 'offer', 'hired', 'rejected']:
            hiring_manager = self.db.query(User).filter(
                User.id == job.created_by
            ).first()
            
            if hiring_manager:
                recipients.append({
                    "type": "hiring_manager",
                    "email": hiring_manager.email,
                    "name": f"{hiring_manager.first_name} {hiring_manager.last_name}"
                })
        
        notification_data["recipients"] = recipients
        
        # Store notification (in real implementation, this would send emails)
        self.sent_notifications.append(notification_data)
        
        logger.info(f"Notification sent for application {application_id} status change to {status_change.new_status}")
        
        return notification_data
    
    def get_sent_notifications(self) -> List[Dict[str, Any]]:
        """Get all sent notifications (for testing purposes)"""
        return self.sent_notifications.copy()
    
    def clear_notifications(self):
        """Clear all sent notifications (for testing purposes)"""
        self.sent_notifications.clear()
    
    def get_notifications_for_application(self, application_id: UUID) -> List[Dict[str, Any]]:
        """Get all notifications sent for a specific application"""
        return [
            notif for notif in self.sent_notifications 
            if notif["application_id"] == application_id
        ]
    
    def should_send_notification(self, status_change: ApplicationStatusHistory) -> bool:
        """Determine if a notification should be sent for this status change"""
        # Define status changes that trigger notifications
        notification_statuses = [
            'screening', 'interview', 'technical_test', 'final_interview', 
            'offer', 'hired', 'rejected', 'withdrawn'
        ]
        
        return status_change.new_status in notification_statuses
    
    def get_notification_template(self, status: str, recipient_type: str) -> Dict[str, str]:
        """Get email template for specific status and recipient type"""
        templates = {
            "candidate": {
                "screening": {
                    "subject": "Application Update: {job_title}",
                    "body": "Dear {candidate_name}, your application for {job_title} has moved to the screening stage."
                },
                "interview": {
                    "subject": "Interview Invitation: {job_title}",
                    "body": "Dear {candidate_name}, you have been invited for an interview for {job_title}."
                },
                "offer": {
                    "subject": "Job Offer: {job_title}",
                    "body": "Dear {candidate_name}, congratulations! We would like to offer you the position of {job_title}."
                },
                "rejected": {
                    "subject": "Application Update: {job_title}",
                    "body": "Dear {candidate_name}, thank you for your interest in {job_title}. We have decided to move forward with other candidates."
                }
            },
            "hiring_manager": {
                "interview": {
                    "subject": "Candidate Ready for Interview: {candidate_name}",
                    "body": "Candidate {candidate_name} is ready for interview for position {job_title}."
                },
                "offer": {
                    "subject": "Offer Extended: {candidate_name}",
                    "body": "An offer has been extended to {candidate_name} for position {job_title}."
                }
            }
        }
        
        return templates.get(recipient_type, {}).get(status, {
            "subject": "Application Status Update",
            "body": "Application status has been updated."
        })