#!/usr/bin/env python3
"""
Unit tests for image_ocr.py module.
"""

import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock
import numpy as np

# Import the module to test
from app.utils.image_ocr import ImageOCR, process_student_image, face_recognition


class TestImageOcr(unittest.TestCase):
    """Tests for ImageOCR class and related functions."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        # Create a temp directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create a simple test image
        self.test_image_path = os.path.join(self.test_dir, "test_image.jpg")
        with open(self.test_image_path, 'wb') as f:
            # Create a simple 100x100 blank image
            f.write(b'\xff' * 100 * 100 * 3)  # Simple RGB white image
    
    def tearDown(self):
        """Clean up test fixtures after each test."""
        # Remove test files
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)
        
        # Remove test directory
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
    
    @unittest.skipIf(face_recognition is None, "face_recognition library not available")
    def test_process_student_image_with_face_detection(self):
        """Test processing a student image with face detection."""
        # Mock face_recognition functions
        with patch('app.utils.image_ocr.face_recognition') as mock_face_rec:
            # Setup mock returns
            mock_face_rec.load_image_file.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
            mock_face_rec.face_locations.return_value = [(10, 50, 60, 20)]  # (top, right, bottom, left)
            mock_face_rec.face_encodings.return_value = [np.zeros(128)]
            
            # Also mock image_ocr.process_image
            with patch('app.utils.image_ocr.image_ocr') as mock_ocr:
                mock_ocr.process_image.return_value = (
                    {'student_id': '12345', 'name': 'Test Student', 'date_of_birth': '01/01/2000'},
                    np.zeros((100, 100, 3), dtype=np.uint8)
                )
                
                # Call the function to test
                result = process_student_image(self.test_image_path)
                
                # Verify calls
                mock_face_rec.load_image_file.assert_called_once_with(self.test_image_path)
                mock_face_rec.face_locations.assert_called_once()
                mock_face_rec.face_encodings.assert_called_once()
                mock_ocr.process_image.assert_called_once_with(self.test_image_path)
                
                # Check result
                self.assertEqual(result['student_id'], '12345')
                self.assertEqual(result['name'], 'Test Student')
                self.assertEqual(result['date_of_birth'], '01/01/2000')
                self.assertTrue(result['face_detected'])
                self.assertEqual(result['face_count'], 1)
                self.assertEqual(result['face_locations'], [(10, 50, 60, 20)])
                self.assertTrue(result['has_face_encoding'])
    
    def test_process_student_image_without_face_detection(self):
        """Test processing a student image without face detection library."""
        # Temporarily set face_recognition to None
        with patch('app.utils.image_ocr.face_recognition', None):
            # Mock OCR process
            with patch('app.utils.image_ocr.image_ocr') as mock_ocr:
                mock_ocr.process_image.return_value = (
                    {'student_id': '12345', 'name': 'Test Student'},
                    np.zeros((100, 100, 3), dtype=np.uint8)
                )
                
                # Call the function to test
                result = process_student_image(self.test_image_path)
                
                # Check result
                self.assertEqual(result['student_id'], '12345')
                self.assertEqual(result['name'], 'Test Student')
                self.assertFalse(result['face_detected'])
                self.assertEqual(result['face_count'], 0)
    
    def test_ocr_extraction(self):
        """Test the OCR text extraction functionality."""
        # Create an instance of ImageOCR
        ocr = ImageOCR()
        
        # Mock _extract_student_info
        with patch.object(ocr, '_extract_student_info') as mock_extract:
            mock_extract.return_value = {
                'student_id': 'ST12345',
                'name': 'John Doe',
                'date_of_birth': '01/01/2000'
            }
            
            # Call the method with mock parameters
            result = ocr._extract_student_info("Sample OCR Text", {})
            
            # Check the result
            self.assertEqual(result['student_id'], 'ST12345')
            self.assertEqual(result['name'], 'John Doe')
            self.assertEqual(result['date_of_birth'], '01/01/2000')


if __name__ == '__main__':
    unittest.main()
