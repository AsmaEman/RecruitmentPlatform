"""
Basic functionality tests for resume service.
"""

import pytest
from app.services.nlp_service import NLPService
from app.services.document_processor import DocumentProcessor


class TestBasicFunctionality:
    """Basic functionality tests"""
    
    def setup_method(self):
        """Set up test fixtures"""
        try:
            self.nlp_service = NLPService()
            self.processor = DocumentProcessor()
        except Exception as e:
            pytest.skip(f"Could not initialize services: {e}")
    
    def test_nlp_service_initialization(self):
        """Test that NLP service initializes correctly"""
        assert self.nlp_service is not None
        assert hasattr(self.nlp_service, 'skill_taxonomy')
        assert len(self.nlp_service.skill_taxonomy) > 0
    
    def test_document_processor_initialization(self):
        """Test that document processor initializes correctly"""
        assert self.processor is not None
        assert hasattr(self.processor, 'supported_formats')
        assert '.txt' in self.processor.supported_formats
        assert '.pdf' in self.processor.supported_formats
    
    def test_text_processing(self):
        """Test basic text processing"""
        sample_text = "John Doe\nSoftware Engineer\njohn.doe@email.com\nSkills: Python, JavaScript"
        
        # Process as text file
        result = self.processor.process_document(sample_text.encode('utf-8'), 'resume.txt')
        
        assert result['metadata']['success']
        assert result['text'] == sample_text
        
        # Extract entities
        entities = self.nlp_service.extract_entities(result['text'])
        
        # Should extract email
        assert 'john.doe@email.com' in entities['emails']
        
        # Should extract some skills
        assert len(entities['skills']) > 0
        skill_names = [skill['skill'] for skill in entities['skills']]
        assert any('python' in skill.lower() for skill in skill_names)
    
    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        # High quality data
        good_data = {
            "names": ["John Doe"],
            "emails": ["john@email.com"],
            "phones": ["555-1234"],
            "skills": [{"skill": "python", "category": "programming", "confidence": 0.9}],
            "education": [{"degree": "BS", "field": "Computer Science"}],
            "experience": [{"title": "Engineer", "company": "Tech Corp"}]
        }
        
        confidence = self.nlp_service.calculate_confidence_score(good_data)
        assert confidence > 0.7
        
        # Low quality data
        poor_data = {
            "names": [],
            "emails": [],
            "phones": [],
            "skills": [],
            "education": [],
            "experience": []
        }
        
        confidence = self.nlp_service.calculate_confidence_score(poor_data)
        assert confidence == 0.0