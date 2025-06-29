"""
API testing utility for the Education Data Cleaning Tool.
This module provides functionality to test API connectivity and endpoints
for future API integration capabilities.
"""

import argparse
import json
import sys
import os
import logging
import random
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.utils.api_connector import ApiConfig, ApiConnector, EducationDataApi
from app.utils.config import Config


class ApiTester:
    """Utility for testing API connectivity and endpoints"""
    
    def __init__(self, api_url: str = None, api_key: str = None, timeout: int = 30, retries: int = 3):
    def __init__(self, api_url=None, api_key=None, timeout=30, retries=3):
        """
        Initialize the API tester
        
        Args:
            api_url: URL of the API server (optional, will use config if None)
            api_key: API key for authentication (optional, will use config if None)
            timeout: API timeout in seconds
            retries: Number of retries for failed requests
        """
        self.config = Config()
        
        # Use provided values or load from config
        self.api_url = api_url or self.config.get("api_url", "")
        self.api_key = api_key or self.config.get("api_key", "")
        self.timeout = timeout or self.config.get("api_timeout", 30)
        self.retries = retries or self.config.get("api_retries", 3)
        
        # Create API config
        self.api_config = ApiConfig(
            base_url=self.api_url,
            api_key=self.api_key,
            timeout=self.timeout,
            retry_count=self.retries,
            retry_delay=2
        )
        
        # Create connector
        self.connector = ApiConnector(self.api_config)
        self.api = EducationDataApi(self.connector)
        
    def test_connection(self):
        """
        Test basic API connectivity
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        print(f"Testing API connection to {self.api_url}...")
        
        try:
            result = self.connector.validate_connection()
            if result:
                print("✓ Connection successful")
            else:
                print("✗ Connection failed")
            return result
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return False
    
    def test_endpoint(self, endpoint, method="GET", data=None):
        """
        Test a specific API endpoint
        
        Args:
            endpoint: Endpoint to test (e.g., "status", "users/1")
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Data to send for POST/PUT requests
            
        Returns:
            ApiResponse: Response from the API
        """
        print(f"Testing {method} {self.api_url}/{endpoint}...")
        
        try:
            if method.upper() == "GET":
                response = self.connector.get(endpoint)
            elif method.upper() == "POST":
                response = self.connector.post(endpoint, data or {})
            elif method.upper() == "PUT":
                response = self.connector.put(endpoint, data or {})
            elif method.upper() == "DELETE":
                response = self.connector.delete(endpoint)
            else:
                print(f"✗ Invalid method: {method}")
                return None
                
            if response.success:
                print(f"✓ Request successful")
                print(f"Response: {json.dumps(response.data, indent=2) if response.data else 'No data'}")
            else:
                print(f"✗ Request failed: {response.error}")
                
            return response
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return None
    
    def test_student_validation(self, student_data=None):
        """
        Test the student record validation API
        
        Args:
            student_data: Student data to validate (will use sample data if None)
            
        Returns:
            ApiResponse: Response from the API
        """
        if student_data is None:
            # Use sample student data
            student_data = {
                "StudentName": "John Smith",
                "DateOfBirth": "2010-05-15",
                "AcademicYear": "2023",
                "Gender": "M",
                "Grade": "7"
            }
            
        print("Testing student validation API...")
        print(f"Student data: {json.dumps(student_data, indent=2)}")
        
        try:
            response = self.api.validate_student_record(student_data)
            
            if response.success:
                print("✓ Validation successful")
            else:
                print(f"✗ Validation failed: {response.error}")
                
            print(f"Response: {json.dumps(response.data, indent=2) if response.data else 'No data'}")
            return response
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return None
    
    def test_duplicate_checking(self, students=None):
        """
        Test the duplicate checking API
        
        Args:
            students: List of student records to check (will use sample data if None)
            
        Returns:
            ApiResponse: Response from the API
        """
        if students is None:
            # Use sample student data with duplicates
            students = [
                {
                    "StudentName": "John Smith",
                    "DateOfBirth": "2010-05-15",
                    "AcademicYear": "2023",
                    "Gender": "M",
                    "Grade": "7"
                },
                {
                    "StudentName": "Jane Doe",
                    "DateOfBirth": "2011-02-20",
                    "AcademicYear": "2023",
                    "Gender": "F",
                    "Grade": "6"
                },
                {
                    "StudentName": "John Smith",
                    "DateOfBirth": "2010-05-15",
                    "AcademicYear": "2023",
                    "Gender": "M",
                    "Grade": "7"
                },
                {
                    "StudentName": "JANE DOE",
                    "DateOfBirth": "2011-02-20",
                    "AcademicYear": "2023",
                    "Gender": "F",
                    "Grade": "6"
                }
            ]
            
        print("Testing duplicate checking API...")
        print(f"Checking {len(students)} student records for duplicates...")
        
        try:
            response = self.api.check_duplicates(students)
            
            if response.success:
                print("✓ Duplicate check successful")
                if response.data and "duplicates" in response.data:
                    print(f"Found {len(response.data['duplicates'])} duplicates")
            else:
                print(f"✗ Duplicate check failed: {response.error}")
                
            print(f"Response: {json.dumps(response.data, indent=2) if response.data else 'No data'}")
            return response
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return None
    
    def run_all_tests(self):
        """Run all available API tests"""
        print("Running all API tests...")
        print("=" * 60)
        
        # Test connection
        connection_result = self.test_connection()
        print("=" * 60)
        
        if not connection_result:
            print("Connection failed. Stopping tests.")
            return False
            
        # Test student validation
        self.test_student_validation()
        print("=" * 60)
        
        # Test duplicate checking
        self.test_duplicate_checking()
        print("=" * 60)
        
def test_batch_processing(self, num_records=100):
    """
    Test batch processing API with simulated data load
    
    Args:
        num_records: Number of records to simulate
        
    Returns:
        ApiResponse: Response from the API
    """
    from faker import Faker
    import random
    from datetime import datetime
    
    print(f"Testing batch processing with {num_records} simulated records...")
    fake = Faker()
    
    # Generate simulated data
    students = []
    current_year = datetime.now().year
    
    for i in range(num_records):
        # Create random birthdate for school-age children
        birth_year = current_year - random.randint(5, 18)
        birth_date = fake.date_between(start_date=f"-{current_year-birth_year}y")
        
        student = {
            "StudentName": fake.name(),
            "DateOfBirth": birth_date.strftime("%Y-%m-%d"),
            "AcademicYear": str(current_year),
            "Gender": random.choice(["M", "F"]),
            "Grade": str(random.randint(1, 12))
        }
        students.append(student)
    
    # Create duplicates (about 15%)
    duplicate_count = int(num_records * 0.15)
    for i in range(duplicate_count):
        if students:
            # Copy a random student with slight modifications
            original = random.choice(students)
            duplicate = original.copy()
            
            # Maybe alter the name slightly
            if random.random() > 0.5:
                name_parts = duplicate["StudentName"].split()
                if len(name_parts) > 1 and random.random() > 0.5:
                    # Typo in first name
                    name_parts[0] = name_parts[0][:-1] + random.choice(["a", "e", "i", "o", "u"])
                duplicate["StudentName"] = " ".join(name_parts)
            
            students.append(duplicate)
    
    try:
        print(f"Sending batch of {len(students)} records for processing...")
        response = self.api.process_batch(students)
        
        if response.success:
            print("✓ Batch processing successful")
            print(f"  - Processed: {response.data.get('processed', 0)} records")
            print(f"  - Duplicates: {response.data.get('duplicates', 0)} records")
            print(f"  - Time: {response.data.get('processing_time', 0)} seconds")
        else:
            print(f"✗ Batch processing failed: {response.error}")
            
        return response
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return None
        
def test_analytics_api(self):
    """
    Test the analytics API endpoints for dashboard integration
    
    Returns:
        dict: Results from various analytics endpoints
    """
    print("Testing analytics API endpoints...")
    results = {}
    
    endpoints = [
        "statistics/summary",
        "statistics/duplicates",
        "statistics/monthly"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Querying {endpoint}...")
            response = self.connector.get(endpoint)
            
            if response.success:
                print(f"✓ {endpoint} query successful")
                results[endpoint] = response.data
            else:
                print(f"✗ {endpoint} query failed: {response.error}")
                results[endpoint] = None
        except Exception as e:
            print(f"✗ Error querying {endpoint}: {str(e)}")
            results[endpoint] = None
    
    return results

def run_all_tests(self):
    """Run all available API tests"""
    print("Running all API tests...")
    print("=" * 60)
    
    # Test connection
    connection_result = self.test_connection()
    print("=" * 60)
    
    if not connection_result:
        print("Connection failed. Stopping tests.")
        return False
            
    # Test student validation
    self.test_student_validation()
    print("=" * 60)
    
    # Test duplicate checking
    self.test_duplicate_checking()
    print("=" * 60)
    
    print("All tests completed.")
    return True


def main():
    parser = argparse.ArgumentParser(description="API Testing Utility for Future Integration")
    parser.add_argument("--url", help="API URL")
    parser.add_argument("--key", help="API Key")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries")
    parser.add_argument("--test-type", choices=["connection", "validation", "duplicates", "batch", "analytics", "all"], 
                      default="connection", help="Type of test to run")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of records for batch processing test")
    
    args = parser.parse_args()
    
    print("\n========================================")
    print("     Education Data API Tester           ")
    print("     (Future Capability)                 ")
    print("========================================\n")
    
    print("NOTE: This utility is for testing future API capabilities.")
    print("The current application works in native mode without requiring API access.\n")
    
    # Create tester
    tester = ApiTester(args.url, args.key, args.timeout, args.retries)
    
    # Determine which tests to run
    if args.endpoint:
        # Test specific endpoint
        data = None
        if args.data:
            try:
                data = json.loads(args.data)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON data: {args.data}")
                return 1
        
        tester.test_endpoint(args.endpoint, args.method, data)
    elif args.validate:
        # Test student validation
        tester.test_student_validation()
    elif args.check_duplicates:
        # Test duplicate checking
        tester.test_duplicate_checking()
    elif args.all:
        # Run all tests
        tester.run_all_tests()
    else:
        # Default to testing connection
        tester.test_connection()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
