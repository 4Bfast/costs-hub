"""
Data models for cost history and AI analysis.

This module defines data structures for storing historical cost data
and AI analysis results in DynamoDB.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from enum import Enum
import json


class CostDataType(Enum):
    """Types of cost data stored."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AnalysisType(Enum):
    """Types of AI analysis."""
    ANOMALY_DETECTION = "anomaly_detection"
    TREND_ANALYSIS = "trend_analysis"
    FORECAST = "forecast"
    OPTIMIZATION = "optimization"
    INSIGHTS = "insights"


@dataclass
class ServiceCostData:
    """Cost data for a specific AWS service."""
    service_name: str
    current_cost: float
    previous_cost: float = 0.0
    change_percent: float = 0.0
    usage_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountCostData:
    """Cost data for a specific AWS account."""
    account_id: str
    account_name: str
    current_cost: float
    previous_cost: float = 0.0
    change_percent: float = 0.0
    services: Dict[str, ServiceCostData] = field(default_factory=dict)


@dataclass
class CostHistoryRecord:
    """Historical cost record for DynamoDB storage."""
    client_id: str
    date: date
    cost_type: CostDataType
    total_cost: float
    services: Dict[str, float] = field(default_factory=dict)
    accounts: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    collection_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def partition_key(self) -> str:
        """Generate DynamoDB partition key."""
        return f"CLIENT#{self.client_id}"
    
    @property
    def sort_key(self) -> str:
        """Generate DynamoDB sort key."""
        return f"COST#{self.date.isoformat()}#{self.cost_type.value}"
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        # Calculate TTL (2 years from now)
        ttl = int((datetime.utcnow().timestamp()) + (2 * 365 * 24 * 60 * 60))
        
        return {
            'PK': self.partition_key,
            'SK': self.sort_key,
            'client_id': self.client_id,
            'date': self.date.isoformat(),
            'cost_type': self.cost_type.value,
            'total_cost': self.total_cost,
            'services': self.services,
            'accounts': self.accounts,
            'metadata': {
                **self.metadata,
                'collection_timestamp': self.collection_timestamp.isoformat(),
                'data_version': '1.0'
            },
            'ttl': ttl
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'CostHistoryRecord':
        """Create from DynamoDB item."""
        return cls(
            client_id=item['client_id'],
            date=date.fromisoformat(item['date']),
            cost_type=CostDataType(item['cost_type']),
            total_cost=float(item['total_cost']),
            services=item.get('services', {}),
            accounts=item.get('accounts', {}),
            metadata=item.get('metadata', {}),
            collection_timestamp=datetime.fromisoformat(
                item.get('metadata', {}).get('collection_timestamp', datetime.utcnow().isoformat())
            )
        )


@dataclass
class AnomalyDetection:
    """Anomaly detection result."""
    service_name: str
    current_cost: float
    expected_cost: float
    deviation_percent: float
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    period: str  # "7d", "30d", "90d"
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0.0 to 1.0
    average_change_percent: float
    key_drivers: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class CostForecast:
    """Cost forecast result."""
    forecast_period: str  # "next_week", "next_month", "next_quarter"
    predicted_cost: float
    confidence_level: float  # 0.0 to 1.0
    prediction_range: Dict[str, float] = field(default_factory=dict)  # min, max
    key_assumptions: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation."""
    category: str  # "rightsizing", "reserved_instances", "unused_resources", etc.
    service_name: str
    potential_savings: float
    effort_level: str  # "low", "medium", "high"
    priority: str  # "low", "medium", "high", "critical"
    description: str
    action_items: List[str] = field(default_factory=list)
    implementation_time: str = ""  # "immediate", "1-2 weeks", "1 month", etc.


@dataclass
class AIAnalysisResult:
    """Complete AI analysis result."""
    client_id: str
    analysis_date: datetime
    analysis_types: List[AnalysisType]
    
    # Analysis results
    anomalies: List[AnomalyDetection] = field(default_factory=list)
    trends: List[TrendAnalysis] = field(default_factory=list)
    forecasts: List[CostForecast] = field(default_factory=list)
    recommendations: List[OptimizationRecommendation] = field(default_factory=list)
    
    # AI-generated insights
    executive_summary: str = ""
    key_insights: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # Metadata
    confidence_score: float = 0.0  # Overall confidence in analysis
    data_quality_score: float = 0.0  # Quality of input data
    processing_time_seconds: float = 0.0
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item for storage."""
        return {
            'PK': f"CLIENT#{self.client_id}",
            'SK': f"ANALYSIS#{self.analysis_date.isoformat()}",
            'client_id': self.client_id,
            'analysis_date': self.analysis_date.isoformat(),
            'analysis_types': [t.value for t in self.analysis_types],
            'anomalies': [
                {
                    'service_name': a.service_name,
                    'current_cost': a.current_cost,
                    'expected_cost': a.expected_cost,
                    'deviation_percent': a.deviation_percent,
                    'severity': a.severity,
                    'description': a.description,
                    'recommendations': a.recommendations
                } for a in self.anomalies
            ],
            'trends': [
                {
                    'period': t.period,
                    'trend_direction': t.trend_direction,
                    'trend_strength': t.trend_strength,
                    'average_change_percent': t.average_change_percent,
                    'key_drivers': t.key_drivers,
                    'description': t.description
                } for t in self.trends
            ],
            'forecasts': [
                {
                    'forecast_period': f.forecast_period,
                    'predicted_cost': f.predicted_cost,
                    'confidence_level': f.confidence_level,
                    'prediction_range': f.prediction_range,
                    'key_assumptions': f.key_assumptions,
                    'description': f.description
                } for f in self.forecasts
            ],
            'recommendations': [
                {
                    'category': r.category,
                    'service_name': r.service_name,
                    'potential_savings': r.potential_savings,
                    'effort_level': r.effort_level,
                    'priority': r.priority,
                    'description': r.description,
                    'action_items': r.action_items,
                    'implementation_time': r.implementation_time
                } for r in self.recommendations
            ],
            'executive_summary': self.executive_summary,
            'key_insights': self.key_insights,
            'risk_factors': self.risk_factors,
            'confidence_score': self.confidence_score,
            'data_quality_score': self.data_quality_score,
            'processing_time_seconds': self.processing_time_seconds,
            'ttl': int((datetime.utcnow().timestamp()) + (365 * 24 * 60 * 60))  # 1 year TTL
        }


@dataclass
class HistoricalDataQuery:
    """Query parameters for historical data retrieval."""
    client_id: str
    start_date: date
    end_date: date
    cost_types: List[CostDataType] = field(default_factory=lambda: [CostDataType.DAILY])
    services: Optional[List[str]] = None
    accounts: Optional[List[str]] = None
    
    def validate(self) -> None:
        """Validate query parameters."""
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before end_date")
        
        if (self.end_date - self.start_date).days > 365:
            raise ValueError("Query period cannot exceed 365 days")
        
        if not self.client_id:
            raise ValueError("client_id is required")