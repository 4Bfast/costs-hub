#!/usr/bin/env python3
"""
Client Management CLI for Lambda Cost Reporting System.

This CLI tool provides commands for managing client configurations including:
- Adding new clients
- Updating existing clients
- Removing clients
- Listing clients
- Validating client configurations
- Bulk import/export operations
"""

import argparse
import json
import sys
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import csv
from datetime import datetime

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import ClientConfig, AccountConfig, ReportConfig, BrandingConfig, ClientStatus
try:
    from services import ClientConfigManager
except ImportError:
    ClientConfigManager = None

try:
    from utils import setup_logging
except ImportError:
    def setup_logging(level="INFO"):
        logging.basicConfig(level=getattr(logging, level))


class ClientManagerCLI:
    """Command-line interface for client management operations."""
    
    def __init__(self, table_name: str = "cost-reporting-clients", region: str = "us-east-1", 
                 kms_key_id: Optional[str] = None):
        """
        Initialize the CLI with configuration.
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
            kms_key_id: KMS key ID for encryption
        """
        self.config_manager = ClientConfigManager(table_name, region, kms_key_id)
        self.logger = logging.getLogger(__name__)
    
    def add_client(self, config_file: str, validate_access: bool = True) -> bool:
        """
        Add a new client from configuration file.
        
        Args:
            config_file: Path to JSON configuration file
            validate_access: Whether to validate AWS access before adding
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Adding client from configuration file: {config_file}")
            
            # Load configuration from file
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Create ClientConfig object
            client_config = ClientConfig.from_dict(config_data)
            
            # Validate AWS access if requested
            if validate_access:
                self.logger.info("Validating AWS access...")
                if not self.config_manager.validate_client_access(client_config):
                    self.logger.error("AWS access validation failed")
                    return False
                self.logger.info("AWS access validation passed")
            
            # Create the client
            created_client = self.config_manager.create_client_config(client_config)
            
            print(f"✅ Successfully added client: {created_client.client_name} ({created_client.client_id})")
            return True
            
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {config_file}")
            print(f"❌ Error: Configuration file not found: {config_file}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            print(f"❌ Error: Invalid JSON in configuration file: {e}")
            return False
        except ValueError as e:
            self.logger.error(f"Configuration validation error: {e}")
            print(f"❌ Error: Configuration validation error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to add client: {e}")
            print(f"❌ Error: Failed to add client: {e}")
            return False
    
    def update_client(self, client_id: str, config_file: str, validate_access: bool = True) -> bool:
        """
        Update an existing client from configuration file.
        
        Args:
            client_id: Client ID to update
            config_file: Path to JSON configuration file
            validate_access: Whether to validate AWS access before updating
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Updating client {client_id} from configuration file: {config_file}")
            
            # Load configuration from file
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Ensure the client_id matches
            config_data['client_id'] = client_id
            
            # Create ClientConfig object
            client_config = ClientConfig.from_dict(config_data)
            
            # Validate AWS access if requested
            if validate_access:
                self.logger.info("Validating AWS access...")
                if not self.config_manager.validate_client_access(client_config):
                    self.logger.error("AWS access validation failed")
                    return False
                self.logger.info("AWS access validation passed")
            
            # Update the client
            updated_client = self.config_manager.update_client_config(client_config)
            
            print(f"✅ Successfully updated client: {updated_client.client_name} ({updated_client.client_id})")
            return True
            
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {config_file}")
            print(f"❌ Error: Configuration file not found: {config_file}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            print(f"❌ Error: Invalid JSON in configuration file: {e}")
            return False
        except ValueError as e:
            self.logger.error(f"Configuration validation error: {e}")
            print(f"❌ Error: Configuration validation error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to update client: {e}")
            print(f"❌ Error: Failed to update client: {e}")
            return False
    
    def remove_client(self, client_id: str, confirm: bool = False) -> bool:
        """
        Remove a client configuration.
        
        Args:
            client_id: Client ID to remove
            confirm: Skip confirmation prompt if True
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Removing client: {client_id}")
            
            # Get client info for confirmation
            try:
                client = self.config_manager.get_client_config(client_id)
                client_name = client.client_name
            except Exception:
                client_name = "Unknown"
            
            # Confirmation prompt
            if not confirm:
                response = input(f"Are you sure you want to remove client '{client_name}' ({client_id})? [y/N]: ")
                if response.lower() not in ['y', 'yes']:
                    print("Operation cancelled")
                    return False
            
            # Remove the client
            self.config_manager.delete_client_config(client_id)
            
            print(f"✅ Successfully removed client: {client_name} ({client_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove client: {e}")
            print(f"❌ Error: Failed to remove client: {e}")
            return False
    
    def list_clients(self, status: Optional[str] = None, output_format: str = "table") -> bool:
        """
        List client configurations.
        
        Args:
            status: Filter by status (active, inactive, suspended)
            output_format: Output format (table, json, csv)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Listing clients with status: {status or 'all'}")
            
            # Get clients
            if status:
                client_status = ClientStatus(status.lower())
                clients = self.config_manager.get_clients_by_status(client_status)
            else:
                # Get all clients by getting each status
                clients = []
                for status_enum in ClientStatus:
                    clients.extend(self.config_manager.get_clients_by_status(status_enum))
            
            if not clients:
                print("No clients found")
                return True
            
            # Output in requested format
            if output_format == "json":
                client_data = [client.to_dict() for client in clients]
                print(json.dumps(client_data, indent=2, default=str))
            elif output_format == "csv":
                self._output_clients_csv(clients)
            else:  # table format
                self._output_clients_table(clients)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to list clients: {e}")
            print(f"❌ Error: Failed to list clients: {e}")
            return False
    
    def validate_client(self, client_id: str) -> bool:
        """
        Validate a client configuration and AWS access.
        
        Args:
            client_id: Client ID to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            self.logger.info(f"Validating client: {client_id}")
            
            # Get client configuration
            client = self.config_manager.get_client_config(client_id)
            
            print(f"Validating client: {client.client_name} ({client.client_id})")
            print(f"Status: {client.status.value}")
            print(f"AWS Accounts: {len(client.aws_accounts)}")
            print(f"Recipients: {len(client.report_config.recipients)}")
            
            # Validate configuration
            try:
                self.config_manager.validate_client_config(client)
                print("✅ Configuration validation: PASSED")
            except Exception as e:
                print(f"❌ Configuration validation: FAILED - {e}")
                return False
            
            # Validate AWS access
            print("Validating AWS access...")
            if self.config_manager.validate_client_access(client):
                print("✅ AWS access validation: PASSED")
                return True
            else:
                print("❌ AWS access validation: FAILED")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to validate client: {e}")
            print(f"❌ Error: Failed to validate client: {e}")
            return False
    
    def export_clients(self, output_file: str, status: Optional[str] = None) -> bool:
        """
        Export client configurations to JSON file.
        
        Args:
            output_file: Output file path
            status: Filter by status (active, inactive, suspended)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Exporting clients to: {output_file}")
            
            # Get clients
            if status:
                client_status = ClientStatus(status.lower())
                clients = self.config_manager.get_clients_by_status(client_status)
            else:
                # Get all clients
                clients = []
                for status_enum in ClientStatus:
                    clients.extend(self.config_manager.get_clients_by_status(status_enum))
            
            # Convert to dict format
            client_data = [client.to_dict() for client in clients]
            
            # Write to file
            with open(output_file, 'w') as f:
                json.dump(client_data, f, indent=2, default=str)
            
            print(f"✅ Successfully exported {len(clients)} clients to: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export clients: {e}")
            print(f"❌ Error: Failed to export clients: {e}")
            return False
    
    def import_clients(self, input_file: str, validate_access: bool = True, 
                      update_existing: bool = False) -> bool:
        """
        Import client configurations from JSON file.
        
        Args:
            input_file: Input file path
            validate_access: Whether to validate AWS access before importing
            update_existing: Whether to update existing clients or skip them
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Importing clients from: {input_file}")
            
            # Load data from file
            with open(input_file, 'r') as f:
                client_data_list = json.load(f)
            
            if not isinstance(client_data_list, list):
                raise ValueError("Input file must contain a list of client configurations")
            
            success_count = 0
            error_count = 0
            
            for i, client_data in enumerate(client_data_list):
                try:
                    # Create ClientConfig object
                    client_config = ClientConfig.from_dict(client_data)
                    
                    print(f"Processing client {i+1}/{len(client_data_list)}: {client_config.client_name}")
                    
                    # Validate AWS access if requested
                    if validate_access:
                        if not self.config_manager.validate_client_access(client_config):
                            print(f"  ❌ AWS access validation failed, skipping")
                            error_count += 1
                            continue
                    
                    # Try to create or update
                    try:
                        self.config_manager.create_client_config(client_config)
                        print(f"  ✅ Created successfully")
                        success_count += 1
                    except Exception as e:
                        if "already exists" in str(e) and update_existing:
                            # Update existing client
                            self.config_manager.update_client_config(client_config)
                            print(f"  ✅ Updated successfully")
                            success_count += 1
                        else:
                            print(f"  ❌ Failed: {e}")
                            error_count += 1
                
                except Exception as e:
                    print(f"  ❌ Failed to process client {i+1}: {e}")
                    error_count += 1
            
            print(f"\nImport completed: {success_count} successful, {error_count} errors")
            return error_count == 0
            
        except FileNotFoundError:
            self.logger.error(f"Input file not found: {input_file}")
            print(f"❌ Error: Input file not found: {input_file}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in input file: {e}")
            print(f"❌ Error: Invalid JSON in input file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to import clients: {e}")
            print(f"❌ Error: Failed to import clients: {e}")
            return False
    
    def _output_clients_table(self, clients: List[ClientConfig]) -> None:
        """Output clients in table format."""
        # Header
        print(f"{'Client ID':<36} {'Name':<30} {'Status':<10} {'Accounts':<8} {'Recipients':<10} {'Updated':<20}")
        print("-" * 120)
        
        # Rows
        for client in clients:
            updated_str = client.updated_at.strftime("%Y-%m-%d %H:%M") if client.updated_at else "N/A"
            print(f"{client.client_id:<36} {client.client_name[:29]:<30} {client.status.value:<10} "
                  f"{len(client.aws_accounts):<8} {len(client.report_config.recipients):<10} {updated_str:<20}")
    
    def _output_clients_csv(self, clients: List[ClientConfig]) -> None:
        """Output clients in CSV format."""
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['client_id', 'client_name', 'status', 'aws_accounts_count', 
                        'recipients_count', 'created_at', 'updated_at'])
        
        # Rows
        for client in clients:
            writer.writerow([
                client.client_id,
                client.client_name,
                client.status.value,
                len(client.aws_accounts),
                len(client.report_config.recipients),
                client.created_at.isoformat() if client.created_at else '',
                client.updated_at.isoformat() if client.updated_at else ''
            ])
        
        print(output.getvalue())


def create_sample_config(output_file: str) -> None:
    """Create a sample client configuration file."""
    import uuid
    
    sample_config = {
        "client_id": str(uuid.uuid4()),
        "client_name": "Example Company",
        "aws_accounts": [
            {
                "account_id": "123456789012",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "region": "us-east-1",
                "account_name": "Production Account"
            }
        ],
        "report_config": {
            "weekly_enabled": True,
            "monthly_enabled": True,
            "recipients": ["admin@example.com", "finance@example.com"],
            "cc_recipients": [],
            "threshold": 1000.0,
            "top_services": 10,
            "include_accounts": True,
            "alert_thresholds": []
        },
        "branding": {
            "logo_s3_key": None,
            "primary_color": "#1f2937",
            "secondary_color": "#f59e0b",
            "company_name": "Example Company",
            "email_footer": "This is an automated cost report from Example Company."
        },
        "status": "active"
    }
    
    with open(output_file, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"✅ Sample configuration created: {output_file}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Client Management CLI for Lambda Cost Reporting System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create sample configuration
  %(prog)s sample-config --output sample-client.json
  
  # Add a new client
  %(prog)s add --config client-config.json
  
  # Update existing client
  %(prog)s update --client-id abc123 --config updated-config.json
  
  # List all clients
  %(prog)s list
  
  # List only active clients in JSON format
  %(prog)s list --status active --format json
  
  # Validate client configuration and AWS access
  %(prog)s validate --client-id abc123
  
  # Export all clients to file
  %(prog)s export --output all-clients.json
  
  # Import clients from file
  %(prog)s import --input clients-to-import.json --update-existing
  
  # Remove a client
  %(prog)s remove --client-id abc123
        """
    )
    
    # Global options
    parser.add_argument('--table-name', default='cost-reporting-clients',
                       help='DynamoDB table name (default: cost-reporting-clients)')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region (default: us-east-1)')
    parser.add_argument('--kms-key-id', 
                       help='KMS key ID for encryption (optional)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log level (default: INFO)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Sample config command
    sample_parser = subparsers.add_parser('sample-config', help='Create sample configuration file')
    sample_parser.add_argument('--output', required=True, help='Output file path')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add new client')
    add_parser.add_argument('--config', required=True, help='Client configuration file (JSON)')
    add_parser.add_argument('--no-validate', action='store_true', 
                           help='Skip AWS access validation')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update existing client')
    update_parser.add_argument('--client-id', required=True, help='Client ID to update')
    update_parser.add_argument('--config', required=True, help='Client configuration file (JSON)')
    update_parser.add_argument('--no-validate', action='store_true',
                              help='Skip AWS access validation')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove client')
    remove_parser.add_argument('--client-id', required=True, help='Client ID to remove')
    remove_parser.add_argument('--confirm', action='store_true',
                              help='Skip confirmation prompt')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List clients')
    list_parser.add_argument('--status', choices=['active', 'inactive', 'suspended'],
                            help='Filter by status')
    list_parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table',
                            help='Output format (default: table)')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate client configuration')
    validate_parser.add_argument('--client-id', required=True, help='Client ID to validate')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export clients to file')
    export_parser.add_argument('--output', required=True, help='Output file path')
    export_parser.add_argument('--status', choices=['active', 'inactive', 'suspended'],
                              help='Filter by status')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import clients from file')
    import_parser.add_argument('--input', required=True, help='Input file path')
    import_parser.add_argument('--no-validate', action='store_true',
                              help='Skip AWS access validation')
    import_parser.add_argument('--update-existing', action='store_true',
                              help='Update existing clients instead of skipping')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Handle sample-config command separately
    if args.command == 'sample-config':
        create_sample_config(args.output)
        return 0
    
    # Initialize CLI
    try:
        if ClientConfigManager is None:
            print("❌ Error: ClientConfigManager not available. Make sure all dependencies are installed.")
            return 1
        cli = ClientManagerCLI(args.table_name, args.region, args.kms_key_id)
    except Exception as e:
        print(f"❌ Error: Failed to initialize CLI: {e}")
        return 1
    
    # Execute command
    success = False
    try:
        if args.command == 'add':
            success = cli.add_client(args.config, not args.no_validate)
        elif args.command == 'update':
            success = cli.update_client(args.client_id, args.config, not args.no_validate)
        elif args.command == 'remove':
            success = cli.remove_client(args.client_id, args.confirm)
        elif args.command == 'list':
            success = cli.list_clients(args.status, args.format)
        elif args.command == 'validate':
            success = cli.validate_client(args.client_id)
        elif args.command == 'export':
            success = cli.export_clients(args.output, args.status)
        elif args.command == 'import':
            success = cli.import_clients(args.input, not args.no_validate, args.update_existing)
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