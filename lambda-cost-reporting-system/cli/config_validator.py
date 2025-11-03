"""
Configuration Validator for Lambda Cost Reporting System.

This module provides comprehensive validation for client configurations including:
- AWS credential validation
- Configuration completeness checks
- Test report generation for new clients
- Validation reporting and recommendations
"""

import boto3
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import tempfile
import os

from models import ClientConfig, AccountConfig, ReportConfig, BrandingConfig
try:
    from services import ClientConfigManager
except ImportError:
    ClientConfigManager = None

try:
    from services import LambdaCostAgent
except ImportError:
    LambdaCostAgent = None

try:
    from services import LambdaReportGenerator
except ImportError:
    LambdaReportGenerator = None


logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation check."""
    
    def __init__(self, check_name: str, passed: bool, message: str, 
                 severity: str = "error", details: Optional[Dict[str, Any]] = None):
        self.check_name = check_name
        self.passed = passed
        self.message = message
        self.severity = severity  # error, warning, info
        self.details = details or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class ValidationReport:
    """Comprehensive validation report."""
    
    def __init__(self, client_config: ClientConfig):
        self.client_config = client_config
        self.results: List[ValidationResult] = []
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
    
    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result."""
        self.results.append(result)
    
    def finalize(self) -> None:
        """Finalize the report."""
        self.end_time = datetime.utcnow()
    
    def is_valid(self) -> bool:
        """Check if all validations passed."""
        return all(result.passed or result.severity != "error" for result in self.results)
    
    def get_errors(self) -> List[ValidationResult]:
        """Get all error results."""
        return [r for r in self.results if not r.passed and r.severity == "error"]
    
    def get_warnings(self) -> List[ValidationResult]:
        """Get all warning results."""
        return [r for r in self.results if not r.passed and r.severity == "warning"]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        errors = self.get_errors()
        warnings = self.get_warnings()
        passed = [r for r in self.results if r.passed]
        
        return {
            "client_id": self.client_config.client_id,
            "client_name": self.client_config.client_name,
            "total_checks": len(self.results),
            "passed": len(passed),
            "errors": len(errors),
            "warnings": len(warnings),
            "overall_status": "PASSED" if self.is_valid() else "FAILED",
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "summary": self.get_summary(),
            "results": [result.to_dict() for result in self.results],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None
        }


class ConfigValidator:
    """Comprehensive configuration validator."""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the validator.
        
        Args:
            region: AWS region for validation
        """
        self.region = region
        self.logger = logging.getLogger(__name__)
    
    def validate_client_config(self, client_config: ClientConfig, 
                             generate_test_report: bool = False) -> ValidationReport:
        """
        Perform comprehensive validation of a client configuration.
        
        Args:
            client_config: Client configuration to validate
            generate_test_report: Whether to generate a test report
            
        Returns:
            ValidationReport with all validation results
        """
        self.logger.info(f"Starting validation for client: {client_config.client_name}")
        
        report = ValidationReport(client_config)
        
        try:
            # Basic configuration validation
            self._validate_basic_config(client_config, report)
            
            # AWS credentials validation
            self._validate_aws_credentials(client_config, report)
            
            # Report configuration validation
            self._validate_report_config(client_config, report)
            
            # Branding configuration validation
            self._validate_branding_config(client_config, report)
            
            # AWS permissions validation
            self._validate_aws_permissions(client_config, report)
            
            # Cost data availability validation
            self._validate_cost_data_availability(client_config, report)
            
            # Generate test report if requested
            if generate_test_report:
                self._generate_test_report(client_config, report)
            
        except Exception as e:
            self.logger.error(f"Validation failed with exception: {e}")
            report.add_result(ValidationResult(
                "validation_exception",
                False,
                f"Validation failed with exception: {e}",
                "error"
            ))
        
        report.finalize()
        self.logger.info(f"Validation completed for client: {client_config.client_name}")
        
        return report
    
    def _validate_basic_config(self, client_config: ClientConfig, report: ValidationReport) -> None:
        """Validate basic configuration structure."""
        self.logger.debug("Validating basic configuration")
        
        # Client name validation
        if not client_config.client_name or len(client_config.client_name.strip()) == 0:
            report.add_result(ValidationResult(
                "client_name",
                False,
                "Client name is required and cannot be empty",
                "error"
            ))
        elif len(client_config.client_name) > 100:
            report.add_result(ValidationResult(
                "client_name_length",
                False,
                "Client name is too long (maximum 100 characters)",
                "warning"
            ))
        else:
            report.add_result(ValidationResult(
                "client_name",
                True,
                "Client name is valid"
            ))
        
        # Client ID validation
        if not client_config.client_id:
            report.add_result(ValidationResult(
                "client_id",
                False,
                "Client ID is required",
                "error"
            ))
        else:
            report.add_result(ValidationResult(
                "client_id",
                True,
                "Client ID is present"
            ))
        
        # AWS accounts validation
        if not client_config.aws_accounts:
            report.add_result(ValidationResult(
                "aws_accounts",
                False,
                "At least one AWS account is required",
                "error"
            ))
        else:
            # Check for duplicate account IDs
            account_ids = [acc.account_id for acc in client_config.aws_accounts]
            if len(account_ids) != len(set(account_ids)):
                report.add_result(ValidationResult(
                    "aws_accounts_unique",
                    False,
                    "Duplicate AWS account IDs found",
                    "error"
                ))
            else:
                report.add_result(ValidationResult(
                    "aws_accounts",
                    True,
                    f"Found {len(client_config.aws_accounts)} AWS account(s)"
                ))
    
    def _validate_aws_credentials(self, client_config: ClientConfig, report: ValidationReport) -> None:
        """Validate AWS credentials format and basic connectivity."""
        self.logger.debug("Validating AWS credentials")
        
        for i, account in enumerate(client_config.aws_accounts):
            account_prefix = f"account_{i+1}"
            
            # Account ID format validation
            if not account.account_id or len(account.account_id) != 12 or not account.account_id.isdigit():
                report.add_result(ValidationResult(
                    f"{account_prefix}_account_id",
                    False,
                    f"Account {account.account_id}: Invalid account ID format (must be 12 digits)",
                    "error"
                ))
                continue
            
            # Access key format validation
            if not account.access_key_id or not account.access_key_id.startswith('AKIA'):
                report.add_result(ValidationResult(
                    f"{account_prefix}_access_key",
                    False,
                    f"Account {account.account_id}: Invalid access key format",
                    "error"
                ))
                continue
            
            # Secret key validation
            if not account.secret_access_key or len(account.secret_access_key) < 20:
                report.add_result(ValidationResult(
                    f"{account_prefix}_secret_key",
                    False,
                    f"Account {account.account_id}: Invalid secret access key",
                    "error"
                ))
                continue
            
            # Region validation
            if not account.region:
                report.add_result(ValidationResult(
                    f"{account_prefix}_region",
                    False,
                    f"Account {account.account_id}: Region is required",
                    "error"
                ))
                continue
            
            # Basic connectivity test
            try:
                session = boto3.Session(
                    aws_access_key_id=account.access_key_id,
                    aws_secret_access_key=account.secret_access_key,
                    region_name=account.region
                )
                
                sts = session.client('sts')
                response = sts.get_caller_identity()
                
                # Verify account ID matches
                if response.get('Account') != account.account_id:
                    report.add_result(ValidationResult(
                        f"{account_prefix}_account_match",
                        False,
                        f"Account {account.account_id}: Credentials belong to different account ({response.get('Account')})",
                        "error"
                    ))
                else:
                    report.add_result(ValidationResult(
                        f"{account_prefix}_credentials",
                        True,
                        f"Account {account.account_id}: Credentials are valid"
                    ))
                
            except Exception as e:
                report.add_result(ValidationResult(
                    f"{account_prefix}_connectivity",
                    False,
                    f"Account {account.account_id}: Failed to connect - {str(e)}",
                    "error"
                ))
    
    def _validate_report_config(self, client_config: ClientConfig, report: ValidationReport) -> None:
        """Validate report configuration."""
        self.logger.debug("Validating report configuration")
        
        config = client_config.report_config
        
        # At least one report type enabled
        if not config.weekly_enabled and not config.monthly_enabled:
            report.add_result(ValidationResult(
                "report_types",
                False,
                "At least one report type (weekly or monthly) must be enabled",
                "error"
            ))
        else:
            enabled_types = []
            if config.weekly_enabled:
                enabled_types.append("weekly")
            if config.monthly_enabled:
                enabled_types.append("monthly")
            
            report.add_result(ValidationResult(
                "report_types",
                True,
                f"Report types enabled: {', '.join(enabled_types)}"
            ))
        
        # Recipients validation
        if not config.recipients:
            report.add_result(ValidationResult(
                "recipients",
                False,
                "At least one recipient email is required",
                "error"
            ))
        else:
            # Validate email format
            import re
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            
            invalid_emails = []
            for email in config.recipients + config.cc_recipients:
                if not email_pattern.match(email):
                    invalid_emails.append(email)
            
            if invalid_emails:
                report.add_result(ValidationResult(
                    "email_format",
                    False,
                    f"Invalid email addresses: {', '.join(invalid_emails)}",
                    "error"
                ))
            else:
                report.add_result(ValidationResult(
                    "recipients",
                    True,
                    f"Found {len(config.recipients)} recipient(s) and {len(config.cc_recipients)} CC recipient(s)"
                ))
        
        # Threshold validation
        if config.threshold < 0:
            report.add_result(ValidationResult(
                "threshold",
                False,
                "Threshold must be non-negative",
                "error"
            ))
        else:
            report.add_result(ValidationResult(
                "threshold",
                True,
                f"Threshold set to ${config.threshold:,.2f}"
            ))
        
        # Top services validation
        if config.top_services < 1 or config.top_services > 50:
            report.add_result(ValidationResult(
                "top_services",
                False,
                "Top services must be between 1 and 50",
                "warning"
            ))
        else:
            report.add_result(ValidationResult(
                "top_services",
                True,
                f"Will show top {config.top_services} services"
            ))
    
    def _validate_branding_config(self, client_config: ClientConfig, report: ValidationReport) -> None:
        """Validate branding configuration."""
        self.logger.debug("Validating branding configuration")
        
        branding = client_config.branding
        
        # Color format validation
        import re
        color_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
        
        if not color_pattern.match(branding.primary_color):
            report.add_result(ValidationResult(
                "primary_color",
                False,
                f"Invalid primary color format: {branding.primary_color}",
                "error"
            ))
        else:
            report.add_result(ValidationResult(
                "primary_color",
                True,
                f"Primary color: {branding.primary_color}"
            ))
        
        if not color_pattern.match(branding.secondary_color):
            report.add_result(ValidationResult(
                "secondary_color",
                False,
                f"Invalid secondary color format: {branding.secondary_color}",
                "error"
            ))
        else:
            report.add_result(ValidationResult(
                "secondary_color",
                True,
                f"Secondary color: {branding.secondary_color}"
            ))
        
        # Logo validation (if provided)
        if branding.logo_s3_key:
            # TODO: Validate S3 key exists and is accessible
            report.add_result(ValidationResult(
                "logo",
                True,
                f"Logo S3 key: {branding.logo_s3_key}",
                "info"
            ))
        else:
            report.add_result(ValidationResult(
                "logo",
                True,
                "No custom logo configured (will use default)",
                "info"
            ))
        
        # Company name
        if branding.company_name:
            report.add_result(ValidationResult(
                "company_name",
                True,
                f"Company name: {branding.company_name}"
            ))
        else:
            report.add_result(ValidationResult(
                "company_name",
                True,
                "No company name configured (will use client name)",
                "info"
            ))
    
    def _validate_aws_permissions(self, client_config: ClientConfig, report: ValidationReport) -> None:
        """Validate AWS permissions for cost data access."""
        self.logger.debug("Validating AWS permissions")
        
        required_permissions = [
            'ce:GetCostAndUsage',
            'ce:GetUsageForecast',
            'ce:GetCostForecast'
        ]
        
        for i, account in enumerate(client_config.aws_accounts):
            account_prefix = f"account_{i+1}_permissions"
            
            try:
                session = boto3.Session(
                    aws_access_key_id=account.access_key_id,
                    aws_secret_access_key=account.secret_access_key,
                    region_name=account.region
                )
                
                # Test Cost Explorer access
                ce = session.client('ce', region_name='us-east-1')  # CE is only available in us-east-1
                
                # Try to get cost data for the last 7 days
                end_date = datetime.utcnow().date()
                start_date = end_date - timedelta(days=7)
                
                response = ce.get_cost_and_usage(
                    TimePeriod={
                        'Start': start_date.strftime('%Y-%m-%d'),
                        'End': end_date.strftime('%Y-%m-%d')
                    },
                    Granularity='DAILY',
                    Metrics=['BlendedCost']
                )
                
                report.add_result(ValidationResult(
                    f"{account_prefix}_cost_explorer",
                    True,
                    f"Account {account.account_id}: Cost Explorer access verified"
                ))
                
            except Exception as e:
                error_msg = str(e)
                if "AccessDenied" in error_msg:
                    report.add_result(ValidationResult(
                        f"{account_prefix}_cost_explorer",
                        False,
                        f"Account {account.account_id}: Missing Cost Explorer permissions",
                        "error",
                        {"required_permissions": required_permissions}
                    ))
                else:
                    report.add_result(ValidationResult(
                        f"{account_prefix}_cost_explorer",
                        False,
                        f"Account {account.account_id}: Cost Explorer access failed - {error_msg}",
                        "error"
                    ))
    
    def _validate_cost_data_availability(self, client_config: ClientConfig, report: ValidationReport) -> None:
        """Validate that cost data is available for the accounts."""
        self.logger.debug("Validating cost data availability")
        
        for i, account in enumerate(client_config.aws_accounts):
            account_prefix = f"account_{i+1}_data"
            
            try:
                session = boto3.Session(
                    aws_access_key_id=account.access_key_id,
                    aws_secret_access_key=account.secret_access_key,
                    region_name=account.region
                )
                
                ce = session.client('ce', region_name='us-east-1')
                
                # Check for cost data in the last 30 days
                end_date = datetime.utcnow().date()
                start_date = end_date - timedelta(days=30)
                
                response = ce.get_cost_and_usage(
                    TimePeriod={
                        'Start': start_date.strftime('%Y-%m-%d'),
                        'End': end_date.strftime('%Y-%m-%d')
                    },
                    Granularity='MONTHLY',
                    Metrics=['BlendedCost']
                )
                
                # Check if there's any cost data
                has_costs = False
                total_cost = 0.0
                
                for result in response.get('ResultsByTime', []):
                    for metric in result.get('Total', {}).values():
                        amount = float(metric.get('Amount', 0))
                        if amount > 0:
                            has_costs = True
                            total_cost += amount
                
                if has_costs:
                    report.add_result(ValidationResult(
                        f"{account_prefix}_availability",
                        True,
                        f"Account {account.account_id}: Cost data available (${total_cost:.2f} in last 30 days)"
                    ))
                else:
                    report.add_result(ValidationResult(
                        f"{account_prefix}_availability",
                        True,
                        f"Account {account.account_id}: No cost data found (new account or no usage)",
                        "warning"
                    ))
                
            except Exception as e:
                report.add_result(ValidationResult(
                    f"{account_prefix}_availability",
                    False,
                    f"Account {account.account_id}: Failed to check cost data - {str(e)}",
                    "warning"
                ))
    
    def _generate_test_report(self, client_config: ClientConfig, report: ValidationReport) -> None:
        """Generate a test report to validate the complete workflow."""
        self.logger.debug("Generating test report")
        
        # Check if required services are available
        if LambdaCostAgent is None or LambdaReportGenerator is None:
            report.add_result(ValidationResult(
                "test_report_generation",
                False,
                "Test report generation skipped: Required services not available",
                "warning"
            ))
            return
        
        try:
            # Create a temporary cost agent
            cost_agent = LambdaCostAgent(client_config)
            
            # Try to collect cost data for weekly report (last 2 periods)
            import asyncio
            
            # Run the async method
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                cost_data = loop.run_until_complete(
                    cost_agent.collect_client_costs(report_type="weekly", periods=2)
                )
                
                if cost_data and cost_data.total_cost > 0:
                    # Generate test report
                    report_generator = LambdaReportGenerator()
                    html_report = report_generator.generate_client_report(cost_data.aggregated_data, client_config)
                    
                    # Save test report to temporary file
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                        f.write(html_report)
                        temp_file = f.name
                    
                    report.add_result(ValidationResult(
                        "test_report_generation",
                        True,
                        f"Test report generated successfully: {temp_file}",
                        "info",
                        {
                            "report_file": temp_file, 
                            "total_cost": cost_data.total_cost,
                            "service_count": cost_data.service_count,
                            "accounts_processed": len(cost_data.accounts_data)
                        }
                    ))
                else:
                    report.add_result(ValidationResult(
                        "test_report_generation",
                        True,
                        "Test report generation completed (no cost data available)",
                        "warning"
                    ))
            finally:
                loop.close()
                
        except Exception as e:
            report.add_result(ValidationResult(
                "test_report_generation",
                False,
                f"Test report generation failed: {str(e)}",
                "error"
            ))
    
    def validate_bulk_configs(self, config_files: List[str]) -> Dict[str, ValidationReport]:
        """
        Validate multiple client configurations.
        
        Args:
            config_files: List of configuration file paths
            
        Returns:
            Dictionary mapping file paths to validation reports
        """
        self.logger.info(f"Starting bulk validation of {len(config_files)} configurations")
        
        results = {}
        
        for config_file in config_files:
            try:
                self.logger.info(f"Validating configuration file: {config_file}")
                
                # Load configuration
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Create ClientConfig object
                client_config = ClientConfig.from_dict(config_data)
                
                # Validate
                validation_report = self.validate_client_config(client_config)
                results[config_file] = validation_report
                
            except Exception as e:
                self.logger.error(f"Failed to validate {config_file}: {e}")
                
                # Create a dummy client config for the error report
                dummy_config = ClientConfig(
                    client_id="unknown",
                    client_name=f"Failed to load: {config_file}",
                    aws_accounts=[],
                    report_config=ReportConfig(recipients=["dummy@example.com"]),
                    branding=BrandingConfig()
                )
                
                error_report = ValidationReport(dummy_config)
                error_report.add_result(ValidationResult(
                    "config_loading",
                    False,
                    f"Failed to load configuration file: {str(e)}",
                    "error"
                ))
                error_report.finalize()
                
                results[config_file] = error_report
        
        self.logger.info(f"Bulk validation completed for {len(config_files)} configurations")
        return results