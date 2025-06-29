"""
Intelligent Field Mapper - Quantize AI Module
Automatically maps fields from any Excel file format to standardized fields
without requiring a specific structure.
"""

import re
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuantizeAI:
    """
    AI-powered field mapping system that works offline to identify and map
    fields from any Excel or CSV file to standard fields based on content patterns.
    """
    
    def __init__(self):
        """Initialize the field mapper with known field patterns."""
        self.field_patterns = {
            'name': [
                r'^(?:student|pupil|learner)?[\s_]*(?:full[\s_]*)?name$', 
                r'^(?:first[\s_]*name|f[\s_]*name)$',
                r'^(?:last[\s_]*name|l[\s_]*name|surname)$'
            ],
            'dob': [
                r'^(?:date[\s_]*of[\s_]*birth|dob|birth[\s_]*date|birthdate)$',
                r'^(?:birth)$'
            ],
            'gender': [
                r'^(?:gender|sex)$'
            ],
            'grade': [
                r'^(?:grade|class|level|std)$'
            ],
            'year': [
                r'^(?:academic[\s_]*year|school[\s_]*year|year|session|term)$'
            ],
            'school': [
                r'^(?:school|institution|center)[\s_]*(?:name|id|code)?$'
            ],
            'enrollment': [
                r'^(?:enrollment|registration|admission)[\s_]*(?:date|day)?$'
            ],
            'address': [
                r'^(?:address|location|residence)$'
            ],
            'contact': [
                r'^(?:contact|phone|mobile|tel|telephone|cell)[\s_]*(?:number|no|#)?$'
            ],
            'email': [
                r'^(?:email|e-mail|mail)[\s_]*(?:address)?$'
            ]
        }
        
        # Content pattern detectors - check actual values in columns
        self.content_detectors = {
            'name': self._is_name_column,
            'dob': self._is_date_column,
            'gender': self._is_gender_column,
            'grade': self._is_grade_column,
            'year': self._is_year_column,
            'school': self._is_school_column,
            'enrollment': self._is_date_column,
            'contact': self._is_contact_column,
            'email': self._is_email_column
        }
        
        # Standard field names to map to
        self.standard_fields = {
            'name': 'StudentName',
            'dob': 'DateOfBirth',
            'gender': 'Gender',
            'grade': 'Grade',
            'year': 'AcademicYear',
            'school': 'SchoolID',
            'enrollment': 'EnrollmentDate',
            'address': 'Address',
            'contact': 'ContactNumber',
            'email': 'EmailAddress'
        }
    
    def map_fields(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Map DataFrame columns to standard field names.
        
        Args:
            df: Pandas DataFrame with data to analyze
            
        Returns:
            Dictionary mapping original column names to standard field names
        """
        field_mapping = {}
        columns = df.columns.tolist()
        
        # First pass: Check column names against patterns
        for column in columns:
            field_type = self._match_column_name(column)
            if field_type:
                field_mapping[column] = self.standard_fields[field_type]
        
        # Second pass: Check column contents for unmapped columns
        unmapped_columns = [col for col in columns if col not in field_mapping]
        for column in unmapped_columns:
            field_type = self._analyze_column_content(df[column])
            if field_type and field_type not in [field_mapping.get(col) for col in field_mapping]:
                field_mapping[column] = self.standard_fields[field_type]
        
        # Log mapping results
        mapped_count = len(field_mapping)
        logger.info(f"Mapped {mapped_count} out of {len(columns)} columns")
        for original, mapped in field_mapping.items():
            logger.info(f"  {original} → {mapped}")
        
        return field_mapping
    
    def _match_column_name(self, column_name: str) -> str:
        """
        Match a column name against known field patterns.
        
        Args:
            column_name: Original column name
            
        Returns:
            Matched field type or None
        """
        # Normalize the column name: lowercase, remove special chars
        norm_name = column_name.lower().strip()
        
        for field_type, patterns in self.field_patterns.items():
            for pattern in patterns:
                if re.search(pattern, norm_name, re.IGNORECASE):
                    return field_type
        
        return None
    
    def _analyze_column_content(self, series: pd.Series) -> str:
        """
        Analyze column values to determine the field type.
        
        Args:
            series: Pandas Series with column data
            
        Returns:
            Detected field type or None
        """
        # Skip empty columns
        if series.isna().all() or len(series) == 0:
            return None
        
        # Check each field type detector
        for field_type, detector in self.content_detectors.items():
            if detector(series):
                return field_type
        
        return None
    
    def _is_name_column(self, series: pd.Series) -> bool:
        """Check if column contains names."""
        # Sample non-null values
        sample = series.dropna().astype(str).sample(min(10, len(series.dropna())))
        
        # Count words per value
        word_counts = sample.str.split().str.len()
        
        # Names typically have 2+ words and are alphabetic
        has_multiple_words = (word_counts >= 2).mean() > 0.7
        is_alpha = sample.str.replace(r'[^a-zA-Z\s]', '').str.len() / sample.str.len() > 0.8
        
        return has_multiple_words and is_alpha.mean() > 0.8
    
    def _is_date_column(self, series: pd.Series) -> bool:
        """Check if column contains dates."""
        try:
            # Try to convert to datetime
            pd.to_datetime(series, errors='coerce')
            # If at least 80% of non-null values are valid dates
            return series.dropna().shape[0] > 0 and pd.to_datetime(series, errors='coerce').notna().mean() > 0.8
        except:
            return False
    
    def _is_gender_column(self, series: pd.Series) -> bool:
        """Check if column contains gender information."""
        # Gender columns typically have very few unique values like M, F, Male, Female
        sample = series.dropna().astype(str).str.lower()
        unique_count = sample.nunique()
        
        if unique_count <= 5 and unique_count > 0:
            # Check for common gender values
            common_values = ['m', 'f', 'male', 'female', 'other', 'non-binary']
            matches = sum(sample.isin(common_values))
            return matches / len(sample) > 0.8
        
        return False
    
    def _is_grade_column(self, series: pd.Series) -> bool:
        """Check if column contains grade/class information."""
        sample = series.dropna().astype(str).str.lower()
        
        # Grades are often numeric (1-12) or have "grade" in them
        numeric_grades = sample.str.extract(r'(\d+)')[0].notna().mean() > 0.5
        grade_keyword = sample.str.contains(r'grade|class|level', case=False).mean() > 0.3
        
        # Limited unique values
        limited_values = sample.nunique() < 20
        
        return limited_values and (numeric_grades or grade_keyword)
    
    def _is_year_column(self, series: pd.Series) -> bool:
        """Check if column contains academic year information."""
        sample = series.dropna().astype(str)
        
        # Years are typically 4 digits or patterns like 2022-2023
        year_pattern = sample.str.contains(r'(19|20)\d{2}(-|/|_)?(19|20)?\d{2}?', case=False).mean() > 0.5
        
        # Limited unique values
        limited_values = sample.nunique() < 10
        
        return limited_values and year_pattern
    
    def _is_school_column(self, series: pd.Series) -> bool:
        """Check if column contains school information."""
        sample = series.dropna().astype(str)
        
        # School IDs often have patterns like "SCH123" or "School Name"
        school_pattern = (sample.str.contains(r'sch|school|college|academy', case=False).mean() > 0.3 or
                         sample.str.contains(r'[A-Z]{2,5}\d+', case=False).mean() > 0.5)
        
        return school_pattern
    
    def _is_contact_column(self, series: pd.Series) -> bool:
        """Check if column contains contact numbers."""
        sample = series.dropna().astype(str)
        
        # Contact numbers typically have 8+ digits
        digit_count = sample.str.replace(r'[^\d]', '').str.len()
        has_phone_length = (digit_count >= 8).mean() > 0.8
        
        return has_phone_length
    
    def _is_email_column(self, series: pd.Series) -> bool:
        """Check if column contains email addresses."""
        sample = series.dropna().astype(str)
        
        # Basic email pattern check
        email_pattern = sample.str.contains(r'@.*\.', case=False)
        
        return email_pattern.mean() > 0.7
    
    def transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform DataFrame to use standard field names and formats.
        
        Args:
            df: Original DataFrame
            
        Returns:
            Transformed DataFrame with standard field names
        """
        field_mapping = self.map_fields(df)
        
        if not field_mapping:
            logger.warning("No fields could be mapped. Returning original DataFrame.")
            return df
        
        # Create a new DataFrame with mapped columns
        new_df = pd.DataFrame()
        
        for original_col, standard_field in field_mapping.items():
            new_df[standard_field] = df[original_col]
        
        # Add unmapped columns with original names
        unmapped_cols = [col for col in df.columns if col not in field_mapping]
        for col in unmapped_cols:
            if col not in new_df:  # Avoid duplicates
                new_df[col] = df[col]
        
        return new_df
