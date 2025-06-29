"""
Configuration utilities for Education Data Cleaning Tool.
"""

import os
import json
import logging
from pathlib import Path


class Config:
    """Configuration manager for the application"""
    
    DEFAULT_CONFIG = {
        "recent_files": [],
        "fuzzy_matching": True,
        "fuzzy_threshold": 90,
        "max_recent_files": 5,
        "auto_export": False,
        "export_directory": "",
        "chunk_size": 50000,  # for large file processing
    }
    
    def __init__(self):
        """Initialize the configuration manager"""
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.config = self._load_config()
        
    def _get_config_dir(self):
        """Get the configuration directory, create if it doesn't exist"""
        home_dir = str(Path.home())
        config_dir = os.path.join(home_dir, ".edu_data_cleaner")
        
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
            except Exception as e:
                logging.error(f"Failed to create config directory: {str(e)}")
                # Fall back to current directory
                config_dir = "."
                
        return config_dir
        
    def _load_config(self):
        """Load configuration from file, or create default if it doesn't exist"""
        if not os.path.exists(self.config_file):
            return self._save_config(self.DEFAULT_CONFIG)
            
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
                
            # Update with any missing default keys
            updated = False
            for key, value in self.DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
                    updated = True
                    
            if updated:
                self._save_config(config)
                
            return config
            
        except Exception as e:
            logging.error(f"Failed to load config: {str(e)}")
            return self._save_config(self.DEFAULT_CONFIG)
            
    def _save_config(self, config):
        """Save configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
            return config
        except Exception as e:
            logging.error(f"Failed to save config: {str(e)}")
            return self.DEFAULT_CONFIG
            
    def get(self, key, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)
        
    def set(self, key, value):
        """Set a configuration value"""
        self.config[key] = value
        self._save_config(self.config)
        
    def add_recent_file(self, file_path):
        """Add a file to the recent files list"""
        recent_files = self.get("recent_files", [])
        
        # Remove if already exists to avoid duplicates
        if file_path in recent_files:
            recent_files.remove(file_path)
            
        # Add to the front of the list
        recent_files.insert(0, file_path)
        
        # Limit the number of recent files
        max_files = self.get("max_recent_files", 5)
        if len(recent_files) > max_files:
            recent_files = recent_files[:max_files]
            
        self.set("recent_files", recent_files)
        return recent_files
