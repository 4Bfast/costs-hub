"""
Enhanced Logging utilities for the Lambda Cost Reporting System.

This module provides standardized logging configuration and utilities
optimized for AWS Lambda execution environment with structured logging,
correlation IDs, and sensitive data masking.
"""

import json
import logging
import sys
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
from contextlib import contextmanager


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging with JSON output.
    
    Formats log records as JSON with consistent structure including
    correlation IDs, timestamps, and structured data.
    """
    
    def __init__(self, correlation_id: str = None):
        super().__init__()
        self.correlation_id = correlation_id or str(uuid.uuid4())
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log structure
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": self.correlation_id
        }
        
        # Add execution context if available
        if hasattr(record, 'execution_id'):
            log_data["execution_id"] = record.execution_id
        
        # Add client context if available
        if hasattr(record, 'client_id'):
            log_data["client_id"] = record.client_id
        
        # Add component context if available
        if hasattr(record, 'component'):
            log_data["component"] = record.component
        
        # Add operation context if available
        if hasattr(record, 'operation'):
            log_data["operation"] = record.operation
        
        # Add duration if available
        if hasattr(record, 'duration_seconds'):
            log_data["duration_seconds"] = record.duration_seconds
        
        # Add error information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add any extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info', 'correlation_id', 'execution_id',
                          'client_id', 'component', 'operation', 'duration_seconds']:
                # Mask sensitive data in extra fields
                if isinstance(value, (str, dict)):
                    extra_fields[key] = mask_sensitive_data_in_object(value)
                else:
                    extra_fields[key] = value
        
        if extra_fields:
            log_data["extra"] = extra_fields
        
        # Add source location for debug/error levels
        if record.levelno >= logging.ERROR:
            log_data["source"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName
            }
        
        return json.dumps(log_data, default=str, separators=(',', ':'))


def create_logger(name: str, level: Optional[str] = None, correlation_id: str = None) -> logging.Logger:
    """
    Create a standardized logger for the Lambda Cost Reporting System.
    
    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses environment variable LOG_LEVEL or defaults to INFO
        correlation_id: Optional correlation ID for request tracking
    
    Returns:
        Configured logger instance with structured logging
    """
    import os
    
    # Determine log level
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    # Set log level
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    # Create console handler for Lambda (logs go to CloudWatch)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level, logging.INFO))
    
    # Use structured formatter for JSON logging
    use_structured = os.getenv('USE_STRUCTURED_LOGGING', 'true').lower() == 'true'
    
    if use_structured:
        formatter = StructuredFormatter(correlation_id)
    else:
        # Fallback to simple formatter for local development
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    # Add correlation ID to logger for consistent tracking
    if correlation_id:
        logger = LoggerAdapter(logger, {"correlation_id": correlation_id})
    
    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds correlation ID and other context to all log records.
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message and add context"""
        # Add correlation ID and other context to extra
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Merge adapter context with log-specific extra
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs


def configure_lambda_logging(level: str = 'INFO') -> None:
    """
    Configure logging for Lambda environment.
    
    Args:
        level: Log level for all loggers
    """
    import os
    
    # Set environment variable for consistent logging
    os.environ['LOG_LEVEL'] = level.upper()
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )
    
    # Reduce noise from boto3/botocore
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging.
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at the end
    
    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ''
    
    return mask_char * (len(data) - visible_chars) + data[-visible_chars:]


def mask_sensitive_data_in_object(obj: Union[str, Dict[str, Any], Any]) -> Union[str, Dict[str, Any], Any]:
    """
    Recursively mask sensitive data in objects for logging.
    
    Args:
        obj: Object to mask sensitive data in
    
    Returns:
        Object with sensitive data masked
    """
    # Patterns for sensitive data
    sensitive_patterns = [
        r'(?i)(password|secret|key|token|credential)',
        r'(?i)(access_key|secret_key)',
        r'(?i)(api_key|auth_token)',
        r'(?i)(private_key|public_key)',
        r'(?i)(session_token|refresh_token)'
    ]
    
    if isinstance(obj, str):
        # Check if string looks like sensitive data
        for pattern in sensitive_patterns:
            if re.search(pattern, obj):
                return mask_sensitive_data(obj)
        
        # Check for AWS access key pattern
        if re.match(r'^AKIA[0-9A-Z]{16}$', obj):
            return mask_sensitive_data(obj, visible_chars=4)
        
        # Check for long base64-like strings (potential secrets)
        if len(obj) > 20 and re.match(r'^[A-Za-z0-9+/=]+$', obj):
            return mask_sensitive_data(obj, visible_chars=6)
        
        return obj
    
    elif isinstance(obj, dict):
        masked_dict = {}
        for key, value in obj.items():
            # Check if key indicates sensitive data
            key_lower = key.lower()
            is_sensitive_key = any(
                sensitive_word in key_lower 
                for sensitive_word in ['password', 'secret', 'key', 'token', 'credential']
            )
            
            if is_sensitive_key and isinstance(value, str):
                masked_dict[key] = mask_sensitive_data(value)
            else:
                masked_dict[key] = mask_sensitive_data_in_object(value)
        
        return masked_dict
    
    elif isinstance(obj, (list, tuple)):
        return type(obj)(mask_sensitive_data_in_object(item) for item in obj)
    
    else:
        return obj


@contextmanager
def log_execution_context(logger: logging.Logger, operation: str, 
                         client_id: str = None, **context):
    """
    Context manager for logging operation execution with structured context.
    
    Args:
        logger: Logger instance
        operation: Operation name
        client_id: Optional client ID
        **context: Additional context to log
    
    Yields:
        Context dictionary that can be updated during execution
    """
    import time
    
    start_time = time.time()
    execution_context = {
        "operation": operation,
        "client_id": client_id,
        **context
    }
    
    logger.info(f"Starting {operation}", extra=execution_context)
    
    try:
        yield execution_context
        
        duration = time.time() - start_time
        execution_context["duration_seconds"] = duration
        execution_context["status"] = "success"
        
        logger.info(f"Completed {operation} successfully", extra=execution_context)
        
    except Exception as e:
        duration = time.time() - start_time
        execution_context["duration_seconds"] = duration
        execution_context["status"] = "failed"
        execution_context["error"] = str(e)
        execution_context["error_type"] = type(e).__name__
        
        logger.error(f"Failed {operation}", extra=execution_context, exc_info=True)
        raise


def log_execution_time(logger: logging.Logger, operation: str):
    """
    Decorator to log execution time of operations.
    
    Args:
        logger: Logger instance to use
        operation: Description of the operation being timed
    
    Returns:
        Decorator function
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"{operation} completed in {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{operation} failed after {execution_time:.2f}s: {e}")
                raise
        
        return wrapper
    return decorator


def log_async_execution_time(logger: logging.Logger, operation: str):
    """
    Decorator to log execution time of async operations.
    
    Args:
        logger: Logger instance to use
        operation: Description of the operation being timed
    
    Returns:
        Decorator function
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"{operation} completed in {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{operation} failed after {execution_time:.2f}s: {e}")
                raise
        
        return wrapper
    return decorator