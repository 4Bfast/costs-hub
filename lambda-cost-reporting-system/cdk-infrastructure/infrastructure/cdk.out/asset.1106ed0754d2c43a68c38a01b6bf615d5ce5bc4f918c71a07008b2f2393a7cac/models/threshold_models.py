"""
Threshold models for cost alerting system.

This module defines the data structures for configuring and managing
cost thresholds and alerts in the Lambda Cost Reporting System.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import uuid


class ThresholdType(Enum):
    """Types of cost thresholds."""
    ABSOLUTE = "absolute"  # Fixed dollar amount
    PERCENTAGE = "percentage"  # Percentage increase from previous period
    SERVICE_SPECIFIC = "service_specific"  # Threshold for specific AWS service
    ACCOUNT_SPECIFIC = "account_specific"  # Threshold for specific AWS account


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComparisonPeriod(Enum):
    """Period for comparison in percentage thresholds."""
    PREVIOUS_WEEK = "previous_week"
    PREVIOUS_MONTH = "previous_month"
    SAME_WEEK_LAST_MONTH = "same_week_last_month"
    SAME_MONTH_LAST_YEAR = "same_month_last_year"


@dataclass
class ThresholdConfig:
    """Configuration for a single cost threshold."""
    threshold_id: str
    name: str
    threshold_type: ThresholdType
    value: float
    severity: AlertSeverity
    enabled: bool = True
    
    # Optional fields for specific threshold types
    service_name: Optional[str] = None  # For SERVICE_SPECIFIC
    account_id: Optional[str] = None    # For ACCOUNT_SPECIFIC
    comparison_period: Optional[ComparisonPeriod] = None  # For PERCENTAGE
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate threshold configuration after initialization."""
        if not self.threshold_id:
            self.threshold_id = str(uuid.uuid4())
        
        if not self.name:
            raise ValueError("Threshold name is required")
        
        if self.value < 0:
            raise ValueError("Threshold value must be non-negative")
        
        # Validate type-specific requirements
        if self.threshold_type == ThresholdType.SERVICE_SPECIFIC and not self.service_name:
            raise ValueError("service_name is required for SERVICE_SPECIFIC thresholds")
        
        if self.threshold_type == ThresholdType.ACCOUNT_SPECIFIC and not self.account_id:
            raise ValueError("account_id is required for ACCOUNT_SPECIFIC thresholds")
        
        if self.threshold_type == ThresholdType.PERCENTAGE and not self.comparison_period:
            raise ValueError("comparison_period is required for PERCENTAGE thresholds")
        
        # Validate percentage values
        if self.threshold_type == ThresholdType.PERCENTAGE and self.value > 1000:
            raise ValueError("Percentage threshold value should be reasonable (< 1000%)")
        
        # Set timestamps if not provided
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "threshold_id": self.threshold_id,
            "name": self.name,
            "threshold_type": self.threshold_type.value,
            "value": self.value,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "service_name": self.service_name,
            "account_id": self.account_id,
            "comparison_period": self.comparison_period.value if self.comparison_period else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThresholdConfig':
        """Create ThresholdConfig from dictionary."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        comparison_period = None
        if data.get("comparison_period"):
            comparison_period = ComparisonPeriod(data["comparison_period"])
        
        return cls(
            threshold_id=data["threshold_id"],
            name=data["name"],
            threshold_type=ThresholdType(data["threshold_type"]),
            value=data["value"],
            severity=AlertSeverity(data["severity"]),
            enabled=data.get("enabled", True),
            service_name=data.get("service_name"),
            account_id=data.get("account_id"),
            comparison_period=comparison_period,
            created_at=created_at,
            updated_at=updated_at
        )


@dataclass
class CostData:
    """Cost data for threshold evaluation."""
    total_cost: float
    service_costs: Dict[str, float] = field(default_factory=dict)
    account_costs: Dict[str, float] = field(default_factory=dict)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    def get_service_cost(self, service_name: str) -> float:
        """Get cost for a specific service."""
        return self.service_costs.get(service_name, 0.0)
    
    def get_account_cost(self, account_id: str) -> float:
        """Get cost for a specific account."""
        return self.account_costs.get(account_id, 0.0)


@dataclass
class AlertResult:
    """Result of threshold evaluation."""
    threshold_config: ThresholdConfig
    triggered: bool
    current_value: float
    threshold_value: float
    severity: AlertSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "threshold_id": self.threshold_config.threshold_id,
            "threshold_name": self.threshold_config.name,
            "triggered": self.triggered,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details
        }


@dataclass
class ThresholdEvaluationResult:
    """Complete result of threshold evaluation for a client."""
    client_id: str
    evaluation_time: datetime
    alerts: List[AlertResult] = field(default_factory=list)
    total_thresholds_checked: int = 0
    triggered_alerts_count: int = 0
    
    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self.triggered_alerts_count = sum(1 for alert in self.alerts if alert.triggered)
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[AlertResult]:
        """Get alerts filtered by severity."""
        return [alert for alert in self.alerts if alert.severity == severity and alert.triggered]
    
    def has_critical_alerts(self) -> bool:
        """Check if there are any critical alerts."""
        return any(alert.triggered and alert.severity == AlertSeverity.CRITICAL for alert in self.alerts)
    
    def has_any_alerts(self) -> bool:
        """Check if there are any triggered alerts."""
        return self.triggered_alerts_count > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "client_id": self.client_id,
            "evaluation_time": self.evaluation_time.isoformat(),
            "alerts": [alert.to_dict() for alert in self.alerts],
            "total_thresholds_checked": self.total_thresholds_checked,
            "triggered_alerts_count": self.triggered_alerts_count
        }