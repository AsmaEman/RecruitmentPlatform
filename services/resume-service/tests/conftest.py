"""
Test configuration for resume service tests.
"""

import pytest
import tempfile
import os
from pathlib import Path

@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing"""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(John Doe Resume) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \n0000000179 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n238\n%%EOF"

@pytest.fixture
def sample_txt_content():
    """Sample text content for testing"""
    return "John Doe\nSoftware Engineer\njohn.doe@email.com\n(555) 123-4567\n\nSkills: Python, JavaScript, React\nEducation: BS Computer Science"

@pytest.fixture
def sample_docx_content():
    """Sample DOCX content for testing"""
    # This would be actual DOCX binary content in a real implementation
    return b"PK\x03\x04\x14\x00\x00\x00\x08\x00"  # Simplified DOCX header

@pytest.fixture
def temp_files():
    """Create temporary files for testing"""
    files = {}
    temp_dir = tempfile.mkdtemp()
    
    # Create sample files
    files['pdf'] = os.path.join(temp_dir, 'resume.pdf')
    files['txt'] = os.path.join(temp_dir, 'resume.txt')
    files['docx'] = os.path.join(temp_dir, 'resume.docx')
    
    yield files
    
    # Cleanup
    for file_path in files.values():
        if os.path.exists(file_path):
            os.remove(file_path)
    os.rmdir(temp_dir)