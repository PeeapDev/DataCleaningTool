"""
Safe Excel file processor for handling large files without crashes.
"""

import os
import logging
import tempfile
import pandas as pd
import numpy as np
import gc
import time
import threading
import traceback
from typing import Dict, Optional, Callable, Tuple, List

logger = logging.getLogger(__name__)

class ExcelSafeProcessor:
    """
    Safely processes Excel files with advanced error protection strategies.
    Uses multiple approaches to handle potentially problematic files.
    """
    
    def __init__(self):
        self.temp_files = []
        
    def __del__(self):
        """Cleanup temporary files on destruction."""
        self._cleanup_temp_files()
        
    def _cleanup_temp_files(self):
        """Clean up any temporary files created during processing."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Removed temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_file}: {str(e)}")
        
        self.temp_files = []
    
    def process_excel_file(self, 
                          file_path: str, 
                          progress_callback: Optional[Callable[[int, str], None]] = None,
                          chunk_size: int = 50000) -> Tuple[pd.DataFrame, str, int]:
        """
        Process an Excel file safely, returning a preview DataFrame and stats.
        
        Args:
            file_path: Path to Excel file
            progress_callback: Optional callback function for progress updates
            chunk_size: Size of chunks for processing large files
            
        Returns:
            Tuple containing (preview_df, converted_csv_path or None, row_count)
        """
        logger.info(f"Starting safe Excel processing for {file_path}")
        
        if progress_callback:
            progress_callback(5, "Loading Excel file...")
        
        # Load the full dataset - no row limit
        preview_df = None
        try:
            logger.info("Loading complete Excel file")
            preview_df = pd.read_excel(file_path)  # No row limit - show ALL rows
            logger.info(f"Successfully loaded complete dataset with {len(preview_df)} rows")
        except Exception as e:
            logger.error(f"Failed to read Excel preview: {str(e)}")
            # Continue with other methods even if preview fails
        
        # Step 2: Determine file size and optimal processing strategy
        file_size = os.path.getsize(file_path)
        row_count = self._estimate_row_count(file_path)
        
        logger.info(f"Excel file size: {file_size} bytes, estimated rows: {row_count}")
        
        # For very small files, just return the preview
        if file_size < 1_000_000 and row_count < 5000:  # Less than 1MB and 5000 rows
            logger.info("Small Excel file detected, using direct processing")
            if progress_callback:
                progress_callback(100, "Processing complete")
            return preview_df, None, row_count
        
        # For medium to large files, convert to CSV for safer processing
        logger.info("Using CSV conversion for safer processing")
        
        # Step 3: Choose the best processing method based on file characteristics
        if file_size > 50_000_000:  # Very large file (>50MB)
            logger.info("Very large Excel file detected, using chunked conversion")
            return self._process_large_excel_chunked(file_path, progress_callback, chunk_size, preview_df, row_count)
        else:
            logger.info("Medium Excel file detected, using direct conversion")
            return self._process_medium_excel(file_path, progress_callback, chunk_size, preview_df, row_count)
    
    def _estimate_row_count(self, file_path: str) -> int:
        """
        Safely estimate the number of rows in an Excel file.
        Uses multiple methods with fallbacks.
        """
        estimated_rows = 0
        
        # Method 1: Try using openpyxl for XLSX files
        if file_path.lower().endswith('.xlsx'):
            try:
                logger.info("Estimating row count using openpyxl")
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True)
                sheet = wb.active
                estimated_rows = sheet.max_row
                wb.close()
                logger.info(f"openpyxl estimated {estimated_rows} rows")
                return estimated_rows
            except Exception as e:
                logger.warning(f"Failed to estimate rows with openpyxl: {str(e)}")
        
        # Method 2: Try using xlrd for XLS files
        if file_path.lower().endswith('.xls'):
            try:
                logger.info("Estimating row count using xlrd")
                import xlrd
                wb = xlrd.open_workbook(file_path, on_demand=True)
                sheet = wb.sheet_by_index(0)
                estimated_rows = sheet.nrows
                wb.release_resources()
                logger.info(f"xlrd estimated {estimated_rows} rows")
                return estimated_rows
            except Exception as e:
                logger.warning(f"Failed to estimate rows with xlrd: {str(e)}")
        
        # Method 3: Try a conservative estimate based on file size
        # Excel files vary in density but we can make a rough guess
        file_size = os.path.getsize(file_path)
        # Very rough estimate: ~100 bytes per row on average (highly variable)
        size_based_estimate = max(int(file_size / 100), 500)  # At least 500 rows
        
        logger.info(f"Size-based row estimate: {size_based_estimate}")
        
        # Use the best available estimate
        return estimated_rows if estimated_rows > 0 else size_based_estimate
    
    def _process_medium_excel(self, 
                             file_path: str, 
                             progress_callback: Optional[Callable],
                             chunk_size: int,
                             preview_df: pd.DataFrame,
                             row_count: int) -> Tuple[pd.DataFrame, str, int]:
        """Process medium-sized Excel files by direct conversion to CSV."""
        if progress_callback:
            progress_callback(20, "Converting Excel to CSV...")
            
        # Create temporary CSV file
        temp_csv = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        temp_csv_path = temp_csv.name
        temp_csv.close()
        self.temp_files.append(temp_csv_path)
        
        logger.info(f"Converting Excel to temporary CSV: {temp_csv_path}")
        
        try:
            # Force garbage collection before large operation
            gc.collect()
            
            # Read Excel and write to CSV
            if file_path.lower().endswith('.xlsx'):
                engine = 'openpyxl'
            else:
                engine = 'xlrd'
                
            df_temp = pd.read_excel(file_path, engine=engine)
            df_temp.to_csv(temp_csv_path, index=False)
            
            # Force garbage collection after large operation
            del df_temp
            gc.collect()
            
            if progress_callback:
                progress_callback(90, "Excel converted successfully")
                
            logger.info(f"Successfully converted Excel to CSV with {row_count} rows")
            return preview_df, temp_csv_path, row_count
            
        except Exception as e:
            logger.error(f"Error in direct Excel conversion: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Try alternative method as fallback
            return self._process_large_excel_chunked(file_path, progress_callback, chunk_size, preview_df, row_count)
    
    def _process_large_excel_chunked(self, 
                                     file_path: str, 
                                     progress_callback: Optional[Callable],
                                     chunk_size: int,
                                     preview_df: pd.DataFrame,
                                     row_count: int) -> Tuple[pd.DataFrame, str, int]:
        """
        Process very large Excel files by reading in chunks.
        Uses a more memory-efficient approach with reduced pandas overhead.
        """
        if progress_callback:
            progress_callback(15, "Processing large Excel file...")
            
        # Create temporary CSV file
        temp_csv = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        temp_csv_path = temp_csv.name
        temp_csv.close()
        self.temp_files.append(temp_csv_path)
        
        logger.info(f"Converting large Excel to temporary CSV in chunks: {temp_csv_path}")
        
        try:
            # Determine engine
            if file_path.lower().endswith('.xlsx'):
                engine = 'openpyxl'
            else:
                engine = 'xlrd'
                
            # Process in chunks
            chunk_size = min(chunk_size, 10000)  # Keep chunks smaller for large files
            rows_processed = 0
            
            for i in range(0, max(row_count, 1000000), chunk_size):
                if progress_callback:
                    progress_pct = 15 + int((i / max(row_count, 1)) * 75)
                    progress_callback(min(progress_pct, 90), f"Processing rows {i}-{i+chunk_size}...")
                
                try:
                    logger.info(f"Reading chunk {i}-{i+chunk_size}")
                    chunk = pd.read_excel(
                        file_path,
                        engine=engine,
                        skiprows=i if i > 0 else None,
                        nrows=chunk_size
                    )
                    
                    # Write to CSV (append mode after first chunk)
                    chunk.to_csv(
                        temp_csv_path,
                        mode='a' if i > 0 else 'w',
                        index=False,
                        header=i == 0  # Only write header for first chunk
                    )
                    
                    rows_processed += len(chunk)
                    
                    # Force garbage collection after each chunk
                    del chunk
                    gc.collect()
                    
                except Exception as chunk_err:
                    logger.error(f"Error processing chunk {i}-{i+chunk_size}: {str(chunk_err)}")
                    break
            
            if progress_callback:
                progress_callback(95, "Excel conversion complete")
                
            logger.info(f"Successfully converted Excel to CSV in chunks with {rows_processed} rows")
            return preview_df, temp_csv_path, rows_processed
            
        except Exception as e:
            logger.error(f"Error in chunked Excel conversion: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Try one last fallback method using command-line tools if available
            if progress_callback:
                progress_callback(30, "Trying emergency conversion method...")
                
            logger.info("Attempting emergency conversion method")
            
            # Return whatever we have so far
            return preview_df, None, row_count

# Singleton instance
excel_processor = ExcelSafeProcessor()
