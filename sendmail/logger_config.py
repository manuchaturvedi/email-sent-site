"""
Logging configuration for JustMailIt application.
Logs are written to files that can be accessed via Docker volume or downloaded.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file paths
APP_LOG_FILE = os.path.join(LOGS_DIR, 'app.log')
ERROR_LOG_FILE = os.path.join(LOGS_DIR, 'error.log')
SCRAPER_LOG_FILE = os.path.join(LOGS_DIR, 'scraper.log')
AUTH_LOG_FILE = os.path.join(LOGS_DIR, 'auth.log')
EMAIL_LOG_FILE = os.path.join(LOGS_DIR, 'email.log')
ACTIVITY_LOG_FILE = os.path.join(LOGS_DIR, 'activity.log')

# Log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def setup_logger(name, log_file, level=logging.INFO, max_bytes=10*1024*1024, backup_count=5):
    """
    Setup a logger with rotating file handler.
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level
        max_bytes: Max file size before rotation (default 10MB)
        backup_count: Number of backup files to keep
    """
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # File handler with rotation
    handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_bytes, 
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    # Prevent duplicate logs
    logger.propagate = False
    
    return logger

# Create default loggers
app_logger = setup_logger('app', APP_LOG_FILE, logging.INFO)
error_logger = setup_logger('error', ERROR_LOG_FILE, logging.ERROR)
scraper_logger = setup_logger('scraper', SCRAPER_LOG_FILE, logging.INFO)
auth_logger = setup_logger('auth', AUTH_LOG_FILE, logging.INFO)
email_logger = setup_logger('email', EMAIL_LOG_FILE, logging.INFO)
activity_logger = setup_logger('activity', ACTIVITY_LOG_FILE, logging.INFO)

# Log startup
app_logger.info("="*60)
app_logger.info("JustMailIt Application Started")
app_logger.info(f"Logs directory: {LOGS_DIR}")
app_logger.info("="*60)
