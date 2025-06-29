#!/usr/bin/env python3
"""
Unit tests for face detection integration in the main_window module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

# Direct import of the functions we want to test
from app.utils.image_ocr import process_student_image


class TestFaceDetectionIntegration(unittest.TestCase):
    """Tests for face detection functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        # Create a temp test image path
        self.test_image_path = "/path/to/test_image.jpg"
    
    @patch('app.utils.image_ocr.face_recognition')
    @patch('app.utils.image_ocr.image_ocr')
    def test_process_student_image_with_face(self, mock_ocr, mock_face_recognition):
        """Test processing a student image with a face."""
        # Configure mocks
        mock_ocr.process_image.return_value = (
            {'student_id': 'S12345', 'name': 'Test Student', 'date_of_birth': '2000-01-01'},
            np.zeros((100, 100, 3))
        )
        
        # Mock face_recognition functions
        mock_face_recognition.load_image_file.return_value = np.zeros((100, 100, 3))
        mock_face_recognition.face_locations.return_value = [(10, 50, 60, 20)]  # One face found
        mock_face_recognition.face_encodings.return_value = [np.zeros(128)]  # Face encoding
        
        # Call the function
        result = process_student_image(self.test_image_path)
        
        # Verify results
        self.assertTrue(result['face_detected'])
        self.assertEqual(result['face_count'], 1)
        self.assertEqual(result['face_locations'], [(10, 50, 60, 20)])
        self.assertTrue(result['has_face_encoding'])
        self.assertEqual(result['student_id'], 'S12345')
    
    @patch('app.utils.image_ocr.face_recognition')
    @patch('app.utils.image_ocr.image_ocr')
    def test_process_student_image_no_face(self, mock_ocr, mock_face_recognition):
        """Test processing a student image without any face."""
        # Configure mocks
        mock_ocr.process_image.return_value = (
            {'student_id': 'S12345', 'name': 'Test Student', 'date_of_birth': '2000-01-01'},
            np.zeros((100, 100, 3))
        )
        
        # Mock face_recognition functions
        mock_face_recognition.load_image_file.return_value = np.zeros((100, 100, 3))
        mock_face_recognition.face_locations.return_value = []  # No faces found
        mock_face_recognition.face_encodings.return_value = []  # No encodings
        
        # Call the function
        result = process_student_image(self.test_image_path)
        
        # Verify results
        self.assertFalse(result['face_detected'])
        self.assertEqual(result['face_count'], 0)
        self.assertEqual(result['face_locations'], [])
        self.assertFalse(result['has_face_encoding'])
        self.assertEqual(result['student_id'], 'S12345')
    
    @patch('app.utils.image_ocr.face_recognition')
    @patch('app.utils.image_ocr.image_ocr')
    def test_process_student_image_multiple_faces(self, mock_ocr, mock_face_recognition):
        """Test processing a student image with multiple faces."""
        # Configure mocks
        mock_ocr.process_image.return_value = (
            {'student_id': 'S12345', 'name': 'Test Student', 'date_of_birth': '2000-01-01'},
            np.zeros((100, 100, 3))
        )
        
        # Mock face_recognition functions - 2 faces
        mock_face_recognition.load_image_file.return_value = np.zeros((100, 100, 3))
        mock_face_recognition.face_locations.return_value = [(10, 50, 60, 20), (70, 90, 120, 60)]
        mock_face_recognition.face_encodings.return_value = [np.zeros(128), np.zeros(128)]
        
        # Call the function
        result = process_student_image(self.test_image_path)
        
        # Verify results
        self.assertTrue(result['face_detected'])
        self.assertEqual(result['face_count'], 2)  # Should detect 2 faces
        self.assertEqual(len(result['face_locations']), 2)
        self.assertTrue(result['has_face_encoding'])
        self.assertEqual(result['student_id'], 'S12345')


if __name__ == '__main__':
    unittest.main()
