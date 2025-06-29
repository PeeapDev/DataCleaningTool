"""
Quantize AI interface for the Education Data Cleaning Tool
"""
import pandas as pd
import logging

from PyQt6.QtWidgets import QMessageBox
from app.views.field_mapper_dialog import FieldMapperDialog

logger = logging.getLogger(__name__)

def run_field_mapping(self):
    """
    Launch the Quantize AI field mapping dialog
    This method should be added to the MainWindow class
    """
    try:
        if not hasattr(self, 'data') or self.data is None:
            QMessageBox.warning(self, "No Data", "Please load data first.")
            return
        
        # Create and show the field mapper dialog
        mapper_dialog = FieldMapperDialog(self.data, self)
        mapper_dialog.mapping_confirmed.connect(self.apply_field_mapping)
        mapper_dialog.exec()
        
    except Exception as e:
        logger.error(f"Error in field mapping: {str(e)}")
        self.status_bar.showMessage(f"Error in field mapping: {str(e)}")
        QMessageBox.critical(self, "Error", f"An error occurred during field mapping: {str(e)}")

def apply_field_mapping(self, field_mapping):
    """
    Apply the field mapping to the loaded data
    This method should be added to the MainWindow class
    
    Args:
        field_mapping: Dictionary mapping original columns to standard fields
    """
    try:
        if not field_mapping:
            return
            
        # Create a copy of the DataFrame with mapped columns
        mapped_data = pd.DataFrame()
        
        for orig_col, std_field in field_mapping.items():
            mapped_data[std_field] = self.data[orig_col]
        
        # Add any unmapped columns as-is
        for col in self.data.columns:
            if col not in field_mapping and col not in mapped_data:
                mapped_data[col] = self.data[col]
        
        # Replace the original data with the mapped data
        self.data = mapped_data
        
        # Update the model
        self.preview_model.setDataFrame(self.data)
        
        # Update column selectors
        self._update_column_selectors()
        
        # Auto-select columns based on standard names
        self._auto_select_columns(self.data.columns)
        
        # Enable processing
        self.process_btn.setEnabled(True)
        
        # Show success message
        self.status_bar.showMessage(f"Successfully mapped {len(field_mapping)} fields.")
        
    except Exception as e:
        logger.error(f"Error applying field mapping: {str(e)}")
        self.status_bar.showMessage(f"Error applying field mapping: {str(e)}")
        QMessageBox.critical(self, "Error", f"An error occurred applying field mapping: {str(e)}")
