"""
Multi-Tenant Client Management Models

This module defines the enhanced data structures for multi-tenant client management
in the multi-cloud cost analytics platform. It extends the existing client configuration
to support multiple cloud providers and enhanced tenant isolation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import uuid
import json

from .multi_cloud_models import CloudProvider, Currency
from .config_models import ClientStatus, ReportConfig, BrandingConfig


class ClientRole(Enum):
    """Client user roles for RBAC."""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class SubscriptionTier(Enum):
    """Client subscription tiers."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class OnboardingStatus(Enum):
    """Client onboarding status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CloudCredentials:
    """Base class for cloud provider credentials."""
    provider: CloudProvider
    credential_type: str
    encrypted_data: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = False
    last_validated: Optional[datetime] = None
    validation_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'provider': self.provider.value,
            'credential_type': self.credential_type,
            'encrypted_data': self.encrypted_data,
            'is_valid': self.is_valid,
            'last_validated': self.last_validated.isoformat() if self.last_validated else None,
            'validation_error': self.validation_error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CloudCredentials':
        """Create CloudCredentials from dictionary."""
        return cls(
            provider=CloudProvider(data['provider']),
            credential_type=data['credential_type'],
            encrypted_data=data.get('encrypted_data', {}),
            is_valid=data.get('is_valid', False),
            last_validated=datetime.fromisoformat(data['last_validated']) if data.get('last_validated') else None,
            validation_error=data.get('validation_error')
        )


@dataclass
class AWSCredentials(CloudCredentials):
    """AWS-specific credentials."""
    
    def __init__(self, access_key_id: str, secret_access_key: str, 
                 session_token: Optional[str] = None, role_arn: Optional[str] = None,
                 external_id: Optional[str] = None, region: str = "us-east-1"):
        super().__init__(
            provider=CloudProvider.AWS,
            credential_type="access_key" if not role_arn else "assume_role"
        )
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token
        self.role_arn = role_arn
        self.external_id = external_id
        self.region = region
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        base_dict = super().to_dict()
        base_dict.update({
            'access_key_id': self.access_key_id,
            'secret_access_key': self.secret_access_key,
            'session_token': self.session_token,
            'role_arn': self.role_arn,
            'external_id': self.external_id,
            'region': self.region
        })
        return base_dict


@dataclass
class GCPCredentials(CloudCredentials):
    """GCP-specific credentials."""
    
    def __init__(self, service_account_key: Dict[str, Any], project_id: str):
        super().__init__(
            provider=CloudProvider.GCP,
            credential_type="service_account"
        )
        self.service_account_key = service_account_key
        self.project_id = project_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        base_dict = super().to_dict()
        base_dict.update({
            'service_account_key': self.service_account_key,
            'project_id': self.project_id
        })
        return base_dict


@dataclass
class AzureCredentials(CloudCredentials):
    """Azure-specific credentials."""
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str, subscription_id: str):
        super().__init__(
            provider=CloudProvider.AZURE,
            credential_type="service_principal"
        )
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        base_dict = super().to_dict()
        base_dict.update({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'tenant_id': self.tenant_id,
            'subscription_id': self.subscription_id
        })
        return base_dict


@dataclass
class CloudAccount:
    """Cloud provider account configuration."""
    account_id: str
    account_name: str
    provider: CloudProvider
    credentials: CloudCredentials
    regions: List[str] = field(default_factory=list)
    cost_allocation_tags: Dict[str, str] = field(default_factory=dict)
    is_active: bool = True
    monthly_budget: Optional[Decimal] = None
    currency: Currency = Currency.USD
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate cloud account configuration."""
        if not self.account_id.strip():
            raise ValueError("Account ID cannot be empty")
        if not self.account_name.strip():
            raise ValueError("Account name cannot be empty")
        if self.monthly_budget is not None and self.monthly_budget < 0:
            raise ValueError("Monthly budget cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'account_id': self.account_id,
            'account_name': self.account_name,
            'provider': self.provider.value,
            'credentials': self.credentials.to_dict(),
            'regions': self.regions,
            'cost_allocation_tags': self.cost_allocation_tags,
            'is_active': self.is_active,
            'monthly_budget': float(self.monthly_budget) if self.monthly_budget else None,
            'currency': self.currency.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CloudAccount':
        """Create CloudAccount from dictionary."""
        provider = CloudProvider(data['provider'])
        
        # Create appropriate credentials based on provider
        cred_data = data['credentials']
        if provider == CloudProvider.AWS:
            credentials = AWSCredentials(
                access_key_id=cred_data.get('access_key_id', ''),
                secret_access_key=cred_data.get('secret_access_key', ''),
                session_token=cred_data.get('session_token'),
                role_arn=cred_data.get('role_arn'),
                external_id=cred_data.get('external_id'),
                region=cred_data.get('region', 'us-east-1')
            )
        elif provider == CloudProvider.GCP:
            credentials = GCPCredentials(
                service_account_key=cred_data.get('service_account_key', {}),
                project_id=cred_data.get('project_id', '')
            )
        elif provider == CloudProvider.AZURE:
            credentials = AzureCredentials(
                client_id=cred_data.get('client_id', ''),
                client_secret=cred_data.get('client_secret', ''),
                tenant_id=cred_data.get('tenant_id', ''),
                subscription_id=cred_data.get('subscription_id', '')
            )
        else:
            credentials = CloudCredentials.from_dict(cred_data)
        
        return cls(
            account_id=data['account_id'],
            account_name=data['account_name'],
            provider=provider,
            credentials=credentials,
            regions=data.get('regions', []),
            cost_allocation_tags=data.get('cost_allocation_tags', {}),
            is_active=data.get('is_active', True),
            monthly_budget=Decimal(str(data['monthly_budget'])) if data.get('monthly_budget') else None,
            currency=Currency(data.get('currency', 'USD')),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )


@dataclass
class BillingPreferences:
    """Client billing and cost preferences."""
    primary_currency: Currency = Currency.USD
    cost_allocation_method: str = "proportional"  # proportional, tag_based, account_based
    default_cost_center: Optional[str] = None
    budget_alerts_enabled: bool = True
    cost_anomaly_detection: bool = True
    monthly_budget_limit: Optional[Decimal] = None
    quarterly_budget_limit: Optional[Decimal] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'primary_currency': self.primary_currency.value,
            'cost_allocation_method': self.cost_allocation_method,
            'default_cost_center': self.default_cost_center,
            'budget_alerts_enabled': self.budget_alerts_enabled,
            'cost_anomaly_detection': self.cost_anomaly_detection,
            'monthly_budget_limit': float(self.monthly_budget_limit) if self.monthly_budget_limit else None,
            'quarterly_budget_limit': float(self.quarterly_budget_limit) if self.quarterly_budget_limit else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BillingPreferences':
        """Create BillingPreferences from dictionary."""
        return cls(
            primary_currency=Currency(data.get('primary_currency', 'USD')),
            cost_allocation_method=data.get('cost_allocation_method', 'proportional'),
            default_cost_center=data.get('default_cost_center'),
            budget_alerts_enabled=data.get('budget_alerts_enabled', True),
            cost_anomaly_detection=data.get('cost_anomaly_detection', True),
            monthly_budget_limit=Decimal(str(data['monthly_budget_limit'])) if data.get('monthly_budget_limit') else None,
            quarterly_budget_limit=Decimal(str(data['quarterly_budget_limit'])) if data.get('quarterly_budget_limit') else None
        )


@dataclass
class AIPreferences:
    """Client AI and analytics preferences."""
    enable_anomaly_detection: bool = True
    anomaly_sensitivity: float = 0.8  # 0.0 to 1.0
    enable_forecasting: bool = True
    forecast_horizon_days: int = 90
    enable_recommendations: bool = True
    enable_automated_insights: bool = True
    ml_model_preference: str = "balanced"  # conservative, balanced, aggressive
    notification_frequency: str = "daily"  # real_time, daily, weekly
    
    def __post_init__(self):
        """Validate AI preferences."""
        if not 0.0 <= self.anomaly_sensitivity <= 1.0:
            raise ValueError("Anomaly sensitivity must be between 0.0 and 1.0")
        if self.forecast_horizon_days < 1:
            raise ValueError("Forecast horizon must be at least 1 day")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'enable_anomaly_detection': self.enable_anomaly_detection,
            'anomaly_sensitivity': self.anomaly_sensitivity,
            'enable_forecasting': self.enable_forecasting,
            'forecast_horizon_days': self.forecast_horizon_days,
            'enable_recommendations': self.enable_recommendations,
            'enable_automated_insights': self.enable_automated_insights,
            'ml_model_preference': self.ml_model_preference,
            'notification_frequency': self.notification_frequency
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIPreferences':
        """Create AIPreferences from dictionary."""
        return cls(
            enable_anomaly_detection=data.get('enable_anomaly_detection', True),
            anomaly_sensitivity=data.get('anomaly_sensitivity', 0.8),
            enable_forecasting=data.get('enable_forecasting', True),
            forecast_horizon_days=data.get('forecast_horizon_days', 90),
            enable_recommendations=data.get('enable_recommendations', True),
            enable_automated_insights=data.get('enable_automated_insights', True),
            ml_model_preference=data.get('ml_model_preference', 'balanced'),
            notification_frequency=data.get('notification_frequency', 'daily')
        )


@dataclass
class NotificationPreferences:
    """Client notification preferences."""
    email_enabled: bool = True
    slack_enabled: bool = False
    webhook_enabled: bool = False
    email_recipients: List[str] = field(default_factory=list)
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    notification_types: List[str] = field(default_factory=lambda: ['anomaly', 'budget_alert', 'forecast'])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'email_enabled': self.email_enabled,
            'slack_enabled': self.slack_enabled,
            'webhook_enabled': self.webhook_enabled,
            'email_recipients': self.email_recipients,
            'slack_webhook_url': self.slack_webhook_url,
            'webhook_url': self.webhook_url,
            'notification_types': self.notification_types
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationPreferences':
        """Create NotificationPreferences from dictionary."""
        return cls(
            email_enabled=data.get('email_enabled', True),
            slack_enabled=data.get('slack_enabled', False),
            webhook_enabled=data.get('webhook_enabled', False),
            email_recipients=data.get('email_recipients', []),
            slack_webhook_url=data.get('slack_webhook_url'),
            webhook_url=data.get('webhook_url'),
            notification_types=data.get('notification_types', ['anomaly', 'budget_alert', 'forecast'])
        )


@dataclass
class ResourceLimits:
    """Client resource allocation limits."""
    max_cloud_accounts: int = 10
    max_monthly_api_calls: int = 100000
    max_data_retention_days: int = 730  # 2 years
    max_custom_dashboards: int = 5
    max_alert_rules: int = 50
    concurrent_collection_limit: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'max_cloud_accounts': self.max_cloud_accounts,
            'max_monthly_api_calls': self.max_monthly_api_calls,
            'max_data_retention_days': self.max_data_retention_days,
            'max_custom_dashboards': self.max_custom_dashboards,
            'max_alert_rules': self.max_alert_rules,
            'concurrent_collection_limit': self.concurrent_collection_limit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceLimits':
        """Create ResourceLimits from dictionary."""
        return cls(
            max_cloud_accounts=data.get('max_cloud_accounts', 10),
            max_monthly_api_calls=data.get('max_monthly_api_calls', 100000),
            max_data_retention_days=data.get('max_data_retention_days', 730),
            max_custom_dashboards=data.get('max_custom_dashboards', 5),
            max_alert_rules=data.get('max_alert_rules', 50),
            concurrent_collection_limit=data.get('concurrent_collection_limit', 5)
        )


@dataclass
class MultiCloudClient:
    """
    Enhanced multi-cloud client configuration with multi-tenant support.
    
    This extends the original ClientConfig to support multiple cloud providers
    and enhanced tenant isolation features.
    """
    client_id: str
    organization_name: str
    cloud_accounts: Dict[CloudProvider, List[CloudAccount]] = field(default_factory=dict)
    billing_preferences: BillingPreferences = field(default_factory=BillingPreferences)
    ai_preferences: AIPreferences = field(default_factory=AIPreferences)
    notification_preferences: NotificationPreferences = field(default_factory=NotificationPreferences)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    
    # Enhanced client metadata
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    status: ClientStatus = ClientStatus.ACTIVE
    onboarding_status: OnboardingStatus = OnboardingStatus.PENDING
    
    # Tenant isolation
    tenant_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data_partition_key: str = ""
    
    # Legacy compatibility
    report_config: Optional[ReportConfig] = None
    branding: Optional[BrandingConfig] = None
    
    # Timestamps and tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: Optional[datetime] = None
    onboarding_completed_at: Optional[datetime] = None
    
    # Usage tracking
    monthly_api_calls: int = 0
    monthly_cost_processed: Decimal = field(default=Decimal('0'))
    
    def __post_init__(self):
        """Validate multi-cloud client configuration."""
        if not self.client_id.strip():
            self.client_id = str(uuid.uuid4())
        
        if not self.organization_name.strip():
            raise ValueError("Organization name is required")
        
        # Set data partition key for tenant isolation
        if not self.data_partition_key:
            self.data_partition_key = f"TENANT#{self.tenant_id}"
        
        # Validate resource limits based on subscription tier
        self._apply_subscription_limits()
    
    def _apply_subscription_limits(self):
        """Apply resource limits based on subscription tier."""
        tier_limits = {
            SubscriptionTier.FREE: ResourceLimits(
                max_cloud_accounts=2,
                max_monthly_api_calls=10000,
                max_data_retention_days=90,
                max_custom_dashboards=1,
                max_alert_rules=5,
                concurrent_collection_limit=1
            ),
            SubscriptionTier.BASIC: ResourceLimits(
                max_cloud_accounts=5,
                max_monthly_api_calls=50000,
                max_data_retention_days=365,
                max_custom_dashboards=3,
                max_alert_rules=20,
                concurrent_collection_limit=2
            ),
            SubscriptionTier.PROFESSIONAL: ResourceLimits(
                max_cloud_accounts=15,
                max_monthly_api_calls=200000,
                max_data_retention_days=730,
                max_custom_dashboards=10,
                max_alert_rules=100,
                concurrent_collection_limit=5
            ),
            SubscriptionTier.ENTERPRISE: ResourceLimits(
                max_cloud_accounts=100,
                max_monthly_api_calls=1000000,
                max_data_retention_days=2555,  # 7 years
                max_custom_dashboards=50,
                max_alert_rules=500,
                concurrent_collection_limit=20
            )
        }
        
        if self.subscription_tier in tier_limits:
            self.resource_limits = tier_limits[self.subscription_tier]
    
    def add_cloud_account(self, account: CloudAccount) -> None:
        """Add a cloud account to the client."""
        provider = account.provider
        
        if provider not in self.cloud_accounts:
            self.cloud_accounts[provider] = []
        
        # Check resource limits
        total_accounts = sum(len(accounts) for accounts in self.cloud_accounts.values())
        if total_accounts >= self.resource_limits.max_cloud_accounts:
            raise ValueError(f"Maximum number of cloud accounts ({self.resource_limits.max_cloud_accounts}) reached")
        
        # Check for duplicate account IDs within the same provider
        existing_ids = [acc.account_id for acc in self.cloud_accounts[provider]]
        if account.account_id in existing_ids:
            raise ValueError(f"Account {account.account_id} already exists for provider {provider.value}")
        
        self.cloud_accounts[provider].append(account)
        self.updated_at = datetime.utcnow()
    
    def remove_cloud_account(self, provider: CloudProvider, account_id: str) -> bool:
        """Remove a cloud account from the client."""
        if provider not in self.cloud_accounts:
            return False
        
        accounts = self.cloud_accounts[provider]
        for i, account in enumerate(accounts):
            if account.account_id == account_id:
                accounts.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        
        return False
    
    def get_cloud_account(self, provider: CloudProvider, account_id: str) -> Optional[CloudAccount]:
        """Get a specific cloud account."""
        if provider not in self.cloud_accounts:
            return None
        
        for account in self.cloud_accounts[provider]:
            if account.account_id == account_id:
                return account
        
        return None
    
    def get_all_accounts(self) -> List[CloudAccount]:
        """Get all cloud accounts across all providers."""
        all_accounts = []
        for accounts in self.cloud_accounts.values():
            all_accounts.extend(accounts)
        return all_accounts
    
    def get_active_accounts(self) -> List[CloudAccount]:
        """Get all active cloud accounts."""
        return [account for account in self.get_all_accounts() if account.is_active]
    
    def get_providers(self) -> List[CloudProvider]:
        """Get list of configured cloud providers."""
        return [provider for provider, accounts in self.cloud_accounts.items() if accounts]
    
    def validate_resource_usage(self) -> List[str]:
        """Validate current resource usage against limits."""
        violations = []
        
        total_accounts = sum(len(accounts) for accounts in self.cloud_accounts.values())
        if total_accounts > self.resource_limits.max_cloud_accounts:
            violations.append(f"Too many cloud accounts: {total_accounts}/{self.resource_limits.max_cloud_accounts}")
        
        if self.monthly_api_calls > self.resource_limits.max_monthly_api_calls:
            violations.append(f"Monthly API call limit exceeded: {self.monthly_api_calls}/{self.resource_limits.max_monthly_api_calls}")
        
        return violations
    
    def increment_api_usage(self, calls: int = 1) -> None:
        """Increment monthly API call counter."""
        self.monthly_api_calls += calls
        self.last_activity = datetime.utcnow()
    
    def reset_monthly_usage(self) -> None:
        """Reset monthly usage counters."""
        self.monthly_api_calls = 0
        self.monthly_cost_processed = Decimal('0')
    
    def complete_onboarding(self) -> None:
        """Mark client onboarding as completed."""
        self.onboarding_status = OnboardingStatus.COMPLETED
        self.onboarding_completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format with tenant isolation."""
        return {
            'PK': f"CLIENT#{self.client_id}",
            'SK': f"CONFIG#{self.tenant_id}",
            'GSI1PK': f"TENANT#{self.tenant_id}",
            'GSI1SK': f"STATUS#{self.status.value}",
            'GSI2PK': f"ORG#{self.organization_name}",
            'GSI2SK': f"CREATED#{self.created_at.isoformat()}",
            
            # Core client data
            'client_id': self.client_id,
            'tenant_id': self.tenant_id,
            'organization_name': self.organization_name,
            'data_partition_key': self.data_partition_key,
            
            # Cloud accounts by provider
            'cloud_accounts': {
                provider.value: [account.to_dict() for account in accounts]
                for provider, accounts in self.cloud_accounts.items()
            },
            
            # Preferences and configuration
            'billing_preferences': self.billing_preferences.to_dict(),
            'ai_preferences': self.ai_preferences.to_dict(),
            'notification_preferences': self.notification_preferences.to_dict(),
            'resource_limits': self.resource_limits.to_dict(),
            
            # Client metadata
            'subscription_tier': self.subscription_tier.value,
            'status': self.status.value,
            'onboarding_status': self.onboarding_status.value,
            
            # Legacy compatibility
            'report_config': self.report_config.to_dict() if self.report_config else None,
            'branding': self.branding.to_dict() if self.branding else None,
            
            # Timestamps
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'onboarding_completed_at': self.onboarding_completed_at.isoformat() if self.onboarding_completed_at else None,
            
            # Usage tracking
            'monthly_api_calls': self.monthly_api_calls,
            'monthly_cost_processed': float(self.monthly_cost_processed),
            
            # TTL for inactive clients (1 year after last activity)
            'ttl': int((self.last_activity or self.updated_at).timestamp() + (365 * 24 * 60 * 60))
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'MultiCloudClient':
        """Create MultiCloudClient from DynamoDB item."""
        # Parse cloud accounts
        cloud_accounts = {}
        for provider_str, accounts_data in item.get('cloud_accounts', {}).items():
            provider = CloudProvider(provider_str)
            accounts = [CloudAccount.from_dict(acc_data) for acc_data in accounts_data]
            cloud_accounts[provider] = accounts
        
        # Parse preferences
        billing_prefs = BillingPreferences.from_dict(item.get('billing_preferences', {}))
        ai_prefs = AIPreferences.from_dict(item.get('ai_preferences', {}))
        notification_prefs = NotificationPreferences.from_dict(item.get('notification_preferences', {}))
        resource_limits = ResourceLimits.from_dict(item.get('resource_limits', {}))
        
        # Parse legacy compatibility
        report_config = None
        if item.get('report_config'):
            report_config = ReportConfig.from_dict(item['report_config'])
        
        branding = None
        if item.get('branding'):
            branding = BrandingConfig.from_dict(item['branding'])
        
        return cls(
            client_id=item['client_id'],
            tenant_id=item.get('tenant_id', str(uuid.uuid4())),
            organization_name=item['organization_name'],
            data_partition_key=item.get('data_partition_key', ''),
            cloud_accounts=cloud_accounts,
            billing_preferences=billing_prefs,
            ai_preferences=ai_prefs,
            notification_preferences=notification_prefs,
            resource_limits=resource_limits,
            subscription_tier=SubscriptionTier(item.get('subscription_tier', 'free')),
            status=ClientStatus(item.get('status', 'active')),
            onboarding_status=OnboardingStatus(item.get('onboarding_status', 'pending')),
            report_config=report_config,
            branding=branding,
            created_at=datetime.fromisoformat(item['created_at']),
            updated_at=datetime.fromisoformat(item['updated_at']),
            last_activity=datetime.fromisoformat(item['last_activity']) if item.get('last_activity') else None,
            onboarding_completed_at=datetime.fromisoformat(item['onboarding_completed_at']) if item.get('onboarding_completed_at') else None,
            monthly_api_calls=item.get('monthly_api_calls', 0),
            monthly_cost_processed=Decimal(str(item.get('monthly_cost_processed', 0)))
        )


# DynamoDB Table Schema for Multi-Tenant Clients
MULTI_TENANT_CLIENT_TABLE_SCHEMA = {
    "TableName": "multi-cloud-clients",
    "KeySchema": [
        {
            "AttributeName": "PK",
            "KeyType": "HASH"  # Partition key
        },
        {
            "AttributeName": "SK", 
            "KeyType": "RANGE"  # Sort key
        }
    ],
    "AttributeDefinitions": [
        {
            "AttributeName": "PK",
            "AttributeType": "S"
        },
        {
            "AttributeName": "SK",
            "AttributeType": "S"
        },
        {
            "AttributeName": "GSI1PK",
            "AttributeType": "S"
        },
        {
            "AttributeName": "GSI1SK",
            "AttributeType": "S"
        },
        {
            "AttributeName": "GSI2PK",
            "AttributeType": "S"
        },
        {
            "AttributeName": "GSI2SK",
            "AttributeType": "S"
        }
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "GSI1",
            "KeySchema": [
                {
                    "AttributeName": "GSI1PK",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "GSI1SK",
                    "KeyType": "RANGE"
                }
            ],
            "Projection": {
                "ProjectionType": "ALL"
            },
            "BillingMode": "PAY_PER_REQUEST"
        },
        {
            "IndexName": "GSI2",
            "KeySchema": [
                {
                    "AttributeName": "GSI2PK",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "GSI2SK",
                    "KeyType": "RANGE"
                }
            ],
            "Projection": {
                "ProjectionType": "ALL"
            },
            "BillingMode": "PAY_PER_REQUEST"
        }
    ],
    "BillingMode": "PAY_PER_REQUEST",
    "StreamSpecification": {
        "StreamEnabled": True,
        "StreamViewType": "NEW_AND_OLD_IMAGES"
    },
    "PointInTimeRecoverySpecification": {
        "PointInTimeRecoveryEnabled": True
    },
    "Tags": [
        {
            "Key": "Project",
            "Value": "multi-cloud-cost-analytics"
        },
        {
            "Key": "Component",
            "Value": "multi-tenant-client-management"
        }
    ]
}