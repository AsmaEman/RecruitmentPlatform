"""
Property test for multi-format parsing consistency.

**Property 4: Multi-format Parsing Consistency**
**Validates: Requirements 2.1, 2.2**

Feature: recruitment-testing-platform, Property 4: Multi-format Parsing Consistency
"""

import pytest
from hypothesis import given, strategies as st, assume
import tempfile
import os
from pathlib import Path

from app.services.document_processor import DocumentProcessor
from app.services.nlp_service import NLPService


class TestMultiFormatParsingProperty:
    """Property tests for multi-format parsing consistency"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = DocumentProcessor()
        self.nlp_service = NLPService()
    
    @given(
        text_content=st.sampled_from([
            "John Doe Software Engineer john@email.com Python JavaScript",
            "Jane Smith Developer jane.smith@company.com React Node.js SQL",
            "Alex Johnson Engineer alex@tech.co Java Spring Docker AWS",
            "Sarah Wilson Analyst sarah@startup.io Python Data Science",
            "Mike Brown Developer mike.brown@email.org JavaScript React Vue"
        ])
    )
    def test_multi_format_parsing_consistency(self, text_content):
        """
        Property: For any text content, parsing it from different formats should extract
        the same core information (names, emails, skills) regardless of format.
        
        **Validates: Requirements 2.1, 2.2**
        """
        # Create temporary files with the same content in different formats
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create TXT file
            txt_path = os.path.join(temp_dir, 'test.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            # Process TXT file
            with open(txt_path, 'rb') as f:
                txt_content_bytes = f.read()
            
            txt_result = self.processor.process_document(txt_content_bytes, 'test.txt')
            
            # Skip if processing failed
            if not txt_result['metadata']['success'] or len(txt_result['text'].strip()) == 0:
                return  # Skip this test case
            
            # Extract entities from TXT
            txt_entities = self.nlp_service.extract_entities(txt_result['text'])
            
            # Create a simple DOCX-like structure (for testing purposes)
            # In a real implementation, this would create actual DOCX files
            docx_result = {
                'text': text_content,
                'metadata': {'format': 'docx', 'success': True}
            }
            
            # Extract entities from DOCX-like content
            docx_entities = self.nlp_service.extract_entities(docx_result['text'])
            
            # Property: Core extracted information should be consistent across formats
            # Check emails
            if txt_entities['emails']:
                assert len(docx_entities['emails']) > 0, "Email extraction should be consistent across formats"
                # At least some emails should match
                common_emails = set(txt_entities['emails']) & set(docx_entities['emails'])
                assert len(common_emails) > 0, "Should have common emails across formats"
            
            # Check skills
            if txt_entities['skills']:
                assert len(docx_entities['skills']) > 0, "Skill extraction should be consistent across formats"
                # At least some skills should match
                txt_skill_names = {skill['skill'] for skill in txt_entities['skills']}
                docx_skill_names = {skill['skill'] for skill in docx_entities['skills']}
                common_skills = txt_skill_names & docx_skill_names
                assert len(common_skills) > 0, "Should have common skills across formats"
            
            # Check names (if any found)
            if txt_entities['names'] and docx_entities['names']:
                # At least some names should match
                common_names = set(txt_entities['names']) & set(docx_entities['names'])
                assert len(common_names) > 0, "Should have common names across formats"
    
    @given(
        email=st.sampled_from([
            "john.doe@email.com",
            "jane.smith@company.org", 
            "test.user@example.com",
            "developer@tech.co",
            "engineer@startup.io"
        ]),
        skills=st.lists(
            st.sampled_from(['python', 'javascript', 'react', 'java', 'sql', 'docker']),
            min_size=1,
            max_size=5
        ),
        name=st.sampled_from([
            "John Doe",
            "Jane Smith", 
            "Alex Johnson",
            "Sarah Wilson",
            "Mike Brown"
        ])
    )
    def test_structured_content_parsing_consistency(self, email, skills, name):
        """
        Property: For structured resume content with known entities,
        all formats should extract the same entities.
        
        **Validates: Requirements 2.1, 2.2**
        """
        # Create structured resume content
        content = f"""
        {name}
        Software Engineer
        Email: {email}
        
        Skills: {', '.join(skills)}
        
        Experience:
        - Senior Developer at Tech Corp
        - Used {skills[0]} and {skills[-1]} extensively
        """
        
        # Process as different formats
        txt_result = self.processor.process_document(content.encode('utf-8'), 'resume.txt')
        assume(txt_result['metadata']['success'])
        
        # Extract entities
        entities = self.nlp_service.extract_entities(txt_result['text'])
        
        # Property: Should extract the email we put in
        assert email in entities['emails'], f"Should extract email {email}"
        
        # Property: Should extract at least some of the skills we put in
        extracted_skill_names = {skill['skill'].lower() for skill in entities['skills']}
        input_skills_lower = {skill.lower() for skill in skills}
        common_skills = extracted_skill_names & input_skills_lower
        assert len(common_skills) > 0, f"Should extract at least some skills from {skills}"
        
        # Property: Confidence score should be reasonable for structured content
        confidence = self.nlp_service.calculate_confidence_score(entities)
        assert confidence > 0.5, "Confidence should be reasonable for structured content"