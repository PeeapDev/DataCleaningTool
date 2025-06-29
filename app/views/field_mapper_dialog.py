"""
Field Mapper Dialog for Quantize AI feature
Allows users to review and adjust AI-suggested field mappings
"""

import os
import sys
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView,
    QMessageBox, QProgressBar, QFrame, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from app.utils.field_mapper import QuantizeAI

logger = logging.getLogger(__name__)

class FieldMapperDialog(QDialog):
    """Dialog for mapping Excel/CSV fields to standard fields with AI assistance"""
    
    mapping_confirmed = pyqtSignal(dict)  # Signal emitted with confirmed mapping
    
    def __init__(self, dataframe, parent=None):
        """
        Initialize the field mapper dialog
        
        Args:
            dataframe: Pandas DataFrame to analyze and map
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Quantize AI - Field Mapping")
        self.setMinimumSize(800, 600)
        
        self.dataframe = dataframe
        self.quantize_ai = QuantizeAI()
        self.field_mapping = {}  # Will hold {original_col: standard_field}
        self.standard_fields = list(self.quantize_ai.standard_fields.values())
        
        # Set up UI
        self.init_ui()
        
        # Run the AI mapping after a short delay (allows UI to show first)
        QTimer.singleShot(100, self.run_ai_mapping)
    
    def init_ui(self):
        """Set up the dialog UI components"""
        layout = QVBoxLayout()
        
        # Header with description
        header_label = QLabel("<h2>Quantize AI Field Mapper</h2>")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        description = QLabel(
            "This tool automatically detects fields in your data file and maps them "
            "to standard fields. Review the suggestions below and make adjustments if needed."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Progress bar for AI analysis
        self.progress_label = QLabel("Analyzing data fields...")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Table for field mapping
        self.mapping_table = QTableWidget(0, 3)
        self.mapping_table.setHorizontalHeaderLabels(["Original Field", "Sample Data", "Map To (Standard Field)"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.mapping_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.mapping_table)
        
        # Preview section
        preview_label = QLabel("<h3>Data Preview (After Mapping)</h3>")
        layout.addWidget(preview_label)
        
        self.preview_table = QTableWidget(0, 0)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.preview_table)
        
        # Buttons row
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.apply_button = QPushButton("Apply Mapping")
        self.apply_button.clicked.connect(self.apply_mapping)
        self.apply_button.setEnabled(False)  # Disabled until mapping is complete
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def run_ai_mapping(self):
        """Run the AI mapping and populate the UI with results"""
        try:
            # Get AI field mapping
            self.field_mapping = self.quantize_ai.map_fields(self.dataframe)
            
            # Display in table
            self.populate_mapping_table()
            
            # Update UI
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.progress_label.setText(f"Analysis complete! {len(self.field_mapping)} fields mapped.")
            self.apply_button.setEnabled(True)
            
            # Update preview table
            self.update_preview()
            
        except Exception as e:
            logger.error(f"Error in AI field mapping: {str(e)}")
            self.progress_label.setText(f"Error in analysis: {str(e)}")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
    
    def populate_mapping_table(self):
        """Populate the mapping table with columns and their suggested mappings"""
        self.mapping_table.setRowCount(len(self.dataframe.columns))
        
        for row, column in enumerate(self.dataframe.columns):
            # Original field name
            self.mapping_table.setItem(row, 0, QTableWidgetItem(column))
            
            # Sample data (first non-null value)
            sample_value = ""
            for value in self.dataframe[column].dropna():
                sample_value = str(value)
                if sample_value.strip():
                    break
            self.mapping_table.setItem(row, 1, QTableWidgetItem(sample_value[:50]))
            
            # Mapped field dropdown
            field_dropdown = QComboBox()
            field_dropdown.addItem("-- Skip Field --")
            
            for field in self.standard_fields:
                field_dropdown.addItem(field)
            
            # Set selected field based on AI mapping
            mapped_field = self.field_mapping.get(column)
            if mapped_field:
                index = field_dropdown.findText(mapped_field)
                field_dropdown.setCurrentIndex(index if index != -1 else 0)
            
            field_dropdown.currentTextChanged.connect(
                lambda text, col=column: self.update_field_mapping(col, text)
            )
            self.mapping_table.setCellWidget(row, 2, field_dropdown)
    
    def update_field_mapping(self, column, mapped_field):
        """
        Update the field mapping when user changes a selection
        
        Args:
            column: Original column name
            mapped_field: New standard field to map to
        """
        if mapped_field == "-- Skip Field --":
            if column in self.field_mapping:
                del self.field_mapping[column]
        else:
            self.field_mapping[column] = mapped_field
        
        self.update_preview()
    
    def update_preview(self):
        """Update the preview table with transformed data"""
        # Get mapped subset of data (first 5 rows)
        preview_data = self.dataframe.head(5).copy()
        
        # Set up preview table
        mapped_cols = [self.field_mapping.get(col, col) for col in preview_data.columns]
        self.preview_table.setRowCount(min(5, len(preview_data)))
        self.preview_table.setColumnCount(len(mapped_cols))
        self.preview_table.setHorizontalHeaderLabels(mapped_cols)
        
        # Fill data
        for row in range(min(5, len(preview_data))):
            for col, orig_col in enumerate(preview_data.columns):
                value = str(preview_data.iloc[row, col])
                self.preview_table.setItem(row, col, QTableWidgetItem(value))
    
    def apply_mapping(self):
        """Apply the field mapping and emit the completed mapping dict"""
        if not self.field_mapping:
            QMessageBox.warning(
                self,
                "No Mapping Selected",
                "No fields have been mapped. Please select at least one field mapping."
            )
            return
        
        # Emit the mapping signal
        self.mapping_confirmed.emit(self.field_mapping)
        
        # Close the dialog
        self.accept()
        
        # Return the mapping dictionary
        return self.field_mapping
