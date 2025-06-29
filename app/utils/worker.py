"""
Worker thread implementation for background processing in the Education Data Cleaning Tool.
"""

from PyQt6.QtCore import QThread, pyqtSignal
import traceback
import logging
import time


class WorkerThread(QThread):
    """Worker thread to handle background processing tasks"""
    
    # Signals
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished_with_result = pyqtSignal(dict)
    
    def __init__(self, task_func, *args, **kwargs):
        """
        Initialize the worker thread
        
        Args:
            task_func: Function to execute in the background
            *args, **kwargs: Arguments to pass to task_func
        """
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.running = False
        self.result = None
        
    def run(self):
        """Execute the task function in a separate thread"""
        self.running = True
        self.result = None
        try:
            # Report initial status
            self.status.emit("Starting background task...")
            self.progress.emit(0)
            
            # Execute the task
            if "progress_callback" not in self.kwargs:
                self.kwargs["progress_callback"] = self.report_progress
                
            self.result = self.task_func(*self.args, **self.kwargs)
            
            # Report completion
            self.progress.emit(100)
            self.status.emit("Task completed.")
            
            # Return the result
            self.finished_with_result.emit(self.result)
            
        except Exception as e:
            logging.error(f"Error in worker thread: {str(e)}")
            logging.error(traceback.format_exc())
            self.error.emit(str(e))
            
        finally:
            self.running = False
            
    def report_progress(self, value, status_text=None):
        """Report progress from the task function"""
        self.progress.emit(value)
        if status_text:
            self.status.emit(status_text)
            
    def is_running(self):
        """Check if the thread is running"""
        return self.running
        
    def cancel(self):
        """Request cancellation of the task"""
        if self.running:
            self.running = False
            self.status.emit("Task cancelled by user.")
            self.quit()
            self.wait()
