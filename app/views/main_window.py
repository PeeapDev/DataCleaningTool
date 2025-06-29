"""
Simplified Main window implementation for Education Data Cleaning Tool.
"""

import os
import sys
import time
import logging
import threading
import platform
import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Qt5Agg')
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QTableView, 
    QComboBox, QProgressBar, QMessageBox, QTabWidget,
    QCheckBox, QSpinBox, QGroupBox, QFormLayout,
    QFrame, QStatusBar, QLineEdit, QDialog, QTextEdit,
    QProgressDialog, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThreadPool, QRunnable, QObject, pyqtSlot
from PyQt6.QtGui import QAction, QPixmap, QFont

from app.controllers.data_cleaner import DataCleaner
from app.models.data_model import PandasTableModel, CleaningOptions
from app.views.field_mapper_dialog import FieldMapperDialog
from app.views.run_quantize import run_field_mapping, apply_field_mapping

# Matplotlib for analytics tab
import matplotlib
matplotlib.use('Agg')  # Offscreen canvas for headless runs
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from app.utils.image_ocr import PhotoProcessor
from app.utils.excel_safeguard import ExcelSafeguard

# Set up logging
logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.
    Supported signals are:
    finished
        No data
    error
        `tuple` (exctype, value, traceback.format_exc())
    result
        `object` data returned from processing, anything
    progress
        `int` indicating % progress
    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int, str)


class Worker(QRunnable):
    '''
    Worker thread
    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.
    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress.emit

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

# Set up logging
logger = logging.getLogger(__name__)

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
        self.threadpool = QThreadPool()
        logger.info(f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads")
        
        # Setup the UI
        self.setup_ui()
        self.setup_menu()
        self.setup_statusbar()
        
    def setup_ui(self):
        """Set up the main UI components"""
        # ---------- Create tab widget ----------
        self.tabs = QTabWidget()

        # ---------- Data Tab (existing UI) ----------
        data_tab = QWidget()
        main_layout = QVBoxLayout(data_tab)
        
        # Top section - Import file
        top_layout = QHBoxLayout()
        
        # File selection
        self.file_label = QLabel("Input File:")
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Select a CSV file to import...")
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        
        self.quantize_btn = QPushButton("Quantize AI")
        self.quantize_btn.setToolTip("Automatically map fields using AI")
        self.quantize_btn.clicked.connect(self.run_field_mapping)
        self.quantize_btn.setEnabled(False)
        
        top_layout.addWidget(self.file_label)
        top_layout.addWidget(self.file_path_edit, 1)  # Stretch factor 1
        top_layout.addWidget(browse_btn)
        top_layout.addWidget(self.quantize_btn)
        
        main_layout.addLayout(top_layout)
        
        # Middle section - Preview table
        main_layout.addWidget(QLabel("<b>Data Preview</b>"))
        
        # Add search bar section
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search across all columns...")
        self.search_input.setClearButtonEnabled(True)  # Add clear (X) button in the search field
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_status_label = QLabel("")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)  # Give search box more space
        search_layout.addWidget(self.search_status_label)
        main_layout.addLayout(search_layout)
        
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

        self.photo_column_combo = QComboBox()
        config_layout.addRow("Photo Column (Optional):", self.photo_column_combo)
        
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
        
        self.process_data_btn = QPushButton("Process Data")
        self.process_data_btn.clicked.connect(self.process_data)
        self.process_data_btn.setEnabled(False)

        self.process_photos_check = QCheckBox("Process Student Photos")
        
        self.export_btn = QPushButton("Export Results")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_data)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        bottom_layout.addWidget(self.process_data_btn)
        bottom_layout.addWidget(self.export_btn)
        bottom_layout.addWidget(self.process_photos_check)
        bottom_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(bottom_layout)
        
        # Add tabs to tab widget
        self.tabs.addTab(data_tab, "Data")

        # ---------- Analytics Tab ----------
        analytics_tab = QWidget()
        analytics_layout = QVBoxLayout(analytics_tab)

        # Matplotlib canvas
        self.analytics_canvas = FigureCanvas(plt.Figure(figsize=(6,4)))
        analytics_layout.addWidget(self.analytics_canvas)
        self.tabs.addTab(analytics_tab, "Analytics")

        # Set central widget to tabs
        self.setCentralWidget(self.tabs)
    
    def setup_menu(self):
        """Set up the menu bar"""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        open_action = QAction("&Open Data File...", self)
        open_action.triggered.connect(self.browse_file)
        file_menu.addAction(open_action)
        
        # New action for OCR
        ocr_action = QAction("Process Student &Photo...", self)
        ocr_action.triggered.connect(self.browse_student_photo)
        file_menu.addAction(ocr_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("&Export Results...", self)
        export_action.triggered.connect(self.export_data)
        export_action.setEnabled(False)
        file_menu.addAction(export_action)
        self.export_action = export_action
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # OCR menu
        ocr_menu = self.menuBar().addMenu("&OCR Tools")
        process_photo_action = QAction("Process Student &Photos...", self)
        process_photo_action.triggered.connect(self.browse_student_photo)
        ocr_menu.addAction(process_photo_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # Add view logs action
        view_logs_action = QAction("View Current Log", self)
        view_logs_action.triggered.connect(self.show_logs)
        help_menu.addAction(view_logs_action)
    
    def setup_statusbar(self):
        """Set up the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def browse_file(self):
        """Open file dialog to select data file and load it in a background thread."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Data File", "", "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if not file_path:
            return

        self.file_path_edit.setText(file_path)
        self.process_data_btn.setEnabled(False)
        self.quantize_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.export_action.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Loading file...")

        # Use the correct method name: safe_load_excel
        safeguard = ExcelSafeguard()
        worker = Worker(safeguard.safe_load_excel, file_path)
        worker.signals.result.connect(self.on_load_complete)
        worker.signals.error.connect(self.on_load_error)
        worker.signals.progress.connect(self._update_status)
        self.threadpool.start(worker)

    def on_load_complete(self, result: dict):
        """Handles the successful completion of the file loading thread."""
        if result and result.get('success'):
            self.status_bar.showMessage("Data loaded successfully.", 5000)
            self.progress_bar.setValue(100)
            
            preview_df = result.get('preview_df')
            temp_csv_path = result.get('temp_csv_path')

            if preview_df is not None and temp_csv_path:
                # This is the non-blocking call to prepare the data cleaner
                load_success = self.data_cleaner.load_data(
                    temp_csv_path=temp_csv_path, 
                    columns=preview_df.columns.tolist()
                )
                
                if load_success:
                    self.preview_model.setData(preview_df)
                    self._update_analytics(preview_df)
                    self._update_column_selectors()
                    self._auto_select_columns(self.data_cleaner.get_columns())
                    
                    self.process_data_btn.setEnabled(True)
                    self.quantize_btn.setEnabled(True)
                    self.export_btn.setEnabled(False)
                else:
                    self.on_load_error(("Failed to prepare data for processing.", ""))
            else:
                self.on_load_error(("Load successful, but no data returned.", ""))
        else:
            error_message = result.get('error', 'An unknown error occurred during loading.')
            self.on_load_error((error_message, ""))

    def on_load_error(self, error_info):
        """Handles errors from the file loading thread."""
        error_message, traceback_info = error_info
        logger.error(f"File loading failed: {error_message}")
        self.progress_bar.setValue(0)
        self.status_bar.showMessage(f"Error: {error_message}", 5000)
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(f"An error occurred: {error_message}")
        msg.setInformativeText("Please check the logs for technical information.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        if traceback_info:
            msg.setDetailedText(str(traceback_info))
        msg.exec()

    def _update_column_selectors(self):
        """Update column selector dropdowns with current DataFrame columns"""
        columns = self.data_cleaner.get_columns()
        
        # Clear existing items
        self.name_combo.clear()
        self.dob_combo.clear()
        self.year_combo.clear()
        self.photo_column_combo.clear()
        
        # Add placeholder
        self.name_combo.addItem("-- Select Name Column --")
        self.dob_combo.addItem("-- Select Date of Birth Column --")
        self.year_combo.addItem("-- Select Academic Year Column --")
        self.photo_column_combo.addItem("-- Select Photo Column --")
        
        # Add columns
        for col in columns:
            self.name_combo.addItem(col)
            self.dob_combo.addItem(col)
            self.year_combo.addItem(col)
            self.photo_column_combo.addItem(col)

    def _auto_select_columns(self, columns):
        """Try to auto-select appropriate columns based on names"""
        columns_lower = [col.lower() for col in columns]
        
        # Try to find name column
        for i, col_lower in enumerate(columns_lower):
            if any(name_kw in col_lower for name_kw in ['name', 'student', 'pupil']):
                self.name_combo.setCurrentIndex(i + 1)  # +1 for placeholder
                break
        
        # Try to find DOB column
        for i, col_lower in enumerate(columns_lower):
            if any(dob_kw in col_lower for dob_kw in ['birth', 'dob', 'date']):
                self.dob_combo.setCurrentIndex(i + 1)
                break
        
        # Try to find academic year column
        for i, col_lower in enumerate(columns_lower):
            if any(year_kw in col_lower for year_kw in ['year', 'grade', 'class']):
                self.year_combo.setCurrentIndex(i + 1)
                break

        # Try to find photo column
        for i, col_lower in enumerate(columns_lower):
            if any(photo_kw in col_lower for photo_kw in ['photo', 'image', 'picture']):
                self.photo_column_combo.setCurrentIndex(i + 1)
                break
    
    def process_data(self):
        """Process data based on selected options in a background thread."""
        if self.process_photos_check.isChecked():
            self._process_student_photos()
        else:
            self._process_standard_data()

    def _process_student_photos(self):
        """Handle the photo processing workflow."""
        photo_col = self.photo_column_combo.currentText()
        if self.photo_column_combo.currentIndex() == 0:
            QMessageBox.warning(self, "Required Field", "Please select a Photo column for processing.")
            return

        data_file_path = self.file_path_edit.text()
        if not data_file_path or not os.path.exists(data_file_path):
            QMessageBox.warning(self, "File Not Found", "The specified data file could not be found.")
            return

        photo_folder_path = os.path.join(os.path.dirname(data_file_path), "student_photos")
        if not os.path.isdir(photo_folder_path):
            QMessageBox.warning(self, "Folder Not Found", 
                                f"The 'student_photos' subfolder could not be found in the directory of the data file.")
            return

        self.status_bar.showMessage("Processing student photos...")
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.process_data_btn.setEnabled(False)

        photo_processor = PhotoProcessor(photo_folder_path, self.data_cleaner.get_data(), photo_col)
        worker = Worker(photo_processor.find_duplicates)
        worker.signals.result.connect(self.on_photo_processing_complete)
        worker.signals.error.connect(self.on_processing_error)
        worker.signals.progress.connect(self._update_status)
        self.threadpool.start(worker)

    def _process_standard_data(self):
        """Handle the standard data cleaning workflow."""
        if self.name_combo.currentIndex() == 0:
            QMessageBox.warning(self, "Required Field", "Please select a Name column.")
            return

        self.options.name_column = self.name_combo.currentText()
        self.options.dob_column = self.dob_combo.currentText() if self.dob_combo.currentIndex() > 0 else None
        self.options.year_column = self.year_combo.currentText() if self.year_combo.currentIndex() > 0 else None
        self.options.fuzzy_match = self.fuzzy_check.isChecked()
        self.options.match_threshold = self.threshold_spin.value()

        self.status_bar.showMessage("Processing data...")
        self.progress_bar.setValue(0)
        self.process_data_btn.setEnabled(False)

        worker = Worker(self.data_cleaner.find_duplicates, self.options)
        worker.signals.result.connect(self.on_processing_complete)
        worker.signals.error.connect(self.on_processing_error)
        worker.signals.progress.connect(self._update_status)
        self.threadpool.start(worker)

    def on_processing_complete(self, result):
        """Handle completion of standard data processing."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.process_data_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.export_action.setEnabled(True)

        clean_count = result.get('clean_count', 0)
        duplicate_count = result.get('duplicate_count', 0)
        total_count = clean_count + duplicate_count

        self.status_bar.showMessage(f"Found {duplicate_count} duplicates out of {total_count} records.")
        QMessageBox.information(self, "Processing Complete",
                                f"Processing complete!\n\n"
                                f"Clean Records: {clean_count}\n"
                                f"Duplicate Records: {duplicate_count}\n\n"
                                f"Click 'Export Results' to save the clean data.")

    def on_photo_processing_complete(self, result):
        """Handle completion of photo processing."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.process_data_btn.setEnabled(True)

        num_duplicates = len(result)
        self.status_bar.showMessage(f"Photo processing complete. Found {num_duplicates} potential duplicate sets.")
        
        log_message = "Photo Duplicate Analysis Results:\n"
        if not result:
            log_message += "No duplicates found based on facial similarity."
        else:
            for i, duplicate_set in enumerate(result):
                log_message += f"\nSet {i+1}:\n"
                for student_info in duplicate_set:
                    log_message += f"  - Name: {student_info['name']}, File: {student_info['photo_file']}\n"
        
        logger.info(log_message)
        
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Photo Processing Complete")
        msg_box.setText(f"Found {num_duplicates} sets of potential duplicates based on facial similarity.")
        msg_box.setInformativeText("Check the logs for a detailed report.")
        msg_box.addButton(QMessageBox.StandardButton.Ok)
        view_log_button = msg_box.addButton("View Log", QMessageBox.ButtonRole.HelpRole)
        msg_box.exec()
        if msg_box.clickedButton() == view_log_button:
            self.show_logs()

    def on_processing_error(self, error_tuple):
        """Handle errors from any processing thread."""
        logger.error(f"Processing error: {error_tuple[1]}\n{error_tuple[2]}")
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("An error occurred during processing.")
        QMessageBox.critical(self, "Error", f"An error occurred: {error_tuple[1]}")
        self.process_data_btn.setEnabled(True)
    
    def export_data(self):
        """Export the clean and duplicate data to files and generate report"""
        # Check if we have data to export
        if self.data_cleaner.get_clean_count() == 0:
            QMessageBox.warning(self, "No Data", "There is no clean data to export")
            return
            
        # Ask for export directory
        export_dir = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", ""
        )
        
        if not export_dir:
            return
            
        # Generate timestamp for filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Define export paths
        clean_path = os.path.join(export_dir, f"clean_data_{timestamp}.csv")
        duplicate_path = os.path.join(export_dir, f"duplicate_data_{timestamp}.csv")
        report_path = os.path.join(export_dir, f"cleaning_report_{timestamp}.txt")
        
        # Update UI
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Exporting data...")
        
        try:
            # Export the data
            self.progress_bar.setValue(10)
            self.data_cleaner.export_clean_data(clean_path)
            
            self.progress_bar.setValue(40)
            self.data_cleaner.export_duplicate_data(duplicate_path)
            
            self.progress_bar.setValue(70)
            
            # Generate and save the report
            report_content = self._generate_report(clean_path, duplicate_path)
            
            with open(report_path, "w") as report_file:
                report_file.write(report_content)
                
            self.progress_bar.setValue(90)
            
            # Update UI
            self.progress_bar.setValue(100)
            self.status_bar.showMessage(f"Data exported to {export_dir}")
            
            # Show report dialog
            report_dialog = QDialog(self)
            report_dialog.setWindowTitle("Cleaning Report")
            report_dialog.resize(600, 500)
            
            layout = QVBoxLayout(report_dialog)
            
            # Report text
            report_text = QTextEdit()
            report_text.setReadOnly(True)
            report_text.setFont(QFont("Courier New", 10))
            report_text.setText(report_content)
            
            # Buttons
            buttons_layout = QHBoxLayout()
            open_report_btn = QPushButton("Open Report")
            open_clean_btn = QPushButton("Open Clean Data")
            open_duplicates_btn = QPushButton("Open Duplicates")
            close_btn = QPushButton("Close")
            
            buttons_layout.addWidget(open_report_btn)
            buttons_layout.addWidget(open_clean_btn)
            buttons_layout.addWidget(open_duplicates_btn)
            buttons_layout.addStretch(1)
            buttons_layout.addWidget(close_btn)
            
            layout.addWidget(report_text)
            layout.addLayout(buttons_layout)
            
            # Connect buttons
            def open_file(path):
                if platform.system() == 'Darwin':  # macOS
                    os.system(f'open "{path}"')
                elif platform.system() == 'Windows':  # Windows
                    os.system(f'start "" "{path}"')
                else:  # linux variants
                    os.system(f'xdg-open "{path}"')

            open_report_btn.clicked.connect(lambda: open_file(report_path))
            open_clean_btn.clicked.connect(lambda: open_file(clean_path))
            open_duplicates_btn.clicked.connect(lambda: open_file(duplicate_path))
            close_btn.clicked.connect(report_dialog.accept)

            report_dialog.exec()

        except Exception as e:
            self.progress_bar.setValue(0)
            self.status_bar.showMessage(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred during export: {str(e)}")

    def _generate_report(self, clean_path, duplicate_path):
        """Generate a detailed report of the data cleaning process"""
        stats = self.data_cleaner.get_summary_report()
        
        report = []
        report.append("===============================================")
        report.append("           EDUCATION DATA CLEANING REPORT           ")
        report.append("===============================================")
        report.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Input file information
        report.append("INPUT FILE INFORMATION")
        report.append("-----------------------")
        report.append(f"File Path: {stats.get('file_path', 'Unknown')}")
        report.append(f"File Type: {stats.get('file_type', 'Unknown').upper()}")
        report.append(f"Total Records: {stats.get('total_records', 0)}")
        report.append(f"Columns: {stats.get('columns', 0)}")
        report.append(f"Loaded At: {stats.get('loaded_at', '-')}")
        report.append("")
        
        # Cleaning configuration
        report.append("CLEANING CONFIGURATION")
        report.append("---------------------")
        report.append(f"Name Column: {self.options.name_column}")
        report.append(f"Date of Birth Column: {self.options.dob_column}")
        report.append(f"Academic Year Column: {self.options.year_column}")
        report.append(f"Fuzzy Matching: {'Enabled' if self.options.fuzzy_matching else 'Disabled'}")
        if self.options.fuzzy_matching:
            report.append(f"Fuzzy Threshold: {self.options.fuzzy_threshold}%")
        report.append("")
        
        # Results
        report.append("CLEANING RESULTS")
        report.append("---------------")
        report.append(f"Clean Records: {stats.get('clean_records', 0)} ({stats.get('clean_records', 0)/stats.get('total_records', 1)*100:.1f}%)")
        report.append(f"Duplicate Records: {stats.get('duplicate_records', 0)} ({stats.get('duplicate_records', 0)/stats.get('total_records', 1)*100:.1f}%)")
        report.append("")
        
        # Export information
        report.append("EXPORTED FILES")
        report.append("--------------")
        report.append(f"Clean Data: {clean_path}")
        report.append(f"Duplicate Data: {duplicate_path}")
        report.append("")
        
        report.append("===============================================")
        report.append("End of Report")
        
        return "\n".join(report)

    def show_about(self):
        """Show the about dialog"""
        QMessageBox.about(
            self, "About Education Data Cleaning Tool",
            "Education Data Cleaning Tool v0.2.0\n\n"
            "A tool for cleaning education data and processing student photos.\n\n"
            " 2025"
        )

    def browse_student_photo(self):
        """Open file dialog to select student photo for OCR processing"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Student Photo",
            "",
            "Image Files (*.jpg *.jpeg *.png);;All Files (*)"
        )
        
        if file_path:
            try:
                # Show progress dialog
                progress = QProgressDialog("Processing photo...", "Cancel", 0, 100, self)
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(0)
                progress.setValue(10)
                
                # Process in a separate thread to keep UI responsive
                self.ocr_thread = threading.Thread(
                    target=self.process_student_photo,
                    args=(file_path, progress)
                )
                self.ocr_thread.daemon = True
                self.ocr_thread.start()
                
                # Create a timer to check status
                self.ocr_timer = QTimer()
                self.ocr_timer.timeout.connect(
                    lambda: self.check_ocr_status(progress)
                )
                self.ocr_timer.start(100)  # Check every 100ms
                
            except Exception as e:
                logging.error(f"Error setting up OCR processing: {str(e)}")
                QMessageBox.critical(self, "Error", f"Error setting up OCR processing: {str(e)}")

    def process_student_photo(self, file_path, progress=None):
        """Process the student photo with OCR to extract information"""
        try:
            # Import OCR utility here to avoid circular imports
            from app.utils.image_ocr import process_student_image
            
            # Update progress
            if progress:
                progress.setValue(30)
            
            # Process the image
            result = process_student_image(file_path)
            
            # Update progress
            if progress:
                progress.setValue(70)
            
            # Store the results for displaying after thread completes
            self.ocr_results = {
                'file_path': file_path,
                'student_id': result.get('student_id', 'Not detected'),
                'name': result.get('name', 'Not detected'),
                'dob': result.get('date_of_birth', 'Not detected'),
                'success': True,
                'face_detected': result.get('face_detected', False),
                'face_count': result.get('face_count', 0),
                'face_locations': result.get('face_locations', []),
                'has_face_encoding': result.get('has_face_encoding', False),
                'face_detection_error': result.get('face_detection_error', None)
            }
            
        except Exception as e:
            logging.error(f"OCR processing error: {str(e)}")
            self.ocr_results = {
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
            
        finally:
            # Update progress to complete
            if progress and progress.value() < 100:
                progress.setValue(100)

    def check_ocr_status(self, progress):
        """Check if OCR processing is complete and show results"""
        if not self.ocr_thread.is_alive():
            # Stop the timer
            self.ocr_timer.stop()
            
            # Close progress dialog
            progress.setValue(100)
            
            # Show results
            if hasattr(self, 'ocr_results'):
                if self.ocr_results['success']:
                    # Create dialog with results
                    dialog = QDialog(self)
                    dialog.setWindowTitle("Student Photo OCR Results")
                    dialog.resize(500, 500)
                    
                    # Layout
                    layout = QVBoxLayout(dialog)
                    
                    # Results
                    layout.addWidget(QLabel("<h3>Extracted Student Information</h3>"))
                    layout.addWidget(QLabel(f"<b>File:</b> {os.path.basename(self.ocr_results['file_path'])}"))
                    layout.addWidget(QLabel(f"<b>Student ID:</b> {self.ocr_results['student_id']}"))
                    layout.addWidget(QLabel(f"<b>Name:</b> {self.ocr_results['name']}"))
                    layout.addWidget(QLabel(f"<b>Date of Birth:</b> {self.ocr_results['dob']}"))
                    
                    # Add a note about accuracy
                    layout.addWidget(QLabel("<i>Note: OCR results may require verification</i>"))
                    
                    # Add face detection results if available
                    layout.addWidget(QLabel("<h3>Face Detection Results</h3>"))
                    
                    # Create horizontal layout for image preview and face info
                    h_layout = QHBoxLayout()
                    
                    # Add image preview
                    try:
                        pixmap = QPixmap(self.ocr_results['file_path'])
                        if not pixmap.isNull():
                            # Scale to a reasonable size
                            pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
                            image_label = QLabel()
                            image_label.setPixmap(pixmap)
                            image_label.setFixedSize(200, 200)
                            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            image_label.setScaledContents(True)
                            h_layout.addWidget(image_label)
                    except Exception as e:
                        logger.error(f"Error displaying image: {e}")
                    
                    # Add face detection information
                    face_info = QVBoxLayout()
                    face_detected = self.ocr_results.get('face_detected', False)
                    face_count = self.ocr_results.get('face_count', 0)
                    
                    if face_detected:
                        face_info.addWidget(QLabel(f"<b>Face Detected:</b> <span style='color:green'>Yes</span>"))
                        face_info.addWidget(QLabel(f"<b>Number of Faces:</b> {face_count}"))
                        
                        # Add more details if available
                        if 'face_locations' in self.ocr_results and self.ocr_results['face_locations']:
                            locations_text = ", ".join([f"({t},{r},{b},{l})" for t, r, b, l in self.ocr_results['face_locations'][:3]])
                            face_info.addWidget(QLabel(f"<b>Face Locations:</b> {locations_text}"))
                            
                        if 'has_face_encoding' in self.ocr_results:
                            has_encoding = "Yes" if self.ocr_results['has_face_encoding'] else "No"
                            face_info.addWidget(QLabel(f"<b>Face Encoding:</b> {has_encoding}"))
                    else:
                        face_info.addWidget(QLabel(f"<b>Face Detected:</b> <span style='color:red'>No</span>"))
                        if 'face_detection_error' in self.ocr_results:
                            face_info.addWidget(QLabel(f"<b>Error:</b> {self.ocr_results['face_detection_error']}"))
                    
                    h_layout.addLayout(face_info)
                    layout.addLayout(h_layout)
                    
                    # Add spacer
                    layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
                    
                    # Add buttons
                    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
                    button_box.accepted.connect(dialog.accept)
                    layout.addWidget(button_box)
                    
                    # Show dialog
                    dialog.exec()
                else:
                    QMessageBox.warning(
                        self,
                        "OCR Error",
                        f"Failed to extract information from the photo:\n{self.ocr_results.get('error', 'Unknown error')}"
                    )
                    
            QMessageBox.critical(self, "Error", f"Could not open the log file: {e}")

    def _update_analytics(self, df):
        """Render basic analytics charts in the Analytics tab."""
        try:
            # Clear the figure and create new subplots
            fig = self.analytics_canvas.figure
            fig.clear()
            
            # Create 2x2 grid of plots for better analytics
            axs = fig.subplots(2, 2)
            
            # Plot 1: Column counts (non-null values)
            ax1 = axs[0, 0]
            df.count().plot(kind='bar', color='#3182ce', ax=ax1)
            ax1.set_title('Non-null values per column')
            ax1.set_ylabel('Count')
            ax1.tick_params(axis='x', labelrotation=45, labelsize=8)
            
            # Plot 2: Data types
            ax2 = axs[0, 1]
            dtypes = df.dtypes.value_counts().reset_index()
            dtypes.columns = ['Data Type', 'Count']
            dtypes.plot(kind='pie', y='Count', labels=dtypes['Data Type'], ax=ax2, autopct='%1.1f%%')
            ax2.set_title('Data Types Distribution')
            ax2.set_ylabel('')
            
            # Plot 3: Missing values
            ax3 = axs[1, 0]
            missing = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
            missing = missing[missing > 0]
            if not missing.empty:
                missing.plot(kind='bar', color='#e53e3e', ax=ax3)
                ax3.set_title('Missing Values (%)')
                ax3.set_ylabel('Percent Missing')
                ax3.tick_params(axis='x', labelrotation=45, labelsize=8)
            else:
                ax3.text(0.5, 0.5, 'No Missing Values!', ha='center', va='center', fontsize=12)
                ax3.set_title('Missing Values Analysis')
                
            # Plot 4: Row counts by a category (if categorical column exists)
            ax4 = axs[1, 1]
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns
            if len(categorical_cols) > 0:
                # Pick first categorical column with manageable unique values
                for col in categorical_cols:
                    if df[col].nunique() <= 10:
                        df[col].value_counts().plot(kind='barh', ax=ax4, color='#805ad5')
                        ax4.set_title(f'Counts by {col}')
                        break
                else:
                    ax4.text(0.5, 0.5, 'No suitable categorical column\nfor visualization', 
                             ha='center', va='center', fontsize=10)
                    ax4.set_title('Category Analysis')
            else:
                ax4.text(0.5, 0.5, 'No categorical columns found', ha='center', va='center', fontsize=10)
                ax4.set_title('Category Analysis')
                
            # Apply tight layout to figure (not canvas)
            fig.tight_layout()
            self.analytics_canvas.draw()
        except Exception as e:
            logger.error(f"Analytics rendering error: {e}")

    def _update_status(self, percent, message):
        """Slot to safely update the progress bar and status message."""
        self.status_bar.showMessage(message)
        if percent < 0:
            # Indeterminate mode (analyzing file)
            if self.progress_bar.maximum() != 0:
                self.progress_bar.setRange(0, 0)
        else:
            # Determinate mode (processing rows)
            if self.progress_bar.maximum() == 0:
                self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)

    # Add Quantize AI Methods
    run_field_mapping = run_field_mapping
    apply_field_mapping = apply_field_mapping
    
    def on_search_changed(self, text):
        """Handle search text changes and filter the data preview."""
        try:
            # Apply search filter to the model
            self.preview_model.search(text)
            
            # Update status label with current row count information
            status_text = self.preview_model.get_row_count_status()
            self.search_status_label.setText(status_text)
            
            # Set status label color based on whether filtering is active
            if text.strip():
                self.search_status_label.setStyleSheet("color: blue;")
            else:
                self.search_status_label.setStyleSheet("")
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            self.status_bar.showMessage(f"Search error: {str(e)}", 3000)
            
    def show_logs(self):
        """Find and open the most recent log file."""
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
        if os.path.exists(logs_dir):
            log_files = [os.path.join(logs_dir, f) for f in os.listdir(logs_dir) 
                      if f.startswith("app_") and f.endswith(".log")]
            if log_files:
                latest_log = max(log_files, key=os.path.getctime)
                
                try:
                    if platform.system() == "Windows":
                        os.startfile(latest_log)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", latest_log], check=True)
                    else:  # Linux
                        subprocess.run(["xdg-open", latest_log], check=True)
                except Exception as e:
                    logger.error(f"Failed to open log file: {e}")
                    QMessageBox.critical(self, "Error", f"Could not open the log file: {e}")
            else:
                QMessageBox.information(self, "No Logs", "No log files found.")
        else:
            QMessageBox.information(self, "No Logs Directory", "Logs directory not found.")