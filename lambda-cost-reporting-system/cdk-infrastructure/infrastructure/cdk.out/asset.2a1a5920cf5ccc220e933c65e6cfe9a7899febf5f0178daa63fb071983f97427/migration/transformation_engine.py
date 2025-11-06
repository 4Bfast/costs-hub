"""
Data Transformation Engine

This module handles the transformation of data from the existing PostgreSQL schema
to the new unified multi-cloud format.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
import uuid

from ..models.multi_cloud_models import (
    ServiceCategory, CloudProvider, Currency,
    SERVICE_CATEGORY_MAPPING, get_unified_service_category
)


logger = logging.getLogger(__name__)


class DataTransformationEngine:
    """
    Engine for transforming data between different formats and schemas.
    """
    
    def __init__(self):
        """Initialize the transformation engine."""
        # Custom service mappings for legacy data
        self.custom_aws_mappings = {
            # Legacy service names that might not be in the standard mapping
            'AmazonEC2': ServiceCategory.COMPUTE,
            'AmazonS3': ServiceCategory.STORAGE,
            'AmazonRDS': ServiceCategory.DATABASE,
            'AmazonDynamoDB': ServiceCategory.DATABASE,
            'AmazonCloudFront': ServiceCategory.NETWORKING,
            'AmazonRoute53': ServiceCategory.NETWORKING,
            'AmazonVPC': ServiceCategory.NETWORKING,
            'AmazonLambda': ServiceCategory.SERVERLESS,
            'AmazonECS': ServiceCategory.CONTAINERS,
            'AmazonEKS': ServiceCategory.CONTAINERS,
            'AmazonRedshift': ServiceCategory.ANALYTICS,
            'AmazonEMR': ServiceCategory.ANALYTICS,
            'AmazonKinesis': ServiceCategory.ANALYTICS,
            'AmazonSageMaker': ServiceCategory.AI_ML,
            'AmazonBedrock': ServiceCategory.AI_ML,
            'AmazonComprehend': ServiceCategory.AI_ML,
            'AmazonRekognition': ServiceCategory.AI_ML,
            'AmazonCloudWatch': ServiceCategory.MANAGEMENT,
            'AmazonCloudTrail': ServiceCategory.MANAGEMENT,
            'AmazonConfig': ServiceCategory.MANAGEMENT,
            'AmazonIAM': ServiceCategory.SECURITY,
            'AmazonKMS': ServiceCategory.SECURITY,
            'AmazonSecretsManager': ServiceCategory.SECURITY,
            'AmazonWAF': ServiceCategory.SECURITY,
            'AmazonGuardDuty': ServiceCategory.SECURITY,
        }
        
        # Organization ID to client ID mapping cache
        self._org_client_mapping = {}
    
    def transform_organization(self, org_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform organization data from PostgreSQL to multi-cloud format.
        
        Args:
            org_data: Organization data from PostgreSQL
            
        Returns:
            Transformed client data
        """
        org_id = org_data['id']
        
        # Generate or retrieve client ID
        if org_id not in self._org_client_mapping:
            self._org_client_mapping[org_id] = f"client-{uuid.uuid4().hex[:8]}"
        
        client_id = self._org_client_mapping[org_id]
        
        # Transform AWS accounts
        aws_accounts = []
        if org_data.get('aws_accounts'):
            for account in org_data['aws_accounts']:
                if account and account.get('id'):
                    aws_accounts.append(self._transform_aws_account(account))
        
        return {
            'client_id': client_id,
            'organization_name': org_data['org_name'],
            'original_org_id': org_id,
            'cloud_accounts': {
                CloudProvider.AWS.value: aws_accounts
            },
            'created_at': org_data['created_at'].isoformat() if org_data.get('created_at') else None,
            'status': 'ACTIVE',
            'migration_metadata': {
                'migrated_at': datetime.utcnow().isoformat(),
                'source_system': 'costshub_postgresql',
                'migration_version': '1.0.0'
            }
        }
    
    def _transform_aws_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform AWS account data."""
        return {
            'account_id': account_data.get('payer_account_id', 'unknown'),
            'account_name': account_data.get('account_name', 'Unknown Account'),
            'provider': CloudProvider.AWS.value,
            'credentials': {
                'credential_type': 'iam_role',
                'role_arn': account_data.get('iam_role_arn'),
                'external_id': account_data.get('external_id'),
                'focus_s3_bucket_path': account_data.get('focus_s3_bucket_path')
            },
            'regions': ['us-east-1'],  # Default region, could be enhanced
            'is_active': account_data.get('status') == 'ACTIVE',
            'original_account_id': account_data.get('id'),
            'migration_metadata': {
                'migrated_at': datetime.utcnow().isoformat(),
                'original_status': account_data.get('status')
            }
        }
    
    def map_aws_service_to_category(self, service_name: str) -> ServiceCategory:
        """
        Map AWS service name to unified service category.
        
        Args:
            service_name: AWS service name
            
        Returns:
            Unified service category
        """
        # First try custom mappings for legacy data
        if service_name in self.custom_aws_mappings:
            return self.custom_aws_mappings[service_name]
        
        # Try standard mapping
        category = get_unified_service_category(CloudProvider.AWS, service_name)
        if category != ServiceCategory.OTHER:
            return category
        
        # Try partial matching for services with prefixes/suffixes
        service_lower = service_name.lower()
        
        # Common patterns in AWS service names
        if any(compute_term in service_lower for compute_term in ['ec2', 'compute', 'instance']):
            return ServiceCategory.COMPUTE
        elif any(storage_term in service_lower for storage_term in ['s3', 'storage', 'ebs', 'efs']):
            return ServiceCategory.STORAGE
        elif any(db_term in service_lower for db_term in ['rds', 'database', 'dynamodb', 'aurora']):
            return ServiceCategory.DATABASE
        elif any(net_term in service_lower for net_term in ['vpc', 'cloudfront', 'route53', 'elb']):
            return ServiceCategory.NETWORKING
        elif any(analytics_term in service_lower for analytics_term in ['redshift', 'emr', 'athena', 'glue']):
            return ServiceCategory.ANALYTICS
        elif any(ai_term in service_lower for ai_term in ['sagemaker', 'bedrock', 'comprehend', 'rekognition']):
            return ServiceCategory.AI_ML
        elif any(security_term in service_lower for security_term in ['iam', 'kms', 'secrets', 'waf']):
            return ServiceCategory.SECURITY
        elif any(mgmt_term in service_lower for mgmt_term in ['cloudwatch', 'cloudtrail', 'config']):
            return ServiceCategory.MANAGEMENT
        elif any(serverless_term in service_lower for serverless_term in ['lambda', 'fargate']):
            return ServiceCategory.SERVERLESS
        elif any(container_term in service_lower for container_term in ['ecs', 'eks', 'container']):
            return ServiceCategory.CONTAINERS
        
        # Log unknown services for future mapping
        logger.warning(f"Unknown AWS service for categorization: {service_name}")
        return ServiceCategory.OTHER
    
    def transform_cost_data(
        self,
        cost_data: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Transform cost data from PostgreSQL format to unified format.
        
        Args:
            cost_data: Cost data from PostgreSQL
            client_id: Client identifier
            
        Returns:
            Transformed cost data
        """
        # Group by date and service
        transformed_data = {}
        
        for record in cost_data:
            date_key = record['usage_date'].strftime('%Y-%m-%d')
            
            if date_key not in transformed_data:
                transformed_data[date_key] = {
                    'client_id': client_id,
                    'provider': CloudProvider.AWS.value,
                    'date': date_key,
                    'total_cost': Decimal('0'),
                    'currency': Currency.USD.value,
                    'services': {},
                    'accounts': {},
                    'regions': {}
                }
            
            # Add service cost
            service_name = record['aws_service']
            cost = Decimal(str(record['cost']))
            category = self.map_aws_service_to_category(service_name)
            
            if service_name not in transformed_data[date_key]['services']:
                transformed_data[date_key]['services'][service_name] = {
                    'service_name': service_name,
                    'unified_category': category.value,
                    'cost': 0,
                    'currency': Currency.USD.value,
                    'provider_specific_data': {
                        'charge_category': record.get('charge_category'),
                        'service_category': record.get('service_category')
                    }
                }
            
            transformed_data[date_key]['services'][service_name]['cost'] += float(cost)
            transformed_data[date_key]['total_cost'] += cost
            
            # Add account cost
            account_id = record['aws_account_id']
            if account_id not in transformed_data[date_key]['accounts']:
                transformed_data[date_key]['accounts'][account_id] = {
                    'account_id': account_id,
                    'account_name': record.get('account_name'),
                    'cost': 0,
                    'currency': Currency.USD.value,
                    'services': {},
                    'regions': {}
                }
            
            transformed_data[date_key]['accounts'][account_id]['cost'] += float(cost)
            
            # Add service to account
            if service_name not in transformed_data[date_key]['accounts'][account_id]['services']:
                transformed_data[date_key]['accounts'][account_id]['services'][service_name] = {
                    'service_name': service_name,
                    'unified_category': category.value,
                    'cost': 0,
                    'currency': Currency.USD.value
                }
            
            transformed_data[date_key]['accounts'][account_id]['services'][service_name]['cost'] += float(cost)
        
        return transformed_data
    
    def normalize_currency(self, amount: Decimal, from_currency: str, to_currency: str = 'USD') -> Decimal:
        """
        Normalize currency amounts (placeholder for future currency conversion).
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Converted amount
        """
        # For now, assume all amounts are in USD
        # In the future, this would integrate with a currency conversion service
        if from_currency.upper() != to_currency.upper():
            logger.warning(f"Currency conversion not implemented: {from_currency} -> {to_currency}")
        
        return amount
    
    def validate_transformation(self, original_data: Dict[str, Any], transformed_data: Dict[str, Any]) -> List[str]:
        """
        Validate that transformation preserved data integrity.
        
        Args:
            original_data: Original data before transformation
            transformed_data: Data after transformation
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check that total costs match
        if 'total_cost' in original_data and 'total_cost' in transformed_data:
            original_total = Decimal(str(original_data['total_cost']))
            transformed_total = Decimal(str(transformed_data['total_cost']))
            
            if abs(original_total - transformed_total) > Decimal('0.01'):
                errors.append(
                    f"Total cost mismatch: original={original_total}, transformed={transformed_total}"
                )
        
        # Check service count
        if 'services' in original_data and 'services' in transformed_data:
            original_services = len(original_data['services'])
            transformed_services = len(transformed_data['services'])
            
            if original_services != transformed_services:
                errors.append(
                    f"Service count mismatch: original={original_services}, transformed={transformed_services}"
                )
        
        # Check account count
        if 'accounts' in original_data and 'accounts' in transformed_data:
            original_accounts = len(original_data['accounts'])
            transformed_accounts = len(transformed_data['accounts'])
            
            if original_accounts != transformed_accounts:
                errors.append(
                    f"Account count mismatch: original={original_accounts}, transformed={transformed_accounts}"
                )
        
        return errors
    
    def get_client_id_for_org(self, org_id: int) -> str:
        """
        Get the client ID for a given organization ID.
        
        Args:
            org_id: Original organization ID
            
        Returns:
            Client ID for the multi-cloud system
        """
        if org_id not in self._org_client_mapping:
            self._org_client_mapping[org_id] = f"client-{uuid.uuid4().hex[:8]}"
        
        return self._org_client_mapping[org_id]
    
    def create_migration_metadata(self, source_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create metadata for migrated records.
        
        Args:
            source_record: Original record from source system
            
        Returns:
            Migration metadata
        """
        return {
            'migrated_at': datetime.utcnow().isoformat(),
            'source_system': 'costshub_postgresql',
            'migration_version': '1.0.0',
            'source_record_id': source_record.get('id'),
            'transformation_applied': True,
            'data_quality_checked': True
        }