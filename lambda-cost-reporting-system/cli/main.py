#!/usr/bin/env python3
"""
Main CLI entry point for Lambda Cost Reporting System.

This provides a unified interface to all CLI tools including:
- Client management (add, update, remove, list clients)
- Configuration validation (validate configs, generate test reports)
- Bulk operations (import/export, bulk validation)
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path


def get_cli_path(cli_name: str) -> str:
    """Get the path to a CLI script."""
    cli_dir = Path(__file__).parent
    return str(cli_dir / cli_name)


def run_client_manager(args: list) -> int:
    """Run the client manager CLI."""
    cli_path = get_cli_path("client_manager.py")
    return subprocess.call([sys.executable, cli_path] + args)


def run_config_validator(args: list) -> int:
    """Run the config validator CLI."""
    cli_path = get_cli_path("validate_config.py")
    return subprocess.call([sys.executable, cli_path] + args)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Lambda Cost Reporting System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Commands:
  client      Client management operations (add, update, remove, list)
  validate    Configuration validation operations
  
Examples:
  # Client Management
  %(prog)s client add --config client-config.json
  %(prog)s client list --status active
  %(prog)s client remove --client-id abc123
  %(prog)s client export --output all-clients.json
  %(prog)s client import --input clients.json
  
  # Configuration Validation  
  %(prog)s validate single --config client-config.json
  %(prog)s validate bulk --configs config1.json config2.json
  %(prog)s validate directory --path ./configs
  
For detailed help on any command:
  %(prog)s client --help
  %(prog)s validate --help
        """
    )
    
    subparsers = parser.add_subparsers(dest='tool', help='Available tools')
    
    # Client management tool
    client_parser = subparsers.add_parser('client', help='Client management operations')
    client_parser.add_argument('args', nargs=argparse.REMAINDER, 
                              help='Arguments to pass to client manager')
    
    # Configuration validation tool
    validate_parser = subparsers.add_parser('validate', help='Configuration validation')
    validate_parser.add_argument('args', nargs=argparse.REMAINDER,
                                help='Arguments to pass to config validator')
    
    args = parser.parse_args()
    
    if not args.tool:
        parser.print_help()
        return 1
    
    # Route to appropriate CLI tool
    if args.tool == 'client':
        return run_client_manager(args.args)
    elif args.tool == 'validate':
        return run_config_validator(args.args)
    else:
        print(f"❌ Error: Unknown tool: {args.tool}")
        return 1


if __name__ == '__main__':
    sys.exit(main())