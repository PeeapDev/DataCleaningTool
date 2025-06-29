#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for the Education Data Cleaning Tool.
"""

import sys
import os
import logging
import argparse
import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox, QStyleFactory
from PyQt6.QtGui import QIcon

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.views.main_window import MainWindow
from app.utils.config import Config
from app.utils.data_generator import generate_education_data

# Configure logging with file output
log_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_directory, exist_ok=True)

log_file = os.path.join(log_directory, f"app_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Create a file handler for logging
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)  # Set to DEBUG to capture all information

# Create a console handler for terminal output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter and set it for both handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)  # Set to capture all levels
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
logger.info(f"Starting application. Log file: {log_file}")


def exception_hook(exctype, value, traceback_obj):
    """Global exception hook to log unhandled exceptions"""
    logger.critical("Unhandled exception:", exc_info=(exctype, value, traceback_obj))
    # Write to emergency file for crashes
    try:
        dump_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'crash_dumps')
        os.makedirs(dump_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        dump_file = os.path.join(dump_dir, f"crash_dump_{timestamp}.log")
        
        with open(dump_file, 'w') as f:
            f.write(f"=== APPLICATION CRASH REPORT ===\n")
            f.write(f"Time: {datetime.datetime.now()}\n")
            f.write(f"Exception type: {exctype}\n")
            f.write(f"Exception value: {value}\n\n")
            import traceback as tb
            f.write(f"=== TRACEBACK ===\n")
            tb.print_exception(exctype, value, traceback_obj, file=f)
            
        logger.info(f"Crash dump written to {dump_file}")
    except Exception as e:
        logger.error(f"Failed to write crash dump: {str(e)}")
    
    # Display a user-friendly error message if possible
    try:
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText("The application has encountered a critical error and needs to close.")
        msg.setInformativeText(f"Error: {str(value)}")
        msg.setWindowTitle("Application Error")
        msg.setDetailedText(f"Please check the log files in the 'logs' directory for more information.\nA crash report has been saved to the 'crash_dumps' directory.")
        msg.exec()
    except:
        pass
        
    # Call the original exception handler
    sys.__excepthook__(exctype, value, traceback_obj)

def create_directories():
    """Create necessary directories"""
    dirs = ['resources', 'reports', 'exports']
    
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Education Data Cleaning Tool - Student Records Deduplication")
        
    # Add command line arguments
    parser.add_argument(
        "--generate-data", 
        action="store_true", 
        help="Generate sample data"
    )
    parser.add_argument(
        "--records", 
        type=int,
        default=1000,
        help="Number of records to generate"
    )
    parser.add_argument(
        "--duplicate-rate",
        type=float,
        default=0.15,
        help="Rate of duplicates to include in generated data (0.0 to 1.0)"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "excel"],
        default="csv",
        help="Output format for generated data (csv or excel)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for generated data"
    )
    # Native-first approach - no online options by default
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Run in debug mode with additional logging"
    )
    
    return parser.parse_args()

def main():
    """Main application entry point"""
    # Install global exception handler
    sys.excepthook = exception_hook
    logger.info("Global exception handler installed")
    
    # Start memory monitoring if available
    try:
        from app.utils.memory_monitor import memory_monitor
        memory_monitor.start_monitoring()
        logger.info("Memory monitoring started")
    except ImportError:
        logger.warning("Memory monitoring not available")
    
    args = parse_arguments()
    
    # Create necessary directories
    create_directories()
    
    # Check if we need to generate sample data
    if args.generate_data:
        # Generate sample data and exit
        extension = ".xlsx" if args.format == "excel" else ".csv"
        
        # Use provided output or default
        output_path = args.output
        if output_path is None:
            output_path = os.path.join('resources', f'sample_data{extension}')
        
        # Generate data
        generate_education_data(
            output_path,
            num_records=args.records,
            duplicate_rate=args.duplicate_rate,
            format=args.format
        )
        
        logger.info(f"Generated {args.format.upper()} data with {args.records} records")
        logger.info(f"Output saved to: {output_path}")
        return
    
    # Initialize configuration
    config = Config()
    
    # Create application
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setApplicationName("Education Data Cleaning Tool")
    
    # Set application icon if available
    icon_path = os.path.join('resources', 'icon.svg')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Set stylesheet for modern look
    app.setStyleSheet("""
    QMainWindow, QDialog {
        background-color: #f5f5f5;
    }
    QPushButton {
        background-color: #2c5282;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #3182ce;
    }
    QPushButton:disabled {
        background-color: #a0aec0;
    }
    QProgressBar {
        border: 1px solid #cbd5e0;
        border-radius: 4px;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #4299e1;
        width: 10px;
    }
    """)
    
    # Create and show main window
    window = MainWindow()
    window.setWindowTitle("Education Data Cleaning Tool | Native Edition")
    
    # Display startup message about native capabilities
    QMessageBox.information(
        window, 
        "Native Application", 
        "Running in native mode with full offline capabilities.\n\n" 
        "All data processing happens locally on your machine."
    )
    
    window.show()
    
    # Run application event loop
    exit_code = app.exec()
    
    # Cleanup before exit
    try:
        from app.utils.memory_monitor import memory_monitor
        memory_monitor.stop_monitoring()
        logger.info("Memory monitoring stopped")
    except Exception as e:
        logger.warning(f"Error stopping memory monitor: {str(e)}")
        
    logger.info("Application shutting down")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
