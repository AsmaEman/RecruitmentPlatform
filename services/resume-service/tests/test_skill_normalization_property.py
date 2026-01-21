"""
Property test for skill normalization consistency.

**Property 7: Skill Normalization Consistency**
**Validates: Requirements 2.7**

Feature: recruitment-testing-platform, Property 7: Skill Normalization Consistency
"""

import pytest
from hypothesis import given, strategies as st, assume

from app.services.nlp_service import NLPService


class TestSkillNormalizationProperty:
    """Property tests for skill normalization consistency"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.nlp_service = NLPService()
    
    @given(
        skills_input=st.lists(
            st.fixed_dictionaries({
                'skill': st.sampled_from(['Python', 'python', 'PYTHON', 'py', 'JavaScript', 'javascript', 'JS', 'js', 'React', 'react.js', 'ReactJS']),
                'category': st.sampled_from(['programming', 'web', 'database']),
                'confidence': st.floats(min_value=0.1, max_value=1.0)
            }),
            min_size=1,
            max_size=10
        )
    )
    def test_skill_normalization_idempotency(self, skills_input):
        """
        Property: Normalizing skills multiple times should produce the same result.
        
        **Validates: Requirements 2.7**
        """
        assume(len(skills_input) > 0)
        assume(all(isinstance(skill.get('skill'), str) for skill in skills_input))
        
        # First normalization
        normalized_once = self.nlp_service.normalize_skills(skills_input)
        
        # Second normalization (should be idempotent)
        normalized_twice = self.nlp_service.normalize_skills(normalized_once)
        
        # Property: Normalizing twice should give same result as normalizing once
        assert len(normalized_once) == len(normalized_twice), "Normalization should be idempotent"
        
        # Check that skill names are the same
        skills_once = {skill['skill'] for skill in normalized_once}
        skills_twice = {skill['skill'] for skill in normalized_twice}
        assert skills_once == skills_twice, "Skill names should be identical after repeated normalization"
    
    @given(
        duplicate_skills=st.lists(
            st.sampled_from([
                {'skill': 'Python', 'category': 'programming', 'confidence': 0.9},
                {'skill': 'python', 'category': 'programming', 'confidence': 0.8},
                {'skill': 'PYTHON', 'category': 'programming', 'confidence': 0.7},
                {'skill': 'JavaScript', 'category': 'web', 'confidence': 0.9},
                {'skill': 'javascript', 'category': 'web', 'confidence': 0.8},
                {'skill': 'JS', 'category': 'web', 'confidence': 0.6},
            ]),
            min_size=2,
            max_size=6
        )
    )
    def test_skill_deduplication_consistency(self, duplicate_skills):
        """
        Property: Skills with the same normalized name should be deduplicated,
        keeping the highest confidence score.
        
        **Validates: Requirements 2.7**
        """
        assume(len(duplicate_skills) >= 2)
        
        # Normalize skills
        normalized = self.nlp_service.normalize_skills(duplicate_skills)
        
        # Property: No duplicate normalized skill names
        skill_names = [skill['skill'] for skill in normalized]
        assert len(skill_names) == len(set(skill_names)), "Should not have duplicate normalized skill names"
        
        # Property: For each normalized skill, confidence should be the maximum
        # from the original duplicates
        for norm_skill in normalized:
            norm_name = norm_skill['skill']
            
            # Find all original skills that would normalize to this name
            original_confidences = []
            for orig_skill in duplicate_skills:
                if self.nlp_service._normalize_skill_name(orig_skill['skill']) == norm_name:
                    original_confidences.append(orig_skill['confidence'])
            
            if original_confidences:
                max_confidence = max(original_confidences)
                assert norm_skill['confidence'] == max_confidence, f"Confidence should be maximum for {norm_name}"
    
    def test_skill_synonym_normalization(self):
        """
        Property: Known synonyms should normalize to the same canonical form.
        
        **Validates: Requirements 2.7**
        """
        # Test known synonyms
        synonym_groups = [
            (['JavaScript', 'javascript', 'JS', 'js'], 'javascript'),
            (['Python', 'python', 'py'], 'python'),
            (['React', 'react.js', 'ReactJS'], 'react'),
            (['Node.js', 'node', 'nodejs'], 'node.js'),
        ]
        
        for synonyms, expected_canonical in synonym_groups:
            skills_input = [
                {'skill': synonym, 'category': 'programming', 'confidence': 0.8}
                for synonym in synonyms
            ]
            
            normalized = self.nlp_service.normalize_skills(skills_input)
            
            # Property: All synonyms should normalize to one canonical form
            assert len(normalized) == 1, f"Synonyms {synonyms} should normalize to one skill"
            
            canonical_skill = normalized[0]
            assert canonical_skill['skill'] == expected_canonical, f"Should normalize to {expected_canonical}"
            
            # Property: All original variants should be preserved
            assert 'variants' in canonical_skill, "Should preserve original variants"
            assert len(canonical_skill['variants']) == len(synonyms), "Should preserve all variants"
    
    @given(
        text_content=st.sampled_from([
            "John Doe python developer experience",
            "Jane Smith javascript engineer skills",
            "Alex Johnson react developer portfolio",
            "Sarah Wilson python data scientist",
            "Mike Brown javascript full stack engineer"
        ])
    )
    def test_skill_extraction_normalization_consistency(self, text_content):
        """
        Property: Skills extracted from text should be properly normalized.
        
        **Validates: Requirements 2.7**
        """
        # Extract skills from text
        extracted_skills = self.nlp_service._extract_skills(text_content)
        
        if extracted_skills:
            # Normalize the extracted skills
            normalized_skills = self.nlp_service.normalize_skills(extracted_skills)
            
            # Property: Normalized skills should have consistent structure
            for skill in normalized_skills:
                assert 'skill' in skill, "Normalized skill should have 'skill' field"
                assert 'category' in skill, "Normalized skill should have 'category' field"
                assert 'confidence' in skill, "Normalized skill should have 'confidence' field"
                assert 'variants' in skill, "Normalized skill should have 'variants' field"
                
                # Property: Confidence should be reasonable
                assert 0.0 <= skill['confidence'] <= 1.0, "Confidence should be between 0 and 1"
                
                # Property: Skill name should be lowercase (canonical form)
                assert skill['skill'].islower() or '.' in skill['skill'], "Canonical skill names should be lowercase"
                
                # Property: Variants should include the canonical form
                variant_names = [v.lower() for v in skill['variants']]
                assert skill['skill'] in variant_names, "Variants should include the canonical form"
    
    def test_skill_category_consistency(self):
        """
        Property: Skills should be consistently categorized.
        
        **Validates: Requirements 2.7**
        """
        # Test skills with known categories
        test_cases = [
            ('python', 'programming'),
            ('javascript', 'programming'),
            ('react', 'web'),
            ('mysql', 'database'),
            ('aws', 'cloud'),
            ('pandas', 'data'),
        ]
        
        for skill_name, expected_category in test_cases:
            skills_input = [{'skill': skill_name, 'category': expected_category, 'confidence': 0.8}]
            normalized = self.nlp_service.normalize_skills(skills_input)
            
            # Property: Category should be preserved during normalization
            assert len(normalized) == 1, f"Should have one normalized skill for {skill_name}"
            assert normalized[0]['category'] == expected_category, f"Category should be {expected_category} for {skill_name}"