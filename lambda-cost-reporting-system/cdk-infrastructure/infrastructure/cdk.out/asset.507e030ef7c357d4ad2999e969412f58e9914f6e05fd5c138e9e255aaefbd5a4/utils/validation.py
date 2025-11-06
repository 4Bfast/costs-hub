"""
Request Validation Utilities

This module provides comprehensive request validation utilities
for the multi-cloud cost analytics API.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from decimal import Decimal, InvalidOperation
from email_validator import validate_email, EmailNotValidError

from ..models.multi_cloud_models import CloudProvider, ServiceCategory, Currency
from ..models.multi_tenant_models import ClientRole, SubscriptionTier
from ..utils.api_response import ValidationError


logger = logging.getLogger(__name__)


class RequestValidator:
    """
    Comprehensive request validation for API endpoints.
    """
    
    def __init__(self):
        """Initialize the request validator."""
        self.email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        self.aws_account_regex = re.compile(r'^\d{12}$')
        self.gcp_project_regex = re.compile(r'^[a-z][a-z0-9-]{4,28}[a-z0-9]$')
        self.azure_subscription_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    
    def validate_request_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate request data against a schema.
        
        Args:
            data: Request data to validate
            schema: Validation schema
            
        Returns:
            Validated and sanitized data
            
        Raises:
            ValidationError: If validation fails
        """
        errors = {}
        validated_data = {}
        
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data or data[field] is None:
                errors[field] = "This field is required"
            elif isinstance(data[field], str) and not data[field].strip():
                errors[field] = "This field cannot be empty"
        
        # Validate each field
        field_schemas = schema.get('fields', {})
        for field_name, field_schema in field_schemas.items():
            if field_name in data:
                try:
                    validated_value = self._validate_field(data[field_name], field_schema, field_name)
                    validated_data[field_name] = validated_value
                except ValidationError as e:
                    errors[field_name] = e.message
        
        if errors:
            raise ValidationError(
                message="Validation failed",
                field_errors=errors
            )
        
        return validated_data
    
    def _validate_field(self, value: Any, schema: Dict[str, Any], field_name: str) -> Any:
        """
        Validate a single field.
        
        Args:
            value: Field value
            schema: Field validation schema
            field_name: Field name for error messages
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If validation fails
        """
        field_type = schema.get('type')
        
        # Type validation
        if field_type == 'string':
            value = self._validate_string(value, schema, field_name)
        elif field_type == 'integer':
            value = self._validate_integer(value, schema, field_name)
        elif field_type == 'float':
            value = self._validate_float(value, schema, field_name)
        elif field_type == 'boolean':
            value = self._validate_boolean(value, schema, field_name)
        elif field_type == 'datetime':
            value = self._validate_datetime(value, schema, field_name)
        elif field_type == 'email':
            value = self._validate_email(value, schema, field_name)
        elif field_type == 'enum':
            value = self._validate_enum(value, schema, field_name)
        elif field_type == 'list':
            value = self._validate_list(value, schema, field_name)
        elif field_type == 'dict':
            value = self._validate_dict(value, schema, field_name)
        elif field_type == 'cloud_provider':
            value = self._validate_cloud_provider(value, field_name)
        elif field_type == 'service_category':
            value = self._validate_service_category(value, field_name)
        elif field_type == 'currency':
            value = self._validate_currency(value, field_name)
        elif field_type == 'client_role':
            value = self._validate_client_role(value, field_name)
        elif field_type == 'subscription_tier':
            value = self._validate_subscription_tier(value, field_name)
        elif field_type == 'aws_account_id':
            value = self._validate_aws_account_id(value, field_name)
        elif field_type == 'gcp_project_id':
            value = self._validate_gcp_project_id(value, field_name)
        elif field_type == 'azure_subscription_id':
            value = self._validate_azure_subscription_id(value, field_name)
        elif field_type == 'uuid':
            value = self._validate_uuid(value, field_name)
        
        # Custom validation function
        if 'validator' in schema:
            validator = schema['validator']
            if callable(validator):
                try:
                    value = validator(value)
                except Exception as e:
                    raise ValidationError(f"Custom validation failed: {e}")
        
        return value
    
    def _validate_string(self, value: Any, schema: Dict[str, Any], field_name: str) -> str:
        """Validate string field."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        # Strip whitespace
        value = value.strip()
        
        # Length validation
        min_length = schema.get('min_length', 0)
        max_length = schema.get('max_length', 1000)
        
        if len(value) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} characters")
        
        if len(value) > max_length:
            raise ValidationError(f"{field_name} must be at most {max_length} characters")
        
        # Pattern validation
        if 'pattern' in schema:
            pattern = re.compile(schema['pattern'])
            if not pattern.match(value):
                raise ValidationError(f"{field_name} format is invalid")
        
        return value
    
    def _validate_integer(self, value: Any, schema: Dict[str, Any], field_name: str) -> int:
        """Validate integer field."""
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be an integer")
        
        # Range validation
        min_value = schema.get('min_value')
        max_value = schema.get('max_value')
        
        if min_value is not None and value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")
        
        if max_value is not None and value > max_value:
            raise ValidationError(f"{field_name} must be at most {max_value}")
        
        return value
    
    def _validate_float(self, value: Any, schema: Dict[str, Any], field_name: str) -> float:
        """Validate float field."""
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a number")
        
        # Range validation
        min_value = schema.get('min_value')
        max_value = schema.get('max_value')
        
        if min_value is not None and value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")
        
        if max_value is not None and value > max_value:
            raise ValidationError(f"{field_name} must be at most {max_value}")
        
        return value
    
    def _validate_boolean(self, value: Any, schema: Dict[str, Any], field_name: str) -> bool:
        """Validate boolean field."""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            if value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif value.lower() in ('false', '0', 'no', 'off'):
                return False
        
        raise ValidationError(f"{field_name} must be a boolean")
    
    def _validate_datetime(self, value: Any, schema: Dict[str, Any], field_name: str) -> datetime:
        """Validate datetime field."""
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Try common formats
                    for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                except ValueError:
                    pass
        
        raise ValidationError(f"{field_name} must be a valid datetime")
    
    def _validate_email(self, value: Any, schema: Dict[str, Any], field_name: str) -> str:
        """Validate email field."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        try:
            # Use email-validator library for comprehensive validation
            validated_email = validate_email(value)
            return validated_email.email
        except EmailNotValidError:
            # Fallback to regex validation
            if not self.email_regex.match(value):
                raise ValidationError(f"{field_name} must be a valid email address")
            return value.lower()
    
    def _validate_enum(self, value: Any, schema: Dict[str, Any], field_name: str) -> str:
        """Validate enum field."""
        allowed_values = schema.get('values', [])
        if value not in allowed_values:
            raise ValidationError(f"{field_name} must be one of: {', '.join(allowed_values)}")
        return value
    
    def _validate_list(self, value: Any, schema: Dict[str, Any], field_name: str) -> List[Any]:
        """Validate list field."""
        if not isinstance(value, list):
            raise ValidationError(f"{field_name} must be a list")
        
        # Length validation
        min_length = schema.get('min_length', 0)
        max_length = schema.get('max_length', 1000)
        
        if len(value) < min_length:
            raise ValidationError(f"{field_name} must have at least {min_length} items")
        
        if len(value) > max_length:
            raise ValidationError(f"{field_name} must have at most {max_length} items")
        
        # Item validation
        if 'item_schema' in schema:
            validated_items = []
            for i, item in enumerate(value):
                try:
                    validated_item = self._validate_field(item, schema['item_schema'], f"{field_name}[{i}]")
                    validated_items.append(validated_item)
                except ValidationError as e:
                    raise ValidationError(f"{field_name}[{i}]: {e.message}")
            return validated_items
        
        return value
    
    def _validate_dict(self, value: Any, schema: Dict[str, Any], field_name: str) -> Dict[str, Any]:
        """Validate dictionary field."""
        if not isinstance(value, dict):
            raise ValidationError(f"{field_name} must be a dictionary")
        
        # Nested schema validation
        if 'schema' in schema:
            return self.validate_request_data(value, schema['schema'])
        
        return value
    
    def _validate_cloud_provider(self, value: Any, field_name: str) -> CloudProvider:
        """Validate cloud provider field."""
        if isinstance(value, CloudProvider):
            return value
        
        if isinstance(value, str):
            try:
                return CloudProvider(value.upper())
            except ValueError:
                pass
        
        valid_providers = [p.value for p in CloudProvider]
        raise ValidationError(f"{field_name} must be one of: {', '.join(valid_providers)}")
    
    def _validate_service_category(self, value: Any, field_name: str) -> ServiceCategory:
        """Validate service category field."""
        if isinstance(value, ServiceCategory):
            return value
        
        if isinstance(value, str):
            try:
                return ServiceCategory(value.lower())
            except ValueError:
                pass
        
        valid_categories = [c.value for c in ServiceCategory]
        raise ValidationError(f"{field_name} must be one of: {', '.join(valid_categories)}")
    
    def _validate_currency(self, value: Any, field_name: str) -> Currency:
        """Validate currency field."""
        if isinstance(value, Currency):
            return value
        
        if isinstance(value, str):
            try:
                return Currency(value.upper())
            except ValueError:
                pass
        
        valid_currencies = [c.value for c in Currency]
        raise ValidationError(f"{field_name} must be one of: {', '.join(valid_currencies)}")
    
    def _validate_client_role(self, value: Any, field_name: str) -> ClientRole:
        """Validate client role field."""
        if isinstance(value, ClientRole):
            return value
        
        if isinstance(value, str):
            try:
                return ClientRole(value.lower())
            except ValueError:
                pass
        
        valid_roles = [r.value for r in ClientRole]
        raise ValidationError(f"{field_name} must be one of: {', '.join(valid_roles)}")
    
    def _validate_subscription_tier(self, value: Any, field_name: str) -> SubscriptionTier:
        """Validate subscription tier field."""
        if isinstance(value, SubscriptionTier):
            return value
        
        if isinstance(value, str):
            try:
                return SubscriptionTier(value.lower())
            except ValueError:
                pass
        
        valid_tiers = [t.value for t in SubscriptionTier]
        raise ValidationError(f"{field_name} must be one of: {', '.join(valid_tiers)}")
    
    def _validate_aws_account_id(self, value: Any, field_name: str) -> str:
        """Validate AWS account ID."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        if not self.aws_account_regex.match(value):
            raise ValidationError(f"{field_name} must be a 12-digit AWS account ID")
        
        return value
    
    def _validate_gcp_project_id(self, value: Any, field_name: str) -> str:
        """Validate GCP project ID."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        if not self.gcp_project_regex.match(value):
            raise ValidationError(f"{field_name} must be a valid GCP project ID")
        
        return value
    
    def _validate_azure_subscription_id(self, value: Any, field_name: str) -> str:
        """Validate Azure subscription ID."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        if not self.azure_subscription_regex.match(value):
            raise ValidationError(f"{field_name} must be a valid Azure subscription ID (UUID format)")
        
        return value
    
    def _validate_uuid(self, value: Any, field_name: str) -> str:
        """Validate UUID field."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        if not self.uuid_regex.match(value):
            raise ValidationError(f"{field_name} must be a valid UUID")
        
        return value


# Common validation schemas
COST_DATA_QUERY_SCHEMA = {
    'fields': {
        'start_date': {'type': 'datetime'},
        'end_date': {'type': 'datetime'},
        'provider': {'type': 'cloud_provider'},
        'granularity': {
            'type': 'enum',
            'values': ['daily', 'weekly', 'monthly']
        },
        'page': {'type': 'integer', 'min_value': 1},
        'page_size': {'type': 'integer', 'min_value': 1, 'max_value': 1000}
    }
}

CLIENT_UPDATE_SCHEMA = {
    'fields': {
        'organization_name': {
            'type': 'string',
            'min_length': 1,
            'max_length': 255
        },
        'billing_preferences': {'type': 'dict'},
        'ai_preferences': {'type': 'dict'},
        'notification_preferences': {'type': 'dict'}
    }
}

CLOUD_ACCOUNT_SCHEMA = {
    'required': ['account_id', 'account_name', 'provider'],
    'fields': {
        'account_id': {'type': 'string', 'min_length': 1, 'max_length': 100},
        'account_name': {'type': 'string', 'min_length': 1, 'max_length': 255},
        'provider': {'type': 'cloud_provider'},
        'regions': {
            'type': 'list',
            'item_schema': {'type': 'string'}
        },
        'cost_allocation_tags': {'type': 'dict'},
        'monthly_budget': {'type': 'float', 'min_value': 0},
        'currency': {'type': 'currency'}
    }
}

WEBHOOK_SCHEMA = {
    'required': ['url', 'events'],
    'fields': {
        'url': {
            'type': 'string',
            'pattern': r'^https?://.*'
        },
        'events': {
            'type': 'list',
            'item_schema': {
                'type': 'enum',
                'values': ['anomaly_detected', 'budget_exceeded', 'forecast_updated', 'cost_spike']
            }
        },
        'secret': {'type': 'string', 'min_length': 8},
        'active': {'type': 'boolean'}
    }
}


def validate_request_data(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate request data using a schema.
    
    Args:
        data: Request data to validate
        schema: Validation schema
        
    Returns:
        Validated data
        
    Raises:
        ValidationError: If validation fails
    """
    validator = RequestValidator()
    return validator.validate_request_data(data, schema)


def validate_date_range(start_date: str, end_date: str, max_days: int = 365) -> Tuple[datetime, datetime]:
    """
    Validate and parse date range.
    
    Args:
        start_date: Start date string
        end_date: End date string
        max_days: Maximum allowed range in days
        
    Returns:
        Tuple of parsed start and end dates
        
    Raises:
        ValidationError: If date range is invalid
    """
    validator = RequestValidator()
    
    try:
        start = validator._validate_datetime(start_date, {}, 'start_date')
        end = validator._validate_datetime(end_date, {}, 'end_date')
    except ValidationError:
        raise
    
    if start >= end:
        raise ValidationError("Start date must be before end date")
    
    if (end - start).days > max_days:
        raise ValidationError(f"Date range cannot exceed {max_days} days")
    
    if end > datetime.utcnow():
        raise ValidationError("End date cannot be in the future")
    
    return start, end


def validate_pagination_params(query_params: Dict[str, str]) -> Dict[str, int]:
    """
    Validate pagination parameters.
    
    Args:
        query_params: Query parameters
        
    Returns:
        Dictionary with validated page and page_size
        
    Raises:
        ValidationError: If parameters are invalid
    """
    validator = RequestValidator()
    
    page = validator._validate_integer(
        query_params.get('page', '1'),
        {'min_value': 1},
        'page'
    )
    
    page_size = validator._validate_integer(
        query_params.get('page_size', '50'),
        {'min_value': 1, 'max_value': 1000},
        'page_size'
    )
    
    return {'page': page, 'page_size': page_size}