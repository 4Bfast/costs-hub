"""
Comprehensive Error Handling for Lambda Cost Reporting System

This module provides error handling for each component (config, cost collection, 
reporting, email), retry logic with exponential backoff, and error categorization 
with appropriate responses.
"""

import time
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
from functools import wraps

import boto3
from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError

from ..utils import create_logger


logger = create_logger(__name__)


class ErrorCategory(Enum):
    """Error category enumeration for classification."""
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    THROTTLING = "throttling"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATA_VALIDATION = "data_validation"
    BUSINESS_LOGIC = "business_logic"
    TIMEOUT = "timeout"
    RESOURCE_NOT_FOUND = "resource_not_found"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Structured error information."""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    component: str
    client_id: Optional[str] = None
    retryable: bool = False
    retry_after_seconds: Optional[int] = None
    original_exception: Optional[Exception] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and metrics."""
        return {
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'component': self.component,
            'client_id': self.client_id,
            'retryable': self.retryable,
            'retry_after_seconds': self.retry_after_seconds,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'context': self.context or {}
        }


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        if attempt <= 0:
            return 0
        
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class ErrorHandler:
    """
    Comprehensive error handler for the Lambda cost reporting system.
    
    Provides error classification, retry logic, and appropriate responses
    for different types of errors across all system components.
    """
    
    def __init__(self):
        """Initialize the error handler."""
        self.logger = create_logger(f"{__name__}.ErrorHandler")
        
        # Default retry configurations for different error categories
        self.retry_configs = {
            ErrorCategory.THROTTLING: RetryConfig(max_attempts=5, base_delay=2.0, max_delay=120.0),
            ErrorCategory.NETWORK: RetryConfig(max_attempts=3, base_delay=1.0, max_delay=30.0),
            ErrorCategory.SERVICE_UNAVAILABLE: RetryConfig(max_attempts=3, base_delay=5.0, max_delay=60.0),
            ErrorCategory.TIMEOUT: RetryConfig(max_attempts=2, base_delay=1.0, max_delay=10.0),
            ErrorCategory.UNKNOWN: RetryConfig(max_attempts=2, base_delay=1.0, max_delay=10.0)
        }
        
        # Error statistics
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_component': {},
            'retried_operations': 0,
            'failed_after_retry': 0
        }
    
    def classify_error(self, exception: Exception, component: str, 
                      client_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """
        Classify an error and return structured error information.
        
        Args:
            exception: The exception to classify
            component: Component where error occurred
            client_id: Optional client identifier
            context: Optional additional context
            
        Returns:
            ErrorInfo object with classification details
        """
        try:
            # AWS-specific errors
            if isinstance(exception, ClientError):
                return self._classify_aws_client_error(exception, component, client_id, context)
            elif isinstance(exception, BotoCoreError):
                return self._classify_botocore_error(exception, component, client_id, context)
            elif isinstance(exception, NoCredentialsError):
                return ErrorInfo(
                    category=ErrorCategory.AUTHENTICATION,
                    severity=ErrorSeverity.HIGH,
                    message="AWS credentials not found or invalid",
                    component=component,
                    client_id=client_id,
                    retryable=False,
                    original_exception=exception,
                    context=context
                )
            
            # Application-specific errors
            elif "timeout" in str(exception).lower():
                return ErrorInfo(
                    category=ErrorCategory.TIMEOUT,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Operation timed out: {str(exception)}",
                    component=component,
                    client_id=client_id,
                    retryable=True,
                    retry_after_seconds=5,
                    original_exception=exception,
                    context=context
                )
            
            elif "validation" in str(exception).lower() or "invalid" in str(exception).lower():
                return ErrorInfo(
                    category=ErrorCategory.DATA_VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Data validation error: {str(exception)}",
                    component=component,
                    client_id=client_id,
                    retryable=False,
                    original_exception=exception,
                    context=context
                )
            
            elif "not found" in str(exception).lower():
                return ErrorInfo(
                    category=ErrorCategory.RESOURCE_NOT_FOUND,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Resource not found: {str(exception)}",
                    component=component,
                    client_id=client_id,
                    retryable=False,
                    original_exception=exception,
                    context=context
                )
            
            # Network-related errors
            elif any(keyword in str(exception).lower() for keyword in ['connection', 'network', 'dns', 'socket']):
                return ErrorInfo(
                    category=ErrorCategory.NETWORK,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Network error: {str(exception)}",
                    component=component,
                    client_id=client_id,
                    retryable=True,
                    retry_after_seconds=2,
                    original_exception=exception,
                    context=context
                )
            
            # Default classification
            else:
                return ErrorInfo(
                    category=ErrorCategory.UNKNOWN,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Unknown error: {str(exception)}",
                    component=component,
                    client_id=client_id,
                    retryable=True,
                    retry_after_seconds=1,
                    original_exception=exception,
                    context=context
                )
                
        except Exception as e:
            self.logger.error(f"Error classifying exception: {str(e)}")
            # Fallback error info
            return ErrorInfo(
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.HIGH,
                message=f"Error classification failed: {str(exception)}",
                component=component,
                client_id=client_id,
                retryable=False,
                original_exception=exception,
                context=context
            )
    
    def _classify_aws_client_error(self, error: ClientError, component: str, 
                                 client_id: Optional[str], context: Optional[Dict[str, Any]]) -> ErrorInfo:
        """Classify AWS ClientError exceptions."""
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        
        # Throttling errors
        if error_code in ['Throttling', 'ThrottlingException', 'RequestLimitExceeded', 'TooManyRequestsException']:
            retry_after = error.response.get('Error', {}).get('RetryAfterSeconds', 5)
            return ErrorInfo(
                category=ErrorCategory.THROTTLING,
                severity=ErrorSeverity.MEDIUM,
                message=f"AWS API throttling: {error_message}",
                component=component,
                client_id=client_id,
                retryable=True,
                retry_after_seconds=retry_after,
                original_exception=error,
                context=context
            )
        
        # Authentication/Authorization errors
        elif error_code in ['UnauthorizedOperation', 'AccessDenied', 'Forbidden', 'InvalidUserID.NotFound']:
            return ErrorInfo(
                category=ErrorCategory.AUTHORIZATION,
                severity=ErrorSeverity.HIGH,
                message=f"AWS authorization error: {error_message}",
                component=component,
                client_id=client_id,
                retryable=False,
                original_exception=error,
                context=context
            )
        
        elif error_code in ['InvalidAccessKeyId', 'SignatureDoesNotMatch', 'TokenRefreshRequired']:
            return ErrorInfo(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                message=f"AWS authentication error: {error_message}",
                component=component,
                client_id=client_id,
                retryable=False,
                original_exception=error,
                context=context
            )
        
        # Service unavailable errors
        elif error_code in ['ServiceUnavailable', 'InternalError', 'InternalFailure']:
            return ErrorInfo(
                category=ErrorCategory.SERVICE_UNAVAILABLE,
                severity=ErrorSeverity.HIGH,
                message=f"AWS service unavailable: {error_message}",
                component=component,
                client_id=client_id,
                retryable=True,
                retry_after_seconds=10,
                original_exception=error,
                context=context
            )
        
        # Resource not found errors
        elif error_code in ['ResourceNotFound', 'NoSuchBucket', 'NoSuchKey', 'ClientNotFound']:
            return ErrorInfo(
                category=ErrorCategory.RESOURCE_NOT_FOUND,
                severity=ErrorSeverity.MEDIUM,
                message=f"AWS resource not found: {error_message}",
                component=component,
                client_id=client_id,
                retryable=False,
                original_exception=error,
                context=context
            )
        
        # Quota/limit errors
        elif error_code in ['LimitExceeded', 'QuotaExceeded', 'SendingQuotaExceeded']:
            return ErrorInfo(
                category=ErrorCategory.QUOTA_EXCEEDED,
                severity=ErrorSeverity.HIGH,
                message=f"AWS quota exceeded: {error_message}",
                component=component,
                client_id=client_id,
                retryable=False,
                original_exception=error,
                context=context
            )
        
        # Validation errors
        elif error_code in ['ValidationException', 'InvalidParameterValue', 'InvalidParameter']:
            return ErrorInfo(
                category=ErrorCategory.DATA_VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                message=f"AWS validation error: {error_message}",
                component=component,
                client_id=client_id,
                retryable=False,
                original_exception=error,
                context=context
            )
        
        # Default AWS error
        else:
            return ErrorInfo(
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.MEDIUM,
                message=f"AWS error ({error_code}): {error_message}",
                component=component,
                client_id=client_id,
                retryable=True,
                retry_after_seconds=2,
                original_exception=error,
                context=context
            )
    
    def _classify_botocore_error(self, error: BotoCoreError, component: str, 
                               client_id: Optional[str], context: Optional[Dict[str, Any]]) -> ErrorInfo:
        """Classify BotoCoreError exceptions."""
        error_message = str(error)
        
        if "timeout" in error_message.lower():
            return ErrorInfo(
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                message=f"AWS timeout error: {error_message}",
                component=component,
                client_id=client_id,
                retryable=True,
                retry_after_seconds=5,
                original_exception=error,
                context=context
            )
        elif "connection" in error_message.lower() or "network" in error_message.lower():
            return ErrorInfo(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                message=f"AWS network error: {error_message}",
                component=component,
                client_id=client_id,
                retryable=True,
                retry_after_seconds=3,
                original_exception=error,
                context=context
            )
        else:
            return ErrorInfo(
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.MEDIUM,
                message=f"AWS BotoCore error: {error_message}",
                component=component,
                client_id=client_id,
                retryable=True,
                retry_after_seconds=2,
                original_exception=error,
                context=context
            )
    
    def handle_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """
        Handle an error based on its classification.
        
        Args:
            error_info: Classified error information
            
        Returns:
            Dictionary with handling results and recommendations
        """
        try:
            # Update statistics
            self.error_stats['total_errors'] += 1
            
            category_key = error_info.category.value
            if category_key not in self.error_stats['errors_by_category']:
                self.error_stats['errors_by_category'][category_key] = 0
            self.error_stats['errors_by_category'][category_key] += 1
            
            if error_info.component not in self.error_stats['errors_by_component']:
                self.error_stats['errors_by_component'][error_info.component] = 0
            self.error_stats['errors_by_component'][error_info.component] += 1
            
            # Log the error
            log_level = {
                ErrorSeverity.LOW: logging.INFO,
                ErrorSeverity.MEDIUM: logging.WARNING,
                ErrorSeverity.HIGH: logging.ERROR,
                ErrorSeverity.CRITICAL: logging.CRITICAL
            }.get(error_info.severity, logging.ERROR)
            
            self.logger.log(log_level, f"Error in {error_info.component}: {error_info.message}", extra={
                'error_info': error_info.to_dict(),
                'traceback': traceback.format_exc() if error_info.original_exception else None
            })
            
            # Determine handling strategy
            handling_result = {
                'error_info': error_info.to_dict(),
                'should_retry': error_info.retryable,
                'should_continue': self._should_continue_processing(error_info),
                'should_alert': self._should_send_alert(error_info),
                'recommended_action': self._get_recommended_action(error_info)
            }
            
            return handling_result
            
        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")
            return {
                'error_info': error_info.to_dict(),
                'should_retry': False,
                'should_continue': False,
                'should_alert': True,
                'recommended_action': 'manual_intervention',
                'handling_error': str(e)
            }
    
    def _should_continue_processing(self, error_info: ErrorInfo) -> bool:
        """Determine if processing should continue after this error."""
        # Critical errors should stop processing
        if error_info.severity == ErrorSeverity.CRITICAL:
            return False
        
        # Configuration and authentication errors should stop processing for that client
        if error_info.category in [ErrorCategory.CONFIGURATION, ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]:
            return False
        
        # Other errors can continue processing
        return True
    
    def _should_send_alert(self, error_info: ErrorInfo) -> bool:
        """Determine if an alert should be sent for this error."""
        # Always alert for critical errors
        if error_info.severity == ErrorSeverity.CRITICAL:
            return True
        
        # Alert for high severity errors
        if error_info.severity == ErrorSeverity.HIGH:
            return True
        
        # Alert for authentication/authorization issues
        if error_info.category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]:
            return True
        
        # Alert for quota exceeded
        if error_info.category == ErrorCategory.QUOTA_EXCEEDED:
            return True
        
        return False
    
    def _get_recommended_action(self, error_info: ErrorInfo) -> str:
        """Get recommended action for the error."""
        if error_info.category == ErrorCategory.AUTHENTICATION:
            return "check_aws_credentials"
        elif error_info.category == ErrorCategory.AUTHORIZATION:
            return "check_aws_permissions"
        elif error_info.category == ErrorCategory.CONFIGURATION:
            return "check_client_configuration"
        elif error_info.category == ErrorCategory.QUOTA_EXCEEDED:
            return "increase_aws_limits"
        elif error_info.category == ErrorCategory.THROTTLING:
            return "reduce_request_rate"
        elif error_info.category == ErrorCategory.RESOURCE_NOT_FOUND:
            return "verify_resource_exists"
        elif error_info.retryable:
            return "retry_operation"
        else:
            return "manual_investigation"
    
    def retry_with_backoff(self, operation: Callable, error_category: ErrorCategory = ErrorCategory.UNKNOWN,
                          custom_config: Optional[RetryConfig] = None, 
                          context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute an operation with retry logic and exponential backoff.
        
        Args:
            operation: Function to execute
            error_category: Category of errors expected
            custom_config: Custom retry configuration
            context: Additional context for error handling
            
        Returns:
            Result of the operation
            
        Raises:
            Last exception if all retries fail
        """
        retry_config = custom_config or self.retry_configs.get(error_category, RetryConfig())
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                if attempt > 0:
                    self.error_stats['retried_operations'] += 1
                
                result = operation()
                
                if attempt > 0:
                    self.logger.info(f"Operation succeeded after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Classify the error
                error_info = self.classify_error(e, "retry_operation", context=context)
                
                # Check if we should retry
                if not error_info.retryable or attempt == retry_config.max_attempts - 1:
                    self.error_stats['failed_after_retry'] += 1
                    self.logger.error(f"Operation failed after {attempt + 1} attempts: {str(e)}")
                    break
                
                # Calculate delay
                delay = retry_config.get_delay(attempt + 1)
                if error_info.retry_after_seconds:
                    delay = max(delay, error_info.retry_after_seconds)
                
                self.logger.warning(f"Operation failed (attempt {attempt + 1}/{retry_config.max_attempts}), "
                                  f"retrying in {delay:.1f} seconds: {str(e)}")
                
                time.sleep(delay)
        
        # All retries failed
        raise last_exception
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        return {
            'error_stats': self.error_stats.copy(),
            'retry_configs': {
                category.value: {
                    'max_attempts': config.max_attempts,
                    'base_delay': config.base_delay,
                    'max_delay': config.max_delay
                }
                for category, config in self.retry_configs.items()
            }
        }
    
    def reset_statistics(self) -> None:
        """Reset error statistics."""
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_component': {},
            'retried_operations': 0,
            'failed_after_retry': 0
        }


def with_error_handling(component: str, error_handler: Optional[ErrorHandler] = None):
    """
    Decorator for automatic error handling.
    
    Args:
        component: Component name for error classification
        error_handler: Optional error handler instance
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = error_handler or ErrorHandler()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Extract client_id from args/kwargs if available
                client_id = None
                if 'client_id' in kwargs:
                    client_id = kwargs['client_id']
                elif len(args) > 0 and hasattr(args[0], 'client_id'):
                    client_id = args[0].client_id
                
                # Classify and handle the error
                error_info = handler.classify_error(e, component, client_id)
                handling_result = handler.handle_error(error_info)
                
                # Re-raise the exception with additional context
                e.error_info = error_info
                e.handling_result = handling_result
                raise
        
        return wrapper
    return decorator


# Global error handler instance
global_error_handler = ErrorHandler()


def handle_component_error(exception: Exception, component: str, 
                         client_id: Optional[str] = None, 
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function for handling component errors.
    
    Args:
        exception: Exception to handle
        component: Component where error occurred
        client_id: Optional client identifier
        context: Optional additional context
        
    Returns:
        Error handling result
    """
    error_info = global_error_handler.classify_error(exception, component, client_id, context)
    return global_error_handler.handle_error(error_info)


def retry_operation(operation: Callable, component: str, 
                   max_attempts: int = 3, base_delay: float = 1.0,
                   context: Optional[Dict[str, Any]] = None) -> Any:
    """
    Convenience function for retrying operations.
    
    Args:
        operation: Function to retry
        component: Component name
        max_attempts: Maximum retry attempts
        base_delay: Base delay between retries
        context: Optional context
        
    Returns:
        Operation result
    """
    retry_config = RetryConfig(max_attempts=max_attempts, base_delay=base_delay)
    return global_error_handler.retry_with_backoff(
        operation, 
        ErrorCategory.UNKNOWN, 
        retry_config, 
        context
    )