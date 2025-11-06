"""
Tenant Data Isolation Service

This service provides comprehensive data isolation capabilities for multi-tenant
cost analytics, including tenant-based data partitioning, access control,
and resource allocation management.
"""

import boto3
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from ..models.multi_tenant_models import MultiCloudClient, ResourceLimits, SubscriptionTier
from ..models.multi_cloud_models import UnifiedCostRecord, CloudProvider


logger = logging.getLogger(__name__)


class IsolationLevel(Enum):
    """Data isolation levels."""
    STRICT = "strict"      # Complete isolation with separate resources
    STANDARD = "standard"  # Logical isolation with shared resources
    BASIC = "basic"        # Basic tenant separation


class AccessPattern(Enum):
    """Data access patterns for optimization."""
    READ_HEAVY = "read_heavy"
    WRITE_HEAVY = "write_heavy"
    BALANCED = "balanced"
    ANALYTICAL = "analytical"


@dataclass
class TenantPartition:
    """Tenant data partition configuration."""
    tenant_id: str
    partition_key: str
    isolation_level: IsolationLevel
    resource_allocation: Dict[str, Any]
    access_patterns: List[AccessPattern]
    created_at: datetime
    last_accessed: Optional[datetime] = None
    data_size_bytes: int = 0
    record_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'tenant_id': self.tenant_id,
            'partition_key': self.partition_key,
            'isolation_level': self.isolation_level.value,
            'resource_allocation': self.resource_allocation,
            'access_patterns': [p.value for p in self.access_patterns],
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'data_size_bytes': self.data_size_bytes,
            'record_count': self.record_count
        }


@dataclass
class ResourceQuota:
    """Resource quota for a tenant."""
    tenant_id: str
    max_storage_gb: int
    max_read_capacity: int
    max_write_capacity: int
    max_concurrent_queries: int
    max_data_retention_days: int
    current_usage: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'tenant_id': self.tenant_id,
            'max_storage_gb': self.max_storage_gb,
            'max_read_capacity': self.max_read_capacity,
            'max_write_capacity': self.max_write_capacity,
            'max_concurrent_queries': self.max_concurrent_queries,
            'max_data_retention_days': self.max_data_retention_days,
            'current_usage': self.current_usage
        }


class TenantDataIsolationError(Exception):
    """Base exception for tenant data isolation errors."""
    pass


class TenantNotFoundError(TenantDataIsolationError):
    """Raised when tenant is not found."""
    pass


class AccessDeniedError(TenantDataIsolationError):
    """Raised when tenant access is denied."""
    pass


class ResourceQuotaExceededError(TenantDataIsolationError):
    """Raised when tenant resource quota is exceeded."""
    pass


class DataIsolationViolationError(TenantDataIsolationError):
    """Raised when data isolation is violated."""
    pass


class TenantDataIsolationService:
    """
    Provides comprehensive tenant data isolation for multi-cloud cost analytics.
    
    Manages tenant partitioning, resource allocation, access control, and
    data lifecycle policies with strict isolation guarantees.
    """
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the TenantDataIsolationService.
        
        Args:
            region: AWS region for DynamoDB operations
        """
        self.region = region
        self._dynamodb = None
        self._cost_table = None
        self._timeseries_table = None
        self._partition_table = None
        self._quota_table = None
        
        # Tenant partition cache
        self._partition_cache: Dict[str, TenantPartition] = {}
        self._quota_cache: Dict[str, ResourceQuota] = {}
        
        # Table names
        self.cost_table_name = "cost-analytics-data"
        self.timeseries_table_name = "cost-analytics-timeseries"
        self.partition_table_name = "tenant-partitions"
        self.quota_table_name = "tenant-quotas"
    
    @property
    def dynamodb(self):
        """Lazy initialization of DynamoDB resource."""
        if self._dynamodb is None:
            self._dynamodb = boto3.resource('dynamodb', region_name=self.region)
        return self._dynamodb
    
    @property
    def cost_table(self):
        """Lazy initialization of cost data table."""
        if self._cost_table is None:
            self._cost_table = self.dynamodb.Table(self.cost_table_name)
        return self._cost_table
    
    @property
    def timeseries_table(self):
        """Lazy initialization of timeseries table."""
        if self._timeseries_table is None:
            self._timeseries_table = self.dynamodb.Table(self.timeseries_table_name)
        return self._timeseries_table
    
    @property
    def partition_table(self):
        """Lazy initialization of partition metadata table."""
        if self._partition_table is None:
            self._partition_table = self.dynamodb.Table(self.partition_table_name)
        return self._partition_table
    
    @property
    def quota_table(self):
        """Lazy initialization of quota table."""
        if self._quota_table is None:
            self._quota_table = self.dynamodb.Table(self.quota_table_name)
        return self._quota_table
    
    def create_tenant_partition(self, client: MultiCloudClient) -> TenantPartition:
        """
        Create a new tenant partition with appropriate isolation level.
        
        Args:
            client: MultiCloudClient to create partition for
            
        Returns:
            Created TenantPartition
            
        Raises:
            TenantDataIsolationError: If partition creation fails
        """
        try:
            logger.info(f"Creating tenant partition for client {client.client_id}")
            
            # Determine isolation level based on subscription tier
            isolation_level = self._determine_isolation_level(client.subscription_tier)
            
            # Create partition configuration
            partition = TenantPartition(
                tenant_id=client.tenant_id,
                partition_key=f"TENANT#{client.tenant_id}",
                isolation_level=isolation_level,
                resource_allocation=self._calculate_resource_allocation(client),
                access_patterns=[AccessPattern.BALANCED],  # Default, can be optimized later
                created_at=datetime.utcnow()
            )
            
            # Store partition metadata
            self.partition_table.put_item(
                Item=partition.to_dict(),
                ConditionExpression='attribute_not_exists(tenant_id)'
            )
            
            # Create resource quota
            quota = self._create_resource_quota(client)
            self.quota_table.put_item(
                Item=quota.to_dict(),
                ConditionExpression='attribute_not_exists(tenant_id)'
            )
            
            # Cache the partition and quota
            self._partition_cache[client.tenant_id] = partition
            self._quota_cache[client.tenant_id] = quota
            
            logger.info(f"Successfully created tenant partition for {client.tenant_id} with {isolation_level.value} isolation")
            return partition
            
        except Exception as e:
            logger.error(f"Failed to create tenant partition for {client.client_id}: {e}")
            raise TenantDataIsolationError(f"Partition creation failed: {e}") from e
    
    def get_tenant_partition(self, tenant_id: str) -> TenantPartition:
        """
        Get tenant partition configuration.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            TenantPartition configuration
            
        Raises:
            TenantNotFoundError: If tenant partition is not found
        """
        try:
            # Check cache first
            if tenant_id in self._partition_cache:
                return self._partition_cache[tenant_id]
            
            # Query from database
            response = self.partition_table.get_item(
                Key={'tenant_id': tenant_id}
            )
            
            if 'Item' not in response:
                raise TenantNotFoundError(f"Tenant partition not found: {tenant_id}")
            
            item = response['Item']
            partition = TenantPartition(
                tenant_id=item['tenant_id'],
                partition_key=item['partition_key'],
                isolation_level=IsolationLevel(item['isolation_level']),
                resource_allocation=item['resource_allocation'],
                access_patterns=[AccessPattern(p) for p in item['access_patterns']],
                created_at=datetime.fromisoformat(item['created_at']),
                last_accessed=datetime.fromisoformat(item['last_accessed']) if item.get('last_accessed') else None,
                data_size_bytes=item.get('data_size_bytes', 0),
                record_count=item.get('record_count', 0)
            )
            
            # Cache the partition
            self._partition_cache[tenant_id] = partition
            return partition
            
        except TenantNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting tenant partition for {tenant_id}: {e}")
            raise TenantDataIsolationError(f"Failed to get tenant partition: {e}") from e
    
    def validate_tenant_access(self, tenant_id: str, operation: str, resource_type: str) -> bool:
        """
        Validate tenant access to a specific resource and operation.
        
        Args:
            tenant_id: Tenant ID
            operation: Operation type (read, write, delete, etc.)
            resource_type: Resource type (cost_data, timeseries, etc.)
            
        Returns:
            True if access is allowed, False otherwise
            
        Raises:
            TenantNotFoundError: If tenant is not found
            AccessDeniedError: If access is denied
        """
        try:
            logger.debug(f"Validating tenant access: {tenant_id}, {operation}, {resource_type}")
            
            # Get tenant partition
            partition = self.get_tenant_partition(tenant_id)
            
            # Get resource quota
            quota = self.get_tenant_quota(tenant_id)
            
            # Check basic access permissions
            if not self._check_basic_permissions(partition, operation, resource_type):
                raise AccessDeniedError(f"Access denied for tenant {tenant_id} to {operation} {resource_type}")
            
            # Check resource quotas
            if not self._check_resource_quotas(quota, operation, resource_type):
                raise ResourceQuotaExceededError(f"Resource quota exceeded for tenant {tenant_id}")
            
            # Update last accessed time
            partition.last_accessed = datetime.utcnow()
            self._update_partition_metadata(partition)
            
            return True
            
        except (TenantNotFoundError, AccessDeniedError, ResourceQuotaExceededError):
            raise
        except Exception as e:
            logger.error(f"Error validating tenant access for {tenant_id}: {e}")
            raise TenantDataIsolationError(f"Access validation failed: {e}") from e
    
    def get_tenant_data_key(self, tenant_id: str, data_type: str, additional_keys: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Generate tenant-specific data keys for DynamoDB operations.
        
        Args:
            tenant_id: Tenant ID
            data_type: Type of data (cost, timeseries, etc.)
            additional_keys: Additional key components
            
        Returns:
            Dictionary containing partition and sort keys
            
        Raises:
            TenantNotFoundError: If tenant is not found
        """
        try:
            partition = self.get_tenant_partition(tenant_id)
            
            # Base partition key
            pk = partition.partition_key
            
            # Generate sort key based on data type
            if data_type == "cost":
                sk_prefix = "COST#"
            elif data_type == "timeseries":
                sk_prefix = "TIMESERIES#"
            elif data_type == "insights":
                sk_prefix = "INSIGHTS#"
            else:
                sk_prefix = f"{data_type.upper()}#"
            
            # Add additional key components
            sk_components = [sk_prefix]
            if additional_keys:
                for key, value in additional_keys.items():
                    sk_components.append(f"{key}#{value}")
            
            sk = "".join(sk_components)
            
            return {
                'PK': pk,
                'SK': sk
            }
            
        except TenantNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error generating tenant data key for {tenant_id}: {e}")
            raise TenantDataIsolationError(f"Data key generation failed: {e}") from e
    
    def store_tenant_cost_data(self, tenant_id: str, cost_record: UnifiedCostRecord) -> None:
        """
        Store cost data with tenant isolation.
        
        Args:
            tenant_id: Tenant ID
            cost_record: Cost record to store
            
        Raises:
            AccessDeniedError: If access is denied
            ResourceQuotaExceededError: If quota is exceeded
        """
        try:
            logger.debug(f"Storing cost data for tenant {tenant_id}")
            
            # Validate tenant access
            self.validate_tenant_access(tenant_id, "write", "cost_data")
            
            # Generate tenant-specific keys
            keys = self.get_tenant_data_key(
                tenant_id, 
                "cost",
                {
                    'provider': cost_record.provider.value,
                    'date': cost_record.date
                }
            )
            
            # Prepare DynamoDB item with tenant isolation
            item = cost_record.to_dynamodb_item()
            item['PK'] = keys['PK']
            item['SK'] = keys['SK']
            
            # Add tenant metadata
            item['tenant_id'] = tenant_id
            item['isolation_level'] = self.get_tenant_partition(tenant_id).isolation_level.value
            
            # Store with conditional check to prevent cross-tenant data leakage
            self.cost_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(PK) OR begins_with(PK, :tenant_prefix)',
                ExpressionAttributeValues={
                    ':tenant_prefix': f"TENANT#{tenant_id}"
                }
            )
            
            # Update tenant usage metrics
            self._update_tenant_usage(tenant_id, "cost_data", 1, len(str(item)))
            
            logger.debug(f"Successfully stored cost data for tenant {tenant_id}")
            
        except (AccessDeniedError, ResourceQuotaExceededError):
            raise
        except Exception as e:
            logger.error(f"Error storing cost data for tenant {tenant_id}: {e}")
            raise TenantDataIsolationError(f"Cost data storage failed: {e}") from e
    
    def query_tenant_cost_data(self, tenant_id: str, query_params: Dict[str, Any]) -> List[UnifiedCostRecord]:
        """
        Query cost data with tenant isolation.
        
        Args:
            tenant_id: Tenant ID
            query_params: Query parameters
            
        Returns:
            List of cost records for the tenant
            
        Raises:
            AccessDeniedError: If access is denied
        """
        try:
            logger.debug(f"Querying cost data for tenant {tenant_id}")
            
            # Validate tenant access
            self.validate_tenant_access(tenant_id, "read", "cost_data")
            
            # Get tenant partition
            partition = self.get_tenant_partition(tenant_id)
            
            # Build query with tenant isolation
            key_condition = boto3.dynamodb.conditions.Key('PK').eq(partition.partition_key)
            
            # Add additional query conditions
            if 'provider' in query_params:
                key_condition = key_condition & boto3.dynamodb.conditions.Key('SK').begins_with(
                    f"COST#{query_params['provider']}#"
                )
            elif 'date_range' in query_params:
                start_date = query_params['date_range']['start']
                end_date = query_params['date_range']['end']
                key_condition = key_condition & boto3.dynamodb.conditions.Key('SK').between(
                    f"COST#{start_date}",
                    f"COST#{end_date}~"  # ~ is after # in ASCII
                )
            
            # Execute query with tenant isolation filter
            response = self.cost_table.query(
                KeyConditionExpression=key_condition,
                FilterExpression=boto3.dynamodb.conditions.Attr('tenant_id').eq(tenant_id),
                Limit=query_params.get('limit', 100)
            )
            
            # Convert to UnifiedCostRecord objects
            cost_records = []
            for item in response.get('Items', []):
                # Verify tenant isolation
                if not item.get('tenant_id') == tenant_id:
                    logger.error(f"Data isolation violation detected for tenant {tenant_id}")
                    raise DataIsolationViolationError(f"Data isolation violation for tenant {tenant_id}")
                
                try:
                    cost_record = UnifiedCostRecord.from_dynamodb_item(item)
                    cost_records.append(cost_record)
                except Exception as e:
                    logger.warning(f"Failed to parse cost record for tenant {tenant_id}: {e}")
                    continue
            
            # Update tenant usage metrics
            self._update_tenant_usage(tenant_id, "read_operations", len(cost_records), 0)
            
            logger.debug(f"Successfully queried {len(cost_records)} cost records for tenant {tenant_id}")
            return cost_records
            
        except (AccessDeniedError, DataIsolationViolationError):
            raise
        except Exception as e:
            logger.error(f"Error querying cost data for tenant {tenant_id}: {e}")
            raise TenantDataIsolationError(f"Cost data query failed: {e}") from e
    
    def delete_tenant_data(self, tenant_id: str, data_type: Optional[str] = None) -> Dict[str, int]:
        """
        Delete all data for a tenant with proper isolation.
        
        Args:
            tenant_id: Tenant ID
            data_type: Optional data type filter (cost, timeseries, etc.)
            
        Returns:
            Dictionary containing deletion counts by data type
            
        Raises:
            AccessDeniedError: If access is denied
        """
        try:
            logger.info(f"Deleting tenant data for {tenant_id}")
            
            # Validate tenant access
            self.validate_tenant_access(tenant_id, "delete", "all_data")
            
            deletion_counts = {}
            
            # Get tenant partition
            partition = self.get_tenant_partition(tenant_id)
            
            # Delete cost data
            if not data_type or data_type == "cost":
                cost_count = self._delete_tenant_table_data(
                    self.cost_table, 
                    partition.partition_key,
                    tenant_id
                )
                deletion_counts['cost_data'] = cost_count
            
            # Delete timeseries data
            if not data_type or data_type == "timeseries":
                timeseries_count = self._delete_tenant_table_data(
                    self.timeseries_table,
                    partition.partition_key,
                    tenant_id
                )
                deletion_counts['timeseries_data'] = timeseries_count
            
            # If deleting all data, also clean up partition and quota
            if not data_type:
                self._cleanup_tenant_metadata(tenant_id)
                deletion_counts['metadata'] = 1
            
            logger.info(f"Successfully deleted tenant data for {tenant_id}: {deletion_counts}")
            return deletion_counts
            
        except AccessDeniedError:
            raise
        except Exception as e:
            logger.error(f"Error deleting tenant data for {tenant_id}: {e}")
            raise TenantDataIsolationError(f"Tenant data deletion failed: {e}") from e
    
    def get_tenant_quota(self, tenant_id: str) -> ResourceQuota:
        """
        Get resource quota for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            ResourceQuota for the tenant
            
        Raises:
            TenantNotFoundError: If tenant quota is not found
        """
        try:
            # Check cache first
            if tenant_id in self._quota_cache:
                return self._quota_cache[tenant_id]
            
            # Query from database
            response = self.quota_table.get_item(
                Key={'tenant_id': tenant_id}
            )
            
            if 'Item' not in response:
                raise TenantNotFoundError(f"Tenant quota not found: {tenant_id}")
            
            item = response['Item']
            quota = ResourceQuota(
                tenant_id=item['tenant_id'],
                max_storage_gb=item['max_storage_gb'],
                max_read_capacity=item['max_read_capacity'],
                max_write_capacity=item['max_write_capacity'],
                max_concurrent_queries=item['max_concurrent_queries'],
                max_data_retention_days=item['max_data_retention_days'],
                current_usage=item.get('current_usage', {})
            )
            
            # Cache the quota
            self._quota_cache[tenant_id] = quota
            return quota
            
        except TenantNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting tenant quota for {tenant_id}: {e}")
            raise TenantDataIsolationError(f"Failed to get tenant quota: {e}") from e
    
    def _determine_isolation_level(self, subscription_tier: SubscriptionTier) -> IsolationLevel:
        """Determine isolation level based on subscription tier."""
        if subscription_tier == SubscriptionTier.ENTERPRISE:
            return IsolationLevel.STRICT
        elif subscription_tier in [SubscriptionTier.PROFESSIONAL, SubscriptionTier.BASIC]:
            return IsolationLevel.STANDARD
        else:
            return IsolationLevel.BASIC
    
    def _calculate_resource_allocation(self, client: MultiCloudClient) -> Dict[str, Any]:
        """Calculate resource allocation based on client configuration."""
        base_allocation = {
            'read_capacity_units': 100,
            'write_capacity_units': 50,
            'storage_gb': 10,
            'concurrent_queries': 5
        }
        
        # Scale based on subscription tier
        tier_multipliers = {
            SubscriptionTier.FREE: 0.5,
            SubscriptionTier.BASIC: 1.0,
            SubscriptionTier.PROFESSIONAL: 3.0,
            SubscriptionTier.ENTERPRISE: 10.0
        }
        
        multiplier = tier_multipliers.get(client.subscription_tier, 1.0)
        
        return {
            key: int(value * multiplier)
            for key, value in base_allocation.items()
        }
    
    def _create_resource_quota(self, client: MultiCloudClient) -> ResourceQuota:
        """Create resource quota for a client."""
        resource_limits = client.resource_limits
        
        return ResourceQuota(
            tenant_id=client.tenant_id,
            max_storage_gb=resource_limits.max_data_retention_days // 30,  # Rough estimate
            max_read_capacity=1000,
            max_write_capacity=500,
            max_concurrent_queries=resource_limits.concurrent_collection_limit * 2,
            max_data_retention_days=resource_limits.max_data_retention_days,
            current_usage={
                'storage_gb': 0,
                'read_operations': 0,
                'write_operations': 0,
                'concurrent_queries': 0
            }
        )
    
    def _check_basic_permissions(self, partition: TenantPartition, operation: str, resource_type: str) -> bool:
        """Check basic permissions for tenant operation."""
        # For now, all operations are allowed if tenant partition exists
        # This can be extended with more granular permissions
        return True
    
    def _check_resource_quotas(self, quota: ResourceQuota, operation: str, resource_type: str) -> bool:
        """Check if operation would exceed resource quotas."""
        current_usage = quota.current_usage
        
        if operation == "read":
            # Check concurrent query limit (simplified check)
            return current_usage.get('concurrent_queries', 0) < quota.max_concurrent_queries
        elif operation == "write":
            # Check storage limit (simplified check)
            return current_usage.get('storage_gb', 0) < quota.max_storage_gb
        
        return True
    
    def _update_partition_metadata(self, partition: TenantPartition) -> None:
        """Update partition metadata in database."""
        try:
            self.partition_table.update_item(
                Key={'tenant_id': partition.tenant_id},
                UpdateExpression='SET last_accessed = :last_accessed',
                ExpressionAttributeValues={
                    ':last_accessed': partition.last_accessed.isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update partition metadata for {partition.tenant_id}: {e}")
    
    def _update_tenant_usage(self, tenant_id: str, metric: str, count: int, size_bytes: int) -> None:
        """Update tenant usage metrics."""
        try:
            self.quota_table.update_item(
                Key={'tenant_id': tenant_id},
                UpdateExpression='ADD current_usage.#metric :count',
                ExpressionAttributeNames={
                    '#metric': metric
                },
                ExpressionAttributeValues={
                    ':count': count
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update tenant usage for {tenant_id}: {e}")
    
    def _delete_tenant_table_data(self, table, partition_key: str, tenant_id: str) -> int:
        """Delete all data for a tenant from a specific table."""
        deleted_count = 0
        
        try:
            # Query all items for the tenant
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq(partition_key),
                FilterExpression=boto3.dynamodb.conditions.Attr('tenant_id').eq(tenant_id),
                ProjectionExpression='PK, SK'
            )
            
            # Delete items in batches
            with table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(
                        Key={
                            'PK': item['PK'],
                            'SK': item['SK']
                        }
                    )
                    deleted_count += 1
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = table.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq(partition_key),
                    FilterExpression=boto3.dynamodb.conditions.Attr('tenant_id').eq(tenant_id),
                    ProjectionExpression='PK, SK',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                
                with table.batch_writer() as batch:
                    for item in response.get('Items', []):
                        batch.delete_item(
                            Key={
                                'PK': item['PK'],
                                'SK': item['SK']
                            }
                        )
                        deleted_count += 1
            
        except Exception as e:
            logger.error(f"Error deleting tenant data from table: {e}")
            raise
        
        return deleted_count
    
    def _cleanup_tenant_metadata(self, tenant_id: str) -> None:
        """Clean up tenant partition and quota metadata."""
        try:
            # Delete partition metadata
            self.partition_table.delete_item(
                Key={'tenant_id': tenant_id}
            )
            
            # Delete quota metadata
            self.quota_table.delete_item(
                Key={'tenant_id': tenant_id}
            )
            
            # Clear cache
            self._partition_cache.pop(tenant_id, None)
            self._quota_cache.pop(tenant_id, None)
            
        except Exception as e:
            logger.error(f"Error cleaning up tenant metadata for {tenant_id}: {e}")
            raise


# DynamoDB Table Schemas for Tenant Isolation

TENANT_PARTITION_TABLE_SCHEMA = {
    "TableName": "tenant-partitions",
    "KeySchema": [
        {
            "AttributeName": "tenant_id",
            "KeyType": "HASH"
        }
    ],
    "AttributeDefinitions": [
        {
            "AttributeName": "tenant_id",
            "AttributeType": "S"
        }
    ],
    "BillingMode": "PAY_PER_REQUEST",
    "Tags": [
        {
            "Key": "Project",
            "Value": "multi-cloud-cost-analytics"
        },
        {
            "Key": "Component",
            "Value": "tenant-isolation"
        }
    ]
}

TENANT_QUOTA_TABLE_SCHEMA = {
    "TableName": "tenant-quotas",
    "KeySchema": [
        {
            "AttributeName": "tenant_id",
            "KeyType": "HASH"
        }
    ],
    "AttributeDefinitions": [
        {
            "AttributeName": "tenant_id",
            "AttributeType": "S"
        }
    ],
    "BillingMode": "PAY_PER_REQUEST",
    "Tags": [
        {
            "Key": "Project",
            "Value": "multi-cloud-cost-analytics"
        },
        {
            "Key": "Component",
            "Value": "tenant-isolation"
        }
    ]
}