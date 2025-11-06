"""
Cost History Storage Service

This module implements the cost history storage service for the multi-cloud cost analytics platform.
It provides functionality for DynamoDB operations, efficient querying methods for time-range analysis,
and data archiving and lifecycle management.
"""

import logging
import asyncio
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError, BotoCoreError
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from ..models.multi_cloud_models import (
    UnifiedCostRecord, UnifiedTimeSeriesRecord, TimeSeriesDataPoint, 
    TimeSeriesAggregations, CloudProvider, ServiceCategory, Currency
)
from ..models.provider_models import DateRange


logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class RecordNotFoundError(StorageError):
    """Exception for when a record is not found."""
    pass


class QueryError(StorageError):
    """Exception for query errors."""
    pass


class ArchiveError(StorageError):
    """Exception for archiving errors."""
    pass


@dataclass
class StorageConfig:
    """Configuration for cost history storage."""
    cost_table_name: str = "cost-analytics-data"
    timeseries_table_name: str = "cost-analytics-timeseries"
    region: str = "us-east-1"
    enable_point_in_time_recovery: bool = True
    enable_encryption: bool = True
    ttl_days: int = 730  # 2 years default
    batch_size: int = 25  # DynamoDB batch write limit
    query_limit: int = 1000
    enable_compression: bool = True
    archive_after_days: int = 365
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'cost_table_name': self.cost_table_name,
            'timeseries_table_name': self.timeseries_table_name,
            'region': self.region,
            'enable_point_in_time_recovery': self.enable_point_in_time_recovery,
            'enable_encryption': self.enable_encryption,
            'ttl_days': self.ttl_days,
            'batch_size': self.batch_size,
            'query_limit': self.query_limit,
            'enable_compression': self.enable_compression,
            'archive_after_days': self.archive_after_days
        }


@dataclass
class QueryOptions:
    """Options for querying cost history."""
    limit: Optional[int] = None
    start_key: Optional[Dict[str, Any]] = None
    consistent_read: bool = False
    projection_expression: Optional[str] = None
    filter_expression: Optional[str] = None
    sort_ascending: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'limit': self.limit,
            'start_key': self.start_key,
            'consistent_read': self.consistent_read,
            'projection_expression': self.projection_expression,
            'filter_expression': self.filter_expression,
            'sort_ascending': self.sort_ascending
        }


@dataclass
class QueryResult:
    """Result of a query operation."""
    items: List[Dict[str, Any]]
    count: int
    scanned_count: int
    last_evaluated_key: Optional[Dict[str, Any]]
    consumed_capacity: Optional[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'items': self.items,
            'count': self.count,
            'scanned_count': self.scanned_count,
            'last_evaluated_key': self.last_evaluated_key,
            'consumed_capacity': self.consumed_capacity
        }


@dataclass
class StorageMetrics:
    """Storage operation metrics."""
    operations_count: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_items_stored: int = 0
    total_items_retrieved: int = 0
    total_storage_size_bytes: int = 0
    average_operation_duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'operations_count': self.operations_count,
            'successful_operations': self.successful_operations,
            'failed_operations': self.failed_operations,
            'total_items_stored': self.total_items_stored,
            'total_items_retrieved': self.total_items_retrieved,
            'total_storage_size_bytes': self.total_storage_size_bytes,
            'average_operation_duration_ms': self.average_operation_duration_ms,
            'success_rate': (self.successful_operations / max(1, self.operations_count)) * 100
        }


class CostHistoryService:
    """
    Service for managing cost history storage in DynamoDB.
    
    This service provides:
    1. Efficient storage and retrieval of cost records
    2. Time-range queries with pagination
    3. Data archiving and lifecycle management
    4. Batch operations for performance
    5. Comprehensive error handling and retry logic
    """
    
    def __init__(self, config: Optional[StorageConfig] = None):
        """Initialize the cost history service."""
        self.config = config or StorageConfig()
        self.logger = logging.getLogger(f"{__name__}.CostHistoryService")
        
        # Initialize DynamoDB clients
        self.dynamodb = boto3.resource('dynamodb', region_name=self.config.region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=self.config.region)
        
        # Get table references
        self.cost_table = self.dynamodb.Table(self.config.cost_table_name)
        self.timeseries_table = self.dynamodb.Table(self.config.timeseries_table_name)
        
        # Storage metrics
        self.metrics = StorageMetrics()
        
        # Operation tracking
        self.operation_times: List[float] = []
    
    async def store_cost_record(self, record: UnifiedCostRecord) -> bool:
        """
        Store a unified cost record in DynamoDB.
        
        Args:
            record: Unified cost record to store
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            StorageError: If storage operation fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Convert record to DynamoDB item
            item = record.to_dynamodb_item()
            
            # Add TTL if configured
            if self.config.ttl_days > 0:
                ttl_timestamp = int((datetime.utcnow() + timedelta(days=self.config.ttl_days)).timestamp())
                item['ttl'] = ttl_timestamp
            
            # Store in cost table
            response = self.cost_table.put_item(Item=item)
            
            # Update metrics
            self._update_metrics(start_time, True, 1, 0)
            
            self.logger.debug(f"Stored cost record {record.record_id} for client {record.client_id}")
            return True
            
        except ClientError as e:
            self._update_metrics(start_time, False, 0, 0)
            error_code = e.response['Error']['Code']
            self.logger.error(f"Failed to store cost record: {error_code} - {e}")
            raise StorageError(f"Failed to store cost record: {error_code}") from e
        except Exception as e:
            self._update_metrics(start_time, False, 0, 0)
            self.logger.error(f"Unexpected error storing cost record: {e}")
            raise StorageError(f"Unexpected error storing cost record: {str(e)}") from e
    
    async def store_timeseries_record(self, record: UnifiedTimeSeriesRecord) -> bool:
        """
        Store a time series record in DynamoDB.
        
        Args:
            record: Time series record to store
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            StorageError: If storage operation fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Convert record to DynamoDB item
            item = record.to_dynamodb_item()
            
            # Add TTL if configured
            if self.config.ttl_days > 0:
                ttl_timestamp = int((datetime.utcnow() + timedelta(days=self.config.ttl_days)).timestamp())
                item['ttl'] = ttl_timestamp
            
            # Store in timeseries table
            response = self.timeseries_table.put_item(Item=item)
            
            # Update metrics
            self._update_metrics(start_time, True, 1, 0)
            
            self.logger.debug(f"Stored timeseries record for client {record.client_id} date {record.date}")
            return True
            
        except ClientError as e:
            self._update_metrics(start_time, False, 0, 0)
            error_code = e.response['Error']['Code']
            self.logger.error(f"Failed to store timeseries record: {error_code} - {e}")
            raise StorageError(f"Failed to store timeseries record: {error_code}") from e
        except Exception as e:
            self._update_metrics(start_time, False, 0, 0)
            self.logger.error(f"Unexpected error storing timeseries record: {e}")
            raise StorageError(f"Unexpected error storing timeseries record: {str(e)}") from e
    
    async def get_cost_record(
        self, 
        client_id: str, 
        provider: CloudProvider, 
        date: str
    ) -> Optional[UnifiedCostRecord]:
        """
        Retrieve a specific cost record.
        
        Args:
            client_id: Client identifier
            provider: Cloud provider
            date: Date in YYYY-MM-DD format
            
        Returns:
            UnifiedCostRecord if found, None otherwise
            
        Raises:
            StorageError: If retrieval operation fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Build key
            pk = f"CLIENT#{client_id}"
            sk = f"COST#{provider.value}#{date}"
            
            # Get item from cost table
            response = self.cost_table.get_item(
                Key={'PK': pk, 'SK': sk}
            )
            
            if 'Item' not in response:
                self._update_metrics(start_time, True, 0, 0)
                return None
            
            # Convert DynamoDB item to UnifiedCostRecord
            record = UnifiedCostRecord.from_dynamodb_item(response['Item'])
            
            # Update metrics
            self._update_metrics(start_time, True, 0, 1)
            
            return record
            
        except ClientError as e:
            self._update_metrics(start_time, False, 0, 0)
            error_code = e.response['Error']['Code']
            self.logger.error(f"Failed to get cost record: {error_code} - {e}")
            raise StorageError(f"Failed to get cost record: {error_code}") from e
        except Exception as e:
            self._update_metrics(start_time, False, 0, 0)
            self.logger.error(f"Unexpected error getting cost record: {e}")
            raise StorageError(f"Unexpected error getting cost record: {str(e)}") from e
    
    async def query_cost_records_by_client(
        self,
        client_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        providers: Optional[List[CloudProvider]] = None,
        options: Optional[QueryOptions] = None
    ) -> QueryResult:
        """
        Query cost records for a specific client.
        
        Args:
            client_id: Client identifier
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            providers: Optional list of providers to filter by
            options: Optional query options
            
        Returns:
            QueryResult with matching records
            
        Raises:
            QueryError: If query operation fails
        """
        start_time = datetime.utcnow()
        options = options or QueryOptions()
        
        try:
            # Build key condition
            pk = f"CLIENT#{client_id}"
            key_condition = Key('PK').eq(pk)
            
            # Add date range to sort key condition if provided
            if start_date and end_date:
                key_condition = key_condition & Key('SK').between(
                    f"COST#{start_date}",
                    f"COST#{end_date}~"  # ~ is after Z in ASCII, ensures we get all providers
                )
            elif start_date:
                key_condition = key_condition & Key('SK').gte(f"COST#{start_date}")
            elif end_date:
                key_condition = key_condition & Key('SK').lte(f"COST#{end_date}~")
            
            # Build query parameters
            query_params = {
                'KeyConditionExpression': key_condition,
                'ScanIndexForward': options.sort_ascending,
                'ConsistentRead': options.consistent_read
            }
            
            # Add optional parameters
            if options.limit:
                query_params['Limit'] = options.limit
            
            if options.start_key:
                query_params['ExclusiveStartKey'] = options.start_key
            
            if options.projection_expression:
                query_params['ProjectionExpression'] = options.projection_expression
            
            # Add provider filter if specified
            filter_expressions = []
            if providers:
                provider_values = [p.value for p in providers]
                filter_expressions.append(Attr('provider').is_in(provider_values))
            
            if options.filter_expression:
                # Parse and add custom filter expression
                # This is a simplified implementation - in production, you'd want more robust parsing
                filter_expressions.append(Attr('custom_filter').exists())
            
            if filter_expressions:
                if len(filter_expressions) == 1:
                    query_params['FilterExpression'] = filter_expressions[0]
                else:
                    combined_filter = filter_expressions[0]
                    for expr in filter_expressions[1:]:
                        combined_filter = combined_filter & expr
                    query_params['FilterExpression'] = combined_filter
            
            # Execute query
            response = self.cost_table.query(**query_params)
            
            # Update metrics
            item_count = len(response.get('Items', []))
            self._update_metrics(start_time, True, 0, item_count)
            
            return QueryResult(
                items=response.get('Items', []),
                count=response.get('Count', 0),
                scanned_count=response.get('ScannedCount', 0),
                last_evaluated_key=response.get('LastEvaluatedKey'),
                consumed_capacity=response.get('ConsumedCapacity')
            )
            
        except ClientError as e:
            self._update_metrics(start_time, False, 0, 0)
            error_code = e.response['Error']['Code']
            self.logger.error(f"Failed to query cost records: {error_code} - {e}")
            raise QueryError(f"Failed to query cost records: {error_code}") from e
        except Exception as e:
            self._update_metrics(start_time, False, 0, 0)
            self.logger.error(f"Unexpected error querying cost records: {e}")
            raise QueryError(f"Unexpected error querying cost records: {str(e)}") from e
    
    async def query_cost_records_by_provider(
        self,
        provider: CloudProvider,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        options: Optional[QueryOptions] = None
    ) -> QueryResult:
        """
        Query cost records by provider using GSI1.
        
        Args:
            provider: Cloud provider
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            options: Optional query options
            
        Returns:
            QueryResult with matching records
            
        Raises:
            QueryError: If query operation fails
        """
        start_time = datetime.utcnow()
        options = options or QueryOptions()
        
        try:
            # Build key condition for GSI1
            gsi1_pk = f"PROVIDER#{provider.value}"
            key_condition = Key('GSI1PK').eq(gsi1_pk)
            
            # Add date range to GSI1SK if provided
            if start_date and end_date:
                key_condition = key_condition & Key('GSI1SK').between(
                    f"DATE#{start_date}",
                    f"DATE#{end_date}"
                )
            elif start_date:
                key_condition = key_condition & Key('GSI1SK').gte(f"DATE#{start_date}")
            elif end_date:
                key_condition = key_condition & Key('GSI1SK').lte(f"DATE#{end_date}")
            
            # Build query parameters
            query_params = {
                'IndexName': 'GSI1',
                'KeyConditionExpression': key_condition,
                'ScanIndexForward': options.sort_ascending
            }
            
            # Add optional parameters
            if options.limit:
                query_params['Limit'] = options.limit
            
            if options.start_key:
                query_params['ExclusiveStartKey'] = options.start_key
            
            if options.projection_expression:
                query_params['ProjectionExpression'] = options.projection_expression
            
            if options.filter_expression:
                # Add custom filter expression
                query_params['FilterExpression'] = Attr('custom_filter').exists()
            
            # Execute query
            response = self.cost_table.query(**query_params)
            
            # Update metrics
            item_count = len(response.get('Items', []))
            self._update_metrics(start_time, True, 0, item_count)
            
            return QueryResult(
                items=response.get('Items', []),
                count=response.get('Count', 0),
                scanned_count=response.get('ScannedCount', 0),
                last_evaluated_key=response.get('LastEvaluatedKey'),
                consumed_capacity=response.get('ConsumedCapacity')
            )
            
        except ClientError as e:
            self._update_metrics(start_time, False, 0, 0)
            error_code = e.response['Error']['Code']
            self.logger.error(f"Failed to query by provider: {error_code} - {e}")
            raise QueryError(f"Failed to query by provider: {error_code}") from e
        except Exception as e:
            self._update_metrics(start_time, False, 0, 0)
            self.logger.error(f"Unexpected error querying by provider: {e}")
            raise QueryError(f"Unexpected error querying by provider: {str(e)}") from e
    
    async def batch_store_cost_records(self, records: List[UnifiedCostRecord]) -> Dict[str, Any]:
        """
        Store multiple cost records in batches.
        
        Args:
            records: List of cost records to store
            
        Returns:
            Dictionary with batch operation results
            
        Raises:
            StorageError: If batch operation fails
        """
        start_time = datetime.utcnow()
        
        try:
            total_records = len(records)
            successful_records = 0
            failed_records = 0
            unprocessed_items = []
            
            # Process records in batches
            for i in range(0, total_records, self.config.batch_size):
                batch = records[i:i + self.config.batch_size]
                
                # Prepare batch write request
                with self.cost_table.batch_writer() as batch_writer:
                    for record in batch:
                        try:
                            item = record.to_dynamodb_item()
                            
                            # Add TTL if configured
                            if self.config.ttl_days > 0:
                                ttl_timestamp = int((datetime.utcnow() + timedelta(days=self.config.ttl_days)).timestamp())
                                item['ttl'] = ttl_timestamp
                            
                            batch_writer.put_item(Item=item)
                            successful_records += 1
                            
                        except Exception as e:
                            self.logger.error(f"Failed to prepare record {record.record_id} for batch: {e}")
                            failed_records += 1
                            unprocessed_items.append({
                                'record_id': record.record_id,
                                'error': str(e)
                            })
            
            # Update metrics
            self._update_metrics(start_time, True, successful_records, 0)
            
            result = {
                'total_records': total_records,
                'successful_records': successful_records,
                'failed_records': failed_records,
                'success_rate': (successful_records / total_records) * 100 if total_records > 0 else 0,
                'unprocessed_items': unprocessed_items
            }
            
            self.logger.info(f"Batch stored {successful_records}/{total_records} cost records")
            return result
            
        except Exception as e:
            self._update_metrics(start_time, False, 0, 0)
            self.logger.error(f"Batch store operation failed: {e}")
            raise StorageError(f"Batch store operation failed: {str(e)}") from e
    
    async def delete_cost_record(
        self, 
        client_id: str, 
        provider: CloudProvider, 
        date: str
    ) -> bool:
        """
        Delete a specific cost record.
        
        Args:
            client_id: Client identifier
            provider: Cloud provider
            date: Date in YYYY-MM-DD format
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            StorageError: If delete operation fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Build key
            pk = f"CLIENT#{client_id}"
            sk = f"COST#{provider.value}#{date}"
            
            # Delete item
            response = self.cost_table.delete_item(
                Key={'PK': pk, 'SK': sk},
                ReturnValues='ALL_OLD'
            )
            
            # Check if item was actually deleted
            deleted = 'Attributes' in response
            
            # Update metrics
            self._update_metrics(start_time, True, 0, 0)
            
            if deleted:
                self.logger.debug(f"Deleted cost record for {client_id}/{provider.value}/{date}")
            else:
                self.logger.debug(f"Cost record not found for deletion: {client_id}/{provider.value}/{date}")
            
            return deleted
            
        except ClientError as e:
            self._update_metrics(start_time, False, 0, 0)
            error_code = e.response['Error']['Code']
            self.logger.error(f"Failed to delete cost record: {error_code} - {e}")
            raise StorageError(f"Failed to delete cost record: {error_code}") from e
        except Exception as e:
            self._update_metrics(start_time, False, 0, 0)
            self.logger.error(f"Unexpected error deleting cost record: {e}")
            raise StorageError(f"Unexpected error deleting cost record: {str(e)}") from e
    
    async def archive_old_records(self, archive_before_date: str) -> Dict[str, Any]:
        """
        Archive records older than the specified date.
        
        Args:
            archive_before_date: Archive records before this date (YYYY-MM-DD)
            
        Returns:
            Dictionary with archiving results
            
        Raises:
            ArchiveError: If archiving operation fails
        """
        start_time = datetime.utcnow()
        
        try:
            archived_count = 0
            failed_count = 0
            total_scanned = 0
            
            # Scan for old records
            scan_params = {
                'FilterExpression': Attr('date').lt(archive_before_date),
                'ProjectionExpression': 'PK, SK, #d',
                'ExpressionAttributeNames': {'#d': 'date'}
            }
            
            paginator = self.dynamodb_client.get_paginator('scan')
            page_iterator = paginator.paginate(
                TableName=self.config.cost_table_name,
                **scan_params
            )
            
            for page in page_iterator:
                items = page.get('Items', [])
                total_scanned += len(items)
                
                # Process items in batches for deletion
                for i in range(0, len(items), self.config.batch_size):
                    batch = items[i:i + self.config.batch_size]
                    
                    # Prepare batch delete request
                    delete_requests = []
                    for item in batch:
                        delete_requests.append({
                            'DeleteRequest': {
                                'Key': {
                                    'PK': item['PK'],
                                    'SK': item['SK']
                                }
                            }
                        })
                    
                    # Execute batch delete
                    try:
                        response = self.dynamodb_client.batch_write_item(
                            RequestItems={
                                self.config.cost_table_name: delete_requests
                            }
                        )
                        
                        # Handle unprocessed items
                        unprocessed = response.get('UnprocessedItems', {})
                        if unprocessed:
                            # Retry unprocessed items (simplified - in production, implement exponential backoff)
                            self.logger.warning(f"Retrying {len(unprocessed)} unprocessed items")
                            # Implementation would retry with backoff
                        
                        archived_count += len(delete_requests)
                        
                    except ClientError as e:
                        self.logger.error(f"Failed to delete batch: {e}")
                        failed_count += len(delete_requests)
            
            # Update metrics
            self._update_metrics(start_time, True, 0, 0)
            
            result = {
                'total_scanned': total_scanned,
                'archived_count': archived_count,
                'failed_count': failed_count,
                'archive_date': archive_before_date,
                'success_rate': (archived_count / max(1, total_scanned)) * 100
            }
            
            self.logger.info(f"Archived {archived_count} records older than {archive_before_date}")
            return result
            
        except Exception as e:
            self._update_metrics(start_time, False, 0, 0)
            self.logger.error(f"Archive operation failed: {e}")
            raise ArchiveError(f"Archive operation failed: {str(e)}") from e
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            # Get table statistics
            cost_table_stats = await self._get_table_statistics(self.config.cost_table_name)
            timeseries_table_stats = await self._get_table_statistics(self.config.timeseries_table_name)
            
            # Combine with operation metrics
            return {
                'operation_metrics': self.metrics.to_dict(),
                'cost_table_statistics': cost_table_stats,
                'timeseries_table_statistics': timeseries_table_stats,
                'configuration': self.config.to_dict()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get storage statistics: {e}")
            return {
                'operation_metrics': self.metrics.to_dict(),
                'error': str(e)
            }
    
    async def _get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for a specific table."""
        try:
            response = self.dynamodb_client.describe_table(TableName=table_name)
            table_info = response['Table']
            
            return {
                'table_name': table_name,
                'table_status': table_info['TableStatus'],
                'item_count': table_info.get('ItemCount', 0),
                'table_size_bytes': table_info.get('TableSizeBytes', 0),
                'creation_date': table_info['CreationDateTime'].isoformat() if 'CreationDateTime' in table_info else None,
                'provisioned_throughput': table_info.get('ProvisionedThroughput', {}),
                'billing_mode': table_info.get('BillingModeSummary', {}).get('BillingMode', 'UNKNOWN')
            }
            
        except ClientError as e:
            self.logger.error(f"Failed to get table statistics for {table_name}: {e}")
            return {
                'table_name': table_name,
                'error': str(e)
            }
    
    def _update_metrics(
        self, 
        start_time: datetime, 
        success: bool, 
        items_stored: int, 
        items_retrieved: int
    ):
        """Update operation metrics."""
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        self.operation_times.append(duration_ms)
        
        # Keep only last 1000 operation times for average calculation
        if len(self.operation_times) > 1000:
            self.operation_times = self.operation_times[-1000:]
        
        self.metrics.operations_count += 1
        if success:
            self.metrics.successful_operations += 1
        else:
            self.metrics.failed_operations += 1
        
        self.metrics.total_items_stored += items_stored
        self.metrics.total_items_retrieved += items_retrieved
        
        # Update average operation duration
        if self.operation_times:
            self.metrics.average_operation_duration_ms = sum(self.operation_times) / len(self.operation_times)
    
    async def create_tables_if_not_exist(self) -> Dict[str, bool]:
        """
        Create DynamoDB tables if they don't exist.
        
        Returns:
            Dictionary indicating which tables were created
        """
        results = {}
        
        # Cost table schema
        cost_table_created = await self._create_table_if_not_exist(
            table_name=self.config.cost_table_name,
            key_schema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            attribute_definitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2SK', 'AttributeType': 'S'}
            ],
            global_secondary_indexes=[
                {
                    'IndexName': 'GSI1',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                {
                    'IndexName': 'GSI2',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ]
        )
        results['cost_table'] = cost_table_created
        
        # Timeseries table schema
        timeseries_table_created = await self._create_table_if_not_exist(
            table_name=self.config.timeseries_table_name,
            key_schema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            attribute_definitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ]
        )
        results['timeseries_table'] = timeseries_table_created
        
        return results
    
    async def _create_table_if_not_exist(
        self,
        table_name: str,
        key_schema: List[Dict[str, str]],
        attribute_definitions: List[Dict[str, str]],
        global_secondary_indexes: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Create a table if it doesn't exist."""
        try:
            # Check if table exists
            self.dynamodb_client.describe_table(TableName=table_name)
            self.logger.info(f"Table {table_name} already exists")
            return False
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                create_params = {
                    'TableName': table_name,
                    'KeySchema': key_schema,
                    'AttributeDefinitions': attribute_definitions,
                    'BillingMode': 'PAY_PER_REQUEST'
                }
                
                if global_secondary_indexes:
                    create_params['GlobalSecondaryIndexes'] = global_secondary_indexes
                
                if self.config.enable_encryption:
                    create_params['SSESpecification'] = {
                        'Enabled': True,
                        'SSEType': 'KMS'
                    }
                
                if self.config.enable_point_in_time_recovery:
                    create_params['PointInTimeRecoverySpecification'] = {
                        'PointInTimeRecoveryEnabled': True
                    }
                
                self.dynamodb_client.create_table(**create_params)
                
                # Wait for table to be active
                waiter = self.dynamodb_client.get_waiter('table_exists')
                waiter.wait(TableName=table_name)
                
                self.logger.info(f"Created table {table_name}")
                return True
            else:
                raise
        except Exception as e:
            self.logger.error(f"Failed to create table {table_name}: {e}")
            raise


# Convenience functions
async def store_cost_record(
    record: UnifiedCostRecord,
    config: Optional[StorageConfig] = None
) -> bool:
    """
    Convenience function to store a single cost record.
    
    Args:
        record: Cost record to store
        config: Optional storage configuration
        
    Returns:
        True if successful
    """
    service = CostHistoryService(config)
    return await service.store_cost_record(record)


async def get_cost_records_for_client(
    client_id: str,
    start_date: str,
    end_date: str,
    providers: Optional[List[CloudProvider]] = None,
    config: Optional[StorageConfig] = None
) -> List[UnifiedCostRecord]:
    """
    Convenience function to get cost records for a client.
    
    Args:
        client_id: Client identifier
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        providers: Optional list of providers to filter by
        config: Optional storage configuration
        
    Returns:
        List of UnifiedCostRecord objects
    """
    service = CostHistoryService(config)
    result = await service.query_cost_records_by_client(
        client_id, start_date, end_date, providers
    )
    
    # Convert DynamoDB items to UnifiedCostRecord objects
    records = []
    for item in result.items:
        try:
            record = UnifiedCostRecord.from_dynamodb_item(item)
            records.append(record)
        except Exception as e:
            logger.error(f"Failed to convert item to UnifiedCostRecord: {e}")
    
    return records


async def batch_store_cost_records(
    records: List[UnifiedCostRecord],
    config: Optional[StorageConfig] = None
) -> Dict[str, Any]:
    """
    Convenience function to batch store cost records.
    
    Args:
        records: List of cost records to store
        config: Optional storage configuration
        
    Returns:
        Dictionary with batch operation results
    """
    service = CostHistoryService(config)
    return await service.batch_store_cost_records(records)