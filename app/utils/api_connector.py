"""
API connector for the Education Data Cleaning Tool.
Provides functionality to connect to external APIs for data validation and enrichment.
"""

import requests
import json
import logging
from typing import Dict, Any, List, Optional, Union
import time
from pydantic import BaseModel


class ApiConfig(BaseModel):
    """Configuration for API endpoints"""
    base_url: str
    api_key: Optional[str] = None
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 2


class ApiResponse(BaseModel):
    """Standard API response model"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class ApiConnector:
    """Connector for external APIs"""
    
    def __init__(self, config: ApiConfig):
        """Initialize the API connector with configuration"""
        self.config = config
        self.session = requests.Session()
        
        # Set up default headers if API key is provided
        if config.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> ApiResponse:
        """
        Make an HTTP request to the API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (will be joined with base_url)
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            ApiResponse object with standardized response format
        """
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Set default timeout
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.config.timeout
            
        # Implement retry logic
        retries = 0
        while retries <= self.config.retry_count:
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Try to parse JSON response
                try:
                    data = response.json()
                except ValueError:
                    # Not JSON, return text content
                    data = response.text
                
                # Check if request was successful
                if response.status_code >= 200 and response.status_code < 300:
                    return ApiResponse(
                        success=True,
                        data=data,
                        meta={"status_code": response.status_code}
                    )
                else:
                    # Request failed
                    error_message = data.get('error', data.get('message', str(data))) \
                        if isinstance(data, dict) else str(data)
                    
                    return ApiResponse(
                        success=False,
                        error=f"API error ({response.status_code}): {error_message}",
                        meta={"status_code": response.status_code}
                    )
            
            except requests.exceptions.RequestException as e:
                # Network error, retry if we haven't exceeded retry count
                retries += 1
                if retries <= self.config.retry_count:
                    logging.warning(f"Request failed, retrying ({retries}/{self.config.retry_count}): {str(e)}")
                    time.sleep(self.config.retry_delay)
                else:
                    # Max retries exceeded
                    return ApiResponse(
                        success=False,
                        error=f"Request failed after {self.config.retry_count} retries: {str(e)}"
                    )
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> ApiResponse:
        """Send a GET request to the API"""
        return self._make_request("GET", endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Union[Dict[str, Any], List[Any]], **kwargs) -> ApiResponse:
        """Send a POST request to the API"""
        return self._make_request("POST", endpoint, json=data, **kwargs)
    
    def put(self, endpoint: str, data: Union[Dict[str, Any], List[Any]], **kwargs) -> ApiResponse:
        """Send a PUT request to the API"""
        return self._make_request("PUT", endpoint, json=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> ApiResponse:
        """Send a DELETE request to the API"""
        return self._make_request("DELETE", endpoint, **kwargs)
    
    def validate_connection(self) -> bool:
        """
        Test the API connection
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to connect to the API health or status endpoint
            response = self.get("status")
            return response.success
        except Exception as e:
            logging.error(f"API connection test failed: {str(e)}")
            return False


class EducationDataApi:
    """
    Client for education data API services.
    This provides specific education data operations on top of the base ApiConnector.
    """
    
    def __init__(self, connector: ApiConnector):
        """Initialize with an API connector"""
        self.connector = connector
    
    def validate_student_record(self, student_data: Dict[str, Any]) -> ApiResponse:
        """
        Validate a student record against external rules
        
        Args:
            student_data: Dictionary containing student data
            
        Returns:
            API response with validation results
        """
        return self.connector.post("students/validate", student_data)
    
    def check_duplicates(self, students: List[Dict[str, Any]]) -> ApiResponse:
        """
        Check for duplicates in a batch of student records using the API
        
        Args:
            students: List of student data dictionaries
            
        Returns:
            API response with duplicate information
        """
        return self.connector.post("students/check-duplicates", students)
    
    def enrich_data(self, student_data: Dict[str, Any]) -> ApiResponse:
        """
        Enrich student data with additional information from the API
        
        Args:
            student_data: Dictionary containing student data
            
        Returns:
            API response with enriched data
        """
        return self.connector.post("students/enrich", student_data)


# Mock API client for testing when real API is not available
class MockEducationDataApi(EducationDataApi):
    """Mock implementation of the EducationDataApi for testing purposes"""
    
    def __init__(self):
        """Initialize the mock API client"""
        # No actual connector needed for mock
        pass
    
    def validate_student_record(self, student_data: Dict[str, Any]) -> ApiResponse:
        """Mock validation of student record"""
        # Simple validation rules
        errors = []
        
        # Check required fields
        required_fields = ['StudentName', 'DateOfBirth', 'AcademicYear']
        for field in required_fields:
            if field not in student_data or not student_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Check name format
        if 'StudentName' in student_data and student_data['StudentName']:
            name = student_data['StudentName']
            if len(name.split()) < 2:
                errors.append("Student name should include at least first and last name")
        
        return ApiResponse(
            success=len(errors) == 0,
            data={"valid": len(errors) == 0},
            error="; ".join(errors) if errors else None
        )
    
    def check_duplicates(self, students: List[Dict[str, Any]]) -> ApiResponse:
        """Mock duplicate checking"""
        # Simple duplicate detection
        duplicates = []
        seen = {}
        
        for i, student in enumerate(students):
            key = f"{student.get('StudentName', '').lower()}|{student.get('DateOfBirth', '')}|{student.get('AcademicYear', '')}"
            
            if key in seen:
                duplicates.append({
                    "original_index": seen[key],
                    "duplicate_index": i,
                    "student": student
                })
            else:
                seen[key] = i
        
        return ApiResponse(
            success=True,
            data={
                "duplicates": duplicates,
                "total_duplicates": len(duplicates),
                "total_records": len(students)
            }
        )
    
    def enrich_data(self, student_data: Dict[str, Any]) -> ApiResponse:
        """Mock data enrichment"""
        # Simulate enrichment by adding mock fields
        enriched = student_data.copy()
        
        # Add mock enriched data
        if 'DateOfBirth' in enriched:
            try:
                from datetime import datetime
                dob = datetime.strptime(enriched['DateOfBirth'], "%Y-%m-%d")
                today = datetime.now()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                enriched['Age'] = age
            except:
                enriched['Age'] = "Unknown"
        
        return ApiResponse(
            success=True,
            data=enriched
        )
