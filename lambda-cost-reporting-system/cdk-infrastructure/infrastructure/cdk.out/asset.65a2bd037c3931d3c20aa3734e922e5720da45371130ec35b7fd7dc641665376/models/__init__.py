"""
Models package for the Lambda Cost Reporting System.

This package contains all data models and schemas used throughout the system,
including legacy single-cloud models and new multi-cloud unified models.
"""

# Legacy models (for backward compatibility)
from .config_models import (
    ClientConfig,
    AccountConfig,
    ReportConfig,
    BrandingConfig,
    ClientStatus,
    ReportType,
    DYNAMODB_TABLE_SCHEMA
)

from .threshold_models import (
    ThresholdConfig,
    ThresholdType,
    AlertSeverity,
    ComparisonPeriod,
    CostData,
    AlertResult,
    ThresholdEvaluationResult
)

# Multi-cloud unified models
from .multi_cloud_models import (
    CloudProvider,
    ServiceCategory,
    Currency,
    DataQualityLevel,
    DataQuality,
    ServiceCost,
    AccountCost,
    RegionCost,
    CollectionMetadata,
    UnifiedCostRecord,
    TimeSeriesDataPoint,
    TimeSeriesAggregations,
    UnifiedTimeSeriesRecord,
    SERVICE_CATEGORY_MAPPING,
    get_unified_service_category,
    validate_cost_record
)

# Validation models
from .validation_models import (
    ValidationSeverity,
    ValidationType,
    ValidationIssue,
    ValidationResult,
    ValidationRule,
    RequiredFieldRule,
    NumericRangeRule,
    RegexRule,
    DateFormatRule,
    EnumRule,
    ConsistencyRule,
    CostDataValidator,
    create_sample_validation_rules
)

__all__ = [
    # Legacy models
    "ClientConfig",
    "AccountConfig", 
    "ReportConfig",
    "BrandingConfig",
    "ClientStatus",
    "ReportType",
    "DYNAMODB_TABLE_SCHEMA",
    "ThresholdConfig",
    "ThresholdType",
    "AlertSeverity",
    "ComparisonPeriod",
    "CostData",
    "AlertResult",
    "ThresholdEvaluationResult",
    
    # Multi-cloud models
    "CloudProvider",
    "ServiceCategory",
    "Currency",
    "DataQualityLevel",
    "DataQuality",
    "ServiceCost",
    "AccountCost",
    "RegionCost",
    "CollectionMetadata",
    "UnifiedCostRecord",
    "TimeSeriesDataPoint",
    "TimeSeriesAggregations",
    "UnifiedTimeSeriesRecord",
    "SERVICE_CATEGORY_MAPPING",
    "get_unified_service_category",
    "validate_cost_record",
    
    # Validation models
    "ValidationSeverity",
    "ValidationType",
    "ValidationIssue",
    "ValidationResult",
    "ValidationRule",
    "RequiredFieldRule",
    "NumericRangeRule",
    "RegexRule",
    "DateFormatRule",
    "EnumRule",
    "ConsistencyRule",
    "CostDataValidator",
    "create_sample_validation_rules"
]