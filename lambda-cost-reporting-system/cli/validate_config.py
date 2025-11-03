#!/usr/bin/env python3
"""
Configuration Validation CLI for Lambda Cost Reporting System.

This CLI tool provides comprehensive validation for client configurations including:
- AWS credential validation
- Configuration completeness checks  
- Test report generation
- Bulk validation operations
"""

import argparse
import json
import sys
import os
import logging
from typing import List, Dict, Any
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import ClientConfig
from cli.config_validator import ConfigValidator, ValidationReport
from utils import setup_logging


def print_validation_summary(report: ValidationReport) -> None:
    """Print a formatted validation summary."""
    summary = report.get_summary()
    
    print(f"\n{'='*60}")
    print(f"VALIDATION REPORT: {summary['client_name']}")
    print(f"{'='*60}")
    print(f"Client ID: {summary['client_id']}")
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Overall Status: {summary['overall_status']}")
    print(f"Duration: {summary['duration_seconds']:.2f} seconds")
    
    # Print errors
    errors = report.get_errors()
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"  • {error.check_name}: {error.message}")
    
    # Print warnings
    warnings = report.get_warnings()
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  • {warning.check_name}: {warning.message}")
    
    # Print successful checks
    passed = [r for r in report.results if r.passed]
    if passed:
        print(f"\n✅ PASSED CHECKS ({len(passed)}):")
        for check in passed:
            if check.severity == "info":
                print(f"  ℹ️  {check.check_name}: {check.message}")
            else:
                print(f"  • {check.check_name}: {check.message}")


def print_bulk_validation_summary(results: Dict[str, ValidationReport]) -> None:
    """Print summary of bulk validation results."""
    total_configs = len(results)
    passed_configs = sum(1 for report in results.values() if report.is_valid())
    failed_configs = total_configs - passed_configs
    
    print(f"\n{'='*80}")
    print(f"BULK VALIDATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total Configurations: {total_configs}")
    print(f"Passed: {passed_configs}")
    print(f"Failed: {failed_configs}")
    print(f"Success Rate: {(passed_configs/total_configs)*100:.1f}%")
    
    # Show results by file
    print(f"\nRESULTS BY FILE:")
    for config_file, report in results.items():
        status = "✅ PASSED" if report.is_valid() else "❌ FAILED"
        summary = report.get_summary()
        print(f"  {status} {config_file}")
        print(f"    Client: {summary['client_name']} ({summary['client_id']})")
        print(f"    Checks: {summary['passed']}/{summary['total_checks']} passed")
        if summary['errors'] > 0:
            print(f"    Errors: {summary['errors']}")
        if summary['warnings'] > 0:
            print(f"    Warnings: {summary['warnings']}")


def validate_single_config(config_file: str, generate_test_report: bool = False, 
                          output_format: str = "text", output_file: str = None) -> bool:
    """
    Validate a single configuration file.
    
    Args:
        config_file: Path to configuration file
        generate_test_report: Whether to generate test report
        output_format: Output format (text, json)
        output_file: Output file path (optional)
        
    Returns:
        True if validation passed, False otherwise
    """
    try:
        # Load configuration
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Create ClientConfig object
        client_config = ClientConfig.from_dict(config_data)
        
        # Create validator
        validator = ConfigValidator()
        
        # Perform validation
        print(f"Validating configuration: {config_file}")
        if generate_test_report:
            print("Note: Test report generation may take a few minutes...")
        
        report = validator.validate_client_config(client_config, generate_test_report)
        
        # Output results
        if output_format == "json":
            result_data = report.to_dict()
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(result_data, f, indent=2)
                print(f"Validation results saved to: {output_file}")
            else:
                print(json.dumps(result_data, indent=2))
        else:
            print_validation_summary(report)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(json.dumps(report.to_dict(), indent=2))
                print(f"Detailed results saved to: {output_file}")
        
        return report.is_valid()
        
    except FileNotFoundError:
        print(f"❌ Error: Configuration file not found: {config_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in configuration file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: Validation failed: {e}")
        return False


def validate_bulk_configs(config_files: List[str], output_file: str = None) -> bool:
    """
    Validate multiple configuration files.
    
    Args:
        config_files: List of configuration file paths
        output_file: Output file path (optional)
        
    Returns:
        True if all validations passed, False otherwise
    """
    try:
        # Create validator
        validator = ConfigValidator()
        
        # Perform bulk validation
        print(f"Validating {len(config_files)} configuration files...")
        results = validator.validate_bulk_configs(config_files)
        
        # Print summary
        print_bulk_validation_summary(results)
        
        # Save detailed results if requested
        if output_file:
            detailed_results = {
                config_file: report.to_dict() 
                for config_file, report in results.items()
            }
            
            with open(output_file, 'w') as f:
                json.dump(detailed_results, f, indent=2)
            
            print(f"\nDetailed results saved to: {output_file}")
        
        # Return True if all validations passed
        return all(report.is_valid() for report in results.values())
        
    except Exception as e:
        print(f"❌ Error: Bulk validation failed: {e}")
        return False


def validate_directory(directory: str, pattern: str = "*.json", 
                      output_file: str = None) -> bool:
    """
    Validate all configuration files in a directory.
    
    Args:
        directory: Directory path
        pattern: File pattern to match
        output_file: Output file path (optional)
        
    Returns:
        True if all validations passed, False otherwise
    """
    try:
        # Find configuration files
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"❌ Error: Directory not found: {directory}")
            return False
        
        config_files = list(dir_path.glob(pattern))
        if not config_files:
            print(f"❌ Error: No configuration files found in {directory} matching {pattern}")
            return False
        
        config_file_paths = [str(f) for f in config_files]
        print(f"Found {len(config_file_paths)} configuration files in {directory}")
        
        # Validate all files
        return validate_bulk_configs(config_file_paths, output_file)
        
    except Exception as e:
        print(f"❌ Error: Directory validation failed: {e}")
        return False


def create_validation_template(output_file: str) -> None:
    """Create a validation checklist template."""
    template = {
        "validation_checklist": {
            "basic_configuration": [
                "Client name is present and valid",
                "Client ID is present",
                "At least one AWS account is configured",
                "No duplicate AWS account IDs"
            ],
            "aws_credentials": [
                "Account IDs are 12-digit numbers",
                "Access keys have correct format (AKIA...)",
                "Secret access keys are present",
                "Regions are specified",
                "Credentials can authenticate with AWS",
                "Account IDs match credential accounts"
            ],
            "aws_permissions": [
                "Cost Explorer access (ce:GetCostAndUsage)",
                "Cost forecasting access (ce:GetUsageForecast, ce:GetCostForecast)",
                "Cost data is available for accounts"
            ],
            "report_configuration": [
                "At least one report type enabled (weekly/monthly)",
                "At least one recipient email configured",
                "Email addresses have valid format",
                "Threshold is non-negative",
                "Top services count is reasonable (1-50)"
            ],
            "branding_configuration": [
                "Primary color has valid hex format",
                "Secondary color has valid hex format",
                "Logo S3 key is accessible (if configured)",
                "Company name is present (optional)"
            ],
            "test_report": [
                "Cost data can be retrieved",
                "HTML report can be generated",
                "Email template can be created"
            ]
        },
        "common_issues": {
            "aws_credentials": [
                "Invalid access key format - must start with AKIA",
                "Credentials belong to different account than specified",
                "Missing Cost Explorer permissions",
                "Account has no cost data (new account)"
            ],
            "configuration": [
                "No recipients configured",
                "Invalid email address format",
                "Both weekly and monthly reports disabled",
                "Invalid color format (must be #RRGGBB)"
            ]
        },
        "required_aws_permissions": [
            "ce:GetCostAndUsage",
            "ce:GetUsageForecast", 
            "ce:GetCostForecast"
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"✅ Validation checklist template created: {output_file}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Configuration Validation CLI for Lambda Cost Reporting System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single configuration
  %(prog)s single --config client-config.json
  
  # Validate with test report generation
  %(prog)s single --config client-config.json --test-report
  
  # Validate and save results to JSON
  %(prog)s single --config client-config.json --format json --output results.json
  
  # Validate multiple configurations
  %(prog)s bulk --configs config1.json config2.json config3.json
  
  # Validate all JSON files in directory
  %(prog)s directory --path ./configs --pattern "*.json"
  
  # Create validation checklist template
  %(prog)s template --output validation-checklist.json
        """
    )
    
    # Global options
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log level (default: INFO)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Single validation command
    single_parser = subparsers.add_parser('single', help='Validate single configuration')
    single_parser.add_argument('--config', required=True, help='Configuration file path')
    single_parser.add_argument('--test-report', action='store_true',
                              help='Generate test report (may take several minutes)')
    single_parser.add_argument('--format', choices=['text', 'json'], default='text',
                              help='Output format (default: text)')
    single_parser.add_argument('--output', help='Output file path (optional)')
    
    # Bulk validation command
    bulk_parser = subparsers.add_parser('bulk', help='Validate multiple configurations')
    bulk_parser.add_argument('--configs', nargs='+', required=True,
                            help='Configuration file paths')
    bulk_parser.add_argument('--output', help='Output file path for detailed results')
    
    # Directory validation command
    dir_parser = subparsers.add_parser('directory', help='Validate all configs in directory')
    dir_parser.add_argument('--path', required=True, help='Directory path')
    dir_parser.add_argument('--pattern', default='*.json', help='File pattern (default: *.json)')
    dir_parser.add_argument('--output', help='Output file path for detailed results')
    
    # Template command
    template_parser = subparsers.add_parser('template', help='Create validation checklist template')
    template_parser.add_argument('--output', required=True, help='Output file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Execute command
    success = False
    try:
        if args.command == 'single':
            success = validate_single_config(
                args.config, 
                args.test_report, 
                args.format, 
                args.output
            )
        elif args.command == 'bulk':
            success = validate_bulk_configs(args.configs, args.output)
        elif args.command == 'directory':
            success = validate_directory(args.path, args.pattern, args.output)
        elif args.command == 'template':
            create_validation_template(args.output)
            success = True
        else:
            print(f"❌ Error: Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: Unexpected error: {e}")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())