#!/usr/bin/env python3
"""
Inspect what's available in the face_recognition_models package
"""

import sys
import pprint

print("Checking face_recognition_models...")
try:
    import face_recognition_models
    print(f"Successfully imported face_recognition_models version: {face_recognition_models.__version__}")
    
    # Print all available attributes
    print("\nAvailable attributes:")
    attrs = dir(face_recognition_models)
    pprint.pprint(attrs)
    
    # Try to call the available functions
    print("\nTrying resource_filename:")
    if 'resource_filename' in attrs:
        print(face_recognition_models.resource_filename("face_recognition_models", "models/shape_predictor_68_face_landmarks.dat"))
    
    # Check if there are any model-related files/functions
    model_attrs = [attr for attr in attrs if 'model' in attr.lower()]
    print("\nModel-related attributes:")
    pprint.pprint(model_attrs)
    
except ImportError as e:
    print(f"Failed to import face_recognition_models: {e}")

print("\nChecking face_recognition...")
try:
    import face_recognition
    print(f"Successfully imported face_recognition")
    
    # Print the functions used for model locations
    model_funcs = [func for func in dir(face_recognition) if 'model' in func.lower()]
    print("\nModel-related functions in face_recognition:")
    pprint.pprint(model_funcs)
    
    # Print face detection backend information
    print("\nFace detection backend:")
    # Check if this attribute exists
    if hasattr(face_recognition, 'api'):
        print(f"Has api module: {hasattr(face_recognition, 'api')}")
        api_funcs = dir(face_recognition.api)
        print("API functions:")
        pprint.pprint([f for f in api_funcs if not f.startswith('_')])
    
except ImportError as e:
    print(f"Failed to import face_recognition: {e}")
