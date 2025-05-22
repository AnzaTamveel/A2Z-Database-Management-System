# utils/logger.py
import logging
from pathlib import Path
from datetime import datetime
import os

class DatabaseLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self._setup_logging()
        
    def _setup_logging(self):
        """Configure logging settings"""
        if not self.log_dir.exists():
            os.makedirs(self.log_dir)
            
        log_file = self.log_dir / f"db_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('DBLogger')

    def log_operation(self, operation: str, target: str, status: str, details: str = ""):
        """Log a database operation"""
        message = f"{operation.upper()} - {target} - {status}"
        if details:
            message += f" - {details}"
        
        self.logger.info(message)

# Singleton logger instance
logger = DatabaseLogger()