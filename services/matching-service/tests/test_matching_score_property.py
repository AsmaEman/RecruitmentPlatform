"""
Property test for matching score calculation.

**Property 8: Matching Score Calculation**
**Validates: Requirements 3.3**

Feature: recruitment-testing-platform, Property 8: Matching Score Calculation
"""

import pytest
from hypothesis import given, strategies as st, assume

from app.services.matching_engine import MatchingEngine


class TestMatchingScoreProperty:
    """Property tests for matching score calculation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = MatchingEngine()
    
    @given(
        candidate_skills=st.lists(
            st.fixed_dictionaries({
                'skill': st.sampled_from(['python', 'java', 'javascript', 'react', 'sql', 'aws']),
                'category': st.sampled_from(['programming', 'web', 'database', 'cloud']),
                'confidence': st.floats(min_value=0.1, max_value=1.0)
            }),
            min_size=0,
            max_size=10
        ),
        required_skills=st.lists(
            st.sampled_from(['python', 'java', 'javascript', 'react', 'sql', 'aws']),
            min_size=0,
            max_size=8
        )
    )
    def test_matching_score_bounds(self, candidate_skills, required_skills):
        """
        Property: Matching scores should always be between 0 and 1.
        
        **Validates: Requirements 3.3**
        """
        candidate = {
            'skills': candidate_skills,
            'experience': [{'years': 3}],
            'education': [{'degree': 'Bachelor'}],
            'location': 'New York'
        }
        
        job = {
            'required_skills': required_skills,
            'required_experience': 2,
            'required_education': 'Bachelor',
            'location': 'New York'
        }
        
        result = self.engine.calculate_match_score(candidate, job)
        
        # Property: All scores should be between 0 and 1
        assert 0.0 <= result['overall_score'] <= 1.0, "Overall score should be between 0 and 1"
        assert 0.0 <= result['skill_score'] <= 1.0, "Skill score should be between 0 and 1"
        assert 0.0 <= result['experience_score'] <= 1.0, "Experience score should be between 0 and 1"
        assert 0.0 <= result['education_score'] <= 1.0, "Education score should be between 0 and 1"
        assert 0.0 <= result['location_score'] <= 1.0, "Location score should be between 0 and 1"
    
    def test_perfect_match_score(self):
        """
        Property: Perfect matches should have high scores.
        
        **Validates: Requirements 3.3**
        """
        candidate = {
            'skills': [
                {'skill': 'python', 'category': 'programming', 'confidence': 0.9},
                {'skill': 'react', 'category': 'web', 'confidence': 0.8}
            ],
            'experience': [{'years': 5}],
            'education': [{'degree': 'Bachelor Computer Science'}],
            'location': 'San Francisco'
        }
        
        job = {
            'required_skills': ['python', 'react'],
            'required_experience': 3,
            'required_education': 'Bachelor',
            'location': 'San Francisco'
        }
        
        result = self.engine.calculate_match_score(candidate, job)
        
        # Property: Perfect or near-perfect matches should have high overall scores
        assert result['overall_score'] >= 0.8, "Perfect match should have high overall score"
        assert result['skill_score'] >= 0.8, "Matching skills should have high skill score"
        assert result['location_score'] >= 0.8, "Same location should have high location score"
    
    def test_no_match_score(self):
        """
        Property: Candidates with no matching qualifications should have low scores.
        
        **Validates: Requirements 3.3**
        """
        candidate = {
            'skills': [
                {'skill': 'cooking', 'category': 'other', 'confidence': 0.9}
            ],
            'experience': [],
            'education': [],
            'location': 'Remote'
        }
        
        job = {
            'required_skills': ['python', 'java', 'react'],
            'required_experience': 5,
            'required_education': 'Master',
            'location': 'New York'
        }
        
        result = self.engine.calculate_match_score(candidate, job)
        
        # Property: Poor matches should have low overall scores
        assert result['overall_score'] <= 0.5, "Poor match should have low overall score"
        assert result['skill_score'] <= 0.3, "No matching skills should have low skill score"
    
    @given(
        experience_years=st.integers(min_value=0, max_value=20),
        required_years=st.integers(min_value=0, max_value=15)
    )
    def test_experience_score_monotonicity(self, experience_years, required_years):
        """
        Property: More experience should never decrease the experience score.
        
        **Validates: Requirements 3.3**
        """
        candidate1 = {
            'skills': [],
            'experience': [{'years': experience_years}],
            'education': [],
            'location': 'Remote'
        }
        
        candidate2 = {
            'skills': [],
            'experience': [{'years': experience_years + 1}],
            'education': [],
            'location': 'Remote'
        }
        
        job = {
            'required_skills': [],
            'required_experience': required_years,
            'required_education': '',
            'location': 'Remote'
        }
        
        result1 = self.engine.calculate_match_score(candidate1, job)
        result2 = self.engine.calculate_match_score(candidate2, job)
        
        # Property: More experience should lead to higher or equal experience score
        assert result2['experience_score'] >= result1['experience_score'], \
            "More experience should not decrease experience score"
    
    def test_skill_match_consistency(self):
        """
        Property: Skill matching should be consistent and symmetric in terms of overlap.
        
        **Validates: Requirements 3.3**
        """
        # Test cases with different skill overlaps
        test_cases = [
            # Complete overlap
            {
                'candidate_skills': ['python', 'java', 'react'],
                'required_skills': ['python', 'java', 'react'],
                'expected_min_score': 0.8
            },
            # Partial overlap
            {
                'candidate_skills': ['python', 'java'],
                'required_skills': ['python', 'react'],
                'expected_min_score': 0.3
            },
            # No overlap
            {
                'candidate_skills': ['cooking', 'driving'],
                'required_skills': ['python', 'java'],
                'expected_min_score': 0.0
            }
        ]
        
        for case in test_cases:
            candidate = {
                'skills': [{'skill': skill, 'category': 'programming', 'confidence': 0.8} 
                          for skill in case['candidate_skills']],
                'experience': [{'years': 3}],
                'education': [{'degree': 'Bachelor'}],
                'location': 'Remote'
            }
            
            job = {
                'required_skills': case['required_skills'],
                'required_experience': 2,
                'required_education': 'Bachelor',
                'location': 'Remote'
            }
            
            result = self.engine.calculate_match_score(candidate, job)
            
            # Property: Skill score should meet minimum expectations based on overlap
            assert result['skill_score'] >= case['expected_min_score'], \
                f"Skill score {result['skill_score']} should be >= {case['expected_min_score']} for case {case}"
    
    def test_education_level_ordering(self):
        """
        Property: Higher education levels should result in higher or equal education scores.
        
        **Validates: Requirements 3.3**
        """
        education_levels = [
            ('High School', 'Bachelor'),
            ('Bachelor', 'Master'),
            ('Master', 'PhD')
        ]
        
        for lower_ed, higher_ed in education_levels:
            candidate_lower = {
                'skills': [],
                'experience': [],
                'education': [{'degree': lower_ed}],
                'location': 'Remote'
            }
            
            candidate_higher = {
                'skills': [],
                'experience': [],
                'education': [{'degree': higher_ed}],
                'location': 'Remote'
            }
            
            job = {
                'required_skills': [],
                'required_experience': 0,
                'required_education': 'Bachelor',
                'location': 'Remote'
            }
            
            result_lower = self.engine.calculate_match_score(candidate_lower, job)
            result_higher = self.engine.calculate_match_score(candidate_higher, job)
            
            # Property: Higher education should lead to higher or equal education score
            assert result_higher['education_score'] >= result_lower['education_score'], \
                f"Higher education ({higher_ed}) should have >= score than lower education ({lower_ed})"
    
    @given(
        num_candidates=st.integers(min_value=2, max_value=10)
    )
    def test_ranking_consistency(self, num_candidates):
        """
        Property: Candidate ranking should be consistent with individual match scores.
        
        **Validates: Requirements 3.3**
        """
        # Create candidates with varying qualifications
        candidates = []
        for i in range(num_candidates):
            candidates.append({
                'id': i,
                'skills': [{'skill': 'python', 'category': 'programming', 'confidence': 0.8}] if i % 2 == 0 else [],
                'experience': [{'years': i}],
                'education': [{'degree': 'Bachelor'}] if i % 3 == 0 else [],
                'location': 'New York' if i % 4 == 0 else 'Remote'
            })
        
        job = {
            'required_skills': ['python'],
            'required_experience': 2,
            'required_education': 'Bachelor',
            'location': 'New York'
        }
        
        ranked_candidates = self.engine.rank_candidates(candidates, job)
        
        # Property: Candidates should be ranked in descending order of match score
        for i in range(len(ranked_candidates) - 1):
            current_score = ranked_candidates[i]['match_score']
            next_score = ranked_candidates[i + 1]['match_score']
            assert current_score >= next_score, \
                f"Candidates should be ranked by descending match score: {current_score} >= {next_score}"
        
        # Property: All candidates should be included in ranking
        assert len(ranked_candidates) == num_candidates, "All candidates should be included in ranking"