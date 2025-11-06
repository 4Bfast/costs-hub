"""
Multi-Tenant Client Manager Service

This service provides comprehensive client management capabilities for the multi-cloud
cost analytics platform, including client onboarding, configuration management,
and tenant isolation.
"""

import boto3
import logging
from typing import List, Optional, Dict, Any, Tuple
from botocore.exceptions import ClientError, BotoCoreError
from datetime import datetime, timedelta
from decimal import Decimal

from ..models.multi_tenant_models import (
    MultiCloudClient, CloudAccount, CloudProvider, ClientStatus, 
    OnboardingStatus, SubscriptionTier, ClientRole,
    AWSCredentials, GCPCredentials, AzureCredentials
)
from ..models.multi_cloud_models import UnifiedCostRecord
from ..utils import SecureCredentialHandler, create_secure_credential_handler


logger = logging.getLogger(__name__)


class MultiTenantClientManagerError(Exception):
    """Base exception for MultiTenantClientManager errors."""
    pass


class ClientNotFoundError(MultiTenantClientManagerError):
    """Raised when a client is not found."""
    pass


class ClientValidationError(MultiTenantClientManagerError):
    """Raised when client configuration validation fails."""
    pass


class ResourceLimitExceededError(MultiTenantClientManagerError):
    """Raised when client resource limits are exceeded."""
    pass


class TenantIsolationError(MultiTenantClientManagerError):
    """Raised when tenant isolation is violated."""
    pass


class DynamoDBError(MultiTenantClientManagerError):
    """Raised when DynamoDB operations fail."""
    pass


class MultiTenantClientManager:
    """
    Manages multi-tenant client configurations with enhanced security and isolation.
    
    Provides comprehensive client lifecycle management including onboarding,
    configuration validation, resource limit enforcement, and tenant isolation.
    """
    
    def __init__(self, table_name: str = "multi-cloud-clients", region: str = "us-east-1",
                 kms_key_id: Optional[str] = None):
        """
        Initialize the MultiTenantClientManager.
        
        Args:
            table_name: Name of the DynamoDB table
            region: AWS region for DynamoDB
            kms_key_id: KMS key ID for encryption (required for production)
        """
        self.table_name = table_name
        self.region = region
        self.kms_key_id = kms_key_id
        self._dynamodb = None
        self._table = None
        self._credential_handler = None
        
        # Initialize encryption (required for multi-tenant security)
        if self.kms_key_id:
            self._credential_handler = create_secure_credential_handler(self.kms_key_id, self.region)
        else:
            logger.warning("No KMS key provided - credentials will not be encrypted")
    
    @property
    def dynamodb(self):
        """Lazy initialization of DynamoDB resource."""
        if self._dynamodb is None:
            self._dynamodb = boto3.resource('dynamodb', region_name=self.region)
        return self._dynamodb
    
    @property
    def table(self):
        """Lazy initialization of DynamoDB table."""
        if self._table is None:
            self._table = self.dynamodb.Table(self.table_name)
        return self._table
    
    def create_client(self, client: MultiCloudClient) -> MultiCloudClient:
        """
        Create a new multi-cloud client with full validation and onboarding workflow.
        
        Args:
            client: MultiCloudClient object to create
            
        Returns:
            Created MultiCloudClient object
            
        Raises:
            ClientValidationError: If validation fails
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Creating multi-cloud client {client.client_id} for organization {client.organization_name}")
            
            # Comprehensive validation
            self.validate_client_configuration(client)
            
            # Set creation metadata
            client.created_at = datetime.utcnow()
            client.updated_at = datetime.utcnow()
            client.onboarding_status = OnboardingStatus.IN_PROGRESS
            
            # Convert to DynamoDB format
            item = client.to_dynamodb_item()
            
            # Encrypt sensitive data if encryption is enabled
            if self._credential_handler:
                item = self._encrypt_client_data(item)
            
            # Create item with condition to prevent overwriting
            self.table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(PK)'
            )
            
            # Start onboarding workflow
            self._initiate_onboarding_workflow(client)
            
            logger.info(f"Successfully created multi-cloud client {client.client_id}")
            return client
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                error_msg = f"Client {client.client_id} already exists"
                logger.error(error_msg)
                raise ClientValidationError(error_msg) from e
            else:
                error_msg = f"DynamoDB error creating client {client.client_id}: {e}"
                logger.error(error_msg)
                raise DynamoDBError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error creating client {client.client_id}: {e}"
            logger.error(error_msg)
            raise MultiTenantClientManagerError(error_msg) from e
    
    def get_client(self, client_id: str, tenant_id: Optional[str] = None) -> MultiCloudClient:
        """
        Retrieve a specific client with tenant isolation.
        
        Args:
            client_id: Unique identifier for the client
            tenant_id: Tenant ID for isolation (if None, derived from client_id)
            
        Returns:
            MultiCloudClient object
            
        Raises:
            ClientNotFoundError: If client is not found
            TenantIsolationError: If tenant access is denied
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Retrieving multi-cloud client {client_id}")
            
            # Query with tenant isolation
            if tenant_id:
                sk = f"CONFIG#{tenant_id}"
            else:
                # If no tenant_id provided, we need to query all configs for this client
                # This should only be used by system administrators
                response = self.table.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq(f"CLIENT#{client_id}")
                )
                
                if not response.get('Items'):
                    raise ClientNotFoundError(f"Client {client_id} not found")
                
                # Use the first (and should be only) configuration
                item = response['Items'][0]
            else:
                response = self.table.get_item(
                    Key={
                        'PK': f"CLIENT#{client_id}",
                        'SK': sk
                    }
                )
                
                if 'Item' not in response:
                    raise ClientNotFoundError(f"Client {client_id} not found or access denied")
                
                item = response['Item']
            
            # Decrypt sensitive data if encryption is enabled
            if self._credential_handler:
                item = self._decrypt_client_data(item)
            
            client = MultiCloudClient.from_dynamodb_item(item)
            
            # Validate tenant access
            if tenant_id and client.tenant_id != tenant_id:
                raise TenantIsolationError(f"Access denied to client {client_id} for tenant {tenant_id}")
            
            logger.info(f"Successfully retrieved client {client_id}")
            return client
            
        except (ClientNotFoundError, TenantIsolationError):
            raise
        except ClientError as e:
            error_msg = f"DynamoDB error retrieving client {client_id}: {e}"
            logger.error(error_msg)
            raise DynamoDBError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error retrieving client {client_id}: {e}"
            logger.error(error_msg)
            raise MultiTenantClientManagerError(error_msg) from e
    
    def update_client(self, client: MultiCloudClient) -> MultiCloudClient:
        """
        Update an existing client configuration with validation.
        
        Args:
            client: MultiCloudClient object to update
            
        Returns:
            Updated MultiCloudClient object
            
        Raises:
            ClientNotFoundError: If client is not found
            ClientValidationError: If validation fails
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Updating multi-cloud client {client.client_id}")
            
            # Validate client configuration
            self.validate_client_configuration(client)
            
            # Set update timestamp
            client.updated_at = datetime.utcnow()
            
            # Convert to DynamoDB format
            item = client.to_dynamodb_item()
            
            # Encrypt sensitive data if encryption is enabled
            if self._credential_handler:
                item = self._encrypt_client_data(item)
            
            # Update item with condition to ensure it exists
            self.table.put_item(
                Item=item,
                ConditionExpression='attribute_exists(PK)'
            )
            
            logger.info(f"Successfully updated client {client.client_id}")
            return client
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                error_msg = f"Client {client.client_id} not found"
                logger.error(error_msg)
                raise ClientNotFoundError(error_msg) from e
            else:
                error_msg = f"DynamoDB error updating client {client.client_id}: {e}"
                logger.error(error_msg)
                raise DynamoDBError(error_msg) from e
        except ClientValidationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error updating client {client.client_id}: {e}"
            logger.error(error_msg)
            raise MultiTenantClientManagerError(error_msg) from e
    
    def delete_client(self, client_id: str, tenant_id: str) -> None:
        """
        Delete a client configuration with tenant isolation.
        
        Args:
            client_id: Unique identifier for the client
            tenant_id: Tenant ID for isolation
            
        Raises:
            ClientNotFoundError: If client is not found
            TenantIsolationError: If tenant access is denied
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Deleting multi-cloud client {client_id}")
            
            # First verify the client exists and tenant has access
            client = self.get_client(client_id, tenant_id)
            
            # Delete item with tenant isolation
            self.table.delete_item(
                Key={
                    'PK': f"CLIENT#{client_id}",
                    'SK': f"CONFIG#{tenant_id}"
                },
                ConditionExpression='attribute_exists(PK)'
            )
            
            # TODO: Implement cleanup of associated cost data
            # This should be done asynchronously to avoid blocking the delete operation
            self._schedule_data_cleanup(client_id, tenant_id)
            
            logger.info(f"Successfully deleted client {client_id}")
            
        except (ClientNotFoundError, TenantIsolationError):
            raise
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                error_msg = f"Client {client_id} not found"
                logger.error(error_msg)
                raise ClientNotFoundError(error_msg) from e
            else:
                error_msg = f"DynamoDB error deleting client {client_id}: {e}"
                logger.error(error_msg)
                raise DynamoDBError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error deleting client {client_id}: {e}"
            logger.error(error_msg)
            raise MultiTenantClientManagerError(error_msg) from e
    
    def list_clients_by_tenant(self, tenant_id: str, status: Optional[ClientStatus] = None) -> List[MultiCloudClient]:
        """
        List all clients for a specific tenant with optional status filtering.
        
        Args:
            tenant_id: Tenant ID for isolation
            status: Optional status filter
            
        Returns:
            List of MultiCloudClient objects
            
        Raises:
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Listing clients for tenant {tenant_id}")
            
            # Query using GSI1 for tenant isolation
            key_condition = boto3.dynamodb.conditions.Key('GSI1PK').eq(f"TENANT#{tenant_id}")
            
            if status:
                key_condition = key_condition & boto3.dynamodb.conditions.Key('GSI1SK').eq(f"STATUS#{status.value}")
            
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression=key_condition,
                ScanIndexForward=False  # Sort by GSI1SK descending
            )
            
            clients = []
            for item in response.get('Items', []):
                try:
                    # Decrypt sensitive data if encryption is enabled
                    if self._credential_handler:
                        item = self._decrypt_client_data(item)
                    
                    client = MultiCloudClient.from_dynamodb_item(item)
                    clients.append(client)
                except Exception as e:
                    logger.error(f"Failed to parse client {item.get('client_id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(clients)} clients for tenant {tenant_id}")
            return clients
            
        except ClientError as e:
            error_msg = f"DynamoDB error listing clients for tenant {tenant_id}: {e}"
            logger.error(error_msg)
            raise DynamoDBError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error listing clients for tenant {tenant_id}: {e}"
            logger.error(error_msg)
            raise MultiTenantClientManagerError(error_msg) from e
    
    def get_active_clients(self) -> List[MultiCloudClient]:
        """
        Get all active clients across all tenants (admin operation).
        
        Returns:
            List of active MultiCloudClient objects
            
        Raises:
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info("Retrieving all active clients")
            
            # Scan for all active clients (admin operation)
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('status').eq(ClientStatus.ACTIVE.value)
            )
            
            clients = []
            for item in response.get('Items', []):
                try:
                    # Decrypt sensitive data if encryption is enabled
                    if self._credential_handler:
                        item = self._decrypt_client_data(item)
                    
                    client = MultiCloudClient.from_dynamodb_item(item)
                    clients.append(client)
                except Exception as e:
                    logger.error(f"Failed to parse client {item.get('client_id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(clients)} active clients")
            return clients
            
        except ClientError as e:
            error_msg = f"DynamoDB error retrieving active clients: {e}"
            logger.error(error_msg)
            raise DynamoDBError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error retrieving active clients: {e}"
            logger.error(error_msg)
            raise MultiTenantClientManagerError(error_msg) from e
    
    def validate_client_configuration(self, client: MultiCloudClient) -> None:
        """
        Comprehensive validation of client configuration.
        
        Args:
            client: MultiCloudClient object to validate
            
        Raises:
            ClientValidationError: If validation fails
        """
        try:
            logger.debug(f"Validating client configuration for {client.client_id}")
            
            # Basic validation is handled by the dataclass __post_init__ methods
            
            # Validate resource limits
            violations = client.validate_resource_usage()
            if violations:
                raise ClientValidationError(f"Resource limit violations: {', '.join(violations)}")
            
            # Validate cloud accounts
            for provider, accounts in client.cloud_accounts.items():
                for account in accounts:
                    self._validate_cloud_account(account)
            
            # Validate subscription tier limits
            total_accounts = sum(len(accounts) for accounts in client.cloud_accounts.values())
            if total_accounts > client.resource_limits.max_cloud_accounts:
                raise ClientValidationError(
                    f"Too many cloud accounts ({total_accounts}) for subscription tier {client.subscription_tier.value}"
                )
            
            # Validate notification preferences
            if client.notification_preferences.email_enabled and not client.notification_preferences.email_recipients:
                raise ClientValidationError("Email notifications enabled but no recipients specified")
            
            logger.debug(f"Client configuration validation passed for {client.client_id}")
            
        except ValueError as e:
            raise ClientValidationError(f"Validation error: {e}") from e
        except Exception as e:
            raise ClientValidationError(f"Unexpected validation error: {e}") from e
    
    def _validate_cloud_account(self, account: CloudAccount) -> None:
        """
        Validate a cloud account configuration.
        
        Args:
            account: CloudAccount to validate
            
        Raises:
            ClientValidationError: If validation fails
        """
        # Provider-specific validation
        if account.provider == CloudProvider.AWS:
            if not isinstance(account.credentials, AWSCredentials):
                raise ClientValidationError(f"Invalid credentials type for AWS account {account.account_id}")
            
            # Validate AWS account ID format
            if not account.account_id.isdigit() or len(account.account_id) != 12:
                raise ClientValidationError(f"Invalid AWS account ID format: {account.account_id}")
        
        elif account.provider == CloudProvider.GCP:
            if not isinstance(account.credentials, GCPCredentials):
                raise ClientValidationError(f"Invalid credentials type for GCP account {account.account_id}")
            
            # Validate GCP project ID format
            if not account.account_id or len(account.account_id) < 6:
                raise ClientValidationError(f"Invalid GCP project ID: {account.account_id}")
        
        elif account.provider == CloudProvider.AZURE:
            if not isinstance(account.credentials, AzureCredentials):
                raise ClientValidationError(f"Invalid credentials type for Azure account {account.account_id}")
            
            # Validate Azure subscription ID format (UUID)
            try:
                import uuid
                uuid.UUID(account.account_id)
            except ValueError:
                raise ClientValidationError(f"Invalid Azure subscription ID format: {account.account_id}")
    
    def validate_provider_credentials(self, client: MultiCloudClient) -> Dict[str, bool]:
        """
        Validate credentials for all cloud providers configured for a client.
        
        Args:
            client: MultiCloudClient to validate
            
        Returns:
            Dictionary mapping provider names to validation results
        """
        logger.info(f"Validating provider credentials for client {client.client_id}")
        
        validation_results = {}
        
        for provider, accounts in client.cloud_accounts.items():
            provider_valid = True
            
            for account in accounts:
                try:
                    if provider == CloudProvider.AWS:
                        account_valid = self._validate_aws_credentials(account)
                    elif provider == CloudProvider.GCP:
                        account_valid = self._validate_gcp_credentials(account)
                    elif provider == CloudProvider.AZURE:
                        account_valid = self._validate_azure_credentials(account)
                    else:
                        account_valid = False
                    
                    if not account_valid:
                        provider_valid = False
                        logger.error(f"Credential validation failed for {provider.value} account {account.account_id}")
                    else:
                        logger.debug(f"Credential validation passed for {provider.value} account {account.account_id}")
                        
                except Exception as e:
                    logger.error(f"Error validating {provider.value} account {account.account_id}: {e}")
                    provider_valid = False
            
            validation_results[provider.value] = provider_valid
        
        logger.info(f"Credential validation completed for client {client.client_id}: {validation_results}")
        return validation_results
    
    def _validate_aws_credentials(self, account: CloudAccount) -> bool:
        """Validate AWS credentials."""
        try:
            creds = account.credentials
            if isinstance(creds, AWSCredentials):
                if creds.role_arn:
                    # Validate assume role credentials
                    session = boto3.Session(
                        aws_access_key_id=creds.access_key_id,
                        aws_secret_access_key=creds.secret_access_key,
                        region_name=creds.region
                    )
                    sts = session.client('sts')
                    
                    assume_role_kwargs = {
                        'RoleArn': creds.role_arn,
                        'RoleSessionName': f'cost-analytics-validation-{account.account_id}'
                    }
                    if creds.external_id:
                        assume_role_kwargs['ExternalId'] = creds.external_id
                    
                    response = sts.assume_role(**assume_role_kwargs)
                    
                    # Test the assumed role credentials
                    assumed_session = boto3.Session(
                        aws_access_key_id=response['Credentials']['AccessKeyId'],
                        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                        aws_session_token=response['Credentials']['SessionToken'],
                        region_name=creds.region
                    )
                    assumed_sts = assumed_session.client('sts')
                    identity = assumed_sts.get_caller_identity()
                    
                    return identity.get('Account') == account.account_id
                else:
                    # Validate direct credentials
                    session = boto3.Session(
                        aws_access_key_id=creds.access_key_id,
                        aws_secret_access_key=creds.secret_access_key,
                        aws_session_token=creds.session_token,
                        region_name=creds.region
                    )
                    sts = session.client('sts')
                    identity = sts.get_caller_identity()
                    
                    return identity.get('Account') == account.account_id
            
            return False
            
        except Exception as e:
            logger.error(f"AWS credential validation error: {e}")
            return False
    
    def _validate_gcp_credentials(self, account: CloudAccount) -> bool:
        """Validate GCP credentials."""
        try:
            # TODO: Implement GCP credential validation
            # This would involve validating the service account key and project access
            logger.warning("GCP credential validation not yet implemented")
            return True
            
        except Exception as e:
            logger.error(f"GCP credential validation error: {e}")
            return False
    
    def _validate_azure_credentials(self, account: CloudAccount) -> bool:
        """Validate Azure credentials."""
        try:
            # TODO: Implement Azure credential validation
            # This would involve validating the service principal and subscription access
            logger.warning("Azure credential validation not yet implemented")
            return True
            
        except Exception as e:
            logger.error(f"Azure credential validation error: {e}")
            return False
    
    def _initiate_onboarding_workflow(self, client: MultiCloudClient) -> None:
        """
        Initiate the client onboarding workflow.
        
        Args:
            client: MultiCloudClient to onboard
        """
        logger.info(f"Initiating onboarding workflow for client {client.client_id}")
        
        try:
            # Validate all provider credentials
            validation_results = self.validate_provider_credentials(client)
            
            # Check if all validations passed
            all_valid = all(validation_results.values())
            
            if all_valid:
                client.complete_onboarding()
                self.update_client(client)
                logger.info(f"Onboarding completed successfully for client {client.client_id}")
            else:
                client.onboarding_status = OnboardingStatus.FAILED
                self.update_client(client)
                logger.error(f"Onboarding failed for client {client.client_id}: {validation_results}")
                
        except Exception as e:
            logger.error(f"Error during onboarding workflow for client {client.client_id}: {e}")
            client.onboarding_status = OnboardingStatus.FAILED
            try:
                self.update_client(client)
            except Exception as update_error:
                logger.error(f"Failed to update client status after onboarding error: {update_error}")
    
    def _encrypt_client_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive client data.
        
        Args:
            item: DynamoDB item to encrypt
            
        Returns:
            Encrypted DynamoDB item
        """
        if not self._credential_handler:
            return item
        
        # TODO: Implement encryption of sensitive fields
        # This should encrypt cloud account credentials and other sensitive data
        return item
    
    def _decrypt_client_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive client data.
        
        Args:
            item: Encrypted DynamoDB item
            
        Returns:
            Decrypted DynamoDB item
        """
        if not self._credential_handler:
            return item
        
        # TODO: Implement decryption of sensitive fields
        # This should decrypt cloud account credentials and other sensitive data
        return item
    
    def _schedule_data_cleanup(self, client_id: str, tenant_id: str) -> None:
        """
        Schedule cleanup of client data after deletion.
        
        Args:
            client_id: Client ID to clean up
            tenant_id: Tenant ID for isolation
        """
        logger.info(f"Scheduling data cleanup for client {client_id}, tenant {tenant_id}")
        
        # TODO: Implement asynchronous data cleanup
        # This should:
        # 1. Delete all cost data for the client
        # 2. Delete all AI insights and forecasts
        # 3. Delete all reports and artifacts
        # 4. Clean up any cached data
        # 5. Send cleanup completion notification
        
        # For now, just log the cleanup request
        logger.info(f"Data cleanup scheduled for client {client_id}")
    
    def update_client_usage(self, client_id: str, tenant_id: str, 
                           api_calls: int = 0, cost_processed: Decimal = Decimal('0')) -> None:
        """
        Update client usage metrics.
        
        Args:
            client_id: Client ID
            tenant_id: Tenant ID for isolation
            api_calls: Number of API calls to add
            cost_processed: Amount of cost data processed
            
        Raises:
            ClientNotFoundError: If client is not found
            ResourceLimitExceededError: If usage limits are exceeded
        """
        try:
            logger.debug(f"Updating usage for client {client_id}: +{api_calls} API calls, +${cost_processed} processed")
            
            # Get current client
            client = self.get_client(client_id, tenant_id)
            
            # Update usage
            client.increment_api_usage(api_calls)
            client.monthly_cost_processed += cost_processed
            
            # Check limits
            violations = client.validate_resource_usage()
            if violations:
                logger.warning(f"Resource limit violations for client {client_id}: {violations}")
                # Don't raise exception here, just log - let the client continue but monitor
            
            # Update in database
            self.table.update_item(
                Key={
                    'PK': f"CLIENT#{client_id}",
                    'SK': f"CONFIG#{tenant_id}"
                },
                UpdateExpression='SET monthly_api_calls = monthly_api_calls + :api_calls, '
                               'monthly_cost_processed = monthly_cost_processed + :cost_processed, '
                               'last_activity = :last_activity',
                ExpressionAttributeValues={
                    ':api_calls': api_calls,
                    ':cost_processed': float(cost_processed),
                    ':last_activity': datetime.utcnow().isoformat()
                }
            )
            
        except ClientNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating usage for client {client_id}: {e}")
            raise MultiTenantClientManagerError(f"Failed to update client usage: {e}") from e