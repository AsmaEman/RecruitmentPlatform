"""
Matching engine for intelligent candidate matching.

Implements TF-IDF vectorization, experience matching, education matching, and location proximity.
Requirements: 3.1, 3.2, 3.3
"""

import math
import re
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class MatchingEngine:
    """Core matching algorithm for candidates and job postings"""
    
    def __init__(self):
        """Initialize matching engine"""
        self.skill_weights = {
            'programming': 1.0,
            'web': 0.9,
            'database': 0.8,
            'cloud': 0.9,
            'data': 0.8
        }
        
        self.education_levels = {
            'high school': 1,
            'associate': 2,
            'bachelor': 3,
            'master': 4,
            'phd': 5,
            'doctorate': 5
        }
        
        logger.info("Matching engine initialized")
    
    def calculate_match_score(self, candidate: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall match score between candidate and job"""
        
        # Calculate individual component scores
        skill_score = self._calculate_skill_match(candidate.get('skills', []), job.get('required_skills', []))
        experience_score = self._calculate_experience_match(candidate.get('experience', []), job.get('required_experience', 0))
        education_score = self._calculate_education_match(candidate.get('education', []), job.get('required_education', ''))
        location_score = self._calculate_location_match(candidate.get('location', ''), job.get('location', ''))
        
        # Weighted overall score
        weights = {
            'skills': 0.4,
            'experience': 0.3,
            'education': 0.2,
            'location': 0.1
        }
        
        overall_score = (
            skill_score * weights['skills'] +
            experience_score * weights['experience'] +
            education_score * weights['education'] +
            location_score * weights['location']
        )
        
        return {
            'overall_score': round(overall_score, 3),
            'skill_score': round(skill_score, 3),
            'experience_score': round(experience_score, 3),
            'education_score': round(education_score, 3),
            'location_score': round(location_score, 3),
            'breakdown': {
                'skills_matched': self._get_matched_skills(candidate.get('skills', []), job.get('required_skills', [])),
                'experience_years': self._extract_total_experience(candidate.get('experience', [])),
                'education_level': self._get_highest_education(candidate.get('education', [])),
                'location_distance': self._calculate_distance(candidate.get('location', ''), job.get('location', ''))
            }
        }
    
    def _calculate_skill_match(self, candidate_skills: List[Dict[str, Any]], required_skills: List[str]) -> float:
        """Calculate skill match using TF-IDF vectorization"""
        if not required_skills:
            return 1.0
        
        # Extract candidate skill names
        candidate_skill_names = [skill.get('skill', '').lower() for skill in candidate_skills]
        required_skill_names = [skill.lower() for skill in required_skills]
        
        # Calculate TF-IDF scores
        candidate_tfidf = self._calculate_tfidf(candidate_skill_names)
        required_tfidf = self._calculate_tfidf(required_skill_names)
        
        # Calculate cosine similarity
        similarity = self._cosine_similarity(candidate_tfidf, required_tfidf)
        
        # Boost score for exact matches
        exact_matches = len(set(candidate_skill_names) & set(required_skill_names))
        match_ratio = exact_matches / len(required_skill_names) if required_skill_names else 0
        
        # Combine similarity and exact match ratio
        final_score = (similarity * 0.6) + (match_ratio * 0.4)
        
        return min(final_score, 1.0)
    
    def _calculate_tfidf(self, skills: List[str]) -> Dict[str, float]:
        """Calculate TF-IDF scores for skills"""
        if not skills:
            return {}
        
        # Term frequency
        tf = Counter(skills)
        total_terms = len(skills)
        
        # Simple IDF calculation (in real implementation, use corpus)
        # For now, use skill category weights as IDF proxy
        tfidf = {}
        for skill, count in tf.items():
            tf_score = count / total_terms
            idf_score = self.skill_weights.get(self._get_skill_category(skill), 1.0)
            tfidf[skill] = tf_score * idf_score
        
        return tfidf
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two TF-IDF vectors"""
        if not vec1 or not vec2:
            return 0.0
        
        # Get all unique terms
        all_terms = set(vec1.keys()) | set(vec2.keys())
        
        # Calculate dot product and magnitudes
        dot_product = sum(vec1.get(term, 0) * vec2.get(term, 0) for term in all_terms)
        magnitude1 = math.sqrt(sum(score ** 2 for score in vec1.values()))
        magnitude2 = math.sqrt(sum(score ** 2 for score in vec2.values()))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _get_skill_category(self, skill: str) -> str:
        """Get category for a skill (simplified mapping)"""
        skill_categories = {
            'python': 'programming',
            'java': 'programming',
            'javascript': 'programming',
            'react': 'web',
            'angular': 'web',
            'html': 'web',
            'css': 'web',
            'mysql': 'database',
            'postgresql': 'database',
            'mongodb': 'database',
            'aws': 'cloud',
            'azure': 'cloud',
            'docker': 'cloud',
            'pandas': 'data',
            'numpy': 'data',
            'tensorflow': 'data'
        }
        return skill_categories.get(skill.lower(), 'programming')
    
    def _calculate_experience_match(self, candidate_experience: List[Dict[str, Any]], required_years: int) -> float:
        """Calculate experience match based on years of experience"""
        if required_years == 0:
            return 1.0
        
        total_experience = self._extract_total_experience(candidate_experience)
        
        if total_experience >= required_years:
            # Bonus for exceeding requirements, but cap at 1.0
            return min(1.0 + (total_experience - required_years) * 0.05, 1.0)
        else:
            # Penalty for not meeting requirements
            return total_experience / required_years
    
    def _extract_total_experience(self, experience: List[Dict[str, Any]]) -> float:
        """Extract total years of experience from experience list"""
        total_years = 0.0
        
        for exp in experience:
            # Try to extract years from experience data
            if 'years' in exp:
                total_years += float(exp['years'])
            elif 'start_date' in exp and 'end_date' in exp:
                # Calculate years from dates
                try:
                    start = datetime.strptime(exp['start_date'], '%Y-%m-%d')
                    end = datetime.strptime(exp['end_date'], '%Y-%m-%d') if exp['end_date'] else datetime.now()
                    years = (end - start).days / 365.25
                    total_years += years
                except:
                    # Fallback: assume 2 years per position
                    total_years += 2.0
            else:
                # Default assumption
                total_years += 2.0
        
        return total_years
    
    def _calculate_education_match(self, candidate_education: List[Dict[str, Any]], required_education: str) -> float:
        """Calculate education match based on degree levels"""
        if not required_education:
            return 1.0
        
        candidate_level = self._get_highest_education_level(candidate_education)
        required_level = self._parse_education_level(required_education)
        
        if candidate_level >= required_level:
            return 1.0
        else:
            # Partial credit for lower education levels
            return candidate_level / required_level if required_level > 0 else 0.0
    
    def _get_highest_education_level(self, education: List[Dict[str, Any]]) -> int:
        """Get the highest education level from candidate's education"""
        max_level = 0
        
        for edu in education:
            degree = edu.get('degree', '').lower()
            level = self._parse_education_level(degree)
            max_level = max(max_level, level)
        
        return max_level
    
    def _get_highest_education(self, education: List[Dict[str, Any]]) -> str:
        """Get the highest education degree name"""
        max_level = 0
        highest_degree = 'None'
        
        for edu in education:
            degree = edu.get('degree', '')
            level = self._parse_education_level(degree)
            if level > max_level:
                max_level = level
                highest_degree = degree
        
        return highest_degree
    
    def _parse_education_level(self, education: str) -> int:
        """Parse education string to get numeric level"""
        education_lower = education.lower()
        
        for level_name, level_value in self.education_levels.items():
            if level_name in education_lower:
                return level_value
        
        return 0
    
    def _calculate_location_match(self, candidate_location: str, job_location: str) -> float:
        """Calculate location proximity match"""
        if not job_location or not candidate_location:
            return 0.5  # Neutral score for missing location data
        
        # Simple string matching (in real implementation, use geocoding)
        candidate_lower = candidate_location.lower()
        job_lower = job_location.lower()
        
        if candidate_lower == job_lower:
            return 1.0
        elif any(word in candidate_lower for word in job_lower.split()):
            return 0.8
        elif 'remote' in job_lower or 'remote' in candidate_lower:
            return 0.9
        else:
            return 0.3
    
    def _calculate_distance(self, location1: str, location2: str) -> str:
        """Calculate distance between locations (simplified)"""
        if not location1 or not location2:
            return 'Unknown'
        
        if location1.lower() == location2.lower():
            return '0 miles'
        elif 'remote' in location1.lower() or 'remote' in location2.lower():
            return 'Remote'
        else:
            return 'Different cities'
    
    def _get_matched_skills(self, candidate_skills: List[Dict[str, Any]], required_skills: List[str]) -> List[str]:
        """Get list of matched skills between candidate and job"""
        candidate_skill_names = [skill.get('skill', '').lower() for skill in candidate_skills]
        required_skill_names = [skill.lower() for skill in required_skills]
        
        matched = list(set(candidate_skill_names) & set(required_skill_names))
        return matched
    
    def rank_candidates(self, candidates: List[Dict[str, Any]], job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank candidates by match score for a job"""
        scored_candidates = []
        
        for candidate in candidates:
            match_result = self.calculate_match_score(candidate, job)
            scored_candidates.append({
                'candidate': candidate,
                'match_score': match_result['overall_score'],
                'match_details': match_result
            })
        
        # Sort by match score (descending)
        scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)
        
        return scored_candidates