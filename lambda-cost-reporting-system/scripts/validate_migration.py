#!/usr/bin/env python3
"""
Data validation tool for migrated configurations.

This script provides comprehensive validation for configurations migrated from
aws-cost-agent-framework to ensure they are compatible with the Lambda Cost Reporting System.
"""

import argparse
import json
import sys
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import re

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import ClientConfig, AccountConfig, ReportConfig, BrandingConfig


class MigrationValidator:
    """Validates migrated configurations for completeness and correctness."""
    
    def __init__(self):
        """Initialize the validator."""
        self.logger = logging.getLogger(__name__)
        self.validation_results = {
            "total_configs": 0,
            "valid_configs": 0,
            "invalid_configs": 0,
            "warnings": 0,
            "errors": 0,
            "details": []
        }
    
    def validate_directory(self, config_dir: str, check_aws_access: bool = False) -> Dict[str, Any]:
        """
        Validate all configuration files in a directory.
        
        Args:
            config_dir: Directory containing configuration files
            check_aws_access: Whether to validate AWS access credentials
            
        Returns:
            Validation results dictionary
        """
        config_path = Path(config_dir)
        if not config_path.exists():
            raise ValueError(f"Configuration directory not found: {config_dir}")
        
        config_files = list(config_path.glob("*.json"))
        if not config_files:
            raise ValueError(f"No JSON configuration files found in: {config_dir}")
        
        self.logger.info(f"Validating {len(config_files)} configuration files")
        
        for config_file in config_files:
            self._validate_single_file(config_file, check_aws_access)
        
        return self.validation_results
    
    def validate_single_file(self, config_file: str, check_aws_access: bool = False) -> Dict[str, Any]:
        """
        Validate a single configuration file.
        
        Args:
            config_file: Path to configuration file
            check_aws_access: Whether to validate AWS access credentials
            
        Returns:
            Validation results for the file
        """
        self.validation_results = {
            "total_configs": 0,
            "valid_configs": 0,
            "invalid_configs": 0,
            "warnings": 0,
            "errors": 0,
            "details": []
        }
        
        self._validate_single_file(Path(config_file), check_aws_access)
        return self.validation_results
    
    def _validate_single_file(self, config_file: Path, check_aws_access: bool) -> None:
        """Validate a single configuration file."""
        self.validation_results["total_configs"] += 1
        
        file_result = {
            "file": str(config_file),
            "status": "unknown",
            "errors": [],
            "warnings": [],
            "client_name": "",
            "client_id": "",
            "aws_accounts": 0,
            "recipients": 0
        }
        
        try:
            # Load and parse JSON
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Create ClientConfig object (this validates basic structure)
            client_config = ClientConfig.from_dict(config_data)
            
            file_result["client_name"] = client_config.client_name
            file_result["client_id"] = client_config.client_id
            file_result["aws_accounts"] = len(client_config.aws_accounts)
            file_result["recipients"] = len(client_config.report_config.recipients)
            
            # Perform detailed validation
            self._validate_client_config(client_config, file_result)
            
            # Validate AWS access if requested
            if check_aws_access:
                self._validate_aws_access(client_config, file_result)
            
            # Determine overall status
            if file_result["errors"]:
                file_result["status"] = "invalid"
                self.validation_results["invalid_configs"] += 1
                self.validation_results["errors"] += len(file_result["errors"])
            else:
                file_result["status"] = "valid"
                self.validation_results["valid_configs"] += 1
            
            self.validation_results["warnings"] += len(file_result["warnings"])
            
        except Exception as e:
            file_result["status"] = "invalid"
            file_result["errors"].append(f"Failed to load/parse configuration: {str(e)}")
            self.validation_results["invalid_configs"] += 1
            self.validation_results["errors"] += 1
        
        self.validation_results["details"].append(file_result)
        
        # Log results
        status_emoji = "✅" if file_result["status"] == "valid" else "❌"
        self.logger.info(f"{status_emoji} {config_file.name}: {file_result['status']}")
        
        if file_result["errors"]:
            for error in file_result["errors"]:
                self.logger.error(f"  ERROR: {error}")
        
        if file_result["warnings"]:
            for warning in file_result["warnings"]:
                self.logger.warning(f"  WARNING: {warning}")
    
    def _validate_client_config(self, client_config: ClientConfig, file_result: Dict[str, Any]) -> None:
        """Validate client configuration details."""
        
        # Validate client basic info
        if not client_config.client_name or client_config.client_name.strip() == "":
            file_result["errors"].append("Client name is empty")
        
        if "Migrated Client" in client_config.client_name:
            file_result["warnings"].append("Client name appears to be auto-generated")
        
        # Validate AWS accounts
        if not client_config.aws_accounts:
            file_result["errors"].append("No AWS accounts configured")
        else:
            for i, account in enumerate(client_config.aws_accounts):
                self._validate_aws_account(account, i, file_result)
        
        # Validate report configuration
        self._validate_report_config(client_config.report_config, file_result)
        
        # Validate branding configuration
        self._validate_branding_config(client_config.branding, file_result)
    
    def _validate_aws_account(self, account: AccountConfig, index: int, file_result: Dict[str, Any]) -> None:
        """Validate AWS account configuration."""
        account_prefix = f"Account {index + 1}"
        
        # Validate account ID format
        if not re.match(r'^\d{12}$', account.account_id):
            if account.account_id == "123456789012":
                file_result["warnings"].append(f"{account_prefix}: Using template account ID")
            else:
                file_result["errors"].append(f"{account_prefix}: Invalid account ID format")
        
        # Check for placeholder credentials
        if "EXAMPLE" in account.access_key_id or "EXAMPLE" in account.secret_access_key:
            file_result["errors"].append(f"{account_prefix}: Using placeholder/example credentials")
        
        if "PROFILE_" in account.access_key_id:
            file_result["errors"].append(f"{account_prefix}: Profile-based credentials need manual conversion")
        
        if "UPDATE REQUIRED" in (account.account_name or ""):
            file_result["warnings"].append(f"{account_prefix}: Account name indicates manual update required")
        
        # Validate access key format
        if not re.match(r'^AKIA[0-9A-Z]{16}$', account.access_key_id) and not account.access_key_id.startswith("PROFILE_"):
            file_result["warnings"].append(f"{account_prefix}: Access key ID format may be invalid")
        
        # Validate region
        valid_regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-northeast-2',
            'ap-south-1', 'sa-east-1', 'ca-central-1'
        ]
        
        if account.region not in valid_regions:
            file_result["warnings"].append(f"{account_prefix}: Unusual AWS region: {account.region}")
    
    def _validate_report_config(self, report_config: ReportConfig, file_result: Dict[str, Any]) -> None:
        """Validate report configuration."""
        
        # Validate recipients
        if not report_config.recipients:
            file_result["errors"].append("No email recipients configured")
        else:
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            
            for email in report_config.recipients:
                if not email_pattern.match(email):
                    file_result["errors"].append(f"Invalid recipient email format: {email}")
                elif email == "admin@example.com":
                    file_result["warnings"].append("Using placeholder recipient email")
            
            # Check CC recipients
            for email in report_config.cc_recipients:
                if not email_pattern.match(email):
                    file_result["errors"].append(f"Invalid CC recipient email format: {email}")
        
        # Validate thresholds and limits
        if report_config.threshold < 0:
            file_result["errors"].append("Cost threshold cannot be negative")
        
        if report_config.top_services < 1:
            file_result["errors"].append("Top services count must be at least 1")
        elif report_config.top_services > 50:
            file_result["warnings"].append("Top services count is very high (>50)")
        
        # Validate report types
        if not report_config.weekly_enabled and not report_config.monthly_enabled:
            file_result["warnings"].append("Both weekly and monthly reports are disabled")
    
    def _validate_branding_config(self, branding: BrandingConfig, file_result: Dict[str, Any]) -> None:
        """Validate branding configuration."""
        
        # Validate color formats
        color_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
        
        if not color_pattern.match(branding.primary_color):
            file_result["errors"].append(f"Invalid primary color format: {branding.primary_color}")
        
        if not color_pattern.match(branding.secondary_color):
            file_result["errors"].append(f"Invalid secondary color format: {branding.secondary_color}")
        
        # Check for empty company name
        if not branding.company_name or branding.company_name.strip() == "":
            file_result["warnings"].append("Company name is empty")
        
        # Check S3 key format if provided
        if branding.logo_s3_key:
            if not branding.logo_s3_key.startswith("logos/") and not branding.logo_s3_key.startswith("assets/"):
                file_result["warnings"].append("Logo S3 key should typically start with 'logos/' or 'assets/'")
    
    def _validate_aws_access(self, client_config: ClientConfig, file_result: Dict[str, Any]) -> None:
        """Validate AWS access credentials."""
        self.logger.info(f"Validating AWS access for {client_config.client_name}")
        
        for i, account in enumerate(client_config.aws_accounts):
            account_prefix = f"Account {i + 1}"
            
            # Skip validation for placeholder credentials
            if ("EXAMPLE" in account.access_key_id or 
                "PROFILE_" in account.access_key_id or
                account.account_id == "123456789012"):
                file_result["warnings"].append(f"{account_prefix}: Skipping AWS access validation (placeholder credentials)")
                continue
            
            try:
                # Create session with the credentials
                session = boto3.Session(
                    aws_access_key_id=account.access_key_id,
                    aws_secret_access_key=account.secret_access_key,
                    region_name=account.region
                )
                
                # Test STS access (basic credential validation)
                sts_client = session.client('sts')
                identity = sts_client.get_caller_identity()
                
                # Verify account ID matches
                actual_account_id = identity.get('Account')
                if actual_account_id != account.account_id:
                    file_result["errors"].append(
                        f"{account_prefix}: Account ID mismatch. "
                        f"Expected: {account.account_id}, Actual: {actual_account_id}"
                    )
                
                # Test Cost Explorer access
                ce_client = session.client('ce', region_name='us-east-1')  # CE is only in us-east-1
                
                # Try a simple Cost Explorer query
                from datetime import datetime, timedelta
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=7)
                
                ce_client.get_cost_and_usage(
                    TimePeriod={
                        'Start': start_date.strftime('%Y-%m-%d'),
                        'End': end_date.strftime('%Y-%m-%d')
                    },
                    Granularity='DAILY',
                    Metrics=['BlendedCost']
                )
                
                self.logger.info(f"  ✅ {account_prefix}: AWS access validated")
                
            except NoCredentialsError:
                file_result["errors"].append(f"{account_prefix}: No valid AWS credentials found")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                
                if error_code == 'InvalidUserID.NotFound':
                    file_result["errors"].append(f"{account_prefix}: Invalid access key ID")
                elif error_code == 'SignatureDoesNotMatch':
                    file_result["errors"].append(f"{account_prefix}: Invalid secret access key")
                elif error_code == 'AccessDenied':
                    file_result["warnings"].append(f"{account_prefix}: Limited AWS permissions (Cost Explorer access denied)")
                else:
                    file_result["warnings"].append(f"{account_prefix}: AWS access issue: {error_code}")
                
                self.logger.warning(f"  ⚠️  {account_prefix}: {error_code}")
                
            except Exception as e:
                file_result["warnings"].append(f"{account_prefix}: AWS access validation failed: {str(e)}")
                self.logger.warning(f"  ⚠️  {account_prefix}: {str(e)}")
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate a detailed validation report.
        
        Args:
            output_file: Optional output file path
            
        Returns:
            Report content as string
        """
        report_lines = []
        report_lines.append("# Migration Validation Report")
        report_lines.append(f"Generated: {datetime.now().isoformat()}")
        report_lines.append("")
        
        # Summary
        results = self.validation_results
        report_lines.append("## Summary")
        report_lines.append(f"- Total configurations: {results['total_configs']}")
        report_lines.append(f"- Valid configurations: {results['valid_configs']}")
        report_lines.append(f"- Invalid configurations: {results['invalid_configs']}")
        report_lines.append(f"- Total errors: {results['errors']}")
        report_lines.append(f"- Total warnings: {results['warnings']}")
        report_lines.append("")
        
        # Detailed results
        report_lines.append("## Detailed Results")
        report_lines.append("")
        
        for detail in results['details']:
            status_emoji = "✅" if detail['status'] == 'valid' else "❌"
            report_lines.append(f"### {status_emoji} {Path(detail['file']).name}")
            report_lines.append(f"- **Status**: {detail['status']}")
            report_lines.append(f"- **Client**: {detail['client_name']} ({detail['client_id']})")
            report_lines.append(f"- **AWS Accounts**: {detail['aws_accounts']}")
            report_lines.append(f"- **Recipients**: {detail['recipients']}")
            
            if detail['errors']:
                report_lines.append("- **Errors**:")
                for error in detail['errors']:
                    report_lines.append(f"  - {error}")
            
            if detail['warnings']:
                report_lines.append("- **Warnings**:")
                for warning in detail['warnings']:
                    report_lines.append(f"  - {warning}")
            
            report_lines.append("")
        
        # Recommendations
        report_lines.append("## Recommendations")
        
        if results['invalid_configs'] > 0:
            report_lines.append("- Fix all configuration errors before deploying to Lambda system")
        
        if results['warnings'] > 0:
            report_lines.append("- Review and address warnings for optimal configuration")
        
        if any("placeholder" in str(detail) for detail in results['details']):
            report_lines.append("- Replace all placeholder values with actual configuration data")
        
        if any("PROFILE_" in str(detail) for detail in results['details']):
            report_lines.append("- Convert profile-based AWS configurations to access key credentials")
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_content)
            self.logger.info(f"Validation report saved to: {output_file}")
        
        return report_content


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validation tool for migrated configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate all configurations in a directory
  %(prog)s --config-dir ./migrated_configs
  
  # Validate with AWS access check and generate report
  %(prog)s --config-dir ./migrated_configs --check-aws --report validation_report.md
  
  # Validate single configuration file
  %(prog)s --config-file client-config.json --check-aws
        """
    )
    
    parser.add_argument('--config-dir', help='Directory containing configuration files')
    parser.add_argument('--config-file', help='Single configuration file to validate')
    parser.add_argument('--check-aws', action='store_true',
                       help='Validate AWS access credentials')
    parser.add_argument('--report', help='Generate detailed report to file')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log level (default: INFO)')
    
    args = parser.parse_args()
    
    if not args.config_dir and not args.config_file:
        parser.error("Either --config-dir or --config-file must be specified")
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        validator = MigrationValidator()
        
        if args.config_dir:
            results = validator.validate_directory(args.config_dir, args.check_aws)
        else:
            results = validator.validate_single_file(args.config_file, args.check_aws)
        
        # Print summary
        print(f"\n📊 Validation Summary:")
        print(f"   Total configurations: {results['total_configs']}")
        print(f"   Valid configurations: {results['valid_configs']}")
        print(f"   Invalid configurations: {results['invalid_configs']}")
        print(f"   Total errors: {results['errors']}")
        print(f"   Total warnings: {results['warnings']}")
        
        # Generate report if requested
        if args.report:
            validator.generate_report(args.report)
            print(f"📋 Detailed report saved to: {args.report}")
        
        # Exit with appropriate code
        if results['invalid_configs'] > 0:
            print(f"\n❌ Validation failed: {results['invalid_configs']} invalid configurations")
            return 1
        elif results['warnings'] > 0:
            print(f"\n⚠️  Validation passed with {results['warnings']} warnings")
            return 0
        else:
            print(f"\n✅ All configurations are valid!")
            return 0
    
    except KeyboardInterrupt:
        print("\n❌ Validation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())