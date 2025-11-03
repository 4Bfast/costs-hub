#!/usr/bin/env python3
"""
Migration utility to convert aws-cost-agent-framework configurations to Lambda Cost Reporting System format.

This script helps migrate from the existing aws-cost-agent-framework to the new Lambda-based system by:
1. Converting configuration formats
2. Validating migrated configurations
3. Providing rollback capabilities
4. Generating migration reports
"""

import argparse
import json
import sys
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import uuid
import shutil
import tempfile

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import ClientConfig, AccountConfig, ReportConfig, BrandingConfig, ClientStatus


class FrameworkMigrator:
    """Migrates configurations from aws-cost-agent-framework to Lambda system."""
    
    def __init__(self, framework_path: str, output_dir: str = "migrated_configs"):
        """
        Initialize the migrator.
        
        Args:
            framework_path: Path to the aws-cost-agent-framework directory
            output_dir: Directory to store migrated configurations
        """
        self.framework_path = Path(framework_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Migration tracking
        self.migration_log = []
        self.backup_dir = None
        
    def migrate_all(self, backup: bool = True) -> Dict[str, Any]:
        """
        Migrate all configurations from the framework.
        
        Args:
            backup: Whether to create backups before migration
            
        Returns:
            Migration report with results and statistics
        """
        self.logger.info("Starting migration from aws-cost-agent-framework")
        
        # Create backup if requested
        if backup:
            self.backup_dir = self._create_backup()
            self.logger.info(f"Created backup at: {self.backup_dir}")
        
        migration_report = {
            "migration_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "framework_path": str(self.framework_path),
            "output_dir": str(self.output_dir),
            "backup_dir": str(self.backup_dir) if self.backup_dir else None,
            "clients_migrated": [],
            "errors": [],
            "warnings": [],
            "statistics": {
                "total_configs_found": 0,
                "successful_migrations": 0,
                "failed_migrations": 0,
                "warnings_count": 0
            }
        }
        
        try:
            # Discover configuration sources
            config_sources = self._discover_config_sources()
            migration_report["statistics"]["total_configs_found"] = len(config_sources)
            
            self.logger.info(f"Found {len(config_sources)} configuration sources")
            
            # Migrate each configuration
            for source in config_sources:
                try:
                    client_config = self._migrate_single_config(source)
                    
                    # Save migrated configuration
                    output_file = self.output_dir / f"{client_config.client_id}.json"
                    self._save_client_config(client_config, output_file)
                    
                    migration_report["clients_migrated"].append({
                        "client_id": client_config.client_id,
                        "client_name": client_config.client_name,
                        "source": str(source),
                        "output_file": str(output_file),
                        "aws_accounts": len(client_config.aws_accounts),
                        "status": "success"
                    })
                    
                    migration_report["statistics"]["successful_migrations"] += 1
                    self.logger.info(f"Successfully migrated: {client_config.client_name}")
                    
                except Exception as e:
                    error_msg = f"Failed to migrate {source}: {str(e)}"
                    self.logger.error(error_msg)
                    migration_report["errors"].append({
                        "source": str(source),
                        "error": error_msg,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    migration_report["statistics"]["failed_migrations"] += 1
            
            # Save migration report
            report_file = self.output_dir / "migration_report.json"
            with open(report_file, 'w') as f:
                json.dump(migration_report, f, indent=2)
            
            self.logger.info(f"Migration completed. Report saved to: {report_file}")
            return migration_report
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            migration_report["errors"].append({
                "source": "migration_process",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            raise
    
    def _discover_config_sources(self) -> List[Path]:
        """
        Discover configuration sources in the framework directory.
        
        Returns:
            List of configuration source paths
        """
        sources = []
        
        # Look for common configuration patterns
        config_patterns = [
            "config/*.json",
            "config/*.yaml",
            "config/*.yml",
            "email_config.json",
            "*.config.json",
            "client_configs/*.json"
        ]
        
        for pattern in config_patterns:
            sources.extend(self.framework_path.glob(pattern))
        
        # Also check for environment-specific configs
        env_dirs = ["config", "configs", "client_configs"]
        for env_dir in env_dirs:
            env_path = self.framework_path / env_dir
            if env_path.exists():
                sources.extend(env_path.glob("*.json"))
                sources.extend(env_path.glob("*.yaml"))
                sources.extend(env_path.glob("*.yml"))
        
        # Remove duplicates and sort
        sources = list(set(sources))
        sources.sort()
        
        self.logger.info(f"Discovered {len(sources)} potential configuration sources")
        return sources
    
    def _migrate_single_config(self, source_path: Path) -> ClientConfig:
        """
        Migrate a single configuration file.
        
        Args:
            source_path: Path to the source configuration file
            
        Returns:
            Migrated ClientConfig object
        """
        self.logger.debug(f"Migrating configuration from: {source_path}")
        
        # Load source configuration
        with open(source_path, 'r') as f:
            if source_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                source_config = yaml.safe_load(f)
            else:
                source_config = json.load(f)
        
        # Convert to Lambda system format
        client_config = self._convert_config_format(source_config, source_path)
        
        # Validate the migrated configuration
        self._validate_migrated_config(client_config)
        
        return client_config
    
    def _convert_config_format(self, source_config: Dict[str, Any], source_path: Path) -> ClientConfig:
        """
        Convert framework configuration format to Lambda system format.
        
        Args:
            source_config: Source configuration dictionary
            source_path: Path to source file (for context)
            
        Returns:
            Converted ClientConfig object
        """
        # Generate client ID and name
        client_id = str(uuid.uuid4())
        client_name = self._extract_client_name(source_config, source_path)
        
        # Convert AWS configuration
        aws_accounts = self._convert_aws_accounts(source_config)
        
        # Convert report configuration
        report_config = self._convert_report_config(source_config)
        
        # Convert branding configuration
        branding = self._convert_branding_config(source_config)
        
        # Create ClientConfig
        client_config = ClientConfig(
            client_id=client_id,
            client_name=client_name,
            aws_accounts=aws_accounts,
            report_config=report_config,
            branding=branding,
            status=ClientStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return client_config
    
    def _extract_client_name(self, source_config: Dict[str, Any], source_path: Path) -> str:
        """Extract or generate client name from source configuration."""
        # Try various fields that might contain the client name
        name_fields = [
            'client_name', 'company_name', 'organization_name', 
            'name', 'title', 'project_name'
        ]
        
        for field in name_fields:
            if field in source_config and source_config[field]:
                return str(source_config[field])
        
        # Try nested configurations
        if 'branding' in source_config:
            branding = source_config['branding']
            if isinstance(branding, dict) and 'company_name' in branding:
                return str(branding['company_name'])
        
        if 'email' in source_config:
            email_config = source_config['email']
            if isinstance(email_config, dict) and 'company_name' in email_config:
                return str(email_config['company_name'])
        
        # Generate name from file path
        file_name = source_path.stem
        if file_name not in ['config', 'email_config', 'settings']:
            return file_name.replace('_', ' ').replace('-', ' ').title()
        
        # Default name
        return f"Migrated Client {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _convert_aws_accounts(self, source_config: Dict[str, Any]) -> List[AccountConfig]:
        """Convert AWS account configuration."""
        accounts = []
        
        # Check for AWS configuration in various formats
        aws_configs = []
        
        # Direct AWS config
        if 'aws' in source_config:
            aws_configs.append(source_config['aws'])
        
        # AWS accounts array
        if 'aws_accounts' in source_config:
            if isinstance(source_config['aws_accounts'], list):
                aws_configs.extend(source_config['aws_accounts'])
            else:
                aws_configs.append(source_config['aws_accounts'])
        
        # Profile-based configuration (framework style)
        if 'profile_name' in source_config or 'region' in source_config:
            aws_configs.append({
                'profile_name': source_config.get('profile_name', 'default'),
                'region': source_config.get('region', 'us-east-1')
            })
        
        # Convert each AWS config
        for i, aws_config in enumerate(aws_configs):
            if isinstance(aws_config, dict):
                account = self._convert_single_aws_account(aws_config, i)
                if account:
                    accounts.append(account)
        
        # If no accounts found, create a template account
        if not accounts:
            self.logger.warning("No AWS accounts found, creating template account")
            accounts.append(AccountConfig(
                account_id="123456789012",  # Template account ID
                access_key_id="AKIAIOSFODNN7EXAMPLE",  # Template access key
                secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # Template secret
                region="us-east-1",
                account_name="Migrated Account (UPDATE REQUIRED)"
            ))
        
        return accounts
    
    def _convert_single_aws_account(self, aws_config: Dict[str, Any], index: int) -> Optional[AccountConfig]:
        """Convert a single AWS account configuration."""
        try:
            # Extract account information
            account_id = aws_config.get('account_id', '123456789012')  # Template if missing
            region = aws_config.get('region', 'us-east-1')
            
            # Handle profile-based configuration (needs manual conversion)
            if 'profile_name' in aws_config:
                profile_name = aws_config['profile_name']
                self.logger.warning(f"Profile-based configuration detected: {profile_name}. "
                                  "Manual conversion to access keys required.")
                
                return AccountConfig(
                    account_id=account_id,
                    access_key_id=f"PROFILE_{profile_name.upper()}_ACCESS_KEY",  # Placeholder
                    secret_access_key=f"PROFILE_{profile_name.upper()}_SECRET_KEY",  # Placeholder
                    region=region,
                    account_name=f"Account from profile: {profile_name} (UPDATE REQUIRED)"
                )
            
            # Direct access key configuration
            access_key_id = aws_config.get('access_key_id')
            secret_access_key = aws_config.get('secret_access_key')
            
            if not access_key_id or not secret_access_key:
                self.logger.warning(f"Missing AWS credentials in account {index + 1}")
                return None
            
            account_name = aws_config.get('account_name', f"Account {index + 1}")
            
            return AccountConfig(
                account_id=account_id,
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
                region=region,
                account_name=account_name
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert AWS account {index + 1}: {e}")
            return None
    
    def _convert_report_config(self, source_config: Dict[str, Any]) -> ReportConfig:
        """Convert report configuration."""
        # Default report configuration
        report_config = {
            "weekly_enabled": True,
            "monthly_enabled": True,
            "recipients": [],
            "cc_recipients": [],
            "threshold": 1.0,
            "top_services": 10,
            "include_accounts": True,
            "alert_thresholds": []
        }
        
        # Extract email recipients
        recipients = []
        
        # Check various email configuration formats
        if 'email' in source_config:
            email_config = source_config['email']
            if isinstance(email_config, dict):
                if 'recipients' in email_config:
                    recipients.extend(self._extract_email_list(email_config['recipients']))
                if 'to' in email_config:
                    recipients.extend(self._extract_email_list(email_config['to']))
        
        if 'recipients' in source_config:
            recipients.extend(self._extract_email_list(source_config['recipients']))
        
        if 'email_recipients' in source_config:
            recipients.extend(self._extract_email_list(source_config['email_recipients']))
        
        # Remove duplicates
        recipients = list(set(recipients))
        
        if recipients:
            report_config["recipients"] = recipients
        else:
            # Add placeholder recipient
            report_config["recipients"] = ["admin@example.com"]
            self.logger.warning("No email recipients found, added placeholder")
        
        # Extract other report settings
        if 'analysis' in source_config:
            analysis_config = source_config['analysis']
            if isinstance(analysis_config, dict):
                report_config["threshold"] = analysis_config.get('min_cost_threshold', 1.0)
                report_config["top_services"] = analysis_config.get('top_services_count', 10)
                report_config["include_accounts"] = analysis_config.get('include_account_analysis', True)
        
        # Extract threshold settings
        if 'threshold' in source_config:
            report_config["threshold"] = float(source_config['threshold'])
        
        if 'top_services' in source_config:
            report_config["top_services"] = int(source_config['top_services'])
        
        return ReportConfig.from_dict(report_config)
    
    def _extract_email_list(self, email_data: Any) -> List[str]:
        """Extract email addresses from various formats."""
        emails = []
        
        if isinstance(email_data, str):
            # Single email or comma-separated
            emails.extend([email.strip() for email in email_data.split(',') if email.strip()])
        elif isinstance(email_data, list):
            # List of emails
            for email in email_data:
                if isinstance(email, str):
                    emails.append(email.strip())
        
        # Validate email format
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        valid_emails = [email for email in emails if email_pattern.match(email)]
        
        if len(valid_emails) != len(emails):
            self.logger.warning(f"Some invalid email addresses were filtered out")
        
        return valid_emails
    
    def _convert_branding_config(self, source_config: Dict[str, Any]) -> BrandingConfig:
        """Convert branding configuration."""
        branding_config = {
            "logo_s3_key": None,
            "primary_color": "#1f2937",
            "secondary_color": "#f59e0b",
            "company_name": "",
            "email_footer": ""
        }
        
        # Extract branding information
        if 'branding' in source_config:
            branding = source_config['branding']
            if isinstance(branding, dict):
                branding_config.update({
                    "logo_s3_key": branding.get('logo_s3_key'),
                    "primary_color": branding.get('primary_color', "#1f2937"),
                    "secondary_color": branding.get('secondary_color', "#f59e0b"),
                    "company_name": branding.get('company_name', ""),
                    "email_footer": branding.get('email_footer', "")
                })
        
        # Extract from email configuration
        if 'email' in source_config:
            email_config = source_config['email']
            if isinstance(email_config, dict):
                if 'company_name' in email_config:
                    branding_config["company_name"] = email_config['company_name']
                if 'footer' in email_config:
                    branding_config["email_footer"] = email_config['footer']
        
        # Extract company name from various sources
        if not branding_config["company_name"]:
            for field in ['company_name', 'organization_name', 'client_name']:
                if field in source_config and source_config[field]:
                    branding_config["company_name"] = str(source_config[field])
                    break
        
        return BrandingConfig.from_dict(branding_config)
    
    def _validate_migrated_config(self, client_config: ClientConfig) -> None:
        """Validate the migrated configuration."""
        try:
            # Basic validation is done by the dataclass __post_init__
            # Additional validation can be added here
            
            # Check for placeholder values that need manual update
            warnings = []
            
            for account in client_config.aws_accounts:
                if "EXAMPLE" in account.access_key_id or "EXAMPLE" in account.secret_access_key:
                    warnings.append(f"Account {account.account_name} has placeholder credentials")
                
                if "PROFILE_" in account.access_key_id:
                    warnings.append(f"Account {account.account_name} needs profile-to-credentials conversion")
                
                if account.account_id == "123456789012":
                    warnings.append(f"Account {account.account_name} has template account ID")
            
            if "admin@example.com" in client_config.report_config.recipients:
                warnings.append("Configuration has placeholder email recipients")
            
            if warnings:
                self.logger.warning(f"Configuration warnings for {client_config.client_name}: {warnings}")
                
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def _save_client_config(self, client_config: ClientConfig, output_file: Path) -> None:
        """Save client configuration to file."""
        config_dict = client_config.to_dict()
        
        with open(output_file, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
        
        self.logger.debug(f"Saved configuration to: {output_file}")
    
    def _create_backup(self) -> Path:
        """Create backup of the framework directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"framework_backup_{timestamp}"
        backup_path = self.output_dir / backup_name
        
        # Copy the framework directory
        shutil.copytree(self.framework_path, backup_path, ignore=shutil.ignore_patterns('*.pyc', '__pycache__'))
        
        return backup_path
    
    def rollback(self, migration_report_file: str) -> bool:
        """
        Rollback a migration using the migration report.
        
        Args:
            migration_report_file: Path to the migration report JSON file
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            self.logger.info(f"Starting rollback from report: {migration_report_file}")
            
            # Load migration report
            with open(migration_report_file, 'r') as f:
                report = json.load(f)
            
            backup_dir = report.get('backup_dir')
            if not backup_dir or not Path(backup_dir).exists():
                self.logger.error("Backup directory not found, cannot rollback")
                return False
            
            # Remove migrated files
            for client in report.get('clients_migrated', []):
                output_file = Path(client['output_file'])
                if output_file.exists():
                    output_file.unlink()
                    self.logger.info(f"Removed migrated file: {output_file}")
            
            # Restore from backup if needed
            if backup_dir and Path(backup_dir).exists():
                self.logger.info(f"Backup available at: {backup_dir}")
                self.logger.info("Manual restoration from backup may be required")
            
            self.logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migration utility for aws-cost-agent-framework to Lambda Cost Reporting System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate all configurations with backup
  %(prog)s migrate --framework-path ../aws-cost-agent-framework --output-dir ./migrated
  
  # Migrate without backup
  %(prog)s migrate --framework-path ../aws-cost-agent-framework --no-backup
  
  # Rollback a migration
  %(prog)s rollback --report ./migrated/migration_report.json
  
  # Validate migrated configurations
  %(prog)s validate --config-dir ./migrated
        """
    )
    
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log level (default: INFO)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate configurations')
    migrate_parser.add_argument('--framework-path', required=True,
                               help='Path to aws-cost-agent-framework directory')
    migrate_parser.add_argument('--output-dir', default='migrated_configs',
                               help='Output directory for migrated configurations')
    migrate_parser.add_argument('--no-backup', action='store_true',
                               help='Skip creating backup')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migration')
    rollback_parser.add_argument('--report', required=True,
                                help='Migration report JSON file')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate migrated configurations')
    validate_parser.add_argument('--config-dir', required=True,
                                help='Directory containing migrated configurations')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        if args.command == 'migrate':
            migrator = FrameworkMigrator(args.framework_path, args.output_dir)
            report = migrator.migrate_all(backup=not args.no_backup)
            
            print(f"\n✅ Migration completed!")
            print(f"📊 Statistics:")
            print(f"   Total configs found: {report['statistics']['total_configs_found']}")
            print(f"   Successful migrations: {report['statistics']['successful_migrations']}")
            print(f"   Failed migrations: {report['statistics']['failed_migrations']}")
            print(f"   Warnings: {report['statistics']['warnings_count']}")
            print(f"📁 Output directory: {args.output_dir}")
            print(f"📋 Migration report: {args.output_dir}/migration_report.json")
            
            if report['statistics']['failed_migrations'] > 0:
                print(f"\n⚠️  Some migrations failed. Check the migration report for details.")
                return 1
            
        elif args.command == 'rollback':
            migrator = FrameworkMigrator("", "")  # Paths not needed for rollback
            success = migrator.rollback(args.report)
            
            if success:
                print("✅ Rollback completed successfully")
                return 0
            else:
                print("❌ Rollback failed")
                return 1
        
        elif args.command == 'validate':
            # Simple validation of migrated configs
            config_dir = Path(args.config_dir)
            if not config_dir.exists():
                print(f"❌ Configuration directory not found: {config_dir}")
                return 1
            
            config_files = list(config_dir.glob("*.json"))
            if not config_files:
                print(f"❌ No configuration files found in: {config_dir}")
                return 1
            
            valid_count = 0
            invalid_count = 0
            
            for config_file in config_files:
                try:
                    with open(config_file, 'r') as f:
                        config_data = json.load(f)
                    
                    client_config = ClientConfig.from_dict(config_data)
                    print(f"✅ {config_file.name}: Valid")
                    valid_count += 1
                    
                except Exception as e:
                    print(f"❌ {config_file.name}: Invalid - {e}")
                    invalid_count += 1
            
            print(f"\n📊 Validation results: {valid_count} valid, {invalid_count} invalid")
            return 0 if invalid_count == 0 else 1
        
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())