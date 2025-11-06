"""
Data Validation Models

This module provides validation utilities and models for ensuring data quality
across the multi-cloud cost analytics platform.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import re


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationType(Enum):
    """Types of validation checks."""
    FORMAT = "format"
    RANGE = "range"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"
    BUSINESS_RULE = "business_rule"
    DATA_QUALITY = "data_quality"


@dataclass
class ValidationIssue:
    """Represents a validation issue found during data validation."""
    field_name: str
    issue_type: ValidationType
    severity: ValidationSeverity
    message: str
    current_value: Any = None
    expected_value: Any = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage and reporting."""
        return {
            'field_name': self.field_name,
            'issue_type': self.issue_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'current_value': str(self.current_value) if self.current_value is not None else None,
            'expected_value': str(self.expected_value) if self.expected_value is not None else None,
            'suggestion': self.suggestion
        }


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    validation_timestamp: datetime = field(default_factory=datetime.utcnow)
    validator_version: str = "1.0.0"
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue."""
        self.issues.append(issue)
        if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.is_valid = False
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues of a specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def has_errors(self) -> bool:
        """Check if there are any error or critical issues."""
        return any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                  for issue in self.issues)
    
    def get_summary(self) -> Dict[str, int]:
        """Get a summary count of issues by severity."""
        summary = {severity.value: 0 for severity in ValidationSeverity}
        for issue in self.issues:
            summary[issue.severity.value] += 1
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage and reporting."""
        return {
            'is_valid': self.is_valid,
            'issues': [issue.to_dict() for issue in self.issues],
            'validation_timestamp': self.validation_timestamp.isoformat(),
            'validator_version': self.validator_version,
            'summary': self.get_summary()
        }


class ValidationRule:
    """Base class for validation rules."""
    
    def __init__(self, field_name: str, rule_name: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.field_name = field_name
        self.rule_name = rule_name
        self.severity = severity
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> Optional[ValidationIssue]:
        """
        Validate a value against this rule.
        
        Args:
            value: The value to validate
            context: Additional context for validation
            
        Returns:
            ValidationIssue if validation fails, None if passes
        """
        raise NotImplementedError("Subclasses must implement validate method")


class RequiredFieldRule(ValidationRule):
    """Validates that a field is not None or empty."""
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> Optional[ValidationIssue]:
        if value is None or (isinstance(value, str) and not value.strip()):
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.COMPLETENESS,
                severity=self.severity,
                message=f"Field '{self.field_name}' is required but is empty or None",
                current_value=value,
                suggestion="Provide a valid value for this field"
            )
        return None


class NumericRangeRule(ValidationRule):
    """Validates that a numeric value is within a specified range."""
    
    def __init__(self, field_name: str, min_value: Optional[float] = None, 
                 max_value: Optional[float] = None, severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(field_name, "numeric_range", severity)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> Optional[ValidationIssue]:
        if value is None:
            return None
        
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.FORMAT,
                severity=self.severity,
                message=f"Field '{self.field_name}' must be numeric",
                current_value=value,
                suggestion="Provide a numeric value"
            )
        
        if self.min_value is not None and numeric_value < self.min_value:
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.RANGE,
                severity=self.severity,
                message=f"Field '{self.field_name}' value {numeric_value} is below minimum {self.min_value}",
                current_value=value,
                expected_value=f">= {self.min_value}",
                suggestion=f"Provide a value >= {self.min_value}"
            )
        
        if self.max_value is not None and numeric_value > self.max_value:
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.RANGE,
                severity=self.severity,
                message=f"Field '{self.field_name}' value {numeric_value} is above maximum {self.max_value}",
                current_value=value,
                expected_value=f"<= {self.max_value}",
                suggestion=f"Provide a value <= {self.max_value}"
            )
        
        return None


class RegexRule(ValidationRule):
    """Validates that a string matches a regular expression pattern."""
    
    def __init__(self, field_name: str, pattern: str, pattern_description: str = None,
                 severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(field_name, "regex", severity)
        self.pattern = re.compile(pattern)
        self.pattern_description = pattern_description or f"pattern {pattern}"
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> Optional[ValidationIssue]:
        if value is None:
            return None
        
        if not isinstance(value, str):
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.FORMAT,
                severity=self.severity,
                message=f"Field '{self.field_name}' must be a string",
                current_value=value,
                suggestion="Provide a string value"
            )
        
        if not self.pattern.match(value):
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.FORMAT,
                severity=self.severity,
                message=f"Field '{self.field_name}' does not match {self.pattern_description}",
                current_value=value,
                suggestion=f"Provide a value matching {self.pattern_description}"
            )
        
        return None


class DateFormatRule(ValidationRule):
    """Validates that a string is a valid date in the specified format."""
    
    def __init__(self, field_name: str, date_format: str = "%Y-%m-%d",
                 severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(field_name, "date_format", severity)
        self.date_format = date_format
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> Optional[ValidationIssue]:
        if value is None:
            return None
        
        if not isinstance(value, str):
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.FORMAT,
                severity=self.severity,
                message=f"Field '{self.field_name}' must be a string",
                current_value=value,
                suggestion="Provide a string date value"
            )
        
        try:
            datetime.strptime(value, self.date_format)
        except ValueError:
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.FORMAT,
                severity=self.severity,
                message=f"Field '{self.field_name}' is not a valid date in format {self.date_format}",
                current_value=value,
                expected_value=self.date_format,
                suggestion=f"Provide a date in format {self.date_format}"
            )
        
        return None


class EnumRule(ValidationRule):
    """Validates that a value is one of the allowed enum values."""
    
    def __init__(self, field_name: str, enum_class: type, severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(field_name, "enum", severity)
        self.enum_class = enum_class
        self.allowed_values = [e.value for e in enum_class]
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> Optional[ValidationIssue]:
        if value is None:
            return None
        
        if value not in self.allowed_values:
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.FORMAT,
                severity=self.severity,
                message=f"Field '{self.field_name}' has invalid value '{value}'",
                current_value=value,
                expected_value=f"One of: {', '.join(self.allowed_values)}",
                suggestion=f"Use one of the allowed values: {', '.join(self.allowed_values)}"
            )
        
        return None


class ConsistencyRule(ValidationRule):
    """Validates consistency between related fields."""
    
    def __init__(self, field_name: str, related_field: str, consistency_check: Callable,
                 error_message: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(field_name, "consistency", severity)
        self.related_field = related_field
        self.consistency_check = consistency_check
        self.error_message = error_message
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> Optional[ValidationIssue]:
        if context is None or self.related_field not in context:
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                message=f"Cannot validate consistency: related field '{self.related_field}' not available",
                current_value=value,
                suggestion="Ensure related field is provided for validation"
            )
        
        related_value = context[self.related_field]
        
        if not self.consistency_check(value, related_value):
            return ValidationIssue(
                field_name=self.field_name,
                issue_type=ValidationType.CONSISTENCY,
                severity=self.severity,
                message=self.error_message,
                current_value=value,
                suggestion="Ensure field values are consistent with related fields"
            )
        
        return None


class CostDataValidator:
    """Comprehensive validator for cost data."""
    
    def __init__(self):
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> Dict[str, List[ValidationRule]]:
        """Initialize validation rules for cost data."""
        from .multi_cloud_models import CloudProvider, ServiceCategory, Currency
        
        return {
            'client_id': [
                RequiredFieldRule('client_id'),
                RegexRule('client_id', r'^[a-zA-Z0-9\-_]+$', 'alphanumeric with hyphens and underscores')
            ],
            'provider': [
                RequiredFieldRule('provider'),
                EnumRule('provider', CloudProvider)
            ],
            'date': [
                RequiredFieldRule('date'),
                DateFormatRule('date', '%Y-%m-%d')
            ],
            'total_cost': [
                RequiredFieldRule('total_cost'),
                NumericRangeRule('total_cost', min_value=0)
            ],
            'currency': [
                RequiredFieldRule('currency'),
                EnumRule('currency', Currency)
            ],
            'service_category': [
                EnumRule('service_category', ServiceCategory)
            ],
            'completeness_score': [
                NumericRangeRule('completeness_score', min_value=0.0, max_value=1.0)
            ],
            'accuracy_score': [
                NumericRangeRule('accuracy_score', min_value=0.0, max_value=1.0)
            ],
            'timeliness_score': [
                NumericRangeRule('timeliness_score', min_value=0.0, max_value=1.0)
            ],
            'consistency_score': [
                NumericRangeRule('consistency_score', min_value=0.0, max_value=1.0)
            ]
        }
    
    def validate_field(self, field_name: str, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate a single field."""
        result = ValidationResult(is_valid=True)
        
        if field_name in self.rules:
            for rule in self.rules[field_name]:
                issue = rule.validate(value, context)
                if issue:
                    result.add_issue(issue)
        
        return result
    
    def validate_cost_record(self, record_data: Dict[str, Any]) -> ValidationResult:
        """Validate a complete cost record."""
        result = ValidationResult(is_valid=True)
        
        # Validate individual fields
        for field_name, value in record_data.items():
            field_result = self.validate_field(field_name, value, record_data)
            result.issues.extend(field_result.issues)
            if not field_result.is_valid:
                result.is_valid = False
        
        # Custom business logic validations
        self._validate_business_rules(record_data, result)
        
        return result
    
    def _validate_business_rules(self, record_data: Dict[str, Any], result: ValidationResult) -> None:
        """Apply business-specific validation rules."""
        
        # Rule: Total cost should match sum of service costs
        if 'services' in record_data and 'total_cost' in record_data:
            services = record_data['services']
            total_cost = record_data['total_cost']
            
            if isinstance(services, dict) and isinstance(total_cost, (int, float, Decimal)):
                service_sum = sum(
                    service.get('cost', 0) if isinstance(service, dict) else 0
                    for service in services.values()
                )
                
                if abs(float(total_cost) - float(service_sum)) > 0.01:
                    result.add_issue(ValidationIssue(
                        field_name='total_cost',
                        issue_type=ValidationType.CONSISTENCY,
                        severity=ValidationSeverity.ERROR,
                        message=f"Total cost ({total_cost}) doesn't match sum of service costs ({service_sum})",
                        current_value=total_cost,
                        expected_value=service_sum,
                        suggestion="Ensure total cost equals the sum of all service costs"
                    ))
        
        # Rule: Date should not be in the future (for cost data)
        if 'date' in record_data:
            try:
                record_date = datetime.strptime(record_data['date'], '%Y-%m-%d').date()
                today = datetime.utcnow().date()
                
                if record_date > today:
                    result.add_issue(ValidationIssue(
                        field_name='date',
                        issue_type=ValidationType.BUSINESS_RULE,
                        severity=ValidationSeverity.WARNING,
                        message=f"Cost data date ({record_date}) is in the future",
                        current_value=record_data['date'],
                        suggestion="Cost data should typically be for past or current dates"
                    ))
            except ValueError:
                pass  # Date format validation will catch this
        
        # Rule: Data quality scores should be reasonable
        quality_fields = ['completeness_score', 'accuracy_score', 'timeliness_score', 'consistency_score']
        low_quality_threshold = 0.5
        
        for field in quality_fields:
            if field in record_data:
                score = record_data[field]
                if isinstance(score, (int, float)) and score < low_quality_threshold:
                    result.add_issue(ValidationIssue(
                        field_name=field,
                        issue_type=ValidationType.DATA_QUALITY,
                        severity=ValidationSeverity.WARNING,
                        message=f"Low data quality score: {field} = {score}",
                        current_value=score,
                        suggestion=f"Investigate why {field} is below {low_quality_threshold}"
                    ))


def create_sample_validation_rules() -> Dict[str, List[ValidationRule]]:
    """Create sample validation rules for testing and examples."""
    from .multi_cloud_models import CloudProvider, ServiceCategory, Currency
    
    return {
        'aws_account_id': [
            RequiredFieldRule('aws_account_id'),
            RegexRule('aws_account_id', r'^\d{12}$', '12-digit AWS account ID')
        ],
        'gcp_project_id': [
            RequiredFieldRule('gcp_project_id'),
            RegexRule('gcp_project_id', r'^[a-z][a-z0-9\-]{4,28}[a-z0-9]$', 'valid GCP project ID format')
        ],
        'azure_subscription_id': [
            RequiredFieldRule('azure_subscription_id'),
            RegexRule('azure_subscription_id', r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', 'UUID format')
        ],
        'email': [
            RequiredFieldRule('email'),
            RegexRule('email', r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', 'valid email format')
        ],
        'cost_threshold': [
            NumericRangeRule('cost_threshold', min_value=0, max_value=1000000)
        ]
    }