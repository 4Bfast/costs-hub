"""
Data models for client configuration and AWS account management.

This module defines the core data structures used throughout the Lambda Cost Reporting System
for managing client configurations, AWS account settings, report preferences, and branding.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from enum import Enum
import json
import uuid

if TYPE_CHECKING:
    from .threshold_models import ThresholdConfig


class ClientStatus(Enum):
    """Client status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class ReportType(Enum):
    """Report type enumeration."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class AccountConfig:
    """Configuration for a single AWS account."""
    account_id: str
    access_key_id: str
    secret_access_key: str  # Will be encrypted when stored
    region: str = "us-east-1"
    account_name: Optional[str] = None
    
    def __post_init__(self):
        """Validate account configuration after initialization."""
        if not self.account_id or len(self.account_id) != 12:
            raise ValueError("account_id must be a 12-digit AWS account ID")
        if not self.access_key_id:
            raise ValueError("access_key_id is required")
        if not self.secret_access_key:
            raise ValueError("secret_access_key is required")
        if not self.region:
            raise ValueError("region is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage."""
        return {
            "account_id": self.account_id,
            "access_key_id": self.access_key_id,
            "secret_access_key": self.secret_access_key,
            "region": self.region,
            "account_name": self.account_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountConfig':
        """Create AccountConfig from dictionary."""
        return cls(
            account_id=data["account_id"],
            access_key_id=data["access_key_id"],
            secret_access_key=data["secret_access_key"],
            region=data.get("region", "us-east-1"),
            account_name=data.get("account_name")
        )


@dataclass
class ReportConfig:
    """Configuration for report generation and delivery."""
    weekly_enabled: bool = True
    monthly_enabled: bool = True
    recipients: List[str] = field(default_factory=list)
    cc_recipients: List[str] = field(default_factory=list)
    threshold: float = 1.0
    top_services: int = 10
    include_accounts: bool = True
    alert_thresholds: List['ThresholdConfig'] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate report configuration after initialization."""
        if not self.recipients:
            raise ValueError("At least one recipient email is required")
        if self.threshold < 0:
            raise ValueError("threshold must be non-negative")
        if self.top_services < 1:
            raise ValueError("top_services must be at least 1")
        
        # Validate email addresses
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for email in self.recipients + self.cc_recipients:
            if not email_pattern.match(email):
                raise ValueError(f"Invalid email address: {email}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage."""
        return {
            "weekly_enabled": self.weekly_enabled,
            "monthly_enabled": self.monthly_enabled,
            "recipients": self.recipients,
            "cc_recipients": self.cc_recipients,
            "threshold": self.threshold,
            "top_services": self.top_services,
            "include_accounts": self.include_accounts,
            "alert_thresholds": [threshold.to_dict() for threshold in self.alert_thresholds]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportConfig':
        """Create ReportConfig from dictionary."""
        # Import here to avoid circular imports
        from .threshold_models import ThresholdConfig
        
        alert_thresholds = []
        threshold_data = data.get("alert_thresholds", [])
        
        # Handle backward compatibility with old dict format
        if isinstance(threshold_data, dict):
            # Convert old format to new format
            from .threshold_models import ThresholdType, AlertSeverity
            for name, value in threshold_data.items():
                alert_thresholds.append(ThresholdConfig(
                    threshold_id="",  # Will be auto-generated
                    name=name,
                    threshold_type=ThresholdType.ABSOLUTE,
                    value=float(value),
                    severity=AlertSeverity.MEDIUM
                ))
        elif isinstance(threshold_data, list):
            alert_thresholds = [ThresholdConfig.from_dict(t) for t in threshold_data]
        
        return cls(
            weekly_enabled=data.get("weekly_enabled", True),
            monthly_enabled=data.get("monthly_enabled", True),
            recipients=data.get("recipients", []),
            cc_recipients=data.get("cc_recipients", []),
            threshold=data.get("threshold", 1.0),
            top_services=data.get("top_services", 10),
            include_accounts=data.get("include_accounts", True),
            alert_thresholds=alert_thresholds
        )


@dataclass
class BrandingConfig:
    """Configuration for client branding and customization."""
    logo_s3_key: Optional[str] = None
    primary_color: str = "#1f2937"
    secondary_color: str = "#f59e0b"
    company_name: str = ""
    email_footer: str = ""
    
    def __post_init__(self):
        """Validate branding configuration after initialization."""
        # Validate color format (hex colors)
        import re
        color_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
        if not color_pattern.match(self.primary_color):
            raise ValueError(f"Invalid primary_color format: {self.primary_color}")
        if not color_pattern.match(self.secondary_color):
            raise ValueError(f"Invalid secondary_color format: {self.secondary_color}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage."""
        return {
            "logo_s3_key": self.logo_s3_key,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "company_name": self.company_name,
            "email_footer": self.email_footer
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrandingConfig':
        """Create BrandingConfig from dictionary."""
        return cls(
            logo_s3_key=data.get("logo_s3_key"),
            primary_color=data.get("primary_color", "#1f2937"),
            secondary_color=data.get("secondary_color", "#f59e0b"),
            company_name=data.get("company_name", ""),
            email_footer=data.get("email_footer", "")
        )


@dataclass
class ClientConfig:
    """Main client configuration containing all client settings."""
    client_id: str
    client_name: str
    aws_accounts: List[AccountConfig]
    report_config: ReportConfig
    branding: BrandingConfig
    status: ClientStatus = ClientStatus.ACTIVE
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_execution: Dict[str, Optional[datetime]] = field(default_factory=lambda: {"weekly": None, "monthly": None})
    
    def __post_init__(self):
        """Validate client configuration after initialization."""
        if not self.client_id:
            self.client_id = str(uuid.uuid4())
        if not self.client_name:
            raise ValueError("client_name is required")
        if not self.aws_accounts:
            raise ValueError("At least one AWS account is required")
        
        # Set timestamps if not provided
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage."""
        return {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "aws_accounts": [account.to_dict() for account in self.aws_accounts],
            "report_config": self.report_config.to_dict(),
            "branding": self.branding.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_execution": {
                k: v.isoformat() if v else None 
                for k, v in self.last_execution.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClientConfig':
        """Create ClientConfig from dictionary."""
        # Parse timestamps
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        # Parse last_execution
        last_execution = {}
        if data.get("last_execution"):
            for k, v in data["last_execution"].items():
                last_execution[k] = datetime.fromisoformat(v) if v else None
        
        return cls(
            client_id=data["client_id"],
            client_name=data["client_name"],
            aws_accounts=[AccountConfig.from_dict(acc) for acc in data["aws_accounts"]],
            report_config=ReportConfig.from_dict(data["report_config"]),
            branding=BrandingConfig.from_dict(data["branding"]),
            status=ClientStatus(data.get("status", "active")),
            created_at=created_at,
            updated_at=updated_at,
            last_execution=last_execution
        )
    
    def is_active(self) -> bool:
        """Check if client is active."""
        return self.status == ClientStatus.ACTIVE
    
    def update_last_execution(self, report_type: ReportType) -> None:
        """Update last execution timestamp for a report type."""
        self.last_execution[report_type.value] = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def get_account_by_id(self, account_id: str) -> Optional[AccountConfig]:
        """Get AWS account configuration by account ID."""
        for account in self.aws_accounts:
            if account.account_id == account_id:
                return account
        return None


# DynamoDB Table Schema Definition
DYNAMODB_TABLE_SCHEMA = {
    "TableName": "cost-reporting-clients",
    "KeySchema": [
        {
            "AttributeName": "client_id",
            "KeyType": "HASH"  # Partition key
        }
    ],
    "AttributeDefinitions": [
        {
            "AttributeName": "client_id",
            "AttributeType": "S"
        },
        {
            "AttributeName": "status",
            "AttributeType": "S"
        },
        {
            "AttributeName": "updated_at",
            "AttributeType": "S"
        }
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "status-updated_at-index",
            "KeySchema": [
                {
                    "AttributeName": "status",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "updated_at",
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
            "Value": "lambda-cost-reporting-system"
        },
        {
            "Key": "Environment",
            "Value": "production"
        }
    ]
}