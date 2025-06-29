"""
Simplified Main window implementation for Education Data Cleaning Tool.
"""

import os
import sys
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QTableView, 
    QComboBox, QProgressBar, QMessageBox, QTabWidget,
    QCheckBox, QSpinBox, QGroupBox, QFormLayout,
    QFrame, QStatusBar, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction

from app.controllers.data_cleaner import DataCleaner
from app.models.data_model import PandasTableModel, CleaningOptions


class MainWindow(QMainWindow):
    """Main application window for the Education Data Cleaning Tool"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Education Data Cleaning Tool")
        self.resize(1000, 700)
        
        # Initialize components
        self.data_cleaner = DataCleaner()
        self.options = CleaningOptions()
        self.preview_model = PandasTableModel()
        
        # Setup the UI
        self.setup_ui()
        self.setup_menu()
        self.setup_statusbar()
        
    def setup_ui(self):
        """Set up the main UI components"""
        # Central widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Top section - Import file
        top_layout = QHBoxLayout()
        
        # File selection
        self.file_label = QLabel("Input File:")
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Select a CSV file to import...")
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        
        top_layout.addWidget(self.file_label)
        top_layout.addWidget(self.file_path_edit, 1)  # Stretch factor 1
        top_layout.addWidget(browse_btn)
        
        main_layout.addLayout(top_layout)
        
        # Middle section - Preview table
        main_layout.addWidget(QLabel("<b>Data Preview</b>"))
        
        self.preview_table = QTableView()
        self.preview_table.setModel(self.preview_model)
        main_layout.addWidget(self.preview_table)
        
        # Configure section
        config_group = QGroupBox("Configure Cleaning")
        config_layout = QFormLayout(config_group)
        
        # Column selection
        self.name_combo = QComboBox()
        self.dob_combo = QComboBox()
        self.year_combo = QComboBox()
        
        config_layout.addRow("Name Column:", self.name_combo)
        config_layout.addRow("Date of Birth Column:", self.dob_combo)
        config_layout.addRow("Academic Year Column:", self.year_combo)
        
        # Fuzzy matching
        self.fuzzy_check = QCheckBox("Enable fuzzy name matching")
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(50, 100)
        self.threshold_spin.setValue(90)
        self.threshold_spin.setSuffix("%")
        self.threshold_spin.setEnabled(False)
        
        config_layout.addRow("", self.fuzzy_check)
        config_layout.addRow("Match Threshold:", self.threshold_spin)
        
        # Connect the checkbox to enable/disable threshold
        self.fuzzy_check.toggled.connect(self.threshold_spin.setEnabled)
        
        main_layout.addWidget(config_group)
        
        # Bottom section - Process button and progress
        bottom_layout = QHBoxLayout()
        
        self.process_btn = QPushButton("Process Data")
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.process_data)
        
        self.export_btn = QPushButton("Export Results")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_data)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        bottom_layout.addWidget(self.process_btn)
        bottom_layout.addWidget(self.export_btn)
        bottom_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(bottom_layout)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
    def setup_menu(self):
        """Set up the menu bar"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        open_action = QAction("&Open CSV...", self)
        open_action.triggered.connect(self.browse_file)
        file_menu.addAction(open_action)
        
        export_action = QAction("&Export Results...", self)
        export_action.triggered.connect(self.export_data)
        export_action.setEnabled(False)
        self.export_action = export_action
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_statusbar(self):
        """Set up the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def browse_file(self):
        """Open file dialog to browse for CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self.options.input_file = file_path
            self.status_bar.showMessage(f"Loading file: {file_path}")
            
            # Load and preview data
            preview_data = self.data_cleaner.load_data(file_path)
            if preview_data is not None:
                self.preview_model.setData(preview_data)
                
                # Update column selection combos
                columns = preview_data.columns.tolist()
                for combo in [self.name_combo, self.dob_combo, self.year_combo]:
                    combo.clear()
                    combo.addItems(columns)
                
                # Try to auto-select columns
                self._auto_select_columns(columns)
                
                self.process_btn.setEnabled(True)
                self.status_bar.showMessage(f"Loaded {len(preview_data)} rows for preview")
            else:
                QMessageBox.critical(self, "Error", f"Failed to load file: {file_path}")
                self.status_bar.showMessage("Failed to load file")
    
    def _auto_select_columns(self, columns):
        """Try to auto-select appropriate columns based on names"""
        # For name column
        for i, col in enumerate(columns):
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["name", "student", "person"]):
                self.name_combo.setCurrentIndex(i)
                break
        
        # For date of birth
        for i, col in enumerate(columns):
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["birth", "dob", "date"]):
                self.dob_combo.setCurrentIndex(i)
                break
        
        # For academic year
        for i, col in enumerate(columns):
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["year", "academic", "session"]):
                self.year_combo.setCurrentIndex(i)
                break
                
    def process_data(self):
        """Process the data to find duplicates"""
        # Update options from UI
        self.options.name_column = self.name_combo.currentText()
        self.options.dob_column = self.dob_combo.currentText()
        self.options.year_column = self.year_combo.currentText()
        self.options.fuzzy_matching = self.fuzzy_check.isChecked()
        self.options.fuzzy_threshold = self.threshold_spin.value()
        
        # Validate selections
        if not all([self.options.name_column, self.options.dob_column, self.options.year_column]):
            QMessageBox.warning(self, "Missing Selection", 
                                "Please select columns for name, date of birth, and academic year.")
            return
            
        # Process the data
        self.status_bar.showMessage("Processing data...")
        self.progress_bar.setValue(10)
        
        try:
            # For simplicity in this demo, we'll process directly
            # In a real app, this should be in a background thread
            result = self.data_cleaner.identify_duplicates(
                self.options.name_column,
                self.options.dob_column,
                self.options.year_column,
                self.options.fuzzy_matching,
                self.options.fuzzy_threshold
            )
            
            if result:
                self.progress_bar.setValue(100)
                self.status_bar.showMessage(f"Found {result['duplicate_records']} duplicates")
                
                # Enable export
                self.export_btn.setEnabled(True)
                self.export_action.setEnabled(True)
                
                # Show a summary
                summary = (
                    f"Total records: {result['total_records']}\n"
                    f"Clean records: {result['clean_records']} "
                    f"({result['clean_records']/result['total_records']*100:.1f}%)\n"
                    f"Duplicate records: {result['duplicate_records']} "
                    f"({result['duplicate_records']/result['total_records']*100:.1f}%)\n"
                )
                
                QMessageBox.information(self, "Processing Complete", summary)
            else:
                self.progress_bar.setValue(0)
                self.status_bar.showMessage("Processing failed")
                QMessageBox.critical(self, "Error", "Failed to process data.")
                
        except Exception as e:
            self.progress_bar.setValue(0)
            self.status_bar.showMessage(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            
    def export_data(self):
        """Export the clean and duplicate data to CSV files"""
        if not (self.data_cleaner.clean_data is not None and self.data_cleaner.duplicate_data is not None):
            QMessageBox.warning(self, "No Data", "No processed data to export.")
            return
            
        # Get base output path
        output_dir = os.path.dirname(self.options.input_file)
        base_name = os.path.splitext(os.path.basename(self.options.input_file))[0]
        
        clean_path, _ = QFileDialog.getSaveFileName(
            self, "Save Clean Data", 
            os.path.join(output_dir, f"{base_name}_clean.csv"),
            "CSV Files (*.csv)"
        )
        
        if not clean_path:
            return
            
        # Generate duplicate path based on clean path
        duplicate_path = clean_path.replace("_clean.csv", "_duplicates.csv")
        if clean_path == duplicate_path:
            duplicate_path = os.path.splitext(clean_path)[0] + "_duplicates.csv"
        
        self.status_bar.showMessage("Exporting data...")
        
        try:
            result = self.data_cleaner.export_data(clean_path, duplicate_path)
            
            if result:
                self.status_bar.showMessage(f"Data exported successfully: {os.path.basename(clean_path)}")
                QMessageBox.information(
                    self, "Export Complete",
                    f"Clean data ({result['clean_records']} records) exported to:\n{clean_path}\n\n"
                    f"Duplicate data ({result['duplicate_records']} records) exported to:\n{duplicate_path}"
                )
            else:
                self.status_bar.showMessage("Export failed")
                QMessageBox.critical(self, "Error", "Failed to export data.")
                
        except Exception as e:
            self.status_bar.showMessage(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred during export: {str(e)}")
    
    def show_about(self):
        """Show the about dialog"""
        QMessageBox.about(
            self, "About Education Data Cleaning Tool",
            "Education Data Cleaning Tool v0.1.0\n\n"
            "A tool for detecting and removing duplicate student records "
            "from education datasets.\n\n"
            "© 2025"
        )
