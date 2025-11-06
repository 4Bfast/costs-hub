"""
Data Quality Engine

This module implements a comprehensive data quality engine for the multi-cloud cost analytics platform.
It provides functionality for data validation, quality scoring, completeness checks, accuracy verification,
consistency validation, and data quality reporting and alerting.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json
import re

from ..models.multi_cloud_models import (
    UnifiedCostRecord, ServiceCost, AccountCost, RegionCost,
    CloudProvider, ServiceCategory, Currency, DataQuality, DataQualityLevel
)
from ..models.provider_models import ProviderCostData


logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationCategory(Enum):
    """Categories of validation checks."""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"


@dataclass
class ValidationIssue:
    """Individual validation issue."""
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    field_name: Optional[str] = None
    current_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'field_name': self.field_name,
            'current_value': str(self.current_value) if self.current_value is not None else None,
            'expected_value': str(self.expected_value) if self.expected_value is not None else None,
            'suggestion': self.suggestion,
            'metadata': self.metadata
        }


@dataclass
class ValidationResult:
    """Result of data validation."""
    record_id: str
    provider: CloudProvider
    client_id: str
    validation_timestamp: datetime
    overall_score: float
    category_scores: Dict[ValidationCategory, float]
    issues: List[ValidationIssue]
    passed_checks: int
    total_checks: int
    data_quality: DataQuality
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical validation issues."""
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)
    
    @property
    def has_high_issues(self) -> bool:
        """Check if there are high severity validation issues."""
        return any(issue.severity == ValidationSeverity.HIGH for issue in self.issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues by severity level."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_issues_by_category(self, category: ValidationCategory) -> List[ValidationIssue]:
        """Get issues by category."""
        return [issue for issue in self.issues if issue.category == category]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'record_id': self.record_id,
            'provider': self.provider.value,
            'client_id': self.client_id,
            'validation_timestamp': self.validation_timestamp.isoformat(),
            'overall_score': self.overall_score,
            'category_scores': {cat.value: score for cat, score in self.category_scores.items()},
            'issues': [issue.to_dict() for issue in self.issues],
            'passed_checks': self.passed_checks,
            'total_checks': self.total_checks,
            'has_critical_issues': self.has_critical_issues,
            'has_high_issues': self.has_high_issues,
            'data_quality': self.data_quality.to_dict()
        }


@dataclass
class QualityThresholds:
    """Quality thresholds for validation."""
    completeness_threshold: float = 0.8
    accuracy_threshold: float = 0.9
    consistency_threshold: float = 0.85
    timeliness_threshold: float = 0.7
    overall_threshold: float = 0.8
    max_cost_variance_percent: float = 5.0
    max_data_age_hours: float = 48.0
    min_service_count: int = 1
    max_zero_cost_services_percent: float = 20.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'completeness_threshold': self.completeness_threshold,
            'accuracy_threshold': self.accuracy_threshold,
            'consistency_threshold': self.consistency_threshold,
            'timeliness_threshold': self.timeliness_threshold,
            'overall_threshold': self.overall_threshold,
            'max_cost_variance_percent': self.max_cost_variance_percent,
            'max_data_age_hours': self.max_data_age_hours,
            'min_service_count': self.min_service_count,
            'max_zero_cost_services_percent': self.max_zero_cost_services_percent
        }


@dataclass
class QualityReport:
    """Comprehensive data quality report."""
    report_id: str
    generated_at: datetime
    client_id: str
    date_range: Tuple[str, str]
    total_records: int
    validation_results: List[ValidationResult]
    summary_statistics: Dict[str, Any]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'client_id': self.client_id,
            'date_range': self.date_range,
            'total_records': self.total_records,
            'validation_results': [result.to_dict() for result in self.validation_results],
            'summary_statistics': self.summary_statistics,
            'recommendations': self.recommendations
        }


class DataValidator:
    """Core data validator with comprehensive validation checks."""
    
    def __init__(self, thresholds: Optional[QualityThresholds] = None):
        """Initialize data validator."""
        self.thresholds = thresholds or QualityThresholds()
        self.logger = logging.getLogger(f"{__name__}.DataValidator")
        
        # Validation statistics
        self.validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'critical_issues_found': 0,
            'high_issues_found': 0
        }
    
    async def validate_cost_record(
        self,
        record: UnifiedCostRecord,
        original_data: Optional[ProviderCostData] = None
    ) -> ValidationResult:
        """
        Perform comprehensive validation of a unified cost record.
        
        Args:
            record: Unified cost record to validate
            original_data: Optional original provider data for comparison
            
        Returns:
            ValidationResult with detailed validation information
        """
        self.logger.debug(f"Starting validation for record {record.record_id}")
        
        issues = []
        category_scores = {}
        total_checks = 0
        passed_checks = 0
        
        # Completeness validation
        completeness_issues, completeness_score, completeness_checks = await self._validate_completeness(record)
        issues.extend(completeness_issues)
        category_scores[ValidationCategory.COMPLETENESS] = completeness_score
        total_checks += completeness_checks[1]
        passed_checks += completeness_checks[0]
        
        # Accuracy validation
        accuracy_issues, accuracy_score, accuracy_checks = await self._validate_accuracy(record, original_data)
        issues.extend(accuracy_issues)
        category_scores[ValidationCategory.ACCURACY] = accuracy_score
        total_checks += accuracy_checks[1]
        passed_checks += accuracy_checks[0]
        
        # Consistency validation
        consistency_issues, consistency_score, consistency_checks = await self._validate_consistency(record)
        issues.extend(consistency_issues)
        category_scores[ValidationCategory.CONSISTENCY] = consistency_score
        total_checks += consistency_checks[1]
        passed_checks += consistency_checks[0]
        
        # Timeliness validation
        timeliness_issues, timeliness_score, timeliness_checks = await self._validate_timeliness(record)
        issues.extend(timeliness_issues)
        category_scores[ValidationCategory.TIMELINESS] = timeliness_score
        total_checks += timeliness_checks[1]
        passed_checks += timeliness_checks[0]
        
        # Validity validation
        validity_issues, validity_score, validity_checks = await self._validate_validity(record)
        issues.extend(validity_issues)
        category_scores[ValidationCategory.VALIDITY] = validity_score
        total_checks += validity_checks[1]
        passed_checks += validity_checks[0]
        
        # Calculate overall score
        overall_score = sum(category_scores.values()) / len(category_scores) if category_scores else 0.0
        
        # Create enhanced data quality object
        data_quality = self._create_enhanced_data_quality(record, issues, category_scores)
        
        # Update statistics
        self.validation_stats['total_validations'] += 1
        if overall_score >= self.thresholds.overall_threshold:
            self.validation_stats['passed_validations'] += 1
        else:
            self.validation_stats['failed_validations'] += 1
        
        # Count critical and high issues
        critical_count = len([i for i in issues if i.severity == ValidationSeverity.CRITICAL])
        high_count = len([i for i in issues if i.severity == ValidationSeverity.HIGH])
        self.validation_stats['critical_issues_found'] += critical_count
        self.validation_stats['high_issues_found'] += high_count
        
        return ValidationResult(
            record_id=record.record_id,
            provider=record.provider,
            client_id=record.client_id,
            validation_timestamp=datetime.utcnow(),
            overall_score=overall_score,
            category_scores=category_scores,
            issues=issues,
            passed_checks=passed_checks,
            total_checks=total_checks,
            data_quality=data_quality
        )
    
    async def _validate_completeness(
        self, 
        record: UnifiedCostRecord
    ) -> Tuple[List[ValidationIssue], float, Tuple[int, int]]:
        """Validate data completeness."""
        issues = []
        passed = 0
        total = 0
        
        # Check if basic fields are present
        total += 1
        if not record.client_id:
            issues.append(ValidationIssue(
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.CRITICAL,
                message="Client ID is missing",
                field_name="client_id",
                suggestion="Ensure client_id is provided during data collection"
            ))
        else:
            passed += 1
        
        total += 1
        if not record.date:
            issues.append(ValidationIssue(
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.CRITICAL,
                message="Date is missing",
                field_name="date",
                suggestion="Ensure date is provided in YYYY-MM-DD format"
            ))
        else:
            passed += 1
        
        # Check if cost data is present
        total += 1
        if not record.services and not record.accounts:
            issues.append(ValidationIssue(
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.HIGH,
                message="No service or account cost data available",
                suggestion="Verify data collection process and provider API access"
            ))
        else:
            passed += 1
        
        # Check service data completeness
        if record.services:
            total += 1
            services_with_zero_cost = sum(1 for s in record.services.values() if s.cost == 0)
            zero_cost_percentage = (services_with_zero_cost / len(record.services)) * 100
            
            if zero_cost_percentage > self.thresholds.max_zero_cost_services_percent:
                issues.append(ValidationIssue(
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.MEDIUM,
                    message=f"High percentage of zero-cost services: {zero_cost_percentage:.1f}%",
                    current_value=zero_cost_percentage,
                    expected_value=self.thresholds.max_zero_cost_services_percent,
                    suggestion="Review data collection filters and service inclusion criteria"
                ))
            else:
                passed += 1
        
        # Check metadata completeness
        total += 1
        if not record.collection_metadata:
            issues.append(ValidationIssue(
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.LOW,
                message="Collection metadata is missing",
                field_name="collection_metadata",
                suggestion="Include collection metadata for better data lineage"
            ))
        else:
            passed += 1
        
        # Calculate completeness score
        score = passed / total if total > 0 else 0.0
        
        return issues, score, (passed, total)
    
    async def _validate_accuracy(
        self, 
        record: UnifiedCostRecord,
        original_data: Optional[ProviderCostData]
    ) -> Tuple[List[ValidationIssue], float, Tuple[int, int]]:
        """Validate data accuracy."""
        issues = []
        passed = 0
        total = 0
        
        # Check cost consistency between services and total
        if record.services:
            total += 1
            service_total = sum(s.cost for s in record.services.values())
            cost_difference = abs(record.total_cost - service_total)
            
            if cost_difference > Decimal('0.01'):
                variance_percent = float((cost_difference / max(record.total_cost, Decimal('0.01'))) * 100)
                
                if variance_percent > self.thresholds.max_cost_variance_percent:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.ACCURACY,
                        severity=ValidationSeverity.HIGH,
                        message=f"Total cost doesn't match sum of service costs (variance: {variance_percent:.2f}%)",
                        current_value=float(record.total_cost),
                        expected_value=float(service_total),
                        suggestion="Review cost aggregation logic and data collection process"
                    ))
                else:
                    passed += 1
            else:
                passed += 1
        
        # Check cost consistency between accounts and total
        if record.accounts:
            total += 1
            account_total = sum(a.cost for a in record.accounts.values())
            cost_difference = abs(record.total_cost - account_total)
            
            if cost_difference > Decimal('0.01'):
                variance_percent = float((cost_difference / max(record.total_cost, Decimal('0.01'))) * 100)
                
                if variance_percent > self.thresholds.max_cost_variance_percent:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.ACCURACY,
                        severity=ValidationSeverity.HIGH,
                        message=f"Total cost doesn't match sum of account costs (variance: {variance_percent:.2f}%)",
                        current_value=float(record.total_cost),
                        expected_value=float(account_total),
                        suggestion="Review account cost aggregation and data collection"
                    ))
                else:
                    passed += 1
            else:
                passed += 1
        
        # Compare with original data if available
        if original_data:
            total += 1
            original_total = original_data.total_cost
            
            # Allow for currency conversion differences
            tolerance = max(Decimal('0.01'), original_total * Decimal('0.01'))  # 1% tolerance
            cost_difference = abs(record.total_cost - original_total)
            
            if cost_difference > tolerance:
                variance_percent = float((cost_difference / max(original_total, Decimal('0.01'))) * 100)
                issues.append(ValidationIssue(
                    category=ValidationCategory.ACCURACY,
                    severity=ValidationSeverity.MEDIUM,
                    message=f"Normalized cost differs significantly from original (variance: {variance_percent:.2f}%)",
                    current_value=float(record.total_cost),
                    expected_value=float(original_total),
                    suggestion="Review currency conversion and normalization process"
                ))
            else:
                passed += 1
        
        # Validate service categories
        if record.services:
            total += 1
            unknown_categories = sum(1 for s in record.services.values() 
                                   if s.unified_category == ServiceCategory.OTHER)
            unknown_percentage = (unknown_categories / len(record.services)) * 100
            
            if unknown_percentage > 30:  # More than 30% unknown categories
                issues.append(ValidationIssue(
                    category=ValidationCategory.ACCURACY,
                    severity=ValidationSeverity.MEDIUM,
                    message=f"High percentage of services with unknown categories: {unknown_percentage:.1f}%",
                    current_value=unknown_percentage,
                    suggestion="Review and update service mapping configuration"
                ))
            else:
                passed += 1
        
        score = passed / total if total > 0 else 1.0
        return issues, score, (passed, total)
    
    async def _validate_consistency(
        self, 
        record: UnifiedCostRecord
    ) -> Tuple[List[ValidationIssue], float, Tuple[int, int]]:
        """Validate data consistency."""
        issues = []
        passed = 0
        total = 0
        
        # Check for negative costs
        total += 1
        if record.total_cost < 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.CRITICAL,
                message="Total cost is negative",
                field_name="total_cost",
                current_value=float(record.total_cost),
                suggestion="Review data collection and processing for cost calculation errors"
            ))
        else:
            passed += 1
        
        # Check service costs for consistency
        negative_services = []
        for service_name, service in record.services.items():
            if service.cost < 0:
                negative_services.append(service_name)
        
        total += 1
        if negative_services:
            issues.append(ValidationIssue(
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.HIGH,
                message=f"Services with negative costs: {', '.join(negative_services)}",
                suggestion="Review service cost calculation and data collection"
            ))
        else:
            passed += 1
        
        # Check account costs for consistency
        negative_accounts = []
        for account_id, account in record.accounts.items():
            if account.cost < 0:
                negative_accounts.append(account_id)
        
        total += 1
        if negative_accounts:
            issues.append(ValidationIssue(
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.HIGH,
                message=f"Accounts with negative costs: {', '.join(negative_accounts)}",
                suggestion="Review account cost calculation and data collection"
            ))
        else:
            passed += 1
        
        # Check currency consistency
        total += 1
        currencies_used = {record.currency}
        
        for service in record.services.values():
            currencies_used.add(service.currency)
        
        for account in record.accounts.values():
            currencies_used.add(account.currency)
        
        for region in record.regions.values():
            currencies_used.add(region.currency)
        
        if len(currencies_used) > 1:
            issues.append(ValidationIssue(
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.MEDIUM,
                message=f"Multiple currencies detected: {[c.value for c in currencies_used]}",
                suggestion="Ensure consistent currency conversion across all cost components"
            ))
        else:
            passed += 1
        
        # Check date format consistency
        total += 1
        try:
            datetime.strptime(record.date, '%Y-%m-%d')
            passed += 1
        except ValueError:
            issues.append(ValidationIssue(
                category=ValidationCategory.CONSISTENCY,
                severity=ValidationSeverity.HIGH,
                message=f"Invalid date format: {record.date}",
                field_name="date",
                expected_value="YYYY-MM-DD",
                suggestion="Ensure date is in YYYY-MM-DD format"
            ))
        
        score = passed / total if total > 0 else 1.0
        return issues, score, (passed, total)
    
    async def _validate_timeliness(
        self, 
        record: UnifiedCostRecord
    ) -> Tuple[List[ValidationIssue], float, Tuple[int, int]]:
        """Validate data timeliness."""
        issues = []
        passed = 0
        total = 0
        
        # Check data freshness
        if record.collection_metadata:
            total += 1
            data_age_hours = (datetime.utcnow() - record.collection_metadata.collection_timestamp).total_seconds() / 3600
            
            if data_age_hours > self.thresholds.max_data_age_hours:
                issues.append(ValidationIssue(
                    category=ValidationCategory.TIMELINESS,
                    severity=ValidationSeverity.MEDIUM,
                    message=f"Data is {data_age_hours:.1f} hours old",
                    current_value=data_age_hours,
                    expected_value=self.thresholds.max_data_age_hours,
                    suggestion="Increase data collection frequency or review collection schedule"
                ))
            else:
                passed += 1
            
            # Check data freshness from provider
            total += 1
            provider_freshness = record.collection_metadata.data_freshness_hours
            if provider_freshness > self.thresholds.max_data_age_hours:
                issues.append(ValidationIssue(
                    category=ValidationCategory.TIMELINESS,
                    severity=ValidationSeverity.LOW,
                    message=f"Provider data is {provider_freshness:.1f} hours old",
                    current_value=provider_freshness,
                    expected_value=self.thresholds.max_data_age_hours,
                    suggestion="Provider data may have inherent delays; consider this in analysis"
                ))
            else:
                passed += 1
        
        # Check if record date is reasonable (not too far in future or past)
        total += 1
        try:
            record_date = datetime.strptime(record.date, '%Y-%m-%d').date()
            today = datetime.utcnow().date()
            days_difference = abs((record_date - today).days)
            
            if days_difference > 90:  # More than 90 days difference
                issues.append(ValidationIssue(
                    category=ValidationCategory.TIMELINESS,
                    severity=ValidationSeverity.LOW,
                    message=f"Record date is {days_difference} days from today",
                    field_name="date",
                    current_value=record.date,
                    suggestion="Verify record date is correct for the intended analysis period"
                ))
            else:
                passed += 1
        except ValueError:
            # Date format issue will be caught in consistency validation
            pass
        
        score = passed / total if total > 0 else 1.0
        return issues, score, (passed, total)
    
    async def _validate_validity(
        self, 
        record: UnifiedCostRecord
    ) -> Tuple[List[ValidationIssue], float, Tuple[int, int]]:
        """Validate data validity (format, ranges, etc.)."""
        issues = []
        passed = 0
        total = 0
        
        # Validate client ID format
        total += 1
        if record.client_id and not re.match(r'^[a-zA-Z0-9_-]+$', record.client_id):
            issues.append(ValidationIssue(
                category=ValidationCategory.VALIDITY,
                severity=ValidationSeverity.LOW,
                message="Client ID contains invalid characters",
                field_name="client_id",
                current_value=record.client_id,
                suggestion="Use only alphanumeric characters, hyphens, and underscores"
            ))
        else:
            passed += 1
        
        # Validate cost ranges (reasonable values)
        total += 1
        if record.total_cost > Decimal('1000000'):  # More than $1M
            issues.append(ValidationIssue(
                category=ValidationCategory.VALIDITY,
                severity=ValidationSeverity.LOW,
                message=f"Very high total cost: {record.total_cost}",
                field_name="total_cost",
                current_value=float(record.total_cost),
                suggestion="Verify cost amount is correct and in expected currency"
            ))
        else:
            passed += 1
        
        # Validate service names
        invalid_service_names = []
        for service_name in record.services.keys():
            if not service_name or not service_name.strip():
                invalid_service_names.append("empty_name")
            elif len(service_name) > 100:
                invalid_service_names.append(f"{service_name[:20]}...")
        
        total += 1
        if invalid_service_names:
            issues.append(ValidationIssue(
                category=ValidationCategory.VALIDITY,
                severity=ValidationSeverity.MEDIUM,
                message=f"Invalid service names: {', '.join(invalid_service_names)}",
                suggestion="Ensure service names are non-empty and reasonable length"
            ))
        else:
            passed += 1
        
        # Validate account IDs
        invalid_account_ids = []
        for account_id in record.accounts.keys():
            if not account_id or not account_id.strip():
                invalid_account_ids.append("empty_id")
            elif not re.match(r'^[a-zA-Z0-9_-]+$', account_id):
                invalid_account_ids.append(account_id[:20])
        
        total += 1
        if invalid_account_ids:
            issues.append(ValidationIssue(
                category=ValidationCategory.VALIDITY,
                severity=ValidationSeverity.MEDIUM,
                message=f"Invalid account IDs: {', '.join(invalid_account_ids)}",
                suggestion="Ensure account IDs follow provider naming conventions"
            ))
        else:
            passed += 1
        
        score = passed / total if total > 0 else 1.0
        return issues, score, (passed, total)
    
    def _create_enhanced_data_quality(
        self,
        record: UnifiedCostRecord,
        issues: List[ValidationIssue],
        category_scores: Dict[ValidationCategory, float]
    ) -> DataQuality:
        """Create enhanced data quality object with validation results."""
        # Extract scores by category
        completeness_score = category_scores.get(ValidationCategory.COMPLETENESS, 0.0)
        accuracy_score = category_scores.get(ValidationCategory.ACCURACY, 0.0)
        consistency_score = category_scores.get(ValidationCategory.CONSISTENCY, 0.0)
        timeliness_score = category_scores.get(ValidationCategory.TIMELINESS, 0.0)
        
        # Determine confidence level based on overall score and critical issues
        overall_score = sum(category_scores.values()) / len(category_scores) if category_scores else 0.0
        has_critical = any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)
        has_high = any(issue.severity == ValidationSeverity.HIGH for issue in issues)
        
        if has_critical:
            confidence_level = DataQualityLevel.LOW
        elif has_high or overall_score < 0.7:
            confidence_level = DataQualityLevel.MEDIUM
        elif overall_score >= 0.9:
            confidence_level = DataQualityLevel.HIGH
        else:
            confidence_level = DataQualityLevel.MEDIUM
        
        # Separate errors and warnings
        errors = [issue.message for issue in issues 
                 if issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.HIGH]]
        warnings = [issue.message for issue in issues 
                   if issue.severity in [ValidationSeverity.MEDIUM, ValidationSeverity.LOW]]
        
        return DataQuality(
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            timeliness_score=timeliness_score,
            consistency_score=consistency_score,
            confidence_level=confidence_level,
            validation_errors=errors,
            validation_warnings=warnings
        )
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = self.validation_stats['total_validations']
        return {
            **self.validation_stats,
            'success_rate': (self.validation_stats['passed_validations'] / max(1, total)) * 100,
            'failure_rate': (self.validation_stats['failed_validations'] / max(1, total)) * 100,
            'critical_issue_rate': (self.validation_stats['critical_issues_found'] / max(1, total)) * 100,
            'high_issue_rate': (self.validation_stats['high_issues_found'] / max(1, total)) * 100
        }


class DataQualityEngine:
    """
    Comprehensive data quality engine that orchestrates validation, reporting, and alerting.
    """
    
    def __init__(self, thresholds: Optional[QualityThresholds] = None):
        """Initialize data quality engine."""
        self.thresholds = thresholds or QualityThresholds()
        self.validator = DataValidator(self.thresholds)
        self.logger = logging.getLogger(f"{__name__}.DataQualityEngine")
        
        # Quality tracking
        self.quality_history: Dict[str, List[ValidationResult]] = {}
        self.alert_callbacks: List[callable] = []
    
    async def validate_cost_record(
        self,
        record: UnifiedCostRecord,
        original_data: Optional[ProviderCostData] = None
    ) -> ValidationResult:
        """Validate a single cost record."""
        result = await self.validator.validate_cost_record(record, original_data)
        
        # Store in history
        client_key = f"{record.client_id}_{record.provider.value}"
        if client_key not in self.quality_history:
            self.quality_history[client_key] = []
        
        self.quality_history[client_key].append(result)
        
        # Keep only last 100 results per client-provider
        if len(self.quality_history[client_key]) > 100:
            self.quality_history[client_key] = self.quality_history[client_key][-100:]
        
        # Check for alerts
        await self._check_quality_alerts(result)
        
        return result
    
    async def batch_validate(
        self,
        records: List[UnifiedCostRecord],
        original_data_map: Optional[Dict[str, ProviderCostData]] = None,
        max_concurrent: int = 10
    ) -> List[ValidationResult]:
        """Validate multiple cost records concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_with_semaphore(record):
            async with semaphore:
                original_data = None
                if original_data_map:
                    original_data = original_data_map.get(record.record_id)
                return await self.validate_cost_record(record, original_data)
        
        tasks = [validate_with_semaphore(record) for record in records]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        validation_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to validate record {i}: {result}")
            else:
                validation_results.append(result)
        
        return validation_results
    
    async def generate_quality_report(
        self,
        client_id: str,
        start_date: str,
        end_date: str,
        providers: Optional[List[CloudProvider]] = None
    ) -> QualityReport:
        """Generate comprehensive data quality report."""
        import uuid
        
        report_id = str(uuid.uuid4())
        
        # Filter validation results
        filtered_results = []
        for key, results in self.quality_history.items():
            key_client_id, key_provider = key.split('_', 1)
            
            if key_client_id != client_id:
                continue
            
            if providers and CloudProvider(key_provider) not in providers:
                continue
            
            # Filter by date range
            for result in results:
                record_date = datetime.strptime(result.validation_timestamp.date().isoformat(), '%Y-%m-%d')
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                
                if start_dt <= record_date <= end_dt:
                    filtered_results.append(result)
        
        # Calculate summary statistics
        summary_stats = self._calculate_summary_statistics(filtered_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(filtered_results, summary_stats)
        
        return QualityReport(
            report_id=report_id,
            generated_at=datetime.utcnow(),
            client_id=client_id,
            date_range=(start_date, end_date),
            total_records=len(filtered_results),
            validation_results=filtered_results,
            summary_statistics=summary_stats,
            recommendations=recommendations
        )
    
    def _calculate_summary_statistics(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Calculate summary statistics for validation results."""
        if not results:
            return {}
        
        # Overall scores
        overall_scores = [r.overall_score for r in results]
        
        # Category scores
        category_stats = {}
        for category in ValidationCategory:
            scores = [r.category_scores.get(category, 0.0) for r in results]
            if scores:
                category_stats[category.value] = {
                    'mean': statistics.mean(scores),
                    'median': statistics.median(scores),
                    'min': min(scores),
                    'max': max(scores),
                    'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0.0
                }
        
        # Issue statistics
        total_issues = sum(len(r.issues) for r in results)
        critical_issues = sum(len(r.get_issues_by_severity(ValidationSeverity.CRITICAL)) for r in results)
        high_issues = sum(len(r.get_issues_by_severity(ValidationSeverity.HIGH)) for r in results)
        
        # Provider breakdown
        provider_stats = {}
        for result in results:
            provider = result.provider.value
            if provider not in provider_stats:
                provider_stats[provider] = {
                    'count': 0,
                    'avg_score': 0.0,
                    'issues': 0
                }
            
            provider_stats[provider]['count'] += 1
            provider_stats[provider]['avg_score'] += result.overall_score
            provider_stats[provider]['issues'] += len(result.issues)
        
        # Calculate averages
        for provider_data in provider_stats.values():
            if provider_data['count'] > 0:
                provider_data['avg_score'] /= provider_data['count']
        
        return {
            'overall_statistics': {
                'mean_score': statistics.mean(overall_scores),
                'median_score': statistics.median(overall_scores),
                'min_score': min(overall_scores),
                'max_score': max(overall_scores),
                'std_dev': statistics.stdev(overall_scores) if len(overall_scores) > 1 else 0.0
            },
            'category_statistics': category_stats,
            'issue_statistics': {
                'total_issues': total_issues,
                'critical_issues': critical_issues,
                'high_issues': high_issues,
                'medium_issues': sum(len(r.get_issues_by_severity(ValidationSeverity.MEDIUM)) for r in results),
                'low_issues': sum(len(r.get_issues_by_severity(ValidationSeverity.LOW)) for r in results),
                'avg_issues_per_record': total_issues / len(results)
            },
            'provider_statistics': provider_stats,
            'quality_trends': self._calculate_quality_trends(results)
        }
    
    def _calculate_quality_trends(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Calculate quality trends over time."""
        if len(results) < 2:
            return {}
        
        # Sort by timestamp
        sorted_results = sorted(results, key=lambda r: r.validation_timestamp)
        
        # Calculate trend for overall scores
        scores = [r.overall_score for r in sorted_results]
        
        # Simple linear trend calculation
        n = len(scores)
        x_values = list(range(n))
        
        # Calculate slope (trend)
        x_mean = sum(x_values) / n
        y_mean = sum(scores) / n
        
        numerator = sum((x_values[i] - x_mean) * (scores[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        trend_slope = numerator / denominator if denominator != 0 else 0
        
        # Determine trend direction
        if trend_slope > 0.01:
            trend_direction = "improving"
        elif trend_slope < -0.01:
            trend_direction = "declining"
        else:
            trend_direction = "stable"
        
        return {
            'trend_direction': trend_direction,
            'trend_slope': trend_slope,
            'first_score': scores[0],
            'last_score': scores[-1],
            'score_change': scores[-1] - scores[0]
        }
    
    def _generate_recommendations(
        self, 
        results: List[ValidationResult], 
        summary_stats: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if not results:
            return recommendations
        
        # Check overall quality
        overall_stats = summary_stats.get('overall_statistics', {})
        mean_score = overall_stats.get('mean_score', 0.0)
        
        if mean_score < self.thresholds.overall_threshold:
            recommendations.append(
                f"Overall data quality score ({mean_score:.2f}) is below threshold "
                f"({self.thresholds.overall_threshold}). Review data collection processes."
            )
        
        # Check category-specific issues
        category_stats = summary_stats.get('category_statistics', {})
        
        for category, stats in category_stats.items():
            if stats['mean'] < getattr(self.thresholds, f"{category}_threshold", 0.8):
                recommendations.append(
                    f"Low {category} score ({stats['mean']:.2f}). "
                    f"Focus on improving {category} in data collection and processing."
                )
        
        # Check for high issue rates
        issue_stats = summary_stats.get('issue_statistics', {})
        critical_rate = issue_stats.get('critical_issues', 0) / max(1, len(results))
        
        if critical_rate > 0.1:  # More than 10% of records have critical issues
            recommendations.append(
                f"High critical issue rate ({critical_rate:.1%}). "
                "Immediate attention required for data collection infrastructure."
            )
        
        # Provider-specific recommendations
        provider_stats = summary_stats.get('provider_statistics', {})
        for provider, stats in provider_stats.items():
            if stats['avg_score'] < self.thresholds.overall_threshold:
                recommendations.append(
                    f"Data quality for {provider} is below threshold ({stats['avg_score']:.2f}). "
                    f"Review {provider}-specific data collection and processing."
                )
        
        # Trend-based recommendations
        trends = summary_stats.get('quality_trends', {})
        if trends.get('trend_direction') == 'declining':
            recommendations.append(
                "Data quality is declining over time. "
                "Investigate recent changes in data collection or processing."
            )
        
        return recommendations
    
    async def _check_quality_alerts(self, result: ValidationResult):
        """Check if quality alerts should be triggered."""
        # Critical issues always trigger alerts
        if result.has_critical_issues:
            await self._trigger_alert(
                "critical",
                f"Critical data quality issues found for {result.provider.value} data",
                result
            )
        
        # Low overall score triggers alert
        if result.overall_score < self.thresholds.overall_threshold:
            await self._trigger_alert(
                "low_quality",
                f"Data quality score ({result.overall_score:.2f}) below threshold",
                result
            )
    
    async def _trigger_alert(self, alert_type: str, message: str, result: ValidationResult):
        """Trigger quality alert."""
        alert_data = {
            'type': alert_type,
            'message': message,
            'client_id': result.client_id,
            'provider': result.provider.value,
            'timestamp': datetime.utcnow().isoformat(),
            'validation_result': result.to_dict()
        }
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert_data)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    def register_alert_callback(self, callback: callable):
        """Register callback for quality alerts."""
        self.alert_callbacks.append(callback)
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Get comprehensive quality statistics."""
        validator_stats = self.validator.get_validation_statistics()
        
        # Calculate history statistics
        total_records = sum(len(results) for results in self.quality_history.values())
        clients_tracked = len(set(key.split('_')[0] for key in self.quality_history.keys()))
        providers_tracked = len(set(key.split('_')[1] for key in self.quality_history.keys()))
        
        return {
            'validator_statistics': validator_stats,
            'history_statistics': {
                'total_records_in_history': total_records,
                'clients_tracked': clients_tracked,
                'providers_tracked': providers_tracked,
                'alert_callbacks_registered': len(self.alert_callbacks)
            },
            'thresholds': self.thresholds.to_dict()
        }


# Convenience functions
async def validate_cost_record(
    record: UnifiedCostRecord,
    original_data: Optional[ProviderCostData] = None,
    thresholds: Optional[QualityThresholds] = None
) -> ValidationResult:
    """
    Convenience function to validate a single cost record.
    
    Args:
        record: Unified cost record to validate
        original_data: Optional original provider data
        thresholds: Optional quality thresholds
        
    Returns:
        ValidationResult
    """
    engine = DataQualityEngine(thresholds)
    return await engine.validate_cost_record(record, original_data)


async def batch_validate_records(
    records: List[UnifiedCostRecord],
    original_data_map: Optional[Dict[str, ProviderCostData]] = None,
    thresholds: Optional[QualityThresholds] = None,
    max_concurrent: int = 10
) -> List[ValidationResult]:
    """
    Convenience function to validate multiple cost records.
    
    Args:
        records: List of unified cost records to validate
        original_data_map: Optional mapping of record IDs to original data
        thresholds: Optional quality thresholds
        max_concurrent: Maximum concurrent validations
        
    Returns:
        List of ValidationResult objects
    """
    engine = DataQualityEngine(thresholds)
    return await engine.batch_validate(records, original_data_map, max_concurrent)