"""
Data models for Education Data Cleaning Tool.
"""

import pandas as pd
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex


class PandasTableModel(QAbstractTableModel):
    """
    Model to display pandas DataFrame in a QTableView
    """
    
    def __init__(self, data=None):
        super().__init__()
        self._data = data if data is not None else pd.DataFrame()
        
    def rowCount(self, parent=QModelIndex()):
        """Return the number of rows"""
        return len(self._data)
        
    def columnCount(self, parent=QModelIndex()):
        """Return the number of columns"""
        return len(self._data.columns)
        
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Return data for the specified role at the index"""
        if not index.isValid():
            return None
            
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)
            
        return None
        
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """Return header data for the specified role"""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            else:
                return str(section + 1)  # Row numbers
                
        return None
        
    def setData(self, data):
        """Set the model data"""
        self.beginResetModel()
        self._data = data if data is not None else pd.DataFrame()
        self.endResetModel()
        
    def update_data(self, data):
        """Update the model data - alias for setData"""
        self.setData(data)
        
        
class CleaningOptions:
    """Model to store data cleaning configuration options"""
    
    def __init__(self):
        self.name_column = None
        self.dob_column = None
        self.year_column = None
        self.fuzzy_matching = False
        self.fuzzy_threshold = 90  # Default threshold for fuzzy matching
        self.chunk_size = None  # For large file processing
        self.input_file = None
        self.output_clean_file = None
        self.output_duplicate_file = None
