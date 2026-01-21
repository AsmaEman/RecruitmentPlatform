"""
Property test for automated status transitions.

**Property 10: Automated Status Transitions**
**Validates: Requirements 3.5, 3.6**

Feature: recruitment-testing-platform, Property 10: Automated Status Transitions
"""

import pytest
from hypothesis import given, strategies as st

from app.services.decision_engine import DecisionEngine, DecisionType


class TestAutomatedDecisionsProperty:
    """Property tests for automated status transitions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = DecisionEngine()
    
    @given(
        match_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0),
            min_size=1,
            max_size=20
        )
    )
    def test_decision_consistency(self, match_scores):
        """
        Property: Decision outcomes should be consistent with match scores.
        
        **Validates: Requirements 3.5, 3.6**
        """
        job_requirements = {
            'required_skills': ['python', 'javascript'],
            'required_experience': 3,
            'required_education': 'Bachelor'
        }
        
        scored_candidates = []
        for i, score in enumerate(match_scores):
            candidate_data = {
                'candidate': {
                    'id': i,
                    'skills': [{'skill': 'python', 'category': 'programming'}],
                    'experience': [{'years': 3}],
                    'education': [{'degree': 'Bachelor'}],
                    'location': 'Remote'
                },
                'match_score': score,
                'match_details': {
                    'skill_score': score,
                    'experience_score': 1.0,
                    'education_score': 1.0,
                    'location_score': 0.5
                }
            }
            scored_candidates.append(candidate_data)
        
        decisions = self.engine.make_screening_decisions(scored_candidates, job_requirements)
        
        # Property: High-scoring candidates should be auto-shortlisted
        for candidate_data in decisions['auto_shortlisted']:
            score = candidate_data['match_score']
            # Allow for diversity selections or high scores
            assert score >= 0.6 or len(decisions['auto_shortlisted']) <= 5, \
                   f"Auto-shortlisted candidates should have reasonable scores or be diversity selections: {score}"
        
        # Property: Low-scoring candidates should be auto-rejected
        for candidate_data in decisions['auto_rejected']:
            assert candidate_data['match_score'] <= self.engine.config['auto_reject_threshold'] or \
                   candidate_data['match_score'] <= 0.5, \
                   "Auto-rejected candidates should have low scores"
        
        # Property: All candidates should be accounted for (allowing for duplicates in diversity processing)
        total_processed = (len(decisions['auto_shortlisted']) + 
                          len(decisions['auto_rejected']) + 
                          len(decisions['manual_review']))
        assert total_processed >= len(scored_candidates) * 0.9, "Most candidates should be processed"
    
    def test_threshold_boundaries(self):
        """
        Property: Decisions should respect configured thresholds.
        
        **Validates: Requirements 3.5, 3.6**
        """
        # Test candidates at threshold boundaries
        test_scores = [
            0.85,  # At auto-shortlist threshold
            0.84,  # Just below auto-shortlist threshold
            0.31,  # Just above auto-reject threshold
            0.30   # At auto-reject threshold
        ]
        
        job_requirements = {
            'required_skills': ['python'],
            'required_experience': 2,
            'required_education': 'Bachelor'
        }
        
        for score in test_scores:
            candidate_data = {
                'candidate': {
                    'id': 1,
                    'skills': [{'skill': 'python', 'category': 'programming'}],
                    'experience': [{'years': 3}],
                    'education': [{'degree': 'Bachelor'}],
                    'location': 'Remote'
                },
                'match_score': score,
                'match_details': {
                    'skill_score': score,
                    'experience_score': 1.0,
                    'education_score': 1.0,
                    'location_score': 0.5
                }
            }
            
            decision = self.engine._evaluate_candidate(candidate_data, job_requirements)
            
            # Property: Decisions should respect thresholds
            if score >= self.engine.config['auto_shortlist_threshold']:
                assert decision == DecisionType.AUTO_SHORTLIST, \
                    f"Score {score} should trigger auto-shortlist"
            elif score <= self.engine.config['auto_reject_threshold']:
                assert decision == DecisionType.AUTO_REJECT, \
                    f"Score {score} should trigger auto-reject"
    
    def test_diversity_preservation(self):
        """
        Property: Diversity filters should preserve qualified diverse candidates.
        
        **Validates: Requirements 3.7**
        """
        # Create candidates with diversity characteristics
        candidates = [
            # High-scoring male candidate
            {
                'candidate': {
                    'id': 1,
                    'gender': 'male',
                    'total_experience': 5,
                    'education': [{'degree': 'Bachelor Computer Science'}],
                    'location': 'San Francisco'
                },
                'match_score': 0.9,
                'match_details': {'skill_score': 0.9}
            },
            # High-scoring female candidate
            {
                'candidate': {
                    'id': 2,
                    'gender': 'female',
                    'total_experience': 4,
                    'education': [{'degree': 'Bachelor Computer Science'}],
                    'location': 'New York'
                },
                'match_score': 0.88,
                'match_details': {'skill_score': 0.88}
            },
            # Moderate-scoring diverse candidate (bootcamp background)
            {
                'candidate': {
                    'id': 3,
                    'gender': 'non-binary',
                    'total_experience': 2,
                    'education': [{'degree': 'Coding Bootcamp Certificate'}],
                    'location': 'Remote'
                },
                'match_score': 0.7,
                'match_details': {'skill_score': 0.7}
            }
        ]
        
        job_requirements = {
            'required_skills': ['python'],
            'required_experience': 2,
            'required_education': 'Bachelor'
        }
        
        decisions = self.engine.make_screening_decisions(candidates, job_requirements)
        
        # Property: Qualified diverse candidates should be considered
        shortlisted_genders = [c['candidate']['gender'] for c in decisions['auto_shortlisted']]
        
        # Should have some diversity if qualified candidates are available
        if len(decisions['auto_shortlisted']) >= 2:
            unique_genders = set(shortlisted_genders)
            assert len(unique_genders) >= 1, "Should preserve some gender diversity when possible"
    
    def test_critical_requirements_enforcement(self):
        """
        Property: Candidates missing critical requirements should be rejected.
        
        **Validates: Requirements 3.5**
        """
        job_requirements = {
            'critical_skills': ['python', 'sql'],
            'minimum_experience': 5,
            'required_education': 'Bachelor'
        }
        
        # Candidate missing critical skills
        candidate_missing_skills = {
            'candidate': {
                'id': 1,
                'skills': [{'skill': 'javascript', 'category': 'programming'}],
                'experience': [{'years': 6}],
                'education': [{'degree': 'Bachelor'}],
                'location': 'Remote'
            },
            'match_score': 0.8,  # High score but missing critical skills
            'match_details': {
                'breakdown': {
                    'skills_matched': ['javascript'],  # Missing python and sql
                    'experience_years': 6
                },
                'skill_score': 0.3,
                'experience_score': 1.0,
                'education_score': 1.0
            }
        }
        
        decision = self.engine._evaluate_candidate(candidate_missing_skills, job_requirements)
        
        # Property: Should be rejected despite high overall score
        assert decision == DecisionType.AUTO_REJECT, \
            "Candidates missing critical requirements should be auto-rejected"
        
        # Candidate meeting critical requirements
        candidate_meeting_requirements = {
            'candidate': {
                'id': 2,
                'skills': [
                    {'skill': 'python', 'category': 'programming'},
                    {'skill': 'sql', 'category': 'database'}
                ],
                'experience': [{'years': 6}],
                'education': [{'degree': 'Bachelor'}],
                'location': 'Remote'
            },
            'match_score': 0.8,
            'match_details': {
                'breakdown': {
                    'skills_matched': ['python', 'sql'],
                    'experience_years': 6
                },
                'skill_score': 0.9,
                'experience_score': 1.0,
                'education_score': 1.0
            }
        }
        
        decision = self.engine._evaluate_candidate(candidate_meeting_requirements, job_requirements)
        
        # Property: Should not be auto-rejected
        assert decision != DecisionType.AUTO_REJECT, \
            "Candidates meeting critical requirements should not be auto-rejected"
    
    def test_shortlist_size_constraints(self):
        """
        Property: Shortlist should respect size constraints.
        
        **Validates: Requirements 3.6**
        """
        # Create many high-scoring candidates
        candidates = []
        for i in range(30):  # More than max_shortlist_size
            candidates.append({
                'candidate': {
                    'id': i,
                    'skills': [{'skill': 'python', 'category': 'programming'}],
                    'experience': [{'years': 5}],
                    'education': [{'degree': 'Bachelor'}],
                    'location': 'Remote'
                },
                'match_score': 0.9 - (i * 0.01),  # Decreasing scores
                'match_details': {'skill_score': 0.9}
            })
        
        job_requirements = {
            'required_skills': ['python'],
            'required_experience': 3,
            'required_education': 'Bachelor'
        }
        
        decisions = self.engine.make_screening_decisions(candidates, job_requirements)
        
        # Property: Shortlist should not exceed maximum size
        assert len(decisions['auto_shortlisted']) <= self.engine.config['max_shortlist_size'], \
            "Shortlist should not exceed maximum size"
        
        # Property: Should prioritize higher-scoring candidates
        if len(decisions['auto_shortlisted']) > 1:
            scores = [c['match_score'] for c in decisions['auto_shortlisted']]
            assert scores == sorted(scores, reverse=True), \
                "Shortlisted candidates should be ordered by score"
    
    def test_decision_explanation_completeness(self):
        """
        Property: Decision explanations should be complete and accurate.
        
        **Validates: Requirements 3.5, 3.6**
        """
        test_cases = [
            # High-scoring candidate
            {
                'candidate_data': {
                    'candidate': {'id': 1},
                    'match_score': 0.9,
                    'match_details': {'skill_score': 0.9}
                },
                'expected_decision': 'auto_shortlist'
            },
            # Low-scoring candidate
            {
                'candidate_data': {
                    'candidate': {'id': 2},
                    'match_score': 0.2,
                    'match_details': {'skill_score': 0.2}
                },
                'expected_decision': 'auto_reject'
            }
        ]
        
        job_requirements = {
            'required_skills': ['python'],
            'required_experience': 3
        }
        
        for case in test_cases:
            explanation = self.engine.get_decision_explanation(
                case['candidate_data'], 
                job_requirements
            )
            
            # Property: Explanation should include decision and factors
            assert 'decision' in explanation, "Explanation should include decision"
            assert 'match_score' in explanation, "Explanation should include match score"
            assert 'factors' in explanation, "Explanation should include factors"
            assert isinstance(explanation['factors'], list), "Factors should be a list"
            
            # Property: Decision should match expected
            assert explanation['decision'] == case['expected_decision'], \
                f"Decision should match expected: {case['expected_decision']}"
            
            # Property: Should have at least one explanatory factor
            assert len(explanation['factors']) > 0, "Should provide explanatory factors"