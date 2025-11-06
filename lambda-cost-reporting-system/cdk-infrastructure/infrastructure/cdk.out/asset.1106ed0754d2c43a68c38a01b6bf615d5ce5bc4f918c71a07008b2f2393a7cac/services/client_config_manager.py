"""
Client Configuration Manager for DynamoDB operations.

This module provides the ClientConfigManager class that handles all CRUD operations
for client configurations in DynamoDB, including validation and error handling.
"""

import boto3
import logging
from typing import List, Optional, Dict, Any
from botocore.exceptions import ClientError, BotoCoreError
from datetime import datetime

from ..models import ClientConfig, ClientStatus, ReportType
from ..utils import SecureCredentialHandler, create_secure_credential_handler


logger = logging.getLogger(__name__)


class ClientConfigManagerError(Exception):
    """Base exception for ClientConfigManager errors."""
    pass


class ClientNotFoundError(ClientConfigManagerError):
    """Raised when a client is not found."""
    pass


class ClientValidationError(ClientConfigManagerError):
    """Raised when client configuration validation fails."""
    pass


class DynamoDBError(ClientConfigManagerError):
    """Raised when DynamoDB operations fail."""
    pass


class ClientConfigManager:
    """
    Manages client configurations in DynamoDB.
    
    Provides CRUD operations for client configurations with proper error handling,
    validation, and logging.
    """
    
    def __init__(self, table_name: str = "cost-reporting-clients", region: str = "us-east-1", 
                 kms_key_id: Optional[str] = None):
        """
        Initialize the ClientConfigManager.
        
        Args:
            table_name: Name of the DynamoDB table
            region: AWS region for DynamoDB
            kms_key_id: KMS key ID for encryption (if None, encryption is disabled)
        """
        self.table_name = table_name
        self.region = region
        self.kms_key_id = kms_key_id
        self._dynamodb = None
        self._table = None
        self._credential_handler = None
        
        # Initialize encryption if KMS key is provided
        if self.kms_key_id:
            self._credential_handler = create_secure_credential_handler(self.kms_key_id, self.region)
    
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
    
    def get_all_active_clients(self) -> List[ClientConfig]:
        """
        Retrieve all active client configurations.
        
        Returns:
            List of active ClientConfig objects
            
        Raises:
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info("Retrieving all active clients")
            
            response = self.table.query(
                IndexName='status-updated_at-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('status').eq(ClientStatus.ACTIVE.value),
                ScanIndexForward=False  # Sort by updated_at descending
            )
            
            clients = []
            for item in response.get('Items', []):
                try:
                    # Decrypt sensitive data if encryption is enabled
                    if self._credential_handler:
                        item = self._credential_handler.decrypt_client_config(item)
                    
                    client = ClientConfig.from_dict(item)
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
            raise ClientConfigManagerError(error_msg) from e
    
    def get_client_config(self, client_id: str) -> ClientConfig:
        """
        Retrieve a specific client configuration.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            ClientConfig object
            
        Raises:
            ClientNotFoundError: If client is not found
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Retrieving client configuration for {client_id}")
            
            response = self.table.get_item(
                Key={'client_id': client_id}
            )
            
            if 'Item' not in response:
                raise ClientNotFoundError(f"Client {client_id} not found")
            
            item = response['Item']
            
            # Decrypt sensitive data if encryption is enabled
            if self._credential_handler:
                item = self._credential_handler.decrypt_client_config(item)
            
            client = ClientConfig.from_dict(item)
            logger.info(f"Successfully retrieved client {client_id}")
            return client
            
        except ClientNotFoundError:
            raise
        except ClientError as e:
            error_msg = f"DynamoDB error retrieving client {client_id}: {e}"
            logger.error(error_msg)
            raise DynamoDBError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error retrieving client {client_id}: {e}"
            logger.error(error_msg)
            raise ClientConfigManagerError(error_msg) from e
    
    def create_client_config(self, client_config: ClientConfig) -> ClientConfig:
        """
        Create a new client configuration.
        
        Args:
            client_config: ClientConfig object to create
            
        Returns:
            Created ClientConfig object
            
        Raises:
            ClientValidationError: If validation fails
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Creating client configuration for {client_config.client_id}")
            
            # Validate client configuration
            self.validate_client_config(client_config)
            
            # Set creation timestamp
            client_config.created_at = datetime.utcnow()
            client_config.updated_at = datetime.utcnow()
            
            # Convert to DynamoDB format
            item = client_config.to_dict()
            
            # Encrypt sensitive data if encryption is enabled
            if self._credential_handler:
                item = self._credential_handler.encrypt_client_config(item)
            
            # Create item with condition to prevent overwriting
            self.table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(client_id)'
            )
            
            logger.info(f"Successfully created client {client_config.client_id}")
            return client_config
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                error_msg = f"Client {client_config.client_id} already exists"
                logger.error(error_msg)
                raise ClientValidationError(error_msg) from e
            else:
                error_msg = f"DynamoDB error creating client {client_config.client_id}: {e}"
                logger.error(error_msg)
                raise DynamoDBError(error_msg) from e
        except ClientValidationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error creating client {client_config.client_id}: {e}"
            logger.error(error_msg)
            raise ClientConfigManagerError(error_msg) from e
    
    def update_client_config(self, client_config: ClientConfig) -> ClientConfig:
        """
        Update an existing client configuration.
        
        Args:
            client_config: ClientConfig object to update
            
        Returns:
            Updated ClientConfig object
            
        Raises:
            ClientNotFoundError: If client is not found
            ClientValidationError: If validation fails
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Updating client configuration for {client_config.client_id}")
            
            # Validate client configuration
            self.validate_client_config(client_config)
            
            # Set update timestamp
            client_config.updated_at = datetime.utcnow()
            
            # Convert to DynamoDB format
            item = client_config.to_dict()
            
            # Encrypt sensitive data if encryption is enabled
            if self._credential_handler:
                item = self._credential_handler.encrypt_client_config(item)
            
            # Update item with condition to ensure it exists
            self.table.put_item(
                Item=item,
                ConditionExpression='attribute_exists(client_id)'
            )
            
            logger.info(f"Successfully updated client {client_config.client_id}")
            return client_config
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                error_msg = f"Client {client_config.client_id} not found"
                logger.error(error_msg)
                raise ClientNotFoundError(error_msg) from e
            else:
                error_msg = f"DynamoDB error updating client {client_config.client_id}: {e}"
                logger.error(error_msg)
                raise DynamoDBError(error_msg) from e
        except ClientValidationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error updating client {client_config.client_id}: {e}"
            logger.error(error_msg)
            raise ClientConfigManagerError(error_msg) from e
    
    def delete_client_config(self, client_id: str) -> None:
        """
        Delete a client configuration.
        
        Args:
            client_id: Unique identifier for the client
            
        Raises:
            ClientNotFoundError: If client is not found
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Deleting client configuration for {client_id}")
            
            # Delete item with condition to ensure it exists
            self.table.delete_item(
                Key={'client_id': client_id},
                ConditionExpression='attribute_exists(client_id)'
            )
            
            logger.info(f"Successfully deleted client {client_id}")
            
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
            raise ClientConfigManagerError(error_msg) from e
    
    def update_last_execution(self, client_id: str, report_type: ReportType, execution_time: Optional[datetime] = None) -> None:
        """
        Update the last execution timestamp for a client and report type.
        
        Args:
            client_id: Unique identifier for the client
            report_type: Type of report (weekly/monthly)
            execution_time: Execution timestamp (defaults to current time)
            
        Raises:
            ClientNotFoundError: If client is not found
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            if execution_time is None:
                execution_time = datetime.utcnow()
            
            logger.info(f"Updating last execution for client {client_id}, report type {report_type.value}")
            
            # Update only the last_execution and updated_at fields
            self.table.update_item(
                Key={'client_id': client_id},
                UpdateExpression='SET last_execution.#report_type = :execution_time, updated_at = :updated_at',
                ExpressionAttributeNames={
                    '#report_type': report_type.value
                },
                ExpressionAttributeValues={
                    ':execution_time': execution_time.isoformat(),
                    ':updated_at': datetime.utcnow().isoformat()
                },
                ConditionExpression='attribute_exists(client_id)'
            )
            
            logger.info(f"Successfully updated last execution for client {client_id}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                error_msg = f"Client {client_id} not found"
                logger.error(error_msg)
                raise ClientNotFoundError(error_msg) from e
            else:
                error_msg = f"DynamoDB error updating last execution for client {client_id}: {e}"
                logger.error(error_msg)
                raise DynamoDBError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error updating last execution for client {client_id}: {e}"
            logger.error(error_msg)
            raise ClientConfigManagerError(error_msg) from e
    
    def validate_client_config(self, client_config: ClientConfig) -> None:
        """
        Validate a client configuration.
        
        Args:
            client_config: ClientConfig object to validate
            
        Raises:
            ClientValidationError: If validation fails
        """
        try:
            logger.debug(f"Validating client configuration for {client_config.client_id}")
            
            # Basic validation is handled by the dataclass __post_init__ methods
            # Additional business logic validation can be added here
            
            # Validate that at least one report type is enabled
            if not client_config.report_config.weekly_enabled and not client_config.report_config.monthly_enabled:
                raise ClientValidationError("At least one report type (weekly or monthly) must be enabled")
            
            # Validate AWS account IDs are unique
            account_ids = [acc.account_id for acc in client_config.aws_accounts]
            if len(account_ids) != len(set(account_ids)):
                raise ClientValidationError("Duplicate AWS account IDs found")
            
            logger.debug(f"Client configuration validation passed for {client_config.client_id}")
            
        except ValueError as e:
            raise ClientValidationError(f"Validation error: {e}") from e
        except Exception as e:
            raise ClientValidationError(f"Unexpected validation error: {e}") from e
    
    def validate_client_access(self, client_config: ClientConfig) -> bool:
        """
        Validate that the client's AWS credentials are working.
        
        Args:
            client_config: ClientConfig object to validate
            
        Returns:
            True if all accounts are accessible, False otherwise
        """
        logger.info(f"Validating AWS access for client {client_config.client_id}")
        
        all_valid = True
        for account in client_config.aws_accounts:
            try:
                # Get decrypted credentials (they should already be decrypted when ClientConfig was created)
                access_key_id = account.access_key_id
                secret_access_key = account.secret_access_key
                
                # Create a session with the account credentials
                session = boto3.Session(
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    region_name=account.region
                )
                
                # Test access by calling STS get_caller_identity
                sts = session.client('sts')
                response = sts.get_caller_identity()
                
                # Verify the account ID matches
                if response.get('Account') != account.account_id:
                    logger.error(f"Account ID mismatch for {account.account_id}: expected {account.account_id}, got {response.get('Account')}")
                    all_valid = False
                else:
                    logger.debug(f"Successfully validated access to account {account.account_id}")
                    
            except Exception as e:
                logger.error(f"Failed to validate access to account {account.account_id}: {e}")
                all_valid = False
        
        logger.info(f"AWS access validation for client {client_config.client_id}: {'passed' if all_valid else 'failed'}")
        return all_valid
    
    def get_clients_by_status(self, status: ClientStatus) -> List[ClientConfig]:
        """
        Retrieve clients by status.
        
        Args:
            status: Client status to filter by
            
        Returns:
            List of ClientConfig objects with the specified status
            
        Raises:
            DynamoDBError: If DynamoDB operation fails
        """
        try:
            logger.info(f"Retrieving clients with status {status.value}")
            
            response = self.table.query(
                IndexName='status-updated_at-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('status').eq(status.value),
                ScanIndexForward=False  # Sort by updated_at descending
            )
            
            clients = []
            for item in response.get('Items', []):
                try:
                    # Decrypt sensitive data if encryption is enabled
                    if self._credential_handler:
                        item = self._credential_handler.decrypt_client_config(item)
                    
                    client = ClientConfig.from_dict(item)
                    clients.append(client)
                except Exception as e:
                    logger.error(f"Failed to parse client {item.get('client_id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(clients)} clients with status {status.value}")
            return clients
            
        except ClientError as e:
            error_msg = f"DynamoDB error retrieving clients by status {status.value}: {e}"
            logger.error(error_msg)
            raise DynamoDBError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error retrieving clients by status {status.value}: {e}"
            logger.error(error_msg)
            raise ClientConfigManagerError(error_msg) from e