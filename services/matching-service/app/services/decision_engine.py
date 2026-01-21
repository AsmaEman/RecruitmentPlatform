"""
Automated decision engine for candidate screening.

Implements auto-shortlisting, auto-rejection, and diversity filters.
Requirements: 3.5, 3.6, 3.7
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class DecisionType(Enum):
    """Decision types for candidate screening"""
    AUTO_SHORTLIST = "auto_shortlist"
    AUTO_REJECT = "auto_reject"
    MANUAL_REVIEW = "manual_review"
    DIVERSITY_HOLD = "diversity_hold"

class DecisionEngine:
    """Automated decision engine for candidate screening"""
    
    def __init__(self):
        """Initialize decision engine with configurable thresholds"""
        self.config = {
            'auto_shortlist_threshold': 0.85,
            'auto_reject_threshold': 0.3,
            'diversity_targets': {
                'gender_balance': 0.4,  # Minimum 40% representation
                'experience_diversity': True,
                'education_diversity': True,
                'location_diversity': True
            },
            'max_shortlist_size': 20,
            'min_shortlist_size': 5
        }
        
        logger.info("Decision engine initialized")
    
    def make_screening_decisions(self, scored_candidates: List[Dict[str, Any]], 
                               job_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Make automated screening decisions for all candidates"""
        
        decisions = {
            'auto_shortlisted': [],
            'auto_rejected': [],
            'manual_review': [],
            'diversity_held': [],
            'summary': {}
        }
        
        # Sort candidates by score (descending)
        sorted_candidates = sorted(scored_candidates, 
                                 key=lambda x: x.get('match_score', 0), 
                                 reverse=True)
        
        # Apply initial screening rules
        for candidate_data in sorted_candidates:
            decision = self._evaluate_candidate(candidate_data, job_requirements)
            
            if decision == DecisionType.AUTO_SHORTLIST:
                decisions['auto_shortlisted'].append(candidate_data)
            elif decision == DecisionType.AUTO_REJECT:
                decisions['auto_rejected'].append(candidate_data)
            elif decision == DecisionType.DIVERSITY_HOLD:
                decisions['diversity_held'].append(candidate_data)
            else:
                decisions['manual_review'].append(candidate_data)
        
        # Apply diversity filters
        final_shortlist = self._apply_diversity_filters(
            decisions['auto_shortlisted'] + decisions['diversity_held'],
            job_requirements
        )
        
        # Update decisions based on diversity filtering
        shortlisted_ids = {c['candidate']['id'] for c in final_shortlist}
        
        # Move non-selected diversity candidates to manual review
        for candidate_data in decisions['diversity_held']:
            if candidate_data['candidate']['id'] not in shortlisted_ids:
                decisions['manual_review'].append(candidate_data)
        
        decisions['auto_shortlisted'] = final_shortlist
        decisions['diversity_held'] = []  # Clear since we've processed them
        
        # Generate summary
        decisions['summary'] = self._generate_summary(decisions, len(scored_candidates))
        
        return decisions
    
    def _evaluate_candidate(self, candidate_data: Dict[str, Any], 
                          job_requirements: Dict[str, Any]) -> DecisionType:
        """Evaluate individual candidate for automated decision"""
        
        match_score = candidate_data.get('match_score', 0)
        candidate = candidate_data.get('candidate', {})
        match_details = candidate_data.get('match_details', {})
        
        # Auto-shortlist high-scoring candidates
        if match_score >= self.config['auto_shortlist_threshold']:
            return DecisionType.AUTO_SHORTLIST
        
        # Auto-reject low-scoring candidates
        if match_score <= self.config['auto_reject_threshold']:
            return DecisionType.AUTO_REJECT
        
        # Check for critical requirements
        if self._has_critical_gaps(match_details, job_requirements):
            return DecisionType.AUTO_REJECT
        
        # Check if candidate adds diversity value
        if self._adds_diversity_value(candidate, job_requirements):
            return DecisionType.DIVERSITY_HOLD
        
        return DecisionType.MANUAL_REVIEW
    
    def _has_critical_gaps(self, match_details: Dict[str, Any], 
                          job_requirements: Dict[str, Any]) -> bool:
        """Check if candidate has critical gaps in requirements"""
        
        # Check critical skills
        critical_skills = job_requirements.get('critical_skills', [])
        if critical_skills:
            matched_skills = match_details.get('breakdown', {}).get('skills_matched', [])
            critical_matched = [skill for skill in critical_skills if skill.lower() in matched_skills]
            
            if len(critical_matched) < len(critical_skills) * 0.5:  # Must have 50% of critical skills
                return True
        
        # Check minimum experience
        min_experience = job_requirements.get('minimum_experience', 0)
        candidate_experience = match_details.get('breakdown', {}).get('experience_years', 0)
        
        if min_experience > 0 and candidate_experience < min_experience * 0.7:  # 70% of minimum
            return True
        
        # Check required education level
        required_education = job_requirements.get('required_education', '')
        if required_education and match_details.get('education_score', 0) < 0.5:
            return True
        
        return False
    
    def _adds_diversity_value(self, candidate: Dict[str, Any], 
                            job_requirements: Dict[str, Any]) -> bool:
        """Check if candidate adds diversity value to the pool"""
        
        # Check for underrepresented characteristics
        diversity_factors = []
        
        # Gender diversity (if available)
        gender = candidate.get('gender', '').lower()
        if gender in ['female', 'non-binary', 'other']:
            diversity_factors.append('gender')
        
        # Experience level diversity
        experience_years = candidate.get('total_experience', 0)
        if experience_years < 2:  # Junior level
            diversity_factors.append('junior_experience')
        elif experience_years > 10:  # Senior level
            diversity_factors.append('senior_experience')
        
        # Educational background diversity
        education = candidate.get('education', [])
        for edu in education:
            degree = edu.get('degree', '').lower()
            if 'associate' in degree or 'bootcamp' in degree or 'certificate' in degree:
                diversity_factors.append('alternative_education')
                break
        
        # Location diversity
        location = candidate.get('location', '').lower()
        if 'remote' in location or any(city in location for city in ['international', 'global']):
            diversity_factors.append('location_diversity')
        
        return len(diversity_factors) > 0
    
    def _apply_diversity_filters(self, candidates: List[Dict[str, Any]], 
                               job_requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply diversity filters to create balanced shortlist"""
        
        if not candidates:
            return []
        
        # Sort by match score
        candidates.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        # Start with top performers
        shortlist = []
        diversity_stats = {
            'gender': {},
            'experience_level': {},
            'education_type': {},
            'location_type': {}
        }
        
        max_size = self.config['max_shortlist_size']
        
        # First pass: Add top candidates regardless of diversity
        top_threshold = 0.9
        for candidate_data in candidates:
            if len(shortlist) >= max_size:
                break
            
            if candidate_data.get('match_score', 0) >= top_threshold:
                shortlist.append(candidate_data)
                self._update_diversity_stats(candidate_data['candidate'], diversity_stats)
        
        # Second pass: Add candidates considering diversity
        for candidate_data in candidates:
            if len(shortlist) >= max_size:
                break
            
            if candidate_data in shortlist:
                continue
            
            candidate = candidate_data['candidate']
            
            # Check if adding this candidate improves diversity
            if self._improves_diversity(candidate, diversity_stats, len(shortlist)):
                shortlist.append(candidate_data)
                self._update_diversity_stats(candidate, diversity_stats)
            elif len(shortlist) < self.config['min_shortlist_size']:
                # Add anyway if we haven't reached minimum size
                shortlist.append(candidate_data)
                self._update_diversity_stats(candidate, diversity_stats)
        
        return shortlist
    
    def _update_diversity_stats(self, candidate: Dict[str, Any], 
                              diversity_stats: Dict[str, Dict[str, int]]):
        """Update diversity statistics with new candidate"""
        
        # Gender
        gender = candidate.get('gender', 'not_specified').lower()
        diversity_stats['gender'][gender] = diversity_stats['gender'].get(gender, 0) + 1
        
        # Experience level
        experience = candidate.get('total_experience', 0)
        if experience < 2:
            level = 'junior'
        elif experience < 5:
            level = 'mid'
        elif experience < 10:
            level = 'senior'
        else:
            level = 'expert'
        
        diversity_stats['experience_level'][level] = diversity_stats['experience_level'].get(level, 0) + 1
        
        # Education type
        education = candidate.get('education', [])
        edu_type = 'traditional'
        for edu in education:
            degree = edu.get('degree', '').lower()
            if 'bootcamp' in degree or 'certificate' in degree:
                edu_type = 'alternative'
                break
        
        diversity_stats['education_type'][edu_type] = diversity_stats['education_type'].get(edu_type, 0) + 1
        
        # Location type
        location = candidate.get('location', '').lower()
        if 'remote' in location:
            loc_type = 'remote'
        else:
            loc_type = 'onsite'
        
        diversity_stats['location_type'][loc_type] = diversity_stats['location_type'].get(loc_type, 0) + 1
    
    def _improves_diversity(self, candidate: Dict[str, Any], 
                          diversity_stats: Dict[str, Dict[str, int]], 
                          current_size: int) -> bool:
        """Check if adding candidate improves diversity"""
        
        if current_size == 0:
            return True
        
        improvements = 0
        
        # Check gender diversity
        gender = candidate.get('gender', 'not_specified').lower()
        if gender in ['female', 'non-binary'] and diversity_stats['gender'].get(gender, 0) == 0:
            improvements += 1
        
        # Check experience diversity
        experience = candidate.get('total_experience', 0)
        if experience < 2 and diversity_stats['experience_level'].get('junior', 0) == 0:
            improvements += 1
        elif experience > 10 and diversity_stats['experience_level'].get('expert', 0) == 0:
            improvements += 1
        
        # Check education diversity
        education = candidate.get('education', [])
        has_alternative_ed = any('bootcamp' in edu.get('degree', '').lower() or 
                               'certificate' in edu.get('degree', '').lower() 
                               for edu in education)
        if has_alternative_ed and diversity_stats['education_type'].get('alternative', 0) == 0:
            improvements += 1
        
        # Check location diversity
        location = candidate.get('location', '').lower()
        if 'remote' in location and diversity_stats['location_type'].get('remote', 0) == 0:
            improvements += 1
        
        return improvements > 0
    
    def _generate_summary(self, decisions: Dict[str, List], total_candidates: int) -> Dict[str, Any]:
        """Generate summary of screening decisions"""
        
        return {
            'total_candidates': total_candidates,
            'auto_shortlisted': len(decisions['auto_shortlisted']),
            'auto_rejected': len(decisions['auto_rejected']),
            'manual_review': len(decisions['manual_review']),
            'shortlist_rate': len(decisions['auto_shortlisted']) / total_candidates if total_candidates > 0 else 0,
            'rejection_rate': len(decisions['auto_rejected']) / total_candidates if total_candidates > 0 else 0,
            'automation_rate': (len(decisions['auto_shortlisted']) + len(decisions['auto_rejected'])) / total_candidates if total_candidates > 0 else 0
        }
    
    def update_thresholds(self, new_config: Dict[str, Any]):
        """Update decision thresholds and configuration"""
        self.config.update(new_config)
        logger.info(f"Decision engine configuration updated: {new_config}")
    
    def get_decision_explanation(self, candidate_data: Dict[str, Any], 
                               job_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Get explanation for a specific candidate decision"""
        
        match_score = candidate_data.get('match_score', 0)
        candidate = candidate_data.get('candidate', {})
        match_details = candidate_data.get('match_details', {})
        
        explanation = {
            'decision': self._evaluate_candidate(candidate_data, job_requirements).value,
            'match_score': match_score,
            'factors': []
        }
        
        # Score-based factors
        if match_score >= self.config['auto_shortlist_threshold']:
            explanation['factors'].append(f"High match score ({match_score:.2f}) exceeds auto-shortlist threshold")
        elif match_score <= self.config['auto_reject_threshold']:
            explanation['factors'].append(f"Low match score ({match_score:.2f}) below auto-reject threshold")
        
        # Critical gaps
        if self._has_critical_gaps(match_details, job_requirements):
            explanation['factors'].append("Has critical gaps in required qualifications")
        
        # Diversity value
        if self._adds_diversity_value(candidate, job_requirements):
            explanation['factors'].append("Adds diversity value to candidate pool")
        
        return explanation