"""
Multi-Cloud Unified Data Models

This module defines the core data structures for the multi-cloud cost analytics platform.
These models provide a unified interface for cost data across AWS, GCP, and Azure.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import uuid
import json


class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "AZURE"


class ServiceCategory(Enum):
    """Unified service categories across all cloud providers."""
    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"
    NETWORKING = "networking"
    ANALYTICS = "analytics"
    SECURITY = "security"
    MANAGEMENT = "management"
    AI_ML = "ai_ml"
    CONTAINERS = "containers"
    SERVERLESS = "serverless"
    OTHER = "other"


class Currency(Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    BRL = "BRL"


class DataQualityLevel(Enum):
    """Data quality confidence levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class DataQuality:
    """Data quality metrics for cost data validation."""
    completeness_score: float  # 0.0 to 1.0
    accuracy_score: float      # 0.0 to 1.0
    timeliness_score: float    # 0.0 to 1.0
    consistency_score: float   # 0.0 to 1.0
    confidence_level: DataQualityLevel
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate data quality scores."""
        for score_name in ['completeness_score', 'accuracy_score', 'timeliness_score', 'consistency_score']:
            score = getattr(self, score_name)
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"{score_name} must be between 0.0 and 1.0, got {score}")
    
    @property
    def overall_score(self) -> float:
        """Calculate overall data quality score."""
        return (self.completeness_score + self.accuracy_score + 
                self.timeliness_score + self.consistency_score) / 4.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'completeness_score': self.completeness_score,
            'accuracy_score': self.accuracy_score,
            'timeliness_score': self.timeliness_score,
            'consistency_score': self.consistency_score,
            'confidence_level': self.confidence_level.value,
            'overall_score': self.overall_score,
            'validation_errors': self.validation_errors,
            'validation_warnings': self.validation_warnings
        }


@dataclass
class ServiceCost:
    """Cost information for a specific service."""
    service_name: str
    unified_category: ServiceCategory
    cost: Decimal
    currency: Currency
    usage_metrics: Dict[str, Any] = field(default_factory=dict)
    provider_specific_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate service cost data."""
        if self.cost < 0:
            raise ValueError("Cost cannot be negative")
        if not self.service_name.strip():
            raise ValueError("Service name cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'service_name': self.service_name,
            'unified_category': self.unified_category.value,
            'cost': float(self.cost),
            'currency': self.currency.value,
            'usage_metrics': self.usage_metrics,
            'provider_specific_data': self.provider_specific_data
        }


@dataclass
class AccountCost:
    """Cost information for a specific cloud account."""
    account_id: str
    account_name: Optional[str]
    cost: Decimal
    currency: Currency
    services: Dict[str, ServiceCost] = field(default_factory=dict)
    regions: Dict[str, Decimal] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate account cost data."""
        if self.cost < 0:
            raise ValueError("Cost cannot be negative")
        if not self.account_id.strip():
            raise ValueError("Account ID cannot be empty")
    
    def add_service_cost(self, service_cost: ServiceCost) -> None:
        """Add a service cost to this account."""
        self.services[service_cost.service_name] = service_cost
    
    def get_total_cost(self) -> Decimal:
        """Calculate total cost from all services."""
        return sum(service.cost for service in self.services.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'account_id': self.account_id,
            'account_name': self.account_name,
            'cost': float(self.cost),
            'currency': self.currency.value,
            'services': {name: service.to_dict() for name, service in self.services.items()},
            'regions': {region: float(cost) for region, cost in self.regions.items()}
        }


@dataclass
class RegionCost:
    """Cost information for a specific region."""
    region_name: str
    cost: Decimal
    currency: Currency
    services: Dict[str, Decimal] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate region cost data."""
        if self.cost < 0:
            raise ValueError("Cost cannot be negative")
        if not self.region_name.strip():
            raise ValueError("Region name cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'region_name': self.region_name,
            'cost': float(self.cost),
            'currency': self.currency.value,
            'services': {service: float(cost) for service, cost in self.services.items()}
        }


@dataclass
class CollectionMetadata:
    """Metadata about the cost data collection process."""
    collection_timestamp: datetime
    collection_duration_seconds: float
    api_calls_made: int
    accounts_processed: int
    services_discovered: int
    data_freshness_hours: float
    collection_method: str  # 'api', 'export', 'manual'
    collector_version: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'collection_timestamp': self.collection_timestamp.isoformat(),
            'collection_duration_seconds': self.collection_duration_seconds,
            'api_calls_made': self.api_calls_made,
            'accounts_processed': self.accounts_processed,
            'services_discovered': self.services_discovered,
            'data_freshness_hours': self.data_freshness_hours,
            'collection_method': self.collection_method,
            'collector_version': self.collector_version
        }


@dataclass
class UnifiedCostRecord:
    """
    Unified cost record that normalizes cost data across all cloud providers.
    This is the core data structure for multi-cloud cost analytics.
    """
    # Primary identifiers
    client_id: str
    provider: CloudProvider
    date: str  # YYYY-MM-DD format
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Cost information
    total_cost: Decimal = field(default=Decimal('0'))
    currency: Currency = Currency.USD
    
    # Hierarchical cost breakdown
    services: Dict[str, ServiceCost] = field(default_factory=dict)
    accounts: Dict[str, AccountCost] = field(default_factory=dict)
    regions: Dict[str, RegionCost] = field(default_factory=dict)
    
    # Metadata and quality
    collection_metadata: Optional[CollectionMetadata] = None
    data_quality: Optional[DataQuality] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Provider-specific raw data (for debugging and advanced analysis)
    raw_provider_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate unified cost record."""
        if not self.client_id.strip():
            raise ValueError("Client ID cannot be empty")
        
        # Validate date format
        try:
            datetime.strptime(self.date, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Date must be in YYYY-MM-DD format, got {self.date}")
        
        if self.total_cost < 0:
            raise ValueError("Total cost cannot be negative")
    
    def add_service_cost(self, service_cost: ServiceCost) -> None:
        """Add a service cost to this record."""
        self.services[service_cost.service_name] = service_cost
        self._recalculate_total_cost()
    
    def add_account_cost(self, account_cost: AccountCost) -> None:
        """Add an account cost to this record."""
        self.accounts[account_cost.account_id] = account_cost
        self._recalculate_total_cost()
    
    def add_region_cost(self, region_cost: RegionCost) -> None:
        """Add a region cost to this record."""
        self.regions[region_cost.region_name] = region_cost
    
    def _recalculate_total_cost(self) -> None:
        """Recalculate total cost from services or accounts."""
        if self.services:
            self.total_cost = sum(service.cost for service in self.services.values())
        elif self.accounts:
            self.total_cost = sum(account.cost for account in self.accounts.values())
    
    def get_services_by_category(self) -> Dict[ServiceCategory, List[ServiceCost]]:
        """Group services by unified category."""
        categories = {}
        for service in self.services.values():
            category = service.unified_category
            if category not in categories:
                categories[category] = []
            categories[category].append(service)
        return categories
    
    def get_top_services(self, limit: int = 10) -> List[ServiceCost]:
        """Get top services by cost."""
        return sorted(self.services.values(), key=lambda s: s.cost, reverse=True)[:limit]
    
    def get_cost_by_category(self) -> Dict[ServiceCategory, Decimal]:
        """Get total cost by service category."""
        category_costs = {}
        for service in self.services.values():
            category = service.unified_category
            if category not in category_costs:
                category_costs[category] = Decimal('0')
            category_costs[category] += service.cost
        return category_costs
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        return {
            'PK': f"CLIENT#{self.client_id}",
            'SK': f"COST#{self.provider.value}#{self.date}",
            'GSI1PK': f"PROVIDER#{self.provider.value}",
            'GSI1SK': f"DATE#{self.date}",
            'GSI2PK': f"CLIENT#{self.client_id}",
            'GSI2SK': f"PROVIDER#{self.provider.value}",
            'record_id': self.record_id,
            'client_id': self.client_id,
            'provider': self.provider.value,
            'date': self.date,
            'cost_data': {
                'total_cost': float(self.total_cost),
                'currency': self.currency.value,
                'services': {name: service.to_dict() for name, service in self.services.items()},
                'accounts': {id: account.to_dict() for id, account in self.accounts.items()},
                'regions': {name: region.to_dict() for name, region in self.regions.items()}
            },
            'metadata': self.collection_metadata.to_dict() if self.collection_metadata else {},
            'data_quality': self.data_quality.to_dict() if self.data_quality else {},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'ttl': int((self.created_at.timestamp() + (2 * 365 * 24 * 60 * 60)))  # 2 years TTL
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'UnifiedCostRecord':
        """Create UnifiedCostRecord from DynamoDB item."""
        cost_data = item.get('cost_data', {})
        
        # Reconstruct services
        services = {}
        for name, service_data in cost_data.get('services', {}).items():
            services[name] = ServiceCost(
                service_name=service_data['service_name'],
                unified_category=ServiceCategory(service_data['unified_category']),
                cost=Decimal(str(service_data['cost'])),
                currency=Currency(service_data['currency']),
                usage_metrics=service_data.get('usage_metrics', {}),
                provider_specific_data=service_data.get('provider_specific_data', {})
            )
        
        # Reconstruct accounts
        accounts = {}
        for id, account_data in cost_data.get('accounts', {}).items():
            account_services = {}
            for svc_name, svc_data in account_data.get('services', {}).items():
                account_services[svc_name] = ServiceCost(
                    service_name=svc_data['service_name'],
                    unified_category=ServiceCategory(svc_data['unified_category']),
                    cost=Decimal(str(svc_data['cost'])),
                    currency=Currency(svc_data['currency']),
                    usage_metrics=svc_data.get('usage_metrics', {}),
                    provider_specific_data=svc_data.get('provider_specific_data', {})
                )
            
            accounts[id] = AccountCost(
                account_id=account_data['account_id'],
                account_name=account_data.get('account_name'),
                cost=Decimal(str(account_data['cost'])),
                currency=Currency(account_data['currency']),
                services=account_services,
                regions={r: Decimal(str(c)) for r, c in account_data.get('regions', {}).items()}
            )
        
        # Reconstruct regions
        regions = {}
        for name, region_data in cost_data.get('regions', {}).items():
            regions[name] = RegionCost(
                region_name=region_data['region_name'],
                cost=Decimal(str(region_data['cost'])),
                currency=Currency(region_data['currency']),
                services={s: Decimal(str(c)) for s, c in region_data.get('services', {}).items()}
            )
        
        # Reconstruct metadata
        metadata = None
        if item.get('metadata'):
            meta_data = item['metadata']
            metadata = CollectionMetadata(
                collection_timestamp=datetime.fromisoformat(meta_data['collection_timestamp']),
                collection_duration_seconds=meta_data['collection_duration_seconds'],
                api_calls_made=meta_data['api_calls_made'],
                accounts_processed=meta_data['accounts_processed'],
                services_discovered=meta_data['services_discovered'],
                data_freshness_hours=meta_data['data_freshness_hours'],
                collection_method=meta_data['collection_method'],
                collector_version=meta_data['collector_version']
            )
        
        # Reconstruct data quality
        data_quality = None
        if item.get('data_quality'):
            quality_data = item['data_quality']
            data_quality = DataQuality(
                completeness_score=quality_data['completeness_score'],
                accuracy_score=quality_data['accuracy_score'],
                timeliness_score=quality_data['timeliness_score'],
                consistency_score=quality_data['consistency_score'],
                confidence_level=DataQualityLevel(quality_data['confidence_level']),
                validation_errors=quality_data.get('validation_errors', []),
                validation_warnings=quality_data.get('validation_warnings', [])
            )
        
        return cls(
            client_id=item['client_id'],
            provider=CloudProvider(item['provider']),
            date=item['date'],
            record_id=item.get('record_id', str(uuid.uuid4())),
            total_cost=Decimal(str(cost_data.get('total_cost', 0))),
            currency=Currency(cost_data.get('currency', 'USD')),
            services=services,
            accounts=accounts,
            regions=regions,
            collection_metadata=metadata,
            data_quality=data_quality,
            created_at=datetime.fromisoformat(item['created_at']),
            updated_at=datetime.fromisoformat(item['updated_at'])
        )


@dataclass
class TimeSeriesDataPoint:
    """Single data point for time series analysis."""
    timestamp: datetime
    provider: CloudProvider
    total_cost: Decimal
    service_costs: Dict[ServiceCategory, Decimal] = field(default_factory=dict)
    normalized_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'provider': self.provider.value,
            'total_cost': float(self.total_cost),
            'service_costs': {cat.value: float(cost) for cat, cost in self.service_costs.items()},
            'normalized_metrics': self.normalized_metrics
        }


@dataclass
class TimeSeriesAggregations:
    """Aggregated metrics for time series data."""
    seven_day_avg: Decimal
    thirty_day_avg: Decimal
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    trend_percentage: float
    seasonal_index: float
    volatility_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            '7_day_avg': float(self.seven_day_avg),
            '30_day_avg': float(self.thirty_day_avg),
            'trend_direction': self.trend_direction,
            'trend_percentage': self.trend_percentage,
            'seasonal_index': self.seasonal_index,
            'volatility_score': self.volatility_score
        }


@dataclass
class UnifiedTimeSeriesRecord:
    """Time series record optimized for ML and trend analysis."""
    client_id: str
    date: str  # YYYY-MM-DD
    data_points: List[TimeSeriesDataPoint] = field(default_factory=list)
    aggregations: Optional[TimeSeriesAggregations] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_data_point(self, data_point: TimeSeriesDataPoint) -> None:
        """Add a data point to the time series."""
        self.data_points.append(data_point)
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format for time series table."""
        return {
            'PK': f"TIMESERIES#{self.client_id}",
            'SK': f"DAILY#{self.date}",
            'client_id': self.client_id,
            'date': self.date,
            'data_points': [dp.to_dict() for dp in self.data_points],
            'aggregations': self.aggregations.to_dict() if self.aggregations else {},
            'created_at': self.created_at.isoformat(),
            'ttl': int((self.created_at.timestamp() + (2 * 365 * 24 * 60 * 60)))  # 2 years TTL
        }


# Service mapping constants for cross-provider normalization
SERVICE_CATEGORY_MAPPING = {
    CloudProvider.AWS: {
        # Compute services
        'EC2': ServiceCategory.COMPUTE,
        'Lambda': ServiceCategory.SERVERLESS,
        'Fargate': ServiceCategory.CONTAINERS,
        'ECS': ServiceCategory.CONTAINERS,
        'EKS': ServiceCategory.CONTAINERS,
        'Batch': ServiceCategory.COMPUTE,
        'Lightsail': ServiceCategory.COMPUTE,
        
        # Storage services
        'S3': ServiceCategory.STORAGE,
        'EBS': ServiceCategory.STORAGE,
        'EFS': ServiceCategory.STORAGE,
        'FSx': ServiceCategory.STORAGE,
        'Glacier': ServiceCategory.STORAGE,
        'Storage Gateway': ServiceCategory.STORAGE,
        
        # Database services
        'RDS': ServiceCategory.DATABASE,
        'DynamoDB': ServiceCategory.DATABASE,
        'Aurora': ServiceCategory.DATABASE,
        'Redshift': ServiceCategory.ANALYTICS,
        'ElastiCache': ServiceCategory.DATABASE,
        'DocumentDB': ServiceCategory.DATABASE,
        'Neptune': ServiceCategory.DATABASE,
        
        # Networking
        'VPC': ServiceCategory.NETWORKING,
        'CloudFront': ServiceCategory.NETWORKING,
        'Route 53': ServiceCategory.NETWORKING,
        'ELB': ServiceCategory.NETWORKING,
        'API Gateway': ServiceCategory.NETWORKING,
        'Direct Connect': ServiceCategory.NETWORKING,
        
        # Analytics
        'EMR': ServiceCategory.ANALYTICS,
        'Athena': ServiceCategory.ANALYTICS,
        'Glue': ServiceCategory.ANALYTICS,
        'Kinesis': ServiceCategory.ANALYTICS,
        'QuickSight': ServiceCategory.ANALYTICS,
        
        # AI/ML
        'SageMaker': ServiceCategory.AI_ML,
        'Bedrock': ServiceCategory.AI_ML,
        'Comprehend': ServiceCategory.AI_ML,
        'Rekognition': ServiceCategory.AI_ML,
        'Textract': ServiceCategory.AI_ML,
        
        # Security
        'IAM': ServiceCategory.SECURITY,
        'KMS': ServiceCategory.SECURITY,
        'Secrets Manager': ServiceCategory.SECURITY,
        'WAF': ServiceCategory.SECURITY,
        'GuardDuty': ServiceCategory.SECURITY,
        'Security Hub': ServiceCategory.SECURITY,
        
        # Management
        'CloudWatch': ServiceCategory.MANAGEMENT,
        'CloudTrail': ServiceCategory.MANAGEMENT,
        'Config': ServiceCategory.MANAGEMENT,
        'Systems Manager': ServiceCategory.MANAGEMENT,
        'CloudFormation': ServiceCategory.MANAGEMENT,
    },
    
    CloudProvider.GCP: {
        # Compute services
        'Compute Engine': ServiceCategory.COMPUTE,
        'Cloud Functions': ServiceCategory.SERVERLESS,
        'Cloud Run': ServiceCategory.CONTAINERS,
        'GKE': ServiceCategory.CONTAINERS,
        'App Engine': ServiceCategory.SERVERLESS,
        
        # Storage services
        'Cloud Storage': ServiceCategory.STORAGE,
        'Persistent Disk': ServiceCategory.STORAGE,
        'Filestore': ServiceCategory.STORAGE,
        
        # Database services
        'Cloud SQL': ServiceCategory.DATABASE,
        'Firestore': ServiceCategory.DATABASE,
        'Bigtable': ServiceCategory.DATABASE,
        'BigQuery': ServiceCategory.ANALYTICS,
        'Memorystore': ServiceCategory.DATABASE,
        'Spanner': ServiceCategory.DATABASE,
        
        # Networking
        'VPC': ServiceCategory.NETWORKING,
        'Cloud CDN': ServiceCategory.NETWORKING,
        'Cloud DNS': ServiceCategory.NETWORKING,
        'Load Balancing': ServiceCategory.NETWORKING,
        'Cloud Interconnect': ServiceCategory.NETWORKING,
        
        # Analytics
        'Dataflow': ServiceCategory.ANALYTICS,
        'Dataproc': ServiceCategory.ANALYTICS,
        'Pub/Sub': ServiceCategory.ANALYTICS,
        'Data Studio': ServiceCategory.ANALYTICS,
        
        # AI/ML
        'AI Platform': ServiceCategory.AI_ML,
        'AutoML': ServiceCategory.AI_ML,
        'Vision API': ServiceCategory.AI_ML,
        'Natural Language': ServiceCategory.AI_ML,
        'Translation': ServiceCategory.AI_ML,
        
        # Security
        'IAM': ServiceCategory.SECURITY,
        'Cloud KMS': ServiceCategory.SECURITY,
        'Secret Manager': ServiceCategory.SECURITY,
        'Cloud Armor': ServiceCategory.SECURITY,
        'Security Command Center': ServiceCategory.SECURITY,
        
        # Management
        'Cloud Monitoring': ServiceCategory.MANAGEMENT,
        'Cloud Logging': ServiceCategory.MANAGEMENT,
        'Cloud Deployment Manager': ServiceCategory.MANAGEMENT,
    },
    
    CloudProvider.AZURE: {
        # Compute services
        'Virtual Machines': ServiceCategory.COMPUTE,
        'Azure Functions': ServiceCategory.SERVERLESS,
        'Container Instances': ServiceCategory.CONTAINERS,
        'AKS': ServiceCategory.CONTAINERS,
        'App Service': ServiceCategory.SERVERLESS,
        'Batch': ServiceCategory.COMPUTE,
        
        # Storage services
        'Blob Storage': ServiceCategory.STORAGE,
        'Disk Storage': ServiceCategory.STORAGE,
        'File Storage': ServiceCategory.STORAGE,
        'Archive Storage': ServiceCategory.STORAGE,
        
        # Database services
        'SQL Database': ServiceCategory.DATABASE,
        'Cosmos DB': ServiceCategory.DATABASE,
        'MySQL': ServiceCategory.DATABASE,
        'PostgreSQL': ServiceCategory.DATABASE,
        'Redis Cache': ServiceCategory.DATABASE,
        'Synapse Analytics': ServiceCategory.ANALYTICS,
        
        # Networking
        'Virtual Network': ServiceCategory.NETWORKING,
        'CDN': ServiceCategory.NETWORKING,
        'DNS': ServiceCategory.NETWORKING,
        'Load Balancer': ServiceCategory.NETWORKING,
        'Application Gateway': ServiceCategory.NETWORKING,
        'ExpressRoute': ServiceCategory.NETWORKING,
        
        # Analytics
        'Data Factory': ServiceCategory.ANALYTICS,
        'HDInsight': ServiceCategory.ANALYTICS,
        'Event Hubs': ServiceCategory.ANALYTICS,
        'Power BI': ServiceCategory.ANALYTICS,
        
        # AI/ML
        'Machine Learning': ServiceCategory.AI_ML,
        'Cognitive Services': ServiceCategory.AI_ML,
        'Bot Service': ServiceCategory.AI_ML,
        'Computer Vision': ServiceCategory.AI_ML,
        'Text Analytics': ServiceCategory.AI_ML,
        
        # Security
        'Active Directory': ServiceCategory.SECURITY,
        'Key Vault': ServiceCategory.SECURITY,
        'Security Center': ServiceCategory.SECURITY,
        'Sentinel': ServiceCategory.SECURITY,
        
        # Management
        'Monitor': ServiceCategory.MANAGEMENT,
        'Log Analytics': ServiceCategory.MANAGEMENT,
        'Resource Manager': ServiceCategory.MANAGEMENT,
        'Automation': ServiceCategory.MANAGEMENT,
    }
}


def get_unified_service_category(provider: CloudProvider, service_name: str) -> ServiceCategory:
    """
    Get the unified service category for a provider-specific service.
    
    Args:
        provider: The cloud provider
        service_name: The provider-specific service name
        
    Returns:
        The unified service category
    """
    provider_mapping = SERVICE_CATEGORY_MAPPING.get(provider, {})
    return provider_mapping.get(service_name, ServiceCategory.OTHER)


def validate_cost_record(record: UnifiedCostRecord) -> List[str]:
    """
    Validate a unified cost record and return any validation errors.
    
    Args:
        record: The cost record to validate
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Basic validation
    if not record.client_id:
        errors.append("Client ID is required")
    
    if record.total_cost < 0:
        errors.append("Total cost cannot be negative")
    
    # Validate services
    for service_name, service in record.services.items():
        if service.cost < 0:
            errors.append(f"Service {service_name} has negative cost")
        if not service.service_name:
            errors.append(f"Service {service_name} has empty name")
    
    # Validate accounts
    for account_id, account in record.accounts.items():
        if account.cost < 0:
            errors.append(f"Account {account_id} has negative cost")
        if not account.account_id:
            errors.append(f"Account {account_id} has empty ID")
    
    # Validate data consistency
    if record.services and record.accounts:
        service_total = sum(s.cost for s in record.services.values())
        account_total = sum(a.cost for a in record.accounts.values())
        if abs(service_total - account_total) > Decimal('0.01'):
            errors.append(f"Service total ({service_total}) doesn't match account total ({account_total})")
    
    # Validate total cost consistency with services
    if record.services:
        service_total = sum(s.cost for s in record.services.values())
        if abs(record.total_cost - service_total) > Decimal('0.01'):
            errors.append(f"Total cost ({record.total_cost}) doesn't match sum of service costs ({service_total})")
    
    # Validate total cost consistency with accounts
    if record.accounts and not record.services:
        account_total = sum(a.cost for a in record.accounts.values())
        if abs(record.total_cost - account_total) > Decimal('0.01'):
            errors.append(f"Total cost ({record.total_cost}) doesn't match sum of account costs ({account_total})")
    
    return errors