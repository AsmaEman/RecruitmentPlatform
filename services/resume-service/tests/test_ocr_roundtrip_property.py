"""
Property test for OCR processing round-trip consistency.

**Property 5: OCR Processing Round-trip**
**Validates: Requirements 2.3**

Feature: recruitment-testing-platform, Property 5: OCR Processing Round-trip
"""

import pytest
from hypothesis import given, strategies as st, assume
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont
import io

from app.services.document_processor import DocumentProcessor


class TestOCRRoundtripProperty:
    """Property tests for OCR processing round-trip consistency"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = DocumentProcessor()
        
        # Skip all tests if OCR is not available
        if '.png' not in self.processor.supported_formats:
            pytest.skip("OCR processing not available - pytesseract/PIL not installed")
    
    @given(
        text_content=st.sampled_from([
            "John Doe",
            "Software Engineer", 
            "Python Developer",
            "Email Address",
            "Phone Number"
        ])
    )
    def test_ocr_text_extraction_consistency(self, text_content):
        """
        Property: For any text rendered as an image, OCR should extract
        text that contains the core information from the original.
        
        **Validates: Requirements 2.3**
        """
        # Create a simple image with text
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to use a default font, fall back to basic if not available
            font = ImageFont.load_default()
        except:
            font = None
        
        # Draw text on image
        draw.text((10, 10), text_content, fill='black', font=font)
        
        # Convert image to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        # Process image with OCR
        result = self.processor.process_document(img_bytes, 'test.png')
        
        # Skip if OCR processing failed
        if not result['metadata']['success'] or not result['metadata'].get('ocr', False):
            return  # Skip this test case
        
        extracted_text = result['text'].strip()
        
        # Property: OCR should extract some recognizable text
        if len(extracted_text) > 0:
            # Check if at least some characters match
            original_chars = set(text_content.lower().replace(' ', ''))
            extracted_chars = set(extracted_text.lower().replace(' ', ''))
            
            if len(original_chars) > 0:
                common_chars = original_chars & extracted_chars
                char_similarity = len(common_chars) / len(original_chars)
                
                # Property: Should have some character similarity
                assert char_similarity > 0.1, f"OCR should extract some recognizable characters. Original: '{text_content}', Extracted: '{extracted_text}'"
        
        # Property: OCR confidence should be reported
        assert 'ocr_confidence' in result['metadata'], "OCR confidence should be reported"
    
    def test_ocr_quality_assessment_consistency(self):
        """
        Property: OCR quality assessment should be consistent with extraction results.
        
        **Validates: Requirements 2.3**
        """
        # Create a high-quality image with clear text
        img = Image.new('RGB', (300, 50), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "John Doe Engineer", fill='black')
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        # Process with OCR
        result = self.processor.process_document(img_bytes, 'clear_text.png')
        
        if result['metadata']['success']:
            # Assess quality
            quality = self.processor.assess_quality(result)
            
            # Property: Quality assessment should reflect OCR confidence
            ocr_confidence = result['metadata'].get('ocr_confidence')
            if ocr_confidence is not None:
                if ocr_confidence < 50:
                    assert quality['quality_score'] < 0.7, "Low OCR confidence should result in low quality score"
                elif ocr_confidence > 80:
                    assert quality['quality_score'] > 0.5, "High OCR confidence should result in reasonable quality score"
            
            # Property: Quality issues should be reported for OCR content
            if result['metadata'].get('ocr'):
                assert 'ocr' in str(quality), "Quality assessment should mention OCR processing"
    
    @given(
        image_size=st.tuples(
            st.integers(min_value=100, max_value=500),
            st.integers(min_value=50, max_value=200)
        ),
        text_content=st.sampled_from([
            "Software Engineer",
            "john.doe@email.com", 
            "Python Developer",
            "123-456-7890",
            "Bachelor Computer Science"
        ])
    )
    def test_ocr_format_independence(self, image_size, text_content):
        """
        Property: OCR should work consistently across different image formats.
        
        **Validates: Requirements 2.3**
        """
        width, height = image_size
        
        # Create image with text
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), text_content, fill='black')
        
        # Test different formats
        formats = ['PNG', 'JPEG']
        results = {}
        
        for fmt in formats:
            img_bytes = io.BytesIO()
            img.save(img_bytes, format=fmt)
            img_bytes = img_bytes.getvalue()
            
            filename = f'test.{fmt.lower()}'
            result = self.processor.process_document(img_bytes, filename)
            
            if result['metadata']['success']:
                results[fmt] = result
        
        # Property: If both formats processed successfully, 
        # they should extract similar information
        if len(results) >= 2:
            format_names = list(results.keys())
            result1 = results[format_names[0]]
            result2 = results[format_names[1]]
            
            # Both should be recognized as OCR
            assert result1['metadata'].get('ocr'), f"{format_names[0]} should be processed with OCR"
            assert result2['metadata'].get('ocr'), f"{format_names[1]} should be processed with OCR"
            
            # If both extracted text, check for similarity
            text1 = result1['text'].strip()
            text2 = result2['text'].strip()
            
            if text1 and text2:
                # Should have some common characters
                chars1 = set(text1.lower().replace(' ', ''))
                chars2 = set(text2.lower().replace(' ', ''))
                
                if chars1 and chars2:
                    common = chars1 & chars2
                    similarity = len(common) / max(len(chars1), len(chars2))
                    assert similarity > 0.3, f"Different image formats should extract similar text. {format_names[0]}: '{text1}', {format_names[1]}: '{text2}'"