"""
Property test for parsing accuracy threshold.

**Property 6: Parsing Accuracy Threshold**
**Validates: Requirements 2.4**

Feature: recruitment-testing-platform, Property 6: Parsing Accuracy Threshold
"""

import pytest
from hypothesis import given, strategies as st, assume

from app.services.nlp_service import NLPService
from app.services.document_processor import DocumentProcessor


class TestParsingAccuracyProperty:
    """Property tests for parsing accuracy threshold"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.nlp_service = NLPService()
        self.processor = DocumentProcessor()
    
    @given(
        quality_indicators=st.dictionaries(
            keys=st.sampled_from(['has_email', 'has_phone', 'has_skills', 'has_name', 'text_length']),
            values=st.booleans() | st.integers(min_value=10, max_value=1000),
            min_size=3,
            max_size=5
        )
    )
    def test_confidence_score_accuracy_correlation(self, quality_indicators):
        """
        Property: Confidence scores should correlate with the presence of 
        identifiable resume elements.
        
        **Validates: Requirements 2.4**
        """
        # Create mock extracted data based on quality indicators
        extracted_data = {
            "names": ["John Doe"] if quality_indicators.get('has_name', False) else [],
            "emails": ["john@email.com"] if quality_indicators.get('has_email', False) else [],
            "phones": ["555-1234"] if quality_indicators.get('has_phone', False) else [],
            "skills": [{"skill": "python", "category": "programming", "confidence": 0.9}] if quality_indicators.get('has_skills', False) else [],
            "education": [],
            "experience": []
        }
        
        # Calculate confidence score
        confidence = self.nlp_service.calculate_confidence_score(extracted_data)
        
        # Property: Confidence should be between 0 and 1
        assert 0.0 <= confidence <= 1.0, "Confidence score should be between 0 and 1"
        
        # Property: More extracted elements should lead to higher confidence
        element_count = sum([
            len(extracted_data["names"]) > 0,
            len(extracted_data["emails"]) > 0,
            len(extracted_data["phones"]) > 0,
            len(extracted_data["skills"]) > 0,
            len(extracted_data["education"]) > 0,
            len(extracted_data["experience"]) > 0
        ])
        
        if element_count == 0:
            assert confidence == 0.0, "No extracted elements should result in zero confidence"
        elif element_count >= 4:
            assert confidence > 0.7, "Many extracted elements should result in high confidence"
        elif element_count >= 2:
            assert confidence > 0.3, "Some extracted elements should result in moderate confidence"
    
    def test_quality_assessment_threshold_consistency(self):
        """
        Property: Quality assessment should consistently flag low-quality extractions.
        
        **Validates: Requirements 2.4**
        """
        # Test cases with different quality levels
        test_cases = [
            # High quality case
            {
                'text': 'John Doe\nSoftware Engineer\njohn.doe@email.com\n(555) 123-4567\nSkills: Python, JavaScript, React',
                'metadata': {'success': True, 'format': 'txt'},
                'expected_quality': 'high'
            },
            # Medium quality case
            {
                'text': 'Engineer john@email.com Python',
                'metadata': {'success': True, 'format': 'txt'},
                'expected_quality': 'medium'
            },
            # Low quality case - very short text
            {
                'text': 'abc',
                'metadata': {'success': True, 'format': 'txt'},
                'expected_quality': 'low'
            },
            # Low quality case - OCR with low confidence
            {
                'text': 'Some extracted text',
                'metadata': {'success': True, 'format': 'image', 'ocr': True, 'ocr_confidence': 30},
                'expected_quality': 'low'
            },
            # Failed processing
            {
                'text': '',
                'metadata': {'success': False, 'error': 'Processing failed'},
                'expected_quality': 'failed'
            }
        ]
        
        for case in test_cases:
            result = {
                'text': case['text'],
                'metadata': case['metadata']
            }
            
            quality = self.processor.assess_quality(result)
            
            # Property: Quality score should reflect expected quality level
            if case['expected_quality'] == 'failed':
                assert quality['quality_score'] == 0.0, "Failed processing should have zero quality score"
                assert quality['needs_review'], "Failed processing should need review"
            elif case['expected_quality'] == 'low':
                assert quality['quality_score'] <= 0.7, "Low quality should have score <= 0.7"
                assert quality['needs_review'], "Low quality should need review"
            elif case['expected_quality'] == 'medium':
                assert 0.3 <= quality['quality_score'] <= 0.9, "Medium quality should have moderate score"
            elif case['expected_quality'] == 'high':
                assert quality['quality_score'] > 0.7, "High quality should have score > 0.7"
                assert not quality['needs_review'], "High quality should not need review"
    
    @given(
        text_length=st.integers(min_value=1, max_value=2000),
        ocr_confidence=st.integers(min_value=0, max_value=100)
    )
    def test_quality_score_monotonicity(self, text_length, ocr_confidence):
        """
        Property: Quality scores should be monotonic with respect to key quality indicators.
        
        **Validates: Requirements 2.4**
        """
        # Create test results with different quality parameters
        result_low_confidence = {
            'text': 'x' * text_length,
            'metadata': {
                'success': True,
                'format': 'image',
                'ocr': True,
                'ocr_confidence': min(ocr_confidence, 40)  # Low confidence
            }
        }
        
        result_high_confidence = {
            'text': 'x' * text_length,
            'metadata': {
                'success': True,
                'format': 'image',
                'ocr': True,
                'ocr_confidence': max(ocr_confidence, 80)  # High confidence
            }
        }
        
        quality_low = self.processor.assess_quality(result_low_confidence)
        quality_high = self.processor.assess_quality(result_high_confidence)
        
        # Property: Higher OCR confidence should lead to higher or equal quality score
        if result_high_confidence['metadata']['ocr_confidence'] > result_low_confidence['metadata']['ocr_confidence']:
            assert quality_high['quality_score'] >= quality_low['quality_score'], \
                "Higher OCR confidence should not decrease quality score"
    
    def test_accuracy_threshold_flagging(self):
        """
        Property: Documents below accuracy threshold should be flagged for manual review.
        
        **Validates: Requirements 2.4**
        """
        # Test various scenarios that should trigger manual review
        review_cases = [
            # Very short extracted text
            {'text': 'ab', 'metadata': {'success': True}},
            # Low OCR confidence
            {'text': 'Some text here', 'metadata': {'success': True, 'ocr': True, 'ocr_confidence': 25}},
            # Processing warnings
            {'text': 'Text with issues', 'metadata': {'success': True, 'warnings': ['Page 1: Error']}},
            # Processing failure
            {'text': '', 'metadata': {'success': False, 'error': 'Failed to process'}}
        ]
        
        for case in review_cases:
            quality = self.processor.assess_quality(case)
            
            # Property: Low quality cases should be flagged for review
            if (len(case['text']) < 50 or 
                case['metadata'].get('ocr_confidence', 100) < 50 or
                case['metadata'].get('warnings') or
                not case['metadata'].get('success', True)):
                
                assert quality['needs_review'], f"Should flag for review: {case}"
                assert len(quality['issues']) > 0, "Should report specific issues"
    
    @given(
        resume_content=st.sampled_from([
            "John Doe Software Engineer john@email.com Python JavaScript React",
            "Jane Smith Developer jane.smith@company.com Java Spring SQL Docker",
            "Alex Johnson Engineer alex@tech.co Python Data Science Machine Learning",
            "Sarah Wilson Analyst sarah@startup.io JavaScript React Node.js MongoDB",
            "Mike Brown Developer mike.brown@email.org Python Django PostgreSQL AWS"
        ])
    )
    def test_confidence_accuracy_relationship(self, resume_content):
        """
        Property: Higher confidence scores should correlate with more accurate extractions.
        
        **Validates: Requirements 2.4**
        """
        # Extract entities
        entities = self.nlp_service.extract_entities(resume_content)
        confidence = self.nlp_service.calculate_confidence_score(entities)
        
        # Property: If confidence is high, should have extracted meaningful data
        if confidence > 0.8:
            total_entities = (len(entities['names']) + len(entities['emails']) + 
                            len(entities['phones']) + len(entities['skills']) + 
                            len(entities['education']) + len(entities['experience']))
            assert total_entities >= 3, "High confidence should correlate with multiple extracted entities"
        
        # Property: If confidence is very low, should have few entities
        if confidence < 0.2:
            total_entities = (len(entities['names']) + len(entities['emails']) + 
                            len(entities['phones']) + len(entities['skills']) + 
                            len(entities['education']) + len(entities['experience']))
            assert total_entities <= 2, "Low confidence should correlate with few extracted entities"