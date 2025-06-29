"""
Image OCR utility for processing student photos and extracting text data.
Uses OpenCV and Tesseract for OCR capabilities.
"""

import os
import cv2
import logging
import numpy as np
from typing import Dict, Optional, Tuple, List, Any
import tempfile

# Attempt to import optional OCR libraries
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

logger = logging.getLogger(__name__)

class ImageOCR:
    """Provides OCR capabilities for student photo processing."""
    
    def __init__(self):
        """Initialize the OCR processor with configuration."""
        self.config = {
            'tesseract_path': None,  # Will be auto-detected or set via configure()
            'language': 'eng',
            'ocr_enabled': self._check_ocr_available()
        }
        
        # Try to auto-detect tesseract path
        if HAS_TESSERACT:
            # Common paths for tesseract
            common_paths = [
                '/usr/bin/tesseract',
                '/usr/local/bin/tesseract',
                'C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    self.config['tesseract_path'] = path
                    break
    
    def _check_ocr_available(self) -> bool:
        """Check if OCR capabilities are available."""
        if not HAS_TESSERACT:
            logger.warning("Tesseract not installed. OCR capabilities will be disabled.")
            return False
            
        try:
            # Quick test to see if OpenCV is working
            test_img = np.zeros((10, 10, 3), dtype=np.uint8)
            cv2.resize(test_img, (5, 5))
            return True
        except Exception as e:
            logger.warning(f"OpenCV not working properly. OCR disabled: {str(e)}")
            return False
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure OCR settings.
        
        Args:
            config: Dictionary with configuration values
                - tesseract_path: Path to tesseract executable
                - language: OCR language (default: eng)
        """
        if 'tesseract_path' in config and config['tesseract_path']:
            self.config['tesseract_path'] = config['tesseract_path']
            
        if 'language' in config:
            self.config['language'] = config['language']
            
        # Update pytesseract configuration if available
        if HAS_TESSERACT and self.config['tesseract_path']:
            try:
                pytesseract.pytesseract.tesseract_cmd = self.config['tesseract_path']
                logger.info(f"Tesseract configured with path: {self.config['tesseract_path']}")
            except Exception as e:
                logger.error(f"Failed to configure tesseract: {str(e)}")
    
    def process_image(self, 
                     image_path: str, 
                     preprocess: bool = True) -> Tuple[Optional[Dict[str, str]], Optional[np.ndarray]]:
        """
        Process an image and extract text using OCR.
        
        Args:
            image_path: Path to the image file
            preprocess: Whether to preprocess the image for better OCR results
            
        Returns:
            Tuple of (extracted_text_dict, processed_image)
        """
        if not self.config['ocr_enabled']:
            logger.warning("OCR is not enabled or available")
            return None, None
            
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return None, None
            
        try:
            # Read image
            image = cv2.imread(image_path)
            processed_image = image.copy()
            
            # Preprocessing for better OCR
            if preprocess:
                processed_image = self._preprocess_image(processed_image)
                
            # Run OCR
            if HAS_TESSERACT:
                text = pytesseract.image_to_string(
                    processed_image, 
                    lang=self.config['language'],
                    config='--psm 3'  # Automatic page segmentation
                )
                
                # Run additional data extraction for structured data
                data = pytesseract.image_to_data(
                    processed_image,
                    lang=self.config['language'],
                    output_type=pytesseract.Output.DICT
                )
                
                # Extract potential student information
                extracted_info = self._extract_student_info(text, data)
                
                return extracted_info, processed_image
            else:
                logger.error("Tesseract not available for OCR")
                return None, processed_image
                
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return None, None
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for better OCR results.
        
        Args:
            image: OpenCV image array
            
        Returns:
            Processed image
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Apply noise removal
            processed = cv2.medianBlur(thresh, 3)
            
            return processed
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            return image
    
    def _extract_student_info(self, 
                             text: str, 
                             data: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract student information from OCR text.
        
        Args:
            text: Raw OCR text
            data: Structured OCR data
            
        Returns:
            Dictionary with extracted information
        """
        result = {
            'student_id': None,
            'name': None,
            'date_of_birth': None,
            'raw_text': text
        }
        
        # Look for common patterns
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for ID numbers
            if any(keyword in line.lower() for keyword in ['id', 'number', '#', 'no.', 'student']):
                # Extract digits with possible alphabets
                import re
                id_matches = re.findall(r'[A-Z0-9]{5,}', line, re.IGNORECASE)
                if id_matches:
                    result['student_id'] = id_matches[0]
            
            # Look for name
            if any(keyword in line.lower() for keyword in ['name:', 'student name', 'full name']):
                # Get text after the colon or keyword
                parts = line.split(':', 1)
                if len(parts) > 1:
                    result['name'] = parts[1].strip()
                else:
                    # Try to get the name from the next part
                    name_parts = re.split(r'name|Name', line)
                    if len(name_parts) > 1:
                        result['name'] = name_parts[1].strip()
            
            # Look for date of birth
            if any(keyword in line.lower() for keyword in ['birth', 'dob', 'born']):
                # Extract date patterns
                import re
                date_matches = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line)
                if date_matches:
                    result['date_of_birth'] = date_matches[0]
        
        return result

# Singleton instance
image_ocr = ImageOCR()


try:
    import face_recognition
except ImportError:
    face_recognition = None
    logger.warning("face_recognition library not found. Facial similarity features will be disabled.")


def process_student_image(image_path):
    """Process a student ID or document photo to extract information and detect faces.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with extracted information and face detection results
    """
    logger.info(f"Processing student photo: {image_path}")
    
    # Process with OCR
    extracted_info, processed_image = image_ocr.process_image(image_path)
    
    # Initialize result dict
    result = {
        'image_path': image_path,
        'student_id': None,
        'name': None,
        'date_of_birth': None,
        'face_detected': False,
        'face_count': 0,
        'face_locations': []
    }
    
    # Add OCR results if available
    if extracted_info:
        result.update(extracted_info)
    
    # Perform face detection if possible
    try:
        if face_recognition:
            # Load image for face detection
            image = face_recognition.load_image_file(image_path)
            
            # Detect face locations (returns list of tuples with (top, right, bottom, left))
            face_locations = face_recognition.face_locations(image)
            
            # Get face encodings if faces are found
            face_encodings = face_recognition.face_encodings(image, face_locations) if face_locations else []
            
            # Add face detection results
            result['face_detected'] = len(face_locations) > 0
            result['face_count'] = len(face_locations)
            result['face_locations'] = face_locations
            result['has_face_encoding'] = len(face_encodings) > 0
            
            logger.info(f"Face detection results: {len(face_locations)} faces found")
        else:
            logger.warning("Face recognition library not available, skipping face detection")
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        result['face_detection_error'] = str(e)
    
    return result

class PhotoProcessor:
    """Handles loading, processing, and comparing student photos for facial similarity."""

    def __init__(self, image_folder_path):
        if not face_recognition:
            raise ImportError("face_recognition library is required for PhotoProcessor.")
        if not os.path.isdir(image_folder_path):
            # Allow initialization even if the folder does not exist yet.
            logger.warning(f"Image folder not found at: {image_folder_path}. It will be expected to exist during processing.")
        self.image_folder_path = image_folder_path

    def _load_image(self, file_name):
        """Loads an image from the specified folder."""
        try:
            image_path = os.path.join(self.image_folder_path, file_name)
            if os.path.exists(image_path):
                return face_recognition.load_image_file(image_path)
            else:
                logger.warning(f"Image file not found: {file_name}")
                return None
        except Exception as e:
            logger.error(f"Error loading image {file_name}: {e}")
            return None

    def get_face_encoding(self, image_file):
        """Gets the face encoding for the first face found in an image."""
        image = self._load_image(image_file)
        if image is not None:
            try:
                face_encodings = face_recognition.face_encodings(image)
                if face_encodings:
                    return face_encodings[0]
            except Exception as e:
                logger.error(f"Could not get face encoding for {image_file}: {e}")
        return None

    def find_duplicates(self, dataframe, photo_column, progress_callback=None):
        """Finds duplicate students based on facial similarity."""
        if photo_column not in dataframe.columns:
            logger.error(f"Photo column '{photo_column}' not found in dataframe.")
            return {}

        face_encodings = {}
        total_rows = len(dataframe)
        for i, (index, row) in enumerate(dataframe.iterrows()):
            photo_file = row[photo_column]
            if photo_file and isinstance(photo_file, str):
                if progress_callback:
                    progress_callback(int((i / total_rows) * 100), f"Encoding photo {i+1}/{total_rows}")
                encoding = self.get_face_encoding(photo_file)
                if encoding is not None:
                    face_encodings[index] = encoding

        if not face_encodings:
            logger.warning("No face encodings could be generated. Check image paths and file integrity.")
            return {}

        duplicates = {}
        # Compare all found encodings
        items = list(face_encodings.items())
        total_comparisons = len(items)
        for i in range(total_comparisons):
            index1, encoding1 = items[i]
            if progress_callback:
                progress_callback(int((i / total_comparisons) * 100), f"Comparing photo {i+1}/{total_comparisons}")

            if index1 in duplicates: continue # Already marked as a duplicate

            # Create a list of encodings to compare against
            compare_indices = [items[j][0] for j in range(i + 1, total_comparisons)]
            compare_encodings = [items[j][1] for j in range(i + 1, total_comparisons)]

            if not compare_encodings: continue

            # Compare face and get a list of True/False values
            results = face_recognition.compare_faces(compare_encodings, encoding1, tolerance=0.6)

            # Find the indices of all matches
            matched_indices = [compare_indices[k] for k, matched in enumerate(results) if matched]

            if matched_indices:
                if index1 not in duplicates:
                    duplicates[index1] = []
                for match_index in matched_indices:
                    if match_index not in duplicates:
                        duplicates[index1].append(match_index)
                        # Mark the other as a duplicate to avoid re-adding
                        duplicates[match_index] = []

        # Clean up the duplicates list to return only parent duplicates
        final_duplicates = {k: v for k, v in duplicates.items() if v}
        return final_duplicates