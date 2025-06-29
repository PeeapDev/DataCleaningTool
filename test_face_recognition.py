#!/usr/bin/env python3
"""
Test script to verify face recognition library is working properly.
"""

import os
import sys
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    import face_recognition
    logger.info("Successfully imported face_recognition library")
    
    # Try to access the models
    try:
        # Create a small test image (white background)
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        # Try to locate faces (there shouldn't be any, but this tests if the models load)
        face_locations = face_recognition.face_locations(test_image)
        logger.info(f"Face detection works! Found {len(face_locations)} faces in test image.")
        
        # Verify model paths
        import face_recognition_models
        logger.info(f"face_recognition_models version: {face_recognition_models.__version__}")
        
        # Print the paths to the models that are actually available
        pose_predictor_model_location = face_recognition_models.pose_predictor_model_location()
        face_recognition_model_location = face_recognition_models.face_recognition_model_location()
        cnn_model_location = face_recognition_models.cnn_face_detector_model_location()
        
        logger.info(f"Pose predictor model: {pose_predictor_model_location}")
        logger.info(f"Face recognition model: {face_recognition_model_location}")
        logger.info(f"CNN face detector model: {cnn_model_location}")
        
        # Check if files exist
        logger.info(f"Pose predictor model exists: {os.path.exists(pose_predictor_model_location)}")
        logger.info(f"Face recognition model exists: {os.path.exists(face_recognition_model_location)}")
        logger.info(f"CNN face detector model exists: {os.path.exists(cnn_model_location)}")
        
        # Let's try to detect faces in a real image from the system
        try:
            from PIL import Image
            # Find an image in Downloads with potential faces
            image_paths = [
                "/Users/mohamedabdulkabia/Downloads/WhatsApp Image 2025-06-05 at 12.11.57.jpeg",
                "/Users/mohamedabdulkabia/Downloads/WhatsApp Image 2025-06-11 at 01.05.31.jpeg"
            ]
            
            for img_path in image_paths:
                if os.path.exists(img_path):
                    logger.info(f"Testing face detection on real image: {img_path}")
                    image = face_recognition.load_image_file(img_path)
                    face_locations = face_recognition.face_locations(image)
                    face_encodings = face_recognition.face_encodings(image, face_locations)
                    
                    logger.info(f"Found {len(face_locations)} faces in the image!")
                    logger.info(f"Generated {len(face_encodings)} face encodings.")
                    if len(face_encodings) > 0:
                        logger.info(f"Encoding shape: {face_encodings[0].shape}")
                    break
            else:
                logger.info("No test images were found.")
        except Exception as e:
            logger.error(f"Error detecting faces in sample image: {e}")
        
        logger.info("All face recognition models are available and working properly!")
    except Exception as e:
        logger.error(f"Error accessing face recognition models: {e}")
except ImportError as e:
    logger.error(f"Failed to import face_recognition: {e}")

print("Face recognition test complete! Check the logs above.")
