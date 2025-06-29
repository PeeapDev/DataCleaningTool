"""
Excel safeguard utility for handling problematic and large Excel files.
This module provides a single, robust method for loading Excel files.
"""

import logging
import os
import pandas as pd
import tempfile
import traceback
from typing import Callable, Optional, Dict

logger = logging.getLogger(__name__)

class ExcelSafeguard:
    """Provides a safe, non-blocking method for loading Excel files."""
    
    def __init__(self):
        self.temp_files = []
        
    def __del__(self):
        """Intentionally do not auto-clean temp files.

        The temporary CSV needs to remain accessible until the DataCleaner
        finishes preparing its iterator. Cleanup is handled explicitly
        elsewhere (e.g., DataCleaner.clear or application shutdown).
        """
        # Do NOT call self.cleanup() here to avoid premature deletion.
        pass
    
    def cleanup(self):
        """Clean up any temporary files created during the loading process."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug(f"Removed temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {str(e)}")
        self.temp_files = []
    
    def safe_load_excel(self, 
                        file_path: str, 
                        progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict:
        """
        Safely and efficiently loads an Excel file by converting it to a temporary CSV in chunks.
        This is the single, unified method for all Excel files. Returns a dictionary with results.
        """
        logger.info(f"Starting robust Excel loading for: {file_path}")
        try:
            result = self._load_excel_chunked(file_path, progress_callback)
            if not result['success']:
                logger.error(f"The unified Excel loading strategy failed. Reason: {result.get('error')}")
                if progress_callback:
                    progress_callback(100, "Failed to load Excel file.")
            return result
        except Exception as e:
            error_msg = f"An unexpected error occurred during Excel loading: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            if progress_callback:
                progress_callback(0, "A critical error occurred during loading.")
            return {'success': False, 'error': error_msg}

    def _load_excel_chunked(self, 
                           file_path: str, 
                           progress_callback: Optional[Callable]) -> Dict:
        """
        The definitive non-blocking method to load any Excel file (.xls or .xlsx) by chunking.
        Always uses an indeterminate progress bar to ensure UI responsiveness.
        """
        try:
            # --- Setup ---
            file_extension = os.path.splitext(file_path)[1].lower()
            engine = None
            if file_extension == '.xlsx':
                engine = 'openpyxl'
            elif file_extension == '.xls':
                engine = 'xlrd'
            else:
                error_msg = f"Unsupported file type: {file_extension}"
                logger.error(error_msg)
                if progress_callback:
                    progress_callback(0, error_msg)
                return {'success': False, 'error': error_msg}

            # --- Processing Rows (No Analysis Phase) ---
            if progress_callback:
                progress_callback(-1, "Starting conversion...")

            # Create temporary CSV file
            temp_csv = tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w', encoding='utf-8')
            temp_csv_path = temp_csv.name
            temp_csv.close()
            self.temp_files.append(temp_csv_path)
            
            # Manually chunk the Excel file using skiprows and nrows since chunksize is not supported.
            logger.info(f"Starting manual chunked conversion to CSV: {temp_csv_path} using engine: {engine}")
            
            preview_df = None
            processed_rows = 0
            chunk_size = 1000
            is_first_chunk = True

            # First, try to estimate total rows to provide better progress feedback.
            try:
                import openpyxl
                if file_extension == '.xlsx':
                    wb = openpyxl.load_workbook(file_path, read_only=True)
                    sheet = wb.active
                    total_rows = sheet.max_row
                    wb.close()
                    logger.info(f"Estimated total rows: {total_rows}")
                else:
                    total_rows = None  # We can't easily estimate for .xls without blocking.
            except Exception as e:
                logger.warning(f"Could not estimate total rows: {e}")
                total_rows = None

            with open(temp_csv_path, 'w', newline='', encoding='utf-8') as f:
                skip = 0
                while True:
                    # Read a small batch of rows.
                    chunk = pd.read_excel(file_path, engine=engine, skiprows=skip, nrows=chunk_size)
                    if len(chunk) == 0:
                        break
                        
                    if is_first_chunk:
                        preview_df = chunk.head(10).copy()
                        chunk.to_csv(f, index=False, header=True)
                        is_first_chunk = False
                    else:
                        chunk.to_csv(f, index=False, header=False)

                    processed_rows += len(chunk)
                    skip += len(chunk)

                    if progress_callback:
                        if total_rows:
                            progress_pct = min(99, int((processed_rows / total_rows) * 99))
                            progress_callback(-1, f"Processing... {processed_rows:,}/{total_rows:,} rows ({progress_pct}%)")
                        else:
                            progress_callback(-1, f"Processing... {processed_rows:,} rows loaded")

            logger.info(f"Chunked conversion successful, total rows: {processed_rows}")
            if progress_callback:
                progress_callback(100, "Load complete.")
            return {'success': True, 'preview_df': preview_df, 'temp_csv_path': temp_csv_path}
        
        except Exception as e:
            error_msg = f"The unified chunked loader failed: {e}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            if progress_callback:
                progress_callback(0, "Error during loading.")
            return {'success': False, 'error': error_msg}

# Singleton instance for easy import and use
excel_safeguard = ExcelSafeguard()
