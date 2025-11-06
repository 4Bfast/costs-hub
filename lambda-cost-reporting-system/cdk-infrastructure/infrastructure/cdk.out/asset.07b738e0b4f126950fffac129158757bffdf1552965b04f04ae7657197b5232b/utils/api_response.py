"""
API Response Utilities

This module provides utilities for standardizing API responses across
the multi-cloud cost analytics platform.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal


logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal objects."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class APIError(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(APIError):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, field_errors: Optional[Dict[str, str]] = None):
        super().__init__(message, status_code=400)
        self.field_errors = field_errors or {}


class AuthenticationError(APIError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class AuthorizationError(APIError):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class NotFoundError(APIError):
    """Raised when resource is not found."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class APIResponse:
    """
    Standardized API response builder for Lambda functions.
    
    Provides consistent response formatting for API Gateway integration
    with proper CORS headers and error handling.
    """
    
    def __init__(self, enable_cors: bool = True):
        """
        Initialize API response builder.
        
        Args:
            enable_cors: Whether to include CORS headers
        """
        self.enable_cors = enable_cors
        self.default_headers = {
            'Content-Type': 'application/json'
        }
        
        if enable_cors:
            self.default_headers.update({
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            })
    
    def success(self, data: Any = None, message: Optional[str] = None, 
                status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create a successful API response.
        
        Args:
            data: Response data
            message: Optional success message
            status_code: HTTP status code (default: 200)
            headers: Additional headers
            
        Returns:
            API Gateway response dictionary
        """
        response_body = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if message:
            response_body['message'] = message
        
        if data is not None:
            response_body['data'] = data
        
        response_headers = self.default_headers.copy()
        if headers:
            response_headers.update(headers)
        
        return {
            'statusCode': status_code,
            'headers': response_headers,
            'body': json.dumps(response_body, cls=DecimalEncoder)
        }
    
    def error(self, message: str, status_code: int = 500, 
              details: Optional[Dict[str, Any]] = None,
              field_errors: Optional[Dict[str, str]] = None,
              headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create an error API response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
            field_errors: Field-specific validation errors
            headers: Additional headers
            
        Returns:
            API Gateway response dictionary
        """
        response_body = {
            'success': False,
            'error': {
                'message': message,
                'code': status_code
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if details:
            response_body['error']['details'] = details
        
        if field_errors:
            response_body['error']['field_errors'] = field_errors
        
        response_headers = self.default_headers.copy()
        if headers:
            response_headers.update(headers)
        
        # Add retry-after header for rate limit errors
        if status_code == 429 and details and 'retry_after' in details:
            response_headers['Retry-After'] = str(details['retry_after'])
        
        return {
            'statusCode': status_code,
            'headers': response_headers,
            'body': json.dumps(response_body, cls=DecimalEncoder)
        }
    
    def paginated(self, data: List[Any], total_count: int, page: int = 1, 
                  page_size: int = 50, message: Optional[str] = None,
                  headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create a paginated API response.
        
        Args:
            data: List of items for current page
            total_count: Total number of items
            page: Current page number (1-based)
            page_size: Number of items per page
            message: Optional message
            headers: Additional headers
            
        Returns:
            API Gateway response dictionary
        """
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        response_data = {
            'items': data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            }
        }
        
        if has_next:
            response_data['pagination']['next_page'] = page + 1
        
        if has_prev:
            response_data['pagination']['prev_page'] = page - 1
        
        return self.success(
            data=response_data,
            message=message,
            headers=headers
        )
    
    def options(self, allowed_methods: List[str] = None) -> Dict[str, Any]:
        """
        Create an OPTIONS response for CORS preflight requests.
        
        Args:
            allowed_methods: List of allowed HTTP methods
            
        Returns:
            API Gateway response dictionary
        """
        if not allowed_methods:
            allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        
        headers = self.default_headers.copy()
        headers['Access-Control-Allow-Methods'] = ','.join(allowed_methods)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    def from_exception(self, exception: Exception) -> Dict[str, Any]:
        """
        Create an error response from an exception.
        
        Args:
            exception: Exception to convert to response
            
        Returns:
            API Gateway response dictionary
        """
        if isinstance(exception, APIError):
            return self.error(
                message=exception.message,
                status_code=exception.status_code,
                details=exception.details,
                field_errors=getattr(exception, 'field_errors', None)
            )
        else:
            # Log unexpected errors
            logger.error(f"Unexpected error: {exception}", exc_info=True)
            
            return self.error(
                message="Internal server error",
                status_code=500,
                details={
                    'error_type': type(exception).__name__
                }
            )


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate that required fields are present in request data.
    
    Args:
        data: Request data dictionary
        required_fields: List of required field names
        
    Raises:
        ValidationError: If any required fields are missing
    """
    missing_fields = []
    field_errors = {}
    
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
            field_errors[field] = "This field is required"
        elif isinstance(data[field], str) and not data[field].strip():
            missing_fields.append(field)
            field_errors[field] = "This field cannot be empty"
    
    if missing_fields:
        raise ValidationError(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            field_errors=field_errors
        )


def validate_field_types(data: Dict[str, Any], field_types: Dict[str, type]) -> None:
    """
    Validate field types in request data.
    
    Args:
        data: Request data dictionary
        field_types: Dictionary mapping field names to expected types
        
    Raises:
        ValidationError: If any fields have incorrect types
    """
    field_errors = {}
    
    for field, expected_type in field_types.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                field_errors[field] = f"Expected {expected_type.__name__}, got {type(data[field]).__name__}"
    
    if field_errors:
        raise ValidationError(
            message="Invalid field types",
            field_errors=field_errors
        )


def validate_enum_fields(data: Dict[str, Any], enum_fields: Dict[str, List[str]]) -> None:
    """
    Validate enum fields in request data.
    
    Args:
        data: Request data dictionary
        enum_fields: Dictionary mapping field names to allowed values
        
    Raises:
        ValidationError: If any enum fields have invalid values
    """
    field_errors = {}
    
    for field, allowed_values in enum_fields.items():
        if field in data and data[field] is not None:
            if data[field] not in allowed_values:
                field_errors[field] = f"Must be one of: {', '.join(allowed_values)}"
    
    if field_errors:
        raise ValidationError(
            message="Invalid enum values",
            field_errors=field_errors
        )


def validate_date_range(start_date: str, end_date: str, max_days: int = 365) -> None:
    """
    Validate date range parameters.
    
    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format
        max_days: Maximum allowed date range in days
        
    Raises:
        ValidationError: If date range is invalid
    """
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError as e:
        raise ValidationError(f"Invalid date format: {e}")
    
    if start >= end:
        raise ValidationError("Start date must be before end date")
    
    if (end - start).days > max_days:
        raise ValidationError(f"Date range cannot exceed {max_days} days")
    
    if end > datetime.utcnow():
        raise ValidationError("End date cannot be in the future")


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Sanitize string input.
    
    Args:
        value: String value to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If string is too long
    """
    if not isinstance(value, str):
        raise ValidationError("Value must be a string")
    
    # Strip whitespace
    sanitized = value.strip()
    
    # Check length
    if len(sanitized) > max_length:
        raise ValidationError(f"String too long (max {max_length} characters)")
    
    return sanitized


def parse_pagination_params(query_params: Dict[str, str]) -> Dict[str, int]:
    """
    Parse pagination parameters from query string.
    
    Args:
        query_params: Query parameters dictionary
        
    Returns:
        Dictionary with page and page_size
        
    Raises:
        ValidationError: If pagination parameters are invalid
    """
    try:
        page = int(query_params.get('page', '1'))
        page_size = int(query_params.get('page_size', '50'))
    except ValueError:
        raise ValidationError("Page and page_size must be integers")
    
    if page < 1:
        raise ValidationError("Page must be >= 1")
    
    if page_size < 1 or page_size > 1000:
        raise ValidationError("Page size must be between 1 and 1000")
    
    return {
        'page': page,
        'page_size': page_size
    }