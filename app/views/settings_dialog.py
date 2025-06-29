"""
Settings dialog for the Education Data Cleaning Tool.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QCheckBox, QSpinBox, QTabWidget,
    QPushButton, QGroupBox, QMessageBox, QComboBox,
    QFileDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.utils.config import Config
from app.utils.api_connector import ApiConfig, ApiConnector, MockEducationDataApi


class SettingsDialog(QDialog):
    """Settings dialog for configuring application preferences"""
    
    # Signal emitted when settings are saved
    settings_saved = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the settings dialog"""
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        
        # Load configuration
        self.config = Config()
        
        # Setup UI
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Set up the dialog UI"""
        main_layout = QVBoxLayout(self)
        
        # Create tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        # Export directory
        self.export_dir_edit = QLineEdit()
        self.export_dir_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_export_dir)
        
        export_layout = QHBoxLayout()
        export_layout.addWidget(self.export_dir_edit, 1)
        export_layout.addWidget(browse_btn)
        
        # Auto export option
        self.auto_export_check = QCheckBox("Auto export results")
        
        # Chunk size for large files
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(1000, 1000000)
        self.chunk_size_spin.setSingleStep(5000)
        self.chunk_size_spin.setValue(50000)
        self.chunk_size_spin.setSuffix(" records")
        
        # Add widgets to general layout
        general_layout.addRow("Default Export Directory:", export_layout)
        general_layout.addRow("", self.auto_export_check)
        general_layout.addRow("Chunk Size for Large Files:", self.chunk_size_spin)
        
        # API tab (Future Capability)
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        
        # Add notice about future capability
        future_notice = QLabel("<b>Note:</b> API integration is a future capability that will enable advanced features. "  
                               "This tool currently operates as a native application with full offline capabilities.")
        future_notice.setWordWrap(True)
        future_notice.setStyleSheet("background-color: #e2e8f0; padding: 10px; border-radius: 4px;")
        api_layout.addWidget(future_notice)
        
        # API settings group
        api_group = QGroupBox("API Configuration (Future Use)")
        api_form = QFormLayout(api_group)
        
        # API URL
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setPlaceholderText("https://api.example.com/v1")
        
        # API Key
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Enter API key")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Enable API
        self.enable_api_check = QCheckBox("Enable API Integration")
        self.enable_api_check.toggled.connect(self.toggle_api_fields)
        
        # Test API Connection
        test_api_btn = QPushButton("Test Connection")
        test_api_btn.clicked.connect(self.test_api_connection)
        
        # API timeout and retry settings
        self.api_timeout_spin = QSpinBox()
        self.api_timeout_spin.setRange(5, 120)
        self.api_timeout_spin.setValue(30)
        self.api_timeout_spin.setSuffix(" seconds")
        
        self.api_retries_spin = QSpinBox()
        self.api_retries_spin.setRange(0, 10)
        self.api_retries_spin.setValue(3)
        
        # Add widgets to API form
        api_form.addRow("", self.enable_api_check)
        api_form.addRow("API URL:", self.api_url_edit)
        api_form.addRow("API Key:", self.api_key_edit)
        api_form.addRow("Timeout:", self.api_timeout_spin)
        api_form.addRow("Max Retries:", self.api_retries_spin)
        api_form.addRow("", test_api_btn)
        
        api_layout.addWidget(api_group)
        
        # Usage Tracking
        usage_group = QGroupBox("Usage Tracking")
        usage_layout = QFormLayout(usage_group)
        
        # Allow usage tracking
        self.usage_tracking_check = QCheckBox("Allow anonymous usage tracking to improve the tool")
        
        # Allow feedback collection
        self.feedback_check = QCheckBox("Allow feedback collection")
        
        # Add widgets to usage layout
        usage_layout.addRow("", self.usage_tracking_check)
        usage_layout.addRow("", self.feedback_check)
        
        api_layout.addWidget(usage_group)
        api_layout.addStretch(1)
        
        # Add tabs
        self.tabs.addTab(general_tab, "General")
        self.tabs.addTab(api_tab, "API & Feedback")
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        
    def browse_export_dir(self):
        """Open a directory dialog to select the export directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", self.export_dir_edit.text()
        )
        
        if dir_path:
            self.export_dir_edit.setText(dir_path)
    
    def toggle_api_fields(self, enabled):
        """Enable or disable API fields based on checkbox state"""
        self.api_url_edit.setEnabled(enabled)
        self.api_key_edit.setEnabled(enabled)
        self.api_timeout_spin.setEnabled(enabled)
        self.api_retries_spin.setEnabled(enabled)
    
    def load_settings(self):
        """Load settings from config"""
        # Load general settings
        self.export_dir_edit.setText(self.config.get("export_directory", ""))
        self.auto_export_check.setChecked(self.config.get("auto_export", False))
        self.chunk_size_spin.setValue(self.config.get("chunk_size", 50000))
        
        # Load API settings
        enable_api = self.config.get("enable_api", False)
        self.enable_api_check.setChecked(enable_api)
        self.api_url_edit.setText(self.config.get("api_url", ""))
        self.api_key_edit.setText(self.config.get("api_key", ""))
        self.api_timeout_spin.setValue(self.config.get("api_timeout", 30))
        self.api_retries_spin.setValue(self.config.get("api_retries", 3))
        
        # Toggle API fields based on enable_api
        self.toggle_api_fields(enable_api)
        
        # Load usage settings
        self.usage_tracking_check.setChecked(self.config.get("usage_tracking", True))
        self.feedback_check.setChecked(self.config.get("collect_feedback", True))
    
    def save_settings(self):
        """Save settings to config"""
        # Save general settings
        self.config.set("export_directory", self.export_dir_edit.text())
        self.config.set("auto_export", self.auto_export_check.isChecked())
        self.config.set("chunk_size", self.chunk_size_spin.value())
        
        # Save API settings
        self.config.set("enable_api", self.enable_api_check.isChecked())
        self.config.set("api_url", self.api_url_edit.text())
        self.config.set("api_key", self.api_key_edit.text())
        self.config.set("api_timeout", self.api_timeout_spin.value())
        self.config.set("api_retries", self.api_retries_spin.value())
        
        # Save usage settings
        self.config.set("usage_tracking", self.usage_tracking_check.isChecked())
        self.config.set("collect_feedback", self.feedback_check.isChecked())
        
        # Emit signal
        self.settings_saved.emit()
        
        # Close dialog
        self.accept()
    
    def test_api_connection(self):
        """Test the API connection with current settings"""
        # Inform the user about the future capability
        QMessageBox.information(
            self,
            "Future Capability",
            "API connectivity is a future feature that will enable advanced online capabilities. \n\n"
            "This application is currently designed to work as a native offline tool. \n\n"
            "API endpoints are being prepared and will be available in a future release."
        )
        return
        
        # The following code is preserved for future API implementation
        '''
        if not self.enable_api_check.isChecked():
            QMessageBox.warning(self, "API Disabled", "Please enable API integration first.")
            return
        
        url = self.api_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a valid API URL.")
            return
        
        # Create API config
        api_config = ApiConfig(
            base_url=url,
            api_key=self.api_key_edit.text().strip(),
            timeout=self.api_timeout_spin.value(),
            retry_count=self.api_retries_spin.value()
        )
        
        try:
            # Create connector and test connection
            connector = ApiConnector(api_config)
            
            # Show a waiting message while testing
            QMessageBox.information(self, "Testing Connection", 
                "Testing API connection. This might take a few seconds...")
            
            if connector.validate_connection():
                QMessageBox.information(self, "Connection Successful", 
                    "Successfully connected to the API.")
            else:
                QMessageBox.warning(self, "Connection Failed", 
                    "Could not connect to the API. Please check your settings.")
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", 
                f"An error occurred while testing the API connection:\n{str(e)}")
        '''


class FeedbackDialog(QDialog):
    """Dialog for collecting user satisfaction feedback"""
    
    def __init__(self, parent=None):
        """Initialize the feedback dialog"""
        super().__init__(parent)
        self.setWindowTitle("Feedback")
        self.setMinimumWidth(400)
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("How satisfied are you with the data cleaning results?")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        
        # Rating group
        rating_group = QGroupBox("Rating")
        rating_layout = QHBoxLayout(rating_group)
        
        self.rating_combo = QComboBox()
        self.rating_combo.addItems([
            "⭐⭐⭐⭐⭐ Very Satisfied",
            "⭐⭐⭐⭐ Satisfied",
            "⭐⭐⭐ Neutral",
            "⭐⭐ Unsatisfied",
            "⭐ Very Unsatisfied"
        ])
        rating_layout.addWidget(self.rating_combo)
        
        layout.addWidget(rating_group)
        
        # Comments
        comment_label = QLabel("Additional comments (optional):")
        layout.addWidget(comment_label)
        
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("Your feedback helps us improve...")
        layout.addWidget(self.comment_edit)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_rating(self):
        """Get the selected rating (5 to 1)"""
        return 5 - self.rating_combo.currentIndex()
        
    def get_comments(self):
        """Get the comments text"""
        return self.comment_edit.text()
