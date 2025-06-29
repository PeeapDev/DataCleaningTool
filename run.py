#!/usr/bin/env python3
"""
Runner script for the Education Data Cleaning Tool.
Provides a convenient way to launch the application.
"""

import sys
import os
from app.main import main

if __name__ == "__main__":
    # Add project root to path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Run the application
    main()
