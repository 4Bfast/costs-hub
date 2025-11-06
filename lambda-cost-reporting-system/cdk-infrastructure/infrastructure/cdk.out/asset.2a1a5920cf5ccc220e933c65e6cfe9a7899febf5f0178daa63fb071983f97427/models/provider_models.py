"""
Provider Models

This module defines the data models for cloud provider integration,
including credentials, validation, and cost data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod
import json


class ProviderType(Enum):
    """Supported cloud provider types."""
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "AZURE"


class CredentialType(Enum):
    """Types of credentials supported."""
    IAM_ROLE = "iam_role"
    ACCESS_KEY = "access_key"
    SERVICE_ACCOUNT = "service_account"
    MANAGED_IDENTITY = "managed_identity"
    CLIENT_SECRET = "client_secret"


class ValidationStatus(Enum):
    """Credential validation status."""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    UNKNOWN = "unknown"


class DataCollectionStatus(Enum):
    """Status of data collection operations."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"


@dataclass
class ProviderCredentials(ABC):
    """Abstract base class for provider credentials."""
    provider: ProviderType
    credential_type: CredentialType
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert credentials to dictionary (excluding sensitive data)."""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate credential format and basic requirements."""
        pass
    
    def is_expired(self) -> bool:
        """Check if credentials are expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


@dataclass
class AWSCredentials(ProviderCredentials):
    """AWS-specific credentials."""
    role_arn: Optional[str] = None
    external_id: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    session_token: Optional[str] = None
    region: str = 'us-east-1'
    
    def __init__(self, **kwargs):
        """Initialize AWS credentials."""
        # Determine credential type
        if kwargs.get('role_arn'):
            credential_type = CredentialType.IAM_ROLE
        elif kwargs.get('access_key_id'):
            credential_type = CredentialType.ACCESS_KEY
        else:
            raise ValueError("Either role_arn or access_key_id must be provided")
        
        # Initialize parent class
        super().__init__(
            provider=ProviderType.AWS,
            credential_type=credential_type,
            **{k: v for k, v in kwargs.items() if k in ['created_at', 'updated_at', 'expires_at', 'is_active']}
        )
        
        # Set AWS-specific fields
        self.role_arn = kwargs.get('role_arn')
        self.external_id = kwargs.get('external_id')
        self.access_key_id = kwargs.get('access_key_id')
        self.secret_access_key = kwargs.get('secret_access_key')
        self.session_token = kwargs.get('session_token')
        self.region = kwargs.get('region', 'us-east-1')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary without sensitive data."""
        return {
            'provider': self.provider.value,
            'credential_type': self.credential_type.value,
            'role_arn': self.role_arn,
            'external_id': self.external_id,
            'region': self.region,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }
    
    def validate(self) -> bool:
        """Validate AWS credentials format."""
        if self.credential_type == CredentialType.IAM_ROLE:
            return bool(self.role_arn and self.role_arn.startswith('arn:aws:iam::'))
        elif self.credential_type == CredentialType.ACCESS_KEY:
            return bool(self.access_key_id and self.secret_access_key)
        return False


@dataclass
class GCPCredentials(ProviderCredentials):
    """GCP-specific credentials."""
    service_account_key: Optional[Dict[str, Any]] = None
    service_account_email: Optional[str] = None
    project_id: Optional[str] = None
    key_file_path: Optional[str] = None
    
    def __init__(self, **kwargs):
        """Initialize GCP credentials."""
        # Initialize parent class
        super().__init__(
            provider=ProviderType.GCP,
            credential_type=CredentialType.SERVICE_ACCOUNT,
            **{k: v for k, v in kwargs.items() if k in ['created_at', 'updated_at', 'expires_at', 'is_active']}
        )
        
        # Set GCP-specific fields
        self.service_account_key = kwargs.get('service_account_key')
        self.service_account_email = kwargs.get('service_account_email')
        self.project_id = kwargs.get('project_id')
        self.key_file_path = kwargs.get('key_file_path')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary without sensitive data."""
        return {
            'provider': self.provider.value,
            'credential_type': self.credential_type.value,
            'service_account_email': self.service_account_email,
            'project_id': self.project_id,
            'key_file_path': self.key_file_path,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }
    
    def validate(self) -> bool:
        """Validate GCP credentials format."""
        if self.service_account_key:
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            return all(field in self.service_account_key for field in required_fields)
        return bool(self.service_account_email and self.project_id)


@dataclass
class AzureCredentials(ProviderCredentials):
    """Azure-specific credentials."""
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    subscription_id: Optional[str] = None
    managed_identity_client_id: Optional[str] = None
    
    def __init__(self, **kwargs):
        """Initialize Azure credentials."""
        # Determine credential type
        if kwargs.get('managed_identity_client_id'):
            credential_type = CredentialType.MANAGED_IDENTITY
        elif kwargs.get('client_secret'):
            credential_type = CredentialType.CLIENT_SECRET
        else:
            raise ValueError("Either managed_identity_client_id or client_secret must be provided")
        
        # Initialize parent class
        super().__init__(
            provider=ProviderType.AZURE,
            credential_type=credential_type,
            **{k: v for k, v in kwargs.items() if k in ['created_at', 'updated_at', 'expires_at', 'is_active']}
        )
        
        # Set Azure-specific fields
        self.tenant_id = kwargs.get('tenant_id')
        self.client_id = kwargs.get('client_id')
        self.client_secret = kwargs.get('client_secret')
        self.subscription_id = kwargs.get('subscription_id')
        self.managed_identity_client_id = kwargs.get('managed_identity_client_id')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary without sensitive data."""
        return {
            'provider': self.provider.value,
            'credential_type': self.credential_type.value,
            'tenant_id': self.tenant_id,
            'client_id': self.client_id,
            'subscription_id': self.subscription_id,
            'managed_identity_client_id': self.managed_identity_client_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }
    
    def validate(self) -> bool:
        """Validate Azure credentials format."""
        if self.credential_type == CredentialType.CLIENT_SECRET:
            return bool(self.tenant_id and self.client_id and self.client_secret and self.subscription_id)
        elif self.credential_type == CredentialType.MANAGED_IDENTITY:
            return bool(self.subscription_id)
        return False


@dataclass
class CredentialValidation:
    """Result of credential validation."""
    status: ValidationStatus
    is_valid: bool
    error_message: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    missing_permissions: List[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)
    validation_duration_seconds: float = 0.0
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'status': self.status.value,
            'is_valid': self.is_valid,
            'error_message': self.error_message,
            'permissions': self.permissions,
            'missing_permissions': self.missing_permissions,
            'validated_at': self.validated_at.isoformat(),
            'validation_duration_seconds': self.validation_duration_seconds,
            'additional_info': self.additional_info
        }


@dataclass
class DateRange:
    """Date range for cost data collection."""
    start_date: date
    end_date: date
    
    def __post_init__(self):
        """Validate date range."""
        if self.start_date > self.end_date:
            raise ValueError("Start date must be before or equal to end date")
    
    @property
    def days(self) -> int:
        """Get number of days in the range."""
        return (self.end_date - self.start_date).days + 1
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }


@dataclass
class ProviderAccount:
    """Information about a cloud provider account."""
    account_id: str
    account_name: Optional[str]
    provider: ProviderType
    is_active: bool = True
    tags: Dict[str, str] = field(default_factory=dict)
    regions: List[str] = field(default_factory=list)
    cost_allocation_tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'account_id': self.account_id,
            'account_name': self.account_name,
            'provider': self.provider.value,
            'is_active': self.is_active,
            'tags': self.tags,
            'regions': self.regions,
            'cost_allocation_tags': self.cost_allocation_tags
        }


@dataclass
class ProviderService:
    """Information about a cloud provider service."""
    service_id: str
    service_name: str
    provider: ProviderType
    category: str
    description: Optional[str] = None
    pricing_model: Optional[str] = None
    regions_available: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'service_id': self.service_id,
            'service_name': self.service_name,
            'provider': self.provider.value,
            'category': self.category,
            'description': self.description,
            'pricing_model': self.pricing_model,
            'regions_available': self.regions_available
        }


@dataclass
class ProviderCostData:
    """Raw cost data from a cloud provider."""
    client_id: str
    provider: ProviderType
    date_range: DateRange
    total_cost: Decimal
    currency: str
    accounts: List[ProviderAccount] = field(default_factory=list)
    services: Dict[str, Any] = field(default_factory=dict)
    regions: Dict[str, Decimal] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    collection_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'client_id': self.client_id,
            'provider': self.provider.value,
            'date_range': self.date_range.to_dict(),
            'total_cost': float(self.total_cost),
            'currency': self.currency,
            'accounts': [account.to_dict() for account in self.accounts],
            'services': self.services,
            'regions': {region: float(cost) for region, cost in self.regions.items()},
            'collection_metadata': self.collection_metadata
        }


@dataclass
class CollectionResult:
    """Result of a cost data collection operation."""
    status: DataCollectionStatus
    provider: ProviderType
    client_id: str
    date_range: DateRange
    cost_data: Optional[ProviderCostData] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    collection_duration_seconds: float = 0.0
    api_calls_made: int = 0
    records_collected: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'status': self.status.value,
            'provider': self.provider.value,
            'client_id': self.client_id,
            'date_range': self.date_range.to_dict(),
            'cost_data': self.cost_data.to_dict() if self.cost_data else None,
            'error_message': self.error_message,
            'warnings': self.warnings,
            'collection_duration_seconds': self.collection_duration_seconds,
            'api_calls_made': self.api_calls_made,
            'records_collected': self.records_collected,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class ProviderError(Exception):
    """Base exception for provider-related errors."""
    provider: ProviderType
    error_code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    retry_after: Optional[int] = None
    is_retryable: bool = False
    
    def __str__(self) -> str:
        return f"{self.provider.value} Error [{self.error_code}]: {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'provider': self.provider.value,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'retry_after': self.retry_after,
            'is_retryable': self.is_retryable
        }


class AuthenticationError(ProviderError):
    """Authentication-related errors."""
    def __init__(self, provider: ProviderType, message: str, **kwargs):
        super().__init__(
            provider=provider,
            error_code="AUTHENTICATION_ERROR",
            message=message,
            is_retryable=False,
            **kwargs
        )


class AuthorizationError(ProviderError):
    """Authorization/permission-related errors."""
    def __init__(self, provider: ProviderType, message: str, **kwargs):
        super().__init__(
            provider=provider,
            error_code="AUTHORIZATION_ERROR",
            message=message,
            is_retryable=False,
            **kwargs
        )


class RateLimitError(ProviderError):
    """Rate limiting errors."""
    def __init__(self, provider: ProviderType, message: str, retry_after: int = None, **kwargs):
        super().__init__(
            provider=provider,
            error_code="RATE_LIMIT_ERROR",
            message=message,
            retry_after=retry_after,
            is_retryable=True,
            **kwargs
        )


class ServiceUnavailableError(ProviderError):
    """Service unavailability errors."""
    def __init__(self, provider: ProviderType, message: str, **kwargs):
        super().__init__(
            provider=provider,
            error_code="SERVICE_UNAVAILABLE",
            message=message,
            is_retryable=True,
            **kwargs
        )


class DataFormatError(ProviderError):
    """Data format/parsing errors."""
    def __init__(self, provider: ProviderType, message: str, **kwargs):
        super().__init__(
            provider=provider,
            error_code="DATA_FORMAT_ERROR",
            message=message,
            is_retryable=False,
            **kwargs
        )


class QuotaExceededError(ProviderError):
    """Quota/limit exceeded errors."""
    def __init__(self, provider: ProviderType, message: str, **kwargs):
        super().__init__(
            provider=provider,
            error_code="QUOTA_EXCEEDED",
            message=message,
            is_retryable=False,
            **kwargs
        )


# Utility functions for working with provider models
def create_credentials(provider: ProviderType, **kwargs) -> ProviderCredentials:
    """
    Factory function to create provider-specific credentials.
    
    Args:
        provider: The cloud provider type
        **kwargs: Provider-specific credential parameters
        
    Returns:
        Provider-specific credentials object
    """
    if provider == ProviderType.AWS:
        return AWSCredentials(**kwargs)
    elif provider == ProviderType.GCP:
        return GCPCredentials(**kwargs)
    elif provider == ProviderType.AZURE:
        return AzureCredentials(**kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def validate_date_range(start_date: Union[str, date], end_date: Union[str, date]) -> DateRange:
    """
    Validate and create a DateRange object.
    
    Args:
        start_date: Start date as string (YYYY-MM-DD) or date object
        end_date: End date as string (YYYY-MM-DD) or date object
        
    Returns:
        DateRange object
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    return DateRange(start_date=start_date, end_date=end_date)


def get_required_permissions(provider: ProviderType) -> List[str]:
    """
    Get the list of required permissions for a cloud provider.
    
    Args:
        provider: The cloud provider type
        
    Returns:
        List of required permissions
    """
    permissions_map = {
        ProviderType.AWS: [
            'ce:GetCostAndUsage',
            'ce:GetUsageReport',
            'ce:GetDimensionValues',
            'ce:GetReservationCoverage',
            'ce:GetReservationPurchaseRecommendation',
            'ce:GetReservationUtilization',
            'ce:GetSavingsPlansUtilization',
            'organizations:ListAccounts',
            'organizations:DescribeOrganization'
        ],
        ProviderType.GCP: [
            'cloudbilling.billingAccounts.get',
            'cloudbilling.billingAccounts.list',
            'cloudbilling.projects.list',
            'cloudbilling.budgets.list',
            'cloudbilling.budgets.get',
            'bigquery.datasets.get',
            'bigquery.tables.get',
            'bigquery.jobs.create'
        ],
        ProviderType.AZURE: [
            'Microsoft.Consumption/*/read',
            'Microsoft.CostManagement/*/read',
            'Microsoft.Billing/*/read',
            'Microsoft.Resources/subscriptions/read',
            'Microsoft.Resources/subscriptions/resourceGroups/read'
        ]
    }
    
    return permissions_map.get(provider, [])