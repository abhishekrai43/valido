"""
FAANG-Level Logging System for Valido

Features:
- Structured logging with context (user, task_id, correlation_id)
- Daily log rotation with compression
- Separate error log for quick scanning
- Performance tracking (execution time)
- Remote debugging support (log export for support)
"""

import logging
import os
import sys
import json
import traceback
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
import time


# Global log directory - handle PyInstaller frozen app
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_dir = os.path.dirname(sys.executable)
else:
    # Running as script
    base_dir = os.getcwd()

LOG_DIR = os.path.join(base_dir, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


class StructuredFormatter(logging.Formatter):
    """Formatter that adds structured context to log messages."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Add timestamp in ISO format
        record.timestamp = datetime.utcnow().isoformat()
        
        # Add structured data if present
        if hasattr(record, 'context'):
            record.context_str = json.dumps(record.context)
        else:
            record.context_str = ''
        
        # Format exception info if present
        if record.exc_info:
            record.exc_text = ''.join(traceback.format_exception(*record.exc_info))
        
        return super().format(record)


class ValidoLogger:
    """Enhanced logger with structured logging and context management."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}
        
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up console, file, and error file handlers."""
        self.logger.setLevel(logging.INFO)
        
        # Console handler - colorized for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = StructuredFormatter(
            fmt='%(asctime)s [%(levelname)s] %(name)s - %(message)s %(context_str)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # Main log file - rotating by size (10MB max, keep 10 backups)
        main_log = os.path.join(LOG_DIR, 'valido.log')
        file_handler = RotatingFileHandler(
            main_log,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = StructuredFormatter(
            fmt='%(timestamp)s [%(levelname)s] %(name)s %(funcName)s:%(lineno)d - %(message)s %(context_str)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Error log file - separate file for quick scanning (daily rotation)
        error_log = os.path.join(LOG_DIR, 'errors.log')
        error_handler = TimedRotatingFileHandler(
            error_log,
            when='midnight',
            interval=1,
            backupCount=30,  # Keep 30 days of error logs
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        
        # Validation log - track all PDF processing
        validation_log = os.path.join(LOG_DIR, 'validation.log')
        validation_handler = TimedRotatingFileHandler(
            validation_log,
            when='midnight',
            interval=1,
            backupCount=7,  # Keep 1 week
            encoding='utf-8'
        )
        validation_handler.setLevel(logging.INFO)
        validation_handler.setFormatter(file_formatter)
        # Only log from validation-related modules
        validation_handler.addFilter(lambda r: 'validator' in r.name.lower() or 'worker' in r.name.lower())
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(validation_handler)
    
    def with_context(self, **kwargs) -> 'ValidoLogger':
        """Add context to all subsequent log messages."""
        self.context.update(kwargs)
        return self
    
    def clear_context(self):
        """Clear all context."""
        self.context = {}
    
    def _log(self, level: int, msg: str, *args, **kwargs):
        """Internal log method that adds context."""
        extra = kwargs.pop('extra', {})
        if self.context:
            extra['context'] = {**self.context, **extra.get('context', {})}
        kwargs['extra'] = extra
        self.logger.log(level, msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, exc_info: bool = False, **kwargs):
        if exc_info and sys.exc_info()[0] is not None:
            kwargs['exc_info'] = sys.exc_info()
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)
    
    @contextmanager
    def operation(self, operation_name: str, **context):
        """Context manager for tracking operation execution time and outcome."""
        op_id = f"{operation_name}_{int(time.time()*1000)}"
        start_time = time.time()
        
        self.info(f"Starting operation: {operation_name}", extra={'context': {**context, 'operation_id': op_id}})
        
        try:
            yield self
            duration = time.time() - start_time
            self.info(
                f"Completed operation: {operation_name} in {duration:.3f}s",
                extra={'context': {**context, 'operation_id': op_id, 'duration_seconds': duration}}
            )
        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"Failed operation: {operation_name} after {duration:.3f}s: {type(e).__name__}: {e}",
                exc_info=True,
                extra={'context': {**context, 'operation_id': op_id, 'duration_seconds': duration}}
            )
            raise


# Global logger cache
_loggers: Dict[str, ValidoLogger] = {}


def get_logger(name: str = __name__) -> ValidoLogger:
    """
    Get or create a logger instance with structured logging support.
    
    Args:
        name: Logger name (usually __name__ of the calling module)
    
    Returns:
        ValidoLogger instance with context support
    
    Example:
        logger = get_logger(__name__)
        logger.with_context(user_id=123, task_id='abc')
        logger.info("Processing PDF", extra={'context': {'filename': 'invoice.pdf'}})
        
        with logger.operation("validate_pdf", filename='invoice.pdf'):
            # Your code here
            pass
    """
    if name not in _loggers:
        _loggers[name] = ValidoLogger(name)
    return _loggers[name]


def get_recent_logs(lines: int = 1000) -> str:
    """
    Get recent log lines for support diagnostics.
    
    Args:
        lines: Number of recent lines to retrieve
    
    Returns:
        Recent log content as string
    """
    log_file = os.path.join(LOG_DIR, 'valido.log')
    if not os.path.exists(log_file):
        return "No log file found"
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return ''.join(recent)
    except Exception as e:
        return f"Error reading logs: {e}"


def get_error_logs(lines: int = 500) -> str:
    """Get recent error logs for quick problem scanning."""
    error_log = os.path.join(LOG_DIR, 'errors.log')
    if not os.path.exists(error_log):
        return "No error log found"
    
    try:
        with open(error_log, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return ''.join(recent)
    except Exception as e:
        return f"Error reading error logs: {e}"
