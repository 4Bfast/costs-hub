"""
Provider Error Handler

This module provides comprehensive error handling and recovery strategies
for cloud provider operations in the multi-cloud cost analytics platform.
"""

import logging
import asyncio
import random
from typing import Dict, List, Optional, Any, Callable, Type
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from ..models.provider_models import (
    ProviderError, ProviderType, AuthenticationError, AuthorizationError,
    RateLimitError, ServiceUnavailableError, DataFormatError, QuotaExceededError
)


class RecoveryAction(Enum):
    """Types of recovery actions for provider errors."""
    RETRY_IMMEDIATELY = "retry_immediately"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_AFTER_DELAY = "retry_after_delay"
    REFRESH_CREDENTIALS = "refresh_credentials"
    SKIP_PROVIDER = "skip_provider"
    FAIL_OPERATION = "fail_operation"
    REDUCE_REQUEST_SIZE = "reduce_request_size"
    SWITCH_REGION = "switch_region"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    provider: ProviderType
    client_id: str
    attempt_number: int
    max_attempts: int
    start_time: datetime
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryStrategy:
    """Recovery strategy for handling provider errors."""
    action: RecoveryAction
    delay_seconds: Optional[float] = None
    max_attempts: int = 3
    backoff_multiplier: float = 2.0
    jitter: bool = True
    conditions: List[str] = field(default_factory=list)
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry with backoff."""
        if self.delay_seconds is None:
            return 0.0
        
        if self.action == RecoveryAction.RETRY_WITH_BACKOFF:
            delay = self.delay_seconds * (self.backoff_multiplier ** (attempt - 1))
            if self.jitter:
                delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
            return min(delay, 300.0)  # Cap at 5 minutes
        
        return self.delay_seconds


@dataclass
class ErrorHandlingResult:
    """Result of error handling operation."""
    action_taken: RecoveryAction
    should_retry: bool
    delay_seconds: float
    error_severity: ErrorSeverity
    recovery_message: str
    additional_data: Dict[str, Any] = field(default_factory=dict)


class ProviderErrorHandler:
    """Comprehensive error handler for cloud provider operations."""
    
    def __init__(self):
        """Initialize the error handler."""
        self.logger = logging.getLogger(f"{__name__}.ProviderErrorHandler")
        self._error_strategies = self._initialize_error_strategies()
        self._error_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def _initialize_error_strategies(self) -> Dict[Type[ProviderError], RecoveryStrategy]:
        """Initialize default error recovery strategies."""
        return {
            AuthenticationError: RecoveryStrategy(
                action=RecoveryAction.REFRESH_CREDENTIALS,
                max_attempts=2,
                conditions=["credential_expired", "invalid_token"]
            ),
            AuthorizationError: RecoveryStrategy(
                action=RecoveryAction.FAIL_OPERATION,
                max_attempts=1,
                conditions=["insufficient_permissions"]
            ),
            RateLimitError: RecoveryStrategy(
                action=RecoveryAction.RETRY_AFTER_DELAY,
                delay_seconds=60.0,
                max_attempts=5,
                backoff_multiplier=1.5,
                conditions=["rate_limited", "throttled"]
            ),
            ServiceUnavailableError: RecoveryStrategy(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                delay_seconds=30.0,
                max_attempts=3,
                backoff_multiplier=2.0,
                conditions=["service_down", "maintenance"]
            ),
            DataFormatError: RecoveryStrategy(
                action=RecoveryAction.FAIL_OPERATION,
                max_attempts=1,
                conditions=["invalid_response", "parsing_error"]
            ),
            QuotaExceededError: RecoveryStrategy(
                action=RecoveryAction.REDUCE_REQUEST_SIZE,
                max_attempts=2,
                conditions=["quota_exceeded", "limit_reached"]
            )
        }
    
    async def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> ErrorHandlingResult:
        """
        Handle a provider error and determine recovery strategy.
        
        Args:
            error: The error that occurred
            context: Context information about the operation
            
        Returns:
            ErrorHandlingResult with recovery strategy
        """
        # Convert to ProviderError if needed
        if not isinstance(error, ProviderError):
            provider_error = self._convert_to_provider_error(error, context.provider)
        else:
            provider_error = error
        
        # Log the error
        self._log_error(provider_error, context)
        
        # Record error in history
        self._record_error_history(provider_error, context)
        
        # Determine recovery strategy
        strategy = self._get_recovery_strategy(provider_error, context)
        
        # Calculate delay
        delay = strategy.calculate_delay(context.attempt_number)
        
        # Determine severity
        severity = self._assess_error_severity(provider_error, context)
        
        # Create result
        result = ErrorHandlingResult(
            action_taken=strategy.action,
            should_retry=self._should_retry(strategy, context),
            delay_seconds=delay,
            error_severity=severity,
            recovery_message=self._generate_recovery_message(provider_error, strategy),
            additional_data={
                'error_type': type(provider_error).__name__,
                'error_code': provider_error.error_code,
                'attempt_number': context.attempt_number,
                'max_attempts': strategy.max_attempts
            }
        )
        
        self.logger.info(
            f"Error handling result for {context.provider.value}: "
            f"action={result.action_taken.value}, retry={result.should_retry}, "
            f"delay={result.delay_seconds}s, severity={result.error_severity.value}"
        )
        
        return result
    
    def _convert_to_provider_error(self, error: Exception, provider: ProviderType) -> ProviderError:
        """Convert generic exception to ProviderError."""
        error_message = str(error)
        error_type = type(error).__name__
        
        # Try to classify the error based on message content
        if any(keyword in error_message.lower() for keyword in ['auth', 'credential', 'token']):
            return AuthenticationError(provider, error_message)
        elif any(keyword in error_message.lower() for keyword in ['permission', 'access', 'forbidden']):
            return AuthorizationError(provider, error_message)
        elif any(keyword in error_message.lower() for keyword in ['rate', 'throttle', 'limit']):
            return RateLimitError(provider, error_message)
        elif any(keyword in error_message.lower() for keyword in ['unavailable', 'timeout', 'connection']):
            return ServiceUnavailableError(provider, error_message)
        elif any(keyword in error_message.lower() for keyword in ['format', 'parse', 'json', 'xml']):
            return DataFormatError(provider, error_message)
        elif any(keyword in error_message.lower() for keyword in ['quota', 'exceeded', 'limit']):
            return QuotaExceededError(provider, error_message)
        else:
            return ProviderError(
                provider=provider,
                error_code="UNKNOWN_ERROR",
                message=error_message,
                details={'original_type': error_type}
            )
    
    def _get_recovery_strategy(
        self, 
        error: ProviderError, 
        context: ErrorContext
    ) -> RecoveryStrategy:
        """Get recovery strategy for the error."""
        # Check for custom strategy based on error type
        strategy = self._error_strategies.get(type(error))
        
        if strategy is None:
            # Default strategy for unknown errors
            strategy = RecoveryStrategy(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                delay_seconds=30.0,
                max_attempts=2
            )
        
        # Adjust strategy based on error history
        error_key = f"{context.provider.value}:{context.client_id}:{error.error_code}"
        recent_errors = self._get_recent_errors(error_key, hours=1)
        
        if len(recent_errors) > 5:
            # Too many recent errors, be more conservative
            strategy = RecoveryStrategy(
                action=RecoveryAction.SKIP_PROVIDER,
                max_attempts=1
            )
        
        return strategy
    
    def _should_retry(self, strategy: RecoveryStrategy, context: ErrorContext) -> bool:
        """Determine if operation should be retried."""
        if context.attempt_number >= strategy.max_attempts:
            return False
        
        if strategy.action in [RecoveryAction.FAIL_OPERATION, RecoveryAction.SKIP_PROVIDER]:
            return False
        
        # Check if we've been trying for too long
        elapsed_time = datetime.utcnow() - context.start_time
        if elapsed_time > timedelta(hours=1):  # Don't retry for more than 1 hour
            return False
        
        return True
    
    def _assess_error_severity(
        self, 
        error: ProviderError, 
        context: ErrorContext
    ) -> ErrorSeverity:
        """Assess the severity of the error."""
        # Critical errors
        if isinstance(error, (AuthenticationError, AuthorizationError)):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if isinstance(error, QuotaExceededError):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if isinstance(error, (RateLimitError, ServiceUnavailableError)):
            return ErrorSeverity.MEDIUM
        
        # Check attempt number
        if context.attempt_number > 3:
            return ErrorSeverity.HIGH
        
        return ErrorSeverity.LOW
    
    def _generate_recovery_message(
        self, 
        error: ProviderError, 
        strategy: RecoveryStrategy
    ) -> str:
        """Generate human-readable recovery message."""
        action_messages = {
            RecoveryAction.RETRY_IMMEDIATELY: "Retrying operation immediately",
            RecoveryAction.RETRY_WITH_BACKOFF: f"Retrying with exponential backoff (base delay: {strategy.delay_seconds}s)",
            RecoveryAction.RETRY_AFTER_DELAY: f"Retrying after {strategy.delay_seconds}s delay",
            RecoveryAction.REFRESH_CREDENTIALS: "Refreshing credentials and retrying",
            RecoveryAction.SKIP_PROVIDER: f"Skipping {error.provider.value} provider due to persistent errors",
            RecoveryAction.FAIL_OPERATION: "Operation failed - manual intervention required",
            RecoveryAction.REDUCE_REQUEST_SIZE: "Reducing request size and retrying",
            RecoveryAction.SWITCH_REGION: "Switching to alternative region"
        }
        
        base_message = action_messages.get(strategy.action, "Unknown recovery action")
        return f"{base_message}. Error: {error.message}"
    
    def _log_error(self, error: ProviderError, context: ErrorContext):
        """Log the error with appropriate level."""
        log_data = {
            'provider': error.provider.value,
            'error_code': error.error_code,
            'operation': context.operation,
            'client_id': context.client_id,
            'attempt': context.attempt_number,
            'message': error.message
        }
        
        if isinstance(error, (AuthenticationError, AuthorizationError)):
            self.logger.error(f"Critical error in {context.operation}: {log_data}")
        elif isinstance(error, (RateLimitError, ServiceUnavailableError)):
            self.logger.warning(f"Recoverable error in {context.operation}: {log_data}")
        else:
            self.logger.info(f"Error in {context.operation}: {log_data}")
    
    def _record_error_history(self, error: ProviderError, context: ErrorContext):
        """Record error in history for pattern analysis."""
        error_key = f"{context.provider.value}:{context.client_id}:{error.error_code}"
        
        if error_key not in self._error_history:
            self._error_history[error_key] = []
        
        error_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': context.operation,
            'attempt_number': context.attempt_number,
            'error_message': error.message,
            'error_details': error.details
        }
        
        self._error_history[error_key].append(error_record)
        
        # Keep only recent errors (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self._error_history[error_key] = [
            record for record in self._error_history[error_key]
            if datetime.fromisoformat(record['timestamp']) > cutoff_time
        ]
    
    def _get_recent_errors(self, error_key: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent errors for a specific error key."""
        if error_key not in self._error_history:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            record for record in self._error_history[error_key]
            if datetime.fromisoformat(record['timestamp']) > cutoff_time
        ]
    
    def get_error_statistics(self, provider: Optional[ProviderType] = None) -> Dict[str, Any]:
        """Get error statistics for monitoring and analysis."""
        stats = {
            'total_errors': 0,
            'errors_by_provider': {},
            'errors_by_type': {},
            'recent_error_rate': 0.0,
            'most_common_errors': []
        }
        
        all_errors = []
        for error_key, error_list in self._error_history.items():
            provider_name = error_key.split(':')[0]
            
            if provider and provider.value != provider_name:
                continue
            
            all_errors.extend(error_list)
            
            # Count by provider
            if provider_name not in stats['errors_by_provider']:
                stats['errors_by_provider'][provider_name] = 0
            stats['errors_by_provider'][provider_name] += len(error_list)
        
        stats['total_errors'] = len(all_errors)
        
        # Calculate recent error rate (last hour)
        recent_errors = [
            error for error in all_errors
            if datetime.fromisoformat(error['timestamp']) > datetime.utcnow() - timedelta(hours=1)
        ]
        stats['recent_error_rate'] = len(recent_errors)
        
        # Count by error type
        error_codes = {}
        for error in all_errors:
            # Extract error code from error key
            for key in self._error_history.keys():
                if any(record['timestamp'] == error['timestamp'] for record in self._error_history[key]):
                    error_code = key.split(':')[2]
                    error_codes[error_code] = error_codes.get(error_code, 0) + 1
                    break
        
        stats['errors_by_type'] = error_codes
        stats['most_common_errors'] = sorted(
            error_codes.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return stats
    
    def clear_error_history(self, provider: Optional[ProviderType] = None):
        """Clear error history for a provider or all providers."""
        if provider:
            keys_to_remove = [
                key for key in self._error_history.keys()
                if key.startswith(f"{provider.value}:")
            ]
            for key in keys_to_remove:
                del self._error_history[key]
        else:
            self._error_history.clear()
        
        self.logger.info(f"Cleared error history for {provider.value if provider else 'all providers'}")


class RetryDecorator:
    """Decorator for automatic retry with error handling."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        error_handler: Optional[ProviderErrorHandler] = None
    ):
        """
        Initialize retry decorator.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff
            jitter: Whether to add random jitter to delays
            error_handler: Custom error handler instance
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.error_handler = error_handler or ProviderErrorHandler()
    
    def __call__(self, func: Callable):
        """Apply retry logic to function."""
        async def wrapper(*args, **kwargs):
            last_error = None
            start_time = datetime.utcnow()
            
            for attempt in range(1, self.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as error:
                    last_error = error
                    
                    # Create error context
                    context = ErrorContext(
                        operation=func.__name__,
                        provider=getattr(args[0], 'provider', ProviderType.AWS),  # Assume first arg is adapter
                        client_id=kwargs.get('client_id', 'unknown'),
                        attempt_number=attempt,
                        max_attempts=self.max_attempts,
                        start_time=start_time
                    )
                    
                    # Handle error
                    result = await self.error_handler.handle_error(error, context)
                    
                    if not result.should_retry or attempt >= self.max_attempts:
                        break
                    
                    # Wait before retry
                    if result.delay_seconds > 0:
                        await asyncio.sleep(result.delay_seconds)
            
            # All retries exhausted
            raise last_error
        
        return wrapper


# Global error handler instance
error_handler = ProviderErrorHandler()