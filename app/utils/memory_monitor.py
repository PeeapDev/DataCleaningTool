"""
Memory monitoring utility to prevent app crashes on large files.
"""

import os
import sys
import time
import logging
import threading
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

class MemoryMonitor:
    """Monitors memory usage during data processing to prevent crashes."""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.last_memory_usage = 0
        self.peak_memory_usage = 0
        self.crash_protection_enabled = True
    
    def start_monitoring(self):
        """Start monitoring memory usage in a background thread."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_thread_func)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("Memory monitoring started")
        
    def stop_monitoring(self):
        """Stop the memory monitoring thread."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        logger.info(f"Memory monitoring stopped. Peak usage: {self.peak_memory_usage} MB")
        
    def _get_memory_usage(self):
        """Get current memory usage of the process in MB."""
        try:
            # Using different approaches by platform
            if sys.platform == 'darwin':  # macOS
                import resource
                rusage = resource.getrusage(resource.RUSAGE_SELF)
                mem_usage = rusage.ru_maxrss / 1024 / 1024  # Bytes to MB
            elif sys.platform == 'win32':  # Windows
                import psutil
                process = psutil.Process(os.getpid())
                mem_usage = process.memory_info().rss / 1024 / 1024  # Bytes to MB
            else:  # Linux and others
                with open(f'/proc/{os.getpid()}/status', 'r') as f:
                    for line in f:
                        if 'VmRSS' in line:
                            mem_usage = int(line.split()[1]) / 1024  # KB to MB
                            break
                    else:
                        # Fallback
                        mem_usage = 0
                        
            return mem_usage
        except Exception as e:
            logger.error(f"Error getting memory usage: {str(e)}")
            return 0
            
    def _monitor_thread_func(self):
        """Background thread function for monitoring memory."""
        try:
            while self.monitoring:
                current_usage = self._get_memory_usage()
                
                # Update peak usage
                if current_usage > self.peak_memory_usage:
                    self.peak_memory_usage = current_usage
                
                # Check for dangerous memory spikes
                memory_change = current_usage - self.last_memory_usage
                if memory_change > 500 and self.crash_protection_enabled:  # 500MB spike
                    logger.critical(f"DANGEROUS MEMORY SPIKE: {memory_change:.2f} MB increase!")
                    logger.critical("Writing emergency memory dump and enabling protective measures")
                    self._write_emergency_dump(f"Memory spike of {memory_change:.2f} MB detected")
                
                # Check for critically high memory (>80% of system memory on most systems)
                if current_usage > 3000 and self.crash_protection_enabled:  # 3GB is dangerous on most systems
                    logger.critical(f"CRITICAL MEMORY USAGE: {current_usage:.2f} MB!")
                    logger.critical("Initiating emergency memory protection")
                    self._write_emergency_dump(f"Critical memory usage: {current_usage:.2f} MB")
                    
                self.last_memory_usage = current_usage
                time.sleep(1.0)  # Check every second
                
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error in memory monitoring thread: {str(e)}\n{tb}")
    
    def _write_emergency_dump(self, reason):
        """Write emergency information before potential crash."""
        try:
            dump_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'emergency_dumps')
            os.makedirs(dump_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dump_file = os.path.join(dump_dir, f"emergency_dump_{timestamp}.log")
            
            with open(dump_file, 'w') as f:
                f.write(f"=== EMERGENCY MEMORY DUMP ===\n")
                f.write(f"Time: {datetime.now()}\n")
                f.write(f"Reason: {reason}\n")
                f.write(f"Current memory: {self.last_memory_usage:.2f} MB\n")
                f.write(f"Peak memory: {self.peak_memory_usage:.2f} MB\n\n")
                
                f.write("=== STACK TRACE ===\n")
                for thread_id, frame in sys._current_frames().items():
                    f.write(f"\nThread {thread_id}:\n")
                    f.write(''.join(traceback.format_stack(frame)))
                
            logger.info(f"Emergency memory dump written to {dump_file}")
        except Exception as e:
            logger.error(f"Failed to write emergency dump: {str(e)}")

# Global memory monitor instance
memory_monitor = MemoryMonitor()
