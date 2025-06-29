#!/usr/bin/env python3
"""
API test utility for Education Data Cleaning Tool.
This script helps test and validate API connectivity.
"""

import os
import sys
import argparse
import json

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.utils.api_tester import ApiTester


def main():
    """Main entry point for the API test utility"""
    parser = argparse.ArgumentParser(description="Test API connectivity for Education Data Cleaning Tool")
    parser.add_argument("--url", help="API URL")
    parser.add_argument("--key", help="API Key")
    parser.add_argument("--mock", action="store_true", help="Use mock API for testing")
    parser.add_argument("--all", action="store_true", help="Run all available tests")
    parser.add_argument("--validate", action="store_true", help="Test student validation")
    parser.add_argument("--duplicates", action="store_true", help="Test duplicate checking")
    
    args = parser.parse_args()
    
    # Use mock URL if not specified and mock mode is enabled
    url = args.url
    if args.mock and not url:
        url = "http://mockapi.education.example.com"
    
    # Create API tester
    tester = ApiTester(url, args.key)
    
    # Determine which tests to run
    if args.all:
        print("Running all API tests...")
        tester.run_all_tests()
    elif args.validate:
        print("Testing student validation...")
        tester.test_student_validation()
    elif args.duplicates:
        print("Testing duplicate checking...")
        tester.test_duplicate_checking()
    else:
        print("Testing basic API connectivity...")
        tester.test_connection()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
