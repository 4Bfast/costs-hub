"""
Rate Limiting Service

This service provides API rate limiting functionality using DynamoDB
for distributed rate limiting across Lambda functions.
"""

import boto3
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class RateLimitingService:
    """
    Distributed rate limiting service using DynamoDB.
    
    Implements token bucket and sliding window algorithms for
    flexible rate limiting across different API endpoints.
    """
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize the rate limiting service.
        
        Args:
            table_name: DynamoDB table name for rate limit storage
            region: AWS region
        """
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
    
    async def check_rate_limit(self, key: str, limit: int, window: int, 
                             algorithm: str = 'sliding_window') -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            key: Unique identifier for the rate limit (e.g., user_id, ip_address)
            limit: Maximum number of requests allowed
            window: Time window in seconds
            algorithm: Rate limiting algorithm ('sliding_window' or 'token_bucket')
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        try:
            if algorithm == 'sliding_window':
                return await self._check_sliding_window(key, limit, window)
            elif algorithm == 'token_bucket':
                return await self._check_token_bucket(key, limit, window)
            else:
                logger.error(f"Unknown rate limiting algorithm: {algorithm}")
                return True  # Allow request if algorithm is unknown
                
        except Exception as e:
            logger.error(f"Rate limiting check failed for key {key}: {e}")
            return True  # Allow request if rate limiting fails
    
    async def _check_sliding_window(self, key: str, limit: int, window: int) -> bool:
        """
        Implement sliding window rate limiting.
        
        Args:
            key: Rate limit key
            limit: Request limit
            window: Time window in seconds
            
        Returns:
            True if request is allowed
        """
        current_time = int(time.time())
        window_start = current_time - window
        
        try:
            # Get current rate limit data
            response = self.table.get_item(
                Key={'rate_limit_key': key}
            )
            
            if 'Item' not in response:
                # First request - create new record
                self.table.put_item(
                    Item={
                        'rate_limit_key': key,
                        'requests': [current_time],
                        'updated_at': current_time,
                        'ttl': current_time + window + 3600  # TTL with buffer
                    }
                )
                return True
            
            item = response['Item']
            requests = item.get('requests', [])
            
            # Filter out requests outside the window
            valid_requests = [req_time for req_time in requests if req_time > window_start]
            
            # Check if we're within the limit
            if len(valid_requests) >= limit:
                return False
            
            # Add current request and update
            valid_requests.append(current_time)
            
            self.table.put_item(
                Item={
                    'rate_limit_key': key,
                    'requests': valid_requests,
                    'updated_at': current_time,
                    'ttl': current_time + window + 3600
                }
            )
            
            return True
            
        except ClientError as e:
            logger.error(f"DynamoDB error in sliding window check: {e}")
            return True
    
    async def _check_token_bucket(self, key: str, limit: int, window: int) -> bool:
        """
        Implement token bucket rate limiting.
        
        Args:
            key: Rate limit key
            limit: Token bucket capacity
            window: Refill period in seconds
            
        Returns:
            True if request is allowed
        """
        current_time = int(time.time())
        refill_rate = limit / window  # Tokens per second
        
        try:
            # Get current bucket state
            response = self.table.get_item(
                Key={'rate_limit_key': key}
            )
            
            if 'Item' not in response:
                # First request - create new bucket
                self.table.put_item(
                    Item={
                        'rate_limit_key': key,
                        'tokens': limit - 1,  # Consume one token
                        'last_refill': current_time,
                        'updated_at': current_time,
                        'ttl': current_time + window + 3600
                    }
                )
                return True
            
            item = response['Item']
            tokens = item.get('tokens', 0)
            last_refill = item.get('last_refill', current_time)
            
            # Calculate tokens to add based on time elapsed
            time_elapsed = current_time - last_refill
            tokens_to_add = time_elapsed * refill_rate
            
            # Update token count (cap at limit)
            new_tokens = min(limit, tokens + tokens_to_add)
            
            # Check if we have tokens available
            if new_tokens < 1:
                return False
            
            # Consume one token and update
            self.table.put_item(
                Item={
                    'rate_limit_key': key,
                    'tokens': new_tokens - 1,
                    'last_refill': current_time,
                    'updated_at': current_time,
                    'ttl': current_time + window + 3600
                }
            )
            
            return True
            
        except ClientError as e:
            logger.error(f"DynamoDB error in token bucket check: {e}")
            return True
    
    async def get_rate_limit_status(self, key: str, limit: int, window: int) -> Dict[str, Any]:
        """
        Get current rate limit status for a key.
        
        Args:
            key: Rate limit key
            limit: Request limit
            window: Time window in seconds
            
        Returns:
            Dictionary with rate limit status information
        """
        try:
            response = self.table.get_item(
                Key={'rate_limit_key': key}
            )
            
            if 'Item' not in response:
                return {
                    'key': key,
                    'limit': limit,
                    'window': window,
                    'remaining': limit,
                    'reset_time': None,
                    'requests_made': 0
                }
            
            item = response['Item']
            current_time = int(time.time())
            window_start = current_time - window
            
            # Count valid requests in current window
            requests = item.get('requests', [])
            valid_requests = [req_time for req_time in requests if req_time > window_start]
            requests_made = len(valid_requests)
            remaining = max(0, limit - requests_made)
            
            # Calculate reset time (when oldest request expires)
            reset_time = None
            if valid_requests:
                oldest_request = min(valid_requests)
                reset_time = oldest_request + window
            
            return {
                'key': key,
                'limit': limit,
                'window': window,
                'remaining': remaining,
                'reset_time': reset_time,
                'requests_made': requests_made
            }
            
        except Exception as e:
            logger.error(f"Failed to get rate limit status for key {key}: {e}")
            return {
                'key': key,
                'limit': limit,
                'window': window,
                'remaining': limit,
                'reset_time': None,
                'requests_made': 0,
                'error': str(e)
            }
    
    async def reset_rate_limit(self, key: str) -> bool:
        """
        Reset rate limit for a specific key.
        
        Args:
            key: Rate limit key to reset
            
        Returns:
            True if reset was successful
        """
        try:
            self.table.delete_item(
                Key={'rate_limit_key': key}
            )
            return True
            
        except ClientError as e:
            logger.error(f"Failed to reset rate limit for key {key}: {e}")
            return False
    
    async def cleanup_expired_entries(self) -> int:
        """
        Clean up expired rate limit entries.
        
        Returns:
            Number of entries cleaned up
        """
        try:
            current_time = int(time.time())
            cleaned_count = 0
            
            # Scan for expired entries
            response = self.table.scan(
                FilterExpression='#ttl < :current_time',
                ExpressionAttributeNames={'#ttl': 'ttl'},
                ExpressionAttributeValues={':current_time': current_time}
            )
            
            # Delete expired entries
            with self.table.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(
                        Key={'rate_limit_key': item['rate_limit_key']}
                    )
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired rate limit entries")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired entries: {e}")
            return 0
    
    def create_rate_limit_table(self) -> bool:
        """
        Create the DynamoDB table for rate limiting.
        
        Returns:
            True if table was created successfully
        """
        try:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'rate_limit_key',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'rate_limit_key',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST',
                StreamSpecification={
                    'StreamEnabled': False
                },
                PointInTimeRecoverySpecification={
                    'PointInTimeRecoveryEnabled': True
                },
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'multi-cloud-cost-analytics'
                    },
                    {
                        'Key': 'Component',
                        'Value': 'rate-limiting'
                    }
                ]
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            
            logger.info(f"Rate limiting table {self.table_name} created successfully")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"Rate limiting table {self.table_name} already exists")
                return True
            else:
                logger.error(f"Failed to create rate limiting table: {e}")
                return False


class RateLimitDecorator:
    """
    Decorator for applying rate limits to API endpoints.
    """
    
    def __init__(self, rate_limiter: RateLimitingService):
        """
        Initialize the rate limit decorator.
        
        Args:
            rate_limiter: RateLimitingService instance
        """
        self.rate_limiter = rate_limiter
    
    def limit(self, key_func, limit: int, window: int, algorithm: str = 'sliding_window'):
        """
        Apply rate limiting to a function.
        
        Args:
            key_func: Function to generate rate limit key from request
            limit: Request limit
            window: Time window in seconds
            algorithm: Rate limiting algorithm
            
        Returns:
            Decorated function
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Extract rate limit key
                rate_limit_key = key_func(*args, **kwargs)
                
                # Check rate limit
                allowed = await self.rate_limiter.check_rate_limit(
                    rate_limit_key, limit, window, algorithm
                )
                
                if not allowed:
                    from ..utils.api_response import RateLimitError
                    raise RateLimitError(
                        message=f"Rate limit exceeded: {limit} requests per {window} seconds",
                        retry_after=window
                    )
                
                # Execute original function
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator


# Rate limiting configurations for different endpoints
RATE_LIMIT_CONFIGS = {
    'cost_data': {
        'limit': 100,
        'window': 3600,  # 1 hour
        'algorithm': 'sliding_window'
    },
    'insights': {
        'limit': 50,
        'window': 3600,  # 1 hour
        'algorithm': 'sliding_window'
    },
    'client_management': {
        'limit': 200,
        'window': 3600,  # 1 hour
        'algorithm': 'sliding_window'
    },
    'webhooks': {
        'limit': 1000,
        'window': 3600,  # 1 hour
        'algorithm': 'token_bucket'
    },
    'notifications': {
        'limit': 500,
        'window': 3600,  # 1 hour
        'algorithm': 'sliding_window'
    }
}


def get_rate_limit_key(user_context: Dict[str, Any], endpoint_type: str) -> str:
    """
    Generate rate limit key for a user and endpoint type.
    
    Args:
        user_context: User context from authentication
        endpoint_type: Type of endpoint being accessed
        
    Returns:
        Rate limit key string
    """
    user_id = user_context.get('user_id', 'anonymous')
    tenant_id = user_context.get('tenant_id', 'unknown')
    
    return f"{endpoint_type}:{tenant_id}:{user_id}"


def get_tenant_rate_limit_key(tenant_id: str, endpoint_type: str) -> str:
    """
    Generate tenant-level rate limit key.
    
    Args:
        tenant_id: Tenant identifier
        endpoint_type: Type of endpoint being accessed
        
    Returns:
        Rate limit key string
    """
    return f"tenant:{endpoint_type}:{tenant_id}"