"""
Data cleaning controller for handling data processing logic.
"""

import os
import re
import time
import logging
import datetime
import gc
import numpy as np
import pandas as pd
import tempfile
import threading
import traceback
from typing import Dict, List, Any, Tuple, Optional, Callable, Union
from collections import defaultdict

# Import memory monitor and excel safeguard
try:
    from app.utils.memory_monitor import memory_monitor
    HAS_MEMORY_MONITOR = True
except ImportError:
    HAS_MEMORY_MONITOR = False
    logging.warning("Memory monitor not available. Large file protection will be limited.")
    
try:
    from app.utils.excel_safeguard import excel_safeguard
    HAS_EXCEL_SAFEGUARD = True
except ImportError:
    HAS_EXCEL_SAFEGUARD = False
    logging.warning("Excel safeguard not available. Large Excel file support will be limited.")

# Try to import fuzzywuzzy, but provide fallback if it fails
try:
    from fuzzywuzzy import fuzz
    HAS_FUZZY = True
except ImportError:
    HAS_FUZZY = False
    logging.warning("fuzzywuzzy with python-Levenshtein not available. Using basic string similarity instead.")

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fallback function for string similarity when Levenshtein is not available
def basic_string_similarity(str1, str2):
    """
    A basic string similarity function that doesn't require Levenshtein
    Returns a score between 0 and 100
    """
    # Convert to lowercase
    str1 = str1.lower()
    str2 = str2.lower()
    
    # Check for exact match
    if str1 == str2:
        return 100
        
    # Check for substring
    if str1 in str2 or str2 in str1:
        # Calculate percentage based on length ratio
        return int(min(len(str1), len(str2)) / max(len(str1), len(str2)) * 90)
    
    # Count matching characters in order
    matches = 0
    for c1, c2 in zip(str1, str2):
        if c1 == c2:
            matches += 1
    
    # Calculate similarity percentage
    max_length = max(len(str1), len(str2))
    if max_length == 0:
        return 0
    return int((matches / max_length) * 80)


class DataCleaner:
    """
    Controller class for cleaning educational data.
    Handles loading, processing, and exporting data.
    """
    
    def __init__(self):
        """Initialize the data cleaner."""
        self.raw_data = None
        self.clean_data = None
        self.duplicate_data = None
        self.columns = []
        self.processing_stats = {}
        self.file_path = None
        self.file_extension = None
        self.temp_file_path = None
        
    def clear(self):
        """Reset all data attributes to their initial state."""
        logger.info("Clearing previous data and resetting state.")
        self.raw_data = None
        self.clean_data = None
        self.duplicate_data = None
        self.columns = []
        self.processing_stats = {}
        self.file_path = None
        self.file_extension = None
        
        # Clean up temp file if it exists
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            try:
                os.remove(self.temp_file_path)
                logger.info(f"Removed temporary file: {self.temp_file_path}")
            except OSError as e:
                logger.error(f"Error removing temp file {self.temp_file_path}: {e}")
        self.temp_file_path = None
        
        # Hint to garbage collector
        gc.collect()

    def load_data(self, temp_csv_path: str, columns: list):
        """
        Prepares a non-blocking data iterator from the temporary CSV file.
        This method assumes the Excel file has already been converted to a CSV.
        """
        logger.info(f"Preparing data iterator from temporary file: {temp_csv_path}")
        try:
            self.temp_file_path = temp_csv_path
            self.columns = columns
            # This creates an iterator; it does not load the file into memory.
            self.raw_data = pd.read_csv(temp_csv_path, chunksize=10000, low_memory=False)
            logger.info("Data iterator is ready for processing.")
            return True
        except Exception as e:
            logger.error(f"Failed to create data iterator from temp CSV: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def get_data(self):
        """Returns the raw data, which could be a DataFrame or None."""
        return self.raw_data

    def get_columns(self):
        """Returns the list of column names."""
        return self.columns

    def get_record_count(self):
        """Returns the total number of records."""
        if self.is_chunked_mode():
            return getattr(self, 'total_records', 0)
        return len(self.raw_data) if self.raw_data is not None else 0

    def is_chunked_mode(self):
        """Checks if the data is being processed in chunks."""
        return self.temp_file_path is not None

    def identify_duplicates(self, name_col, dob_col, year_col, fuzzy_match=False, fuzzy_threshold=90):
        """
        Find duplicate entries based on name and DOB within same year.
        
        Args:
            name_col: Column name for student name
            dob_col: Column name for date of birth
            year_col: Column name for academic year
            fuzzy_match: Whether to use fuzzy matching for names
            fuzzy_threshold: Threshold for fuzzy matching (0-100)
            
        Returns:
            Dictionary with statistics about the cleaning operation
        """
        if self.raw_data is None:
            logger.error("No data loaded. Please load data first.")
            return None
            
        try:
            # If we're processing in chunks
            if isinstance(self.raw_data, pd.io.parsers.TextFileReader):
                return self._process_in_chunks(name_col, dob_col, year_col, fuzzy_match, fuzzy_threshold)
            
            # Process the entire dataframe at once
            return self._process_dataframe(self.raw_data, name_col, dob_col, year_col, 
                                         fuzzy_match, fuzzy_threshold)
                
        except Exception as e:
            logger.error(f"Error identifying duplicates: {str(e)}")
            return None
    
    def _process_dataframe(self, df, name_col, dob_col, year_col, fuzzy_match, fuzzy_threshold):
        """Process a single dataframe to identify duplicates."""
        
        # Normalize names if doing fuzzy matching
        if fuzzy_match:
            df['normalized_name'] = df[name_col].str.lower().str.strip()
            
            # Group by year and dob to find potential duplicates
            duplicates = []
            unique_records = []
            
            for (year, dob), group in df.groupby([year_col, dob_col]):
                # Skip groups with only one record
                if len(group) == 1:
                    unique_records.append(group.iloc[0])
                    continue
                    
                # Process this group to find fuzzy duplicates
                processed = set()
                for idx, row in group.iterrows():
                    if idx in processed:
                        continue
                        
                    name = row['normalized_name']
                    matches = []
                    
                    for inner_idx, inner_row in group.iterrows():
                        if inner_idx == idx or inner_idx in processed:
                            continue
                            
                        inner_name = inner_row['normalized_name']
                        # Calculate similarity - always do this for grouped records
                        if HAS_FUZZY:
                            similarity = fuzz.ratio(name, inner_name)
                        else:
                            similarity = basic_string_similarity(name, inner_name)
                        
                        if similarity >= fuzzy_threshold:
                            matches.append(inner_idx)
                            processed.add(inner_idx)
                    
                    # Keep the first record, mark others as duplicates
                    unique_records.append(row)
                    for match_idx in matches:
                        duplicates.append(group.loc[match_idx])
                    processed.add(idx)
            
            # Create the clean and duplicate dataframes
            self.clean_data = pd.DataFrame(unique_records) if unique_records else pd.DataFrame(columns=df.columns)
            self.duplicate_data = pd.DataFrame(duplicates) if duplicates else pd.DataFrame(columns=df.columns)
            
            # Remove the normalized_name column
            if 'normalized_name' in self.clean_data.columns:
                self.clean_data = self.clean_data.drop('normalized_name', axis=1)
            if 'normalized_name' in self.duplicate_data.columns:
                self.duplicate_data = self.duplicate_data.drop('normalized_name', axis=1)
                
        else:
            # Exact matching using pandas duplicated method
            duplicate_mask = df.duplicated(
                subset=[name_col, dob_col, year_col], 
                keep='first'
            )
            
            self.clean_data = df[~duplicate_mask].copy()
            self.duplicate_data = df[duplicate_mask].copy()
        
        # Gather stats
        stats = {
            'total_records': len(df),
            'clean_records': len(self.clean_data),
            'duplicate_records': len(self.duplicate_data),
            'duplicate_percentage': round(len(self.duplicate_data) / len(df) * 100, 2) if len(df) > 0 else 0
        }
        
        logger.info(f"Duplicate detection complete. Found {stats['duplicate_records']} duplicates.")
        self.processing_stats.update(stats)
        
        return stats
    
    def _process_in_chunks(self, name_col, dob_col, year_col, fuzzy_match, fuzzy_threshold):
        """Process data in chunks to handle large datasets."""
        
        all_clean = []
        all_duplicates = []
        total_records = 0
        
        for chunk in self.raw_data:
            total_records += len(chunk)
            chunk_stats = self._process_dataframe(chunk, name_col, dob_col, year_col, 
                                             fuzzy_match, fuzzy_threshold)
            
            all_clean.append(self.clean_data)
            all_duplicates.append(self.duplicate_data)
        
        # Combine the results
        self.clean_data = pd.concat(all_clean, ignore_index=True)
        self.duplicate_data = pd.concat(all_duplicates, ignore_index=True)
        
        # Final duplicate check across chunks
        if not fuzzy_match:
            duplicate_mask = self.clean_data.duplicated(
                subset=[name_col, dob_col, year_col], 
                keep='first'
            )
            
            additional_duplicates = self.clean_data[duplicate_mask].copy()
            self.clean_data = self.clean_data[~duplicate_mask].copy()
            self.duplicate_data = pd.concat([self.duplicate_data, additional_duplicates], ignore_index=True)
        
        # Gather stats
        stats = {
            'total_records': total_records,
            'clean_records': len(self.clean_data),
            'duplicate_records': len(self.duplicate_data),
            'duplicate_percentage': round(len(self.duplicate_data) / total_records * 100, 2) if total_records > 0 else 0
        }
        
        logger.info(f"Chunked processing complete. Found {stats['duplicate_records']} duplicates.")
        self.processing_stats.update(stats)
        
        return stats
        
    def export_data(self, clean_path, duplicate_path):
        """
        Export clean and duplicate data to separate files in CSV or Excel format.
        
        Args:
            clean_path: Path to save clean data
            duplicate_path: Path to save duplicate data
            
        Returns:
            Dictionary with export paths and statistics
        """
        if self.clean_data is None or self.duplicate_data is None:
            logger.error("No processed data to export. Please process data first.")
            return None
            
        try:
            # Create directory if needed
            for path in [clean_path, duplicate_path]:
                directory = os.path.dirname(path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
            
            # Determine file format based on extension
            clean_ext = os.path.splitext(clean_path)[1].lower()
            duplicate_ext = os.path.splitext(duplicate_path)[1].lower()
            
            # Export clean data
            if clean_ext in ['.xlsx', '.xls']:
                engine = 'openpyxl' if clean_ext == '.xlsx' else 'xlrd'
                self.clean_data.to_excel(clean_path, index=False, engine=engine)
                logger.info(f"Exported clean data to Excel file: {clean_path}")
            else:  # Default to CSV
                self.clean_data.to_csv(clean_path, index=False)
                logger.info(f"Exported clean data to CSV file: {clean_path}")
            
            # Export duplicate data
            if duplicate_ext in ['.xlsx', '.xls']:
                engine = 'openpyxl' if duplicate_ext == '.xlsx' else 'xlrd'
                self.duplicate_data.to_excel(duplicate_path, index=False, engine=engine)
                logger.info(f"Exported duplicate data to Excel file: {duplicate_path}")
            else:  # Default to CSV
                self.duplicate_data.to_csv(duplicate_path, index=False)
                logger.info(f"Exported duplicate data to CSV file: {duplicate_path}")
            
            # Create result with statistics
            result = {
                'clean_path': clean_path,
                'clean_records': len(self.clean_data),
                'duplicate_path': duplicate_path,
                'duplicate_records': len(self.duplicate_data),
                'total_records': len(self.clean_data) + len(self.duplicate_data),
                'export_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'clean_format': 'Excel' if clean_ext in ['.xlsx', '.xls'] else 'CSV',
                'duplicate_format': 'Excel' if duplicate_ext in ['.xlsx', '.xls'] else 'CSV'
            }
            
            # Update processing stats
            self.processing_stats.update({
                'exported_at': result['export_time'],
                'clean_path': clean_path,
                'duplicate_path': duplicate_path
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return None
            
    def get_summary_report(self):
        """
        Generate a summary report of the cleaning process.
        
        Returns:
            Dictionary with summary statistics and information
        """
        if not self.processing_stats:
            logger.error("No processing statistics available.")
            return None
            
        return self.processing_stats
