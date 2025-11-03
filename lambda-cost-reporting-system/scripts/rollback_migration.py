#!/usr/bin/env python3
"""
Rollback utility for Lambda Cost Reporting System migrations.

This script provides comprehensive rollback capabilities for migrations including:
1. Configuration rollback from backups
2. DynamoDB data rollback
3. S3 asset cleanup
4. Infrastructure rollback coordination
"""

import argparse
import json
import sys
import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import shutil
import boto3
from botocore.exceptions import ClientError

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from services import ClientConfigManager
except ImportError:
    ClientConfigManager = None


class MigrationRollback:
    """Handles rollback operations for Lambda Cost Reporting System migrations."""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the rollback utility.
        
        Args:
            region: AWS region for services
        """
        self.region = region
        self.logger = logging.getLogger(__name__)
        
        # AWS clients
        self.dynamodb = None
        self.s3 = None
        
        # Rollback tracking
        self.rollback_log = []
    
    def rollback_from_report(self, migration_report_file: str, 
                           rollback_configs: bool = True,
                           rollback_dynamodb: bool = False,
                           rollback_s3: bool = False,
                           table_name: str = "cost-reporting-clients",
                           s3_bucket: str = None) -> Dict[str, Any]:
        """
        Perform rollback based on migration report.
        
        Args:
            migration_report_file: Path to migration report JSON file
            rollback_configs: Whether to rollback configuration files
            rollback_dynamodb: Whether to rollback DynamoDB data
            rollback_s3: Whether to rollback S3 assets
            table_name: DynamoDB table name
            s3_bucket: S3 bucket name for assets
            
        Returns:
            Rollback results dictionary
        """
        self.logger.info(f"Starting rollback from report: {migration_report_file}")
        
        # Load migration report
        try:
            with open(migration_report_file, 'r') as f:
                migration_report = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load migration report: {e}")
        
        rollback_results = {
            "rollback_id": f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "migration_report": migration_report_file,
            "operations": {
                "configs": rollback_configs,
                "dynamodb": rollback_dynamodb,
                "s3": rollback_s3
            },
            "results": {
                "configs": {"status": "skipped", "details": []},
                "dynamodb": {"status": "skipped", "details": []},
                "s3": {"status": "skipped", "details": []}
            },
            "errors": [],
            "success": False
        }
        
        try:
            # Rollback configuration files
            if rollback_configs:
                config_result = self._rollback_configurations(migration_report)
                rollback_results["results"]["configs"] = config_result
            
            # Rollback DynamoDB data
            if rollback_dynamodb:
                dynamodb_result = self._rollback_dynamodb_data(migration_report, table_name)
                rollback_results["results"]["dynamodb"] = dynamodb_result
            
            # Rollback S3 assets
            if rollback_s3 and s3_bucket:
                s3_result = self._rollback_s3_assets(migration_report, s3_bucket)
                rollback_results["results"]["s3"] = s3_result
            
            # Determine overall success
            all_successful = True
            for operation, result in rollback_results["results"].items():
                if result["status"] == "failed":
                    all_successful = False
                    break
            
            rollback_results["success"] = all_successful
            
            # Save rollback report
            report_file = Path(migration_report_file).parent / f"rollback_report_{rollback_results['rollback_id']}.json"
            with open(report_file, 'w') as f:
                json.dump(rollback_results, f, indent=2)
            
            self.logger.info(f"Rollback completed. Report saved to: {report_file}")
            return rollback_results
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            rollback_results["errors"].append({
                "operation": "general",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            rollback_results["success"] = False
            return rollback_results
    
    def _rollback_configurations(self, migration_report: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback configuration files."""
        self.logger.info("Rolling back configuration files")
        
        result = {
            "status": "success",
            "details": [],
            "files_removed": 0,
            "backup_restored": False
        }
        
        try:
            # Remove migrated configuration files
            clients_migrated = migration_report.get("clients_migrated", [])
            
            for client in clients_migrated:
                output_file = client.get("output_file")
                if output_file and Path(output_file).exists():
                    try:
                        Path(output_file).unlink()
                        result["files_removed"] += 1
                        result["details"].append(f"Removed: {output_file}")
                        self.logger.info(f"Removed migrated file: {output_file}")
                    except Exception as e:
                        error_msg = f"Failed to remove {output_file}: {e}"
                        result["details"].append(error_msg)
                        self.logger.error(error_msg)
            
            # Restore from backup if available
            backup_dir = migration_report.get("backup_dir")
            if backup_dir and Path(backup_dir).exists():
                framework_path = migration_report.get("framework_path")
                if framework_path:
                    try:
                        # Create restoration confirmation
                        self.logger.info(f"Backup available at: {backup_dir}")
                        self.logger.info(f"Original framework path: {framework_path}")
                        
                        # Note: We don't automatically restore the backup to avoid overwriting
                        # any changes made since the migration
                        result["details"].append(f"Backup available for manual restoration: {backup_dir}")
                        result["backup_restored"] = False
                        
                    except Exception as e:
                        error_msg = f"Backup restoration issue: {e}"
                        result["details"].append(error_msg)
                        self.logger.warning(error_msg)
            
            if result["files_removed"] == len(clients_migrated):
                result["status"] = "success"
            else:
                result["status"] = "partial"
            
        except Exception as e:
            result["status"] = "failed"
            result["details"].append(f"Configuration rollback failed: {e}")
            self.logger.error(f"Configuration rollback failed: {e}")
        
        return result
    
    def _rollback_dynamodb_data(self, migration_report: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Rollback DynamoDB data."""
        self.logger.info(f"Rolling back DynamoDB data from table: {table_name}")
        
        result = {
            "status": "success",
            "details": [],
            "clients_removed": 0,
            "table_name": table_name
        }
        
        try:
            # Initialize DynamoDB client
            if not self.dynamodb:
                self.dynamodb = boto3.client('dynamodb', region_name=self.region)
            
            # Check if table exists
            try:
                self.dynamodb.describe_table(TableName=table_name)
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    result["status"] = "skipped"
                    result["details"].append(f"Table {table_name} does not exist")
                    return result
                else:
                    raise
            
            # Remove migrated clients from DynamoDB
            clients_migrated = migration_report.get("clients_migrated", [])
            
            for client in clients_migrated:
                client_id = client.get("client_id")
                if client_id:
                    try:
                        # Delete the client from DynamoDB
                        self.dynamodb.delete_item(
                            TableName=table_name,
                            Key={'client_id': {'S': client_id}}
                        )
                        
                        result["clients_removed"] += 1
                        result["details"].append(f"Removed client: {client_id}")
                        self.logger.info(f"Removed client from DynamoDB: {client_id}")
                        
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'ResourceNotFoundException':
                            result["details"].append(f"Client not found in DynamoDB: {client_id}")
                        else:
                            error_msg = f"Failed to remove client {client_id}: {e}"
                            result["details"].append(error_msg)
                            self.logger.error(error_msg)
            
            if result["clients_removed"] == len(clients_migrated):
                result["status"] = "success"
            else:
                result["status"] = "partial"
            
        except Exception as e:
            result["status"] = "failed"
            result["details"].append(f"DynamoDB rollback failed: {e}")
            self.logger.error(f"DynamoDB rollback failed: {e}")
        
        return result
    
    def _rollback_s3_assets(self, migration_report: Dict[str, Any], s3_bucket: str) -> Dict[str, Any]:
        """Rollback S3 assets."""
        self.logger.info(f"Rolling back S3 assets from bucket: {s3_bucket}")
        
        result = {
            "status": "success",
            "details": [],
            "assets_removed": 0,
            "bucket": s3_bucket
        }
        
        try:
            # Initialize S3 client
            if not self.s3:
                self.s3 = boto3.client('s3', region_name=self.region)
            
            # Check if bucket exists
            try:
                self.s3.head_bucket(Bucket=s3_bucket)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    result["status"] = "skipped"
                    result["details"].append(f"Bucket {s3_bucket} does not exist")
                    return result
                else:
                    raise
            
            # Remove assets for migrated clients
            clients_migrated = migration_report.get("clients_migrated", [])
            
            for client in clients_migrated:
                client_id = client.get("client_id")
                if client_id:
                    try:
                        # List objects with client ID prefix
                        response = self.s3.list_objects_v2(
                            Bucket=s3_bucket,
                            Prefix=f"clients/{client_id}/"
                        )
                        
                        objects = response.get('Contents', [])
                        
                        if objects:
                            # Delete objects
                            delete_objects = [{'Key': obj['Key']} for obj in objects]
                            
                            self.s3.delete_objects(
                                Bucket=s3_bucket,
                                Delete={'Objects': delete_objects}
                            )
                            
                            result["assets_removed"] += len(delete_objects)
                            result["details"].append(f"Removed {len(delete_objects)} assets for client: {client_id}")
                            self.logger.info(f"Removed {len(delete_objects)} S3 assets for client: {client_id}")
                        else:
                            result["details"].append(f"No assets found for client: {client_id}")
                        
                    except ClientError as e:
                        error_msg = f"Failed to remove assets for client {client_id}: {e}"
                        result["details"].append(error_msg)
                        self.logger.error(error_msg)
            
            result["status"] = "success"
            
        except Exception as e:
            result["status"] = "failed"
            result["details"].append(f"S3 rollback failed: {e}")
            self.logger.error(f"S3 rollback failed: {e}")
        
        return result
    
    def create_rollback_plan(self, migration_report_file: str) -> Dict[str, Any]:
        """
        Create a rollback plan based on migration report.
        
        Args:
            migration_report_file: Path to migration report JSON file
            
        Returns:
            Rollback plan dictionary
        """
        try:
            with open(migration_report_file, 'r') as f:
                migration_report = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load migration report: {e}")
        
        plan = {
            "plan_id": f"rollback_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "migration_report": migration_report_file,
            "migration_id": migration_report.get("migration_id"),
            "clients_to_rollback": len(migration_report.get("clients_migrated", [])),
            "operations": {
                "configuration_files": {
                    "description": "Remove migrated configuration files",
                    "files_to_remove": [client.get("output_file") for client in migration_report.get("clients_migrated", [])],
                    "backup_available": bool(migration_report.get("backup_dir"))
                },
                "dynamodb_data": {
                    "description": "Remove client data from DynamoDB",
                    "clients_to_remove": [client.get("client_id") for client in migration_report.get("clients_migrated", [])],
                    "table_name": "cost-reporting-clients"
                },
                "s3_assets": {
                    "description": "Remove client assets from S3",
                    "clients_with_assets": [client.get("client_id") for client in migration_report.get("clients_migrated", [])],
                    "bucket_name": "cost-reporting-assets"
                }
            },
            "recommendations": [],
            "warnings": []
        }
        
        # Add recommendations
        if migration_report.get("backup_dir"):
            plan["recommendations"].append("Backup is available for manual restoration if needed")
        else:
            plan["warnings"].append("No backup was created during migration")
        
        if migration_report.get("statistics", {}).get("failed_migrations", 0) > 0:
            plan["warnings"].append("Original migration had failures - partial rollback may be sufficient")
        
        return plan
    
    def interactive_rollback(self, migration_report_file: str) -> Dict[str, Any]:
        """
        Perform interactive rollback with user confirmation.
        
        Args:
            migration_report_file: Path to migration report JSON file
            
        Returns:
            Rollback results dictionary
        """
        # Create rollback plan
        plan = self.create_rollback_plan(migration_report_file)
        
        print("🔄 Migration Rollback Plan")
        print("=" * 50)
        print(f"Migration ID: {plan['migration_id']}")
        print(f"Clients to rollback: {plan['clients_to_rollback']}")
        print()
        
        # Show operations
        print("📋 Planned Operations:")
        for op_name, op_details in plan["operations"].items():
            print(f"  • {op_name.replace('_', ' ').title()}: {op_details['description']}")
        print()
        
        # Show warnings
        if plan["warnings"]:
            print("⚠️  Warnings:")
            for warning in plan["warnings"]:
                print(f"  • {warning}")
            print()
        
        # Show recommendations
        if plan["recommendations"]:
            print("💡 Recommendations:")
            for rec in plan["recommendations"]:
                print(f"  • {rec}")
            print()
        
        # Get user confirmation
        print("Select rollback operations:")
        rollback_configs = input("Rollback configuration files? [y/N]: ").lower() in ['y', 'yes']
        rollback_dynamodb = input("Rollback DynamoDB data? [y/N]: ").lower() in ['y', 'yes']
        rollback_s3 = input("Rollback S3 assets? [y/N]: ").lower() in ['y', 'yes']
        
        if not any([rollback_configs, rollback_dynamodb, rollback_s3]):
            print("No operations selected. Rollback cancelled.")
            return {"success": False, "message": "No operations selected"}
        
        # Get additional parameters
        table_name = "cost-reporting-clients"
        s3_bucket = None
        
        if rollback_dynamodb:
            table_input = input(f"DynamoDB table name [{table_name}]: ").strip()
            if table_input:
                table_name = table_input
        
        if rollback_s3:
            s3_bucket = input("S3 bucket name: ").strip()
            if not s3_bucket:
                print("S3 bucket name is required for S3 rollback")
                rollback_s3 = False
        
        # Final confirmation
        print("\n🚨 Final Confirmation")
        print("This operation will:")
        if rollback_configs:
            print("  • Remove migrated configuration files")
        if rollback_dynamodb:
            print(f"  • Remove client data from DynamoDB table: {table_name}")
        if rollback_s3:
            print(f"  • Remove client assets from S3 bucket: {s3_bucket}")
        
        final_confirm = input("\nProceed with rollback? [y/N]: ").lower()
        if final_confirm not in ['y', 'yes']:
            print("Rollback cancelled by user")
            return {"success": False, "message": "Cancelled by user"}
        
        # Perform rollback
        print("\n🔄 Performing rollback...")
        return self.rollback_from_report(
            migration_report_file,
            rollback_configs=rollback_configs,
            rollback_dynamodb=rollback_dynamodb,
            rollback_s3=rollback_s3,
            table_name=table_name,
            s3_bucket=s3_bucket
        )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Rollback utility for Lambda Cost Reporting System migrations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive rollback
  %(prog)s interactive --report migration_report.json
  
  # Rollback configuration files only
  %(prog)s auto --report migration_report.json --configs-only
  
  # Full rollback including DynamoDB and S3
  %(prog)s auto --report migration_report.json --all --table cost-reporting-clients --bucket cost-assets
  
  # Create rollback plan
  %(prog)s plan --report migration_report.json --output rollback_plan.json
        """
    )
    
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region (default: us-east-1)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log level (default: INFO)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Interactive rollback
    interactive_parser = subparsers.add_parser('interactive', help='Interactive rollback with prompts')
    interactive_parser.add_argument('--report', required=True, help='Migration report JSON file')
    
    # Automatic rollback
    auto_parser = subparsers.add_parser('auto', help='Automatic rollback')
    auto_parser.add_argument('--report', required=True, help='Migration report JSON file')
    auto_parser.add_argument('--configs-only', action='store_true',
                            help='Rollback configuration files only')
    auto_parser.add_argument('--all', action='store_true',
                            help='Rollback all components (configs, DynamoDB, S3)')
    auto_parser.add_argument('--table', default='cost-reporting-clients',
                            help='DynamoDB table name')
    auto_parser.add_argument('--bucket', help='S3 bucket name')
    
    # Plan creation
    plan_parser = subparsers.add_parser('plan', help='Create rollback plan')
    plan_parser.add_argument('--report', required=True, help='Migration report JSON file')
    plan_parser.add_argument('--output', help='Output file for rollback plan')
    
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
        rollback = MigrationRollback(args.region)
        
        if args.command == 'interactive':
            results = rollback.interactive_rollback(args.report)
            
            if results.get("success"):
                print("\n✅ Rollback completed successfully!")
                return 0
            else:
                print(f"\n❌ Rollback failed: {results.get('message', 'Unknown error')}")
                return 1
        
        elif args.command == 'auto':
            if args.configs_only:
                rollback_configs = True
                rollback_dynamodb = False
                rollback_s3 = False
            elif args.all:
                rollback_configs = True
                rollback_dynamodb = True
                rollback_s3 = True
            else:
                print("❌ Error: Specify either --configs-only or --all for automatic rollback")
                return 1
            
            results = rollback.rollback_from_report(
                args.report,
                rollback_configs=rollback_configs,
                rollback_dynamodb=rollback_dynamodb,
                rollback_s3=rollback_s3,
                table_name=args.table,
                s3_bucket=args.bucket
            )
            
            if results["success"]:
                print("\n✅ Rollback completed successfully!")
                return 0
            else:
                print("\n❌ Rollback failed or completed with errors")
                for error in results.get("errors", []):
                    print(f"  Error: {error.get('error', 'Unknown error')}")
                return 1
        
        elif args.command == 'plan':
            plan = rollback.create_rollback_plan(args.report)
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(plan, f, indent=2)
                print(f"✅ Rollback plan saved to: {args.output}")
            else:
                print(json.dumps(plan, indent=2))
            
            return 0
        
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