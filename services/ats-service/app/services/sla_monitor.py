import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .workflow_service import WorkflowService

logger = logging.getLogger(__name__)

class SLAMonitorService:
    """Background service for monitoring SLA violations and triggering escalations"""
    
    def __init__(self):
        self.is_running = False
        self.check_interval = 300  # Check every 5 minutes
    
    async def start_monitoring(self):
        """Start the SLA monitoring background task"""
        self.is_running = True
        logger.info("SLA monitoring service started")
        
        while self.is_running:
            try:
                await self._check_sla_violations()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in SLA monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop_monitoring(self):
        """Stop the SLA monitoring background task"""
        self.is_running = False
        logger.info("SLA monitoring service stopped")
    
    async def _check_sla_violations(self):
        """Check for SLA violations and create escalations"""
        db = next(get_db())
        try:
            workflow_service = WorkflowService(db)
            
            # Get all overdue stage transitions
            overdue_transitions = workflow_service.check_sla_violations()
            
            if overdue_transitions:
                logger.info(f"Found {len(overdue_transitions)} SLA violations")
                
                for transition in overdue_transitions:
                    try:
                        # Calculate how overdue the application is
                        overdue_hours = (datetime.utcnow() - transition.sla_deadline).total_seconds() / 3600
                        
                        # Determine escalation type based on how overdue
                        if overdue_hours < 24:
                            escalation_type = "warning"
                        elif overdue_hours < 72:
                            escalation_type = "critical"
                        else:
                            escalation_type = "overdue"
                        
                        # Create escalation
                        escalation = workflow_service.escalate_sla_violation(
                            stage_transition=transition,
                            escalation_type=escalation_type
                        )
                        
                        logger.info(f"Created {escalation_type} escalation for application {transition.application_id}")
                        
                        # TODO: Send notification to escalated user
                        # This would integrate with the notification service
                        
                    except Exception as e:
                        logger.error(f"Failed to escalate SLA violation for transition {transition.id}: {e}")
            
        except Exception as e:
            logger.error(f"Error checking SLA violations: {e}")
        finally:
            db.close()
    
    async def send_daily_sla_report(self):
        """Send daily SLA performance report to managers"""
        # This would be implemented to send daily reports
        # showing SLA performance metrics
        pass

# Global instance
sla_monitor = SLAMonitorService()