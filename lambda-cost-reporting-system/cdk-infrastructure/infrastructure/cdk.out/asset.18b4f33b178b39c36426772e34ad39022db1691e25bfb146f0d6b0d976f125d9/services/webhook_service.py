"""
Webhook Service

This service provides comprehensive webhook management functionality
for real-time notifications and integrations with external systems.
"""

import boto3
import json
import logging
import hmac
import hashlib
import secrets
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from botocore.exceptions import ClientError

from ..models.multi_cloud_models import CloudProvider
from ..utils.api_response import ValidationError, NotFoundError


logger = logging.getLogger(__name__)


class WebhookEventType(Enum):
    """Webhook event types."""
    ANOMALY_DETECTED = "anomaly_detected"
    BUDGET_EXCEEDED = "budget_exceeded"
    FORECAST_UPDATED = "forecast_updated"
    COST_SPIKE = "cost_spike"
    THRESHOLD_BREACH = "threshold_breach"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    DATA_QUALITY_ISSUE = "data_quality_issue"
    COLLECTION_FAILED = "collection_failed"


class WebhookStatus(Enum):
    """Webhook status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    SUSPENDED = "suspended"


class DeliveryStatus(Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class WebhookConfig:
    """Webhook configuration structure."""
    webhook_id: str
    user_id: str
    tenant_id: str
    name: str
    url: str
    secret: str
    events: List[WebhookEventType]
    status: WebhookStatus
    created_at: datetime
    updated_at: datetime
    headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_count: int = 3
    retry_delay_seconds: int = 60
    last_delivery_at: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'webhook_id': self.webhook_id,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'url': self.url,
            'events': [event.value for event in self.events],
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'headers': self.headers,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
            'retry_delay_seconds': self.retry_delay_seconds,
            'last_delivery_at': self.last_delivery_at.isoformat() if self.last_delivery_at else None,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebhookConfig':
        """Create from dictionary representation."""
        return cls(
            webhook_id=data['webhook_id'],
            user_id=data['user_id'],
            tenant_id=data['tenant_id'],
            name=data['name'],
            url=data['url'],
            secret=data.get('secret', ''),
            events=[WebhookEventType(event) for event in data.get('events', [])],
            status=WebhookStatus(data.get('status', 'active')),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            headers=data.get('headers', {}),
            timeout_seconds=data.get('timeout_seconds', 30),
            retry_count=data.get('retry_count', 3),
            retry_delay_seconds=data.get('retry_delay_seconds', 60),
            last_delivery_at=datetime.fromisoformat(data['last_delivery_at']) if data.get('last_delivery_at') else None,
            success_count=data.get('success_count', 0),
            failure_count=data.get('failure_count', 0),
            metadata=data.get('metadata', {})
        )


@dataclass
class WebhookEvent:
    """Webhook event structure."""
    event_id: str
    webhook_id: str
    event_type: WebhookEventType
    payload: Dict[str, Any]
    created_at: datetime
    tenant_id: str
    user_id: str
    delivery_attempts: int = 0
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    last_attempt_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'event_id': self.event_id,
            'webhook_id': self.webhook_id,
            'event_type': self.event_type.value,
            'payload': self.payload,
            'created_at': self.created_at.isoformat(),
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'delivery_attempts': self.delivery_attempts,
            'delivery_status': self.delivery_status.value,
            'last_attempt_at': self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'error_message': self.error_message
        }


class WebhookService:
    """
    Comprehensive webhook management and delivery service.
    
    Provides functionality for managing webhooks, delivering events,
    handling retries, and monitoring delivery status.
    """
    
    def __init__(self, table_name: str, queue_name: str, region: str = 'us-east-1'):
        """
        Initialize the webhook service.
        
        Args:
            table_name: DynamoDB table name for webhook storage
            queue_name: SQS queue name for webhook delivery
            region: AWS region
        """
        self.table_name = table_name
        self.queue_name = queue_name
        self.region = region
        
        # Initialize AWS services
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.sqs = boto3.client('sqs', region_name=region)
        
        # Get queue URL
        try:
            response = self.sqs.get_queue_url(QueueName=queue_name)
            self.queue_url = response['QueueUrl']
        except ClientError:
            self.queue_url = None
            logger.warning(f"SQS queue {queue_name} not found")
        
        # Configuration
        self.max_webhooks_per_user = 20
        self.max_payload_size = 1024 * 1024  # 1MB
        self.signature_header = 'X-Webhook-Signature'
        self.timestamp_header = 'X-Webhook-Timestamp'
    
    def create_webhook(self, user_id: str, tenant_id: str, name: str, url: str,
                      events: List[WebhookEventType], secret: Optional[str] = None,
                      headers: Optional[Dict[str, str]] = None,
                      timeout_seconds: int = 30, retry_count: int = 3,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new webhook.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            name: Webhook name
            url: Webhook URL
            events: List of event types to subscribe to
            secret: Optional webhook secret for signature verification
            headers: Optional custom headers
            timeout_seconds: Request timeout
            retry_count: Number of retry attempts
            metadata: Optional metadata
            
        Returns:
            Webhook ID
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate inputs
        self._validate_webhook_config(user_id, tenant_id, name, url, events)
        
        # Check user's webhook limit
        existing_webhooks = self.list_user_webhooks(user_id)
        active_webhooks = [w for w in existing_webhooks if w.status == WebhookStatus.ACTIVE]
        
        if len(active_webhooks) >= self.max_webhooks_per_user:
            raise ValidationError(f"Maximum number of webhooks ({self.max_webhooks_per_user}) reached")
        
        # Generate webhook ID and secret
        webhook_id = self._generate_webhook_id()
        if not secret:
            secret = self._generate_webhook_secret()
        
        # Create webhook config
        webhook_config = WebhookConfig(
            webhook_id=webhook_id,
            user_id=user_id,
            tenant_id=tenant_id,
            name=name,
            url=url,
            secret=secret,
            events=events,
            status=WebhookStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            headers=headers or {},
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            metadata=metadata or {}
        )
        
        # Store in DynamoDB
        try:
            self.table.put_item(
                Item={
                    'PK': f"WEBHOOK#{webhook_id}",
                    'SK': f"CONFIG#{webhook_id}",
                    'GSI1PK': f"USER#{user_id}",
                    'GSI1SK': f"WEBHOOK#{webhook_id}",
                    'GSI2PK': f"TENANT#{tenant_id}",
                    'GSI2SK': f"WEBHOOK#{webhook_id}",
                    'webhook_id': webhook_id,
                    'user_id': user_id,
                    'tenant_id': tenant_id,
                    'name': name,
                    'url': url,
                    'secret': secret,
                    'events': [event.value for event in events],
                    'status': webhook_config.status.value,
                    'created_at': webhook_config.created_at.isoformat(),
                    'updated_at': webhook_config.updated_at.isoformat(),
                    'headers': headers or {},
                    'timeout_seconds': timeout_seconds,
                    'retry_count': retry_count,
                    'success_count': 0,
                    'failure_count': 0,
                    'metadata': metadata or {}
                }
            )
            
            logger.info(f"Created webhook {webhook_id} for user {user_id}")
            return webhook_id
            
        except ClientError as e:
            logger.error(f"Failed to create webhook: {e}")
            raise ValidationError("Failed to create webhook")
    
    def get_webhook(self, webhook_id: str) -> WebhookConfig:
        """
        Get webhook configuration.
        
        Args:
            webhook_id: Webhook identifier
            
        Returns:
            WebhookConfig object
            
        Raises:
            NotFoundError: If webhook not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': f"WEBHOOK#{webhook_id}",
                    'SK': f"CONFIG#{webhook_id}"
                }
            )
            
            if 'Item' not in response:
                raise NotFoundError("Webhook not found")
            
            item = response['Item']
            
            return WebhookConfig(
                webhook_id=item['webhook_id'],
                user_id=item['user_id'],
                tenant_id=item['tenant_id'],
                name=item['name'],
                url=item['url'],
                secret=item['secret'],
                events=[WebhookEventType(event) for event in item.get('events', [])],
                status=WebhookStatus(item.get('status', 'active')),
                created_at=datetime.fromisoformat(item['created_at']),
                updated_at=datetime.fromisoformat(item['updated_at']),
                headers=item.get('headers', {}),
                timeout_seconds=item.get('timeout_seconds', 30),
                retry_count=item.get('retry_count', 3),
                retry_delay_seconds=item.get('retry_delay_seconds', 60),
                last_delivery_at=datetime.fromisoformat(item['last_delivery_at']) if item.get('last_delivery_at') else None,
                success_count=item.get('success_count', 0),
                failure_count=item.get('failure_count', 0),
                metadata=item.get('metadata', {})
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get webhook {webhook_id}: {e}")
            raise NotFoundError("Webhook not found")
    
    def update_webhook(self, webhook_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update webhook configuration.
        
        Args:
            webhook_id: Webhook identifier
            user_id: User identifier (for authorization)
            updates: Dictionary of updates to apply
            
        Returns:
            True if update was successful
            
        Raises:
            NotFoundError: If webhook not found
            ValidationError: If user doesn't own the webhook or updates are invalid
        """
        try:
            # Get webhook to verify ownership
            webhook = self.get_webhook(webhook_id)
            
            if webhook.user_id != user_id:
                raise ValidationError("You don't have permission to update this webhook")
            
            # Validate allowed updates
            allowed_fields = ['name', 'url', 'events', 'headers', 'timeout_seconds', 'retry_count', 'metadata']
            update_expression_parts = []
            expression_values = {}
            
            for field, value in updates.items():
                if field not in allowed_fields:
                    raise ValidationError(f"Field '{field}' cannot be updated")
                
                # Special handling for events
                if field == 'events':
                    if not isinstance(value, list):
                        raise ValidationError("Events must be a list")
                    
                    # Validate event types
                    try:
                        events = [WebhookEventType(event) for event in value]
                        value = [event.value for event in events]
                    except ValueError as e:
                        raise ValidationError(f"Invalid event type: {e}")
                
                update_expression_parts.append(f"{field} = :{field}")
                expression_values[f":{field}"] = value
            
            if not update_expression_parts:
                raise ValidationError("No valid updates provided")
            
            # Add updated timestamp
            update_expression_parts.append("updated_at = :updated_at")
            expression_values[":updated_at"] = datetime.utcnow().isoformat()
            
            # Perform update
            self.table.update_item(
                Key={
                    'PK': f"WEBHOOK#{webhook_id}",
                    'SK': f"CONFIG#{webhook_id}"
                },
                UpdateExpression=f"SET {', '.join(update_expression_parts)}",
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"Updated webhook {webhook_id} for user {user_id}")
            return True
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to update webhook {webhook_id}: {e}")
            return False
    
    def delete_webhook(self, webhook_id: str, user_id: str) -> bool:
        """
        Delete a webhook.
        
        Args:
            webhook_id: Webhook identifier
            user_id: User identifier (for authorization)
            
        Returns:
            True if deletion was successful
            
        Raises:
            NotFoundError: If webhook not found
            ValidationError: If user doesn't own the webhook
        """
        try:
            # Get webhook to verify ownership
            webhook = self.get_webhook(webhook_id)
            
            if webhook.user_id != user_id:
                raise ValidationError("You don't have permission to delete this webhook")
            
            # Delete from DynamoDB
            self.table.delete_item(
                Key={
                    'PK': f"WEBHOOK#{webhook_id}",
                    'SK': f"CONFIG#{webhook_id}"
                }
            )
            
            logger.info(f"Deleted webhook {webhook_id} for user {user_id}")
            return True
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete webhook {webhook_id}: {e}")
            return False
    
    def list_user_webhooks(self, user_id: str) -> List[WebhookConfig]:
        """
        List webhooks for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of WebhookConfig objects
        """
        try:
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f"USER#{user_id}"
                }
            )
            
            webhooks = []
            for item in response['Items']:
                webhook = WebhookConfig(
                    webhook_id=item['webhook_id'],
                    user_id=item['user_id'],
                    tenant_id=item['tenant_id'],
                    name=item['name'],
                    url=item['url'],
                    secret=item['secret'],
                    events=[WebhookEventType(event) for event in item.get('events', [])],
                    status=WebhookStatus(item.get('status', 'active')),
                    created_at=datetime.fromisoformat(item['created_at']),
                    updated_at=datetime.fromisoformat(item['updated_at']),
                    headers=item.get('headers', {}),
                    timeout_seconds=item.get('timeout_seconds', 30),
                    retry_count=item.get('retry_count', 3),
                    retry_delay_seconds=item.get('retry_delay_seconds', 60),
                    last_delivery_at=datetime.fromisoformat(item['last_delivery_at']) if item.get('last_delivery_at') else None,
                    success_count=item.get('success_count', 0),
                    failure_count=item.get('failure_count', 0),
                    metadata=item.get('metadata', {})
                )
                webhooks.append(webhook)
            
            return webhooks
            
        except Exception as e:
            logger.error(f"Failed to list webhooks for user {user_id}: {e}")
            return []
    
    async def trigger_webhook_event(self, tenant_id: str, event_type: WebhookEventType,
                                  payload: Dict[str, Any], user_id: Optional[str] = None) -> List[str]:
        """
        Trigger webhook events for all matching webhooks.
        
        Args:
            tenant_id: Tenant identifier
            event_type: Event type
            payload: Event payload
            user_id: Optional user identifier for user-specific events
            
        Returns:
            List of event IDs created
        """
        try:
            # Find matching webhooks
            if user_id:
                webhooks = self.list_user_webhooks(user_id)
            else:
                webhooks = self.list_tenant_webhooks(tenant_id)
            
            # Filter webhooks that subscribe to this event type
            matching_webhooks = [
                webhook for webhook in webhooks
                if webhook.status == WebhookStatus.ACTIVE and event_type in webhook.events
            ]
            
            if not matching_webhooks:
                logger.info(f"No matching webhooks found for event {event_type.value}")
                return []
            
            # Create webhook events
            event_ids = []
            for webhook in matching_webhooks:
                event_id = await self._create_webhook_event(
                    webhook.webhook_id, event_type, payload, tenant_id, webhook.user_id
                )
                if event_id:
                    event_ids.append(event_id)
            
            logger.info(f"Created {len(event_ids)} webhook events for {event_type.value}")
            return event_ids
            
        except Exception as e:
            logger.error(f"Failed to trigger webhook events: {e}")
            return []
    
    async def deliver_webhook_event(self, event_id: str) -> bool:
        """
        Deliver a webhook event.
        
        Args:
            event_id: Event identifier
            
        Returns:
            True if delivery was successful
        """
        try:
            # Get event details
            event = await self._get_webhook_event(event_id)
            if not event:
                logger.error(f"Webhook event {event_id} not found")
                return False
            
            # Get webhook configuration
            webhook = self.get_webhook(event.webhook_id)
            if webhook.status != WebhookStatus.ACTIVE:
                logger.warning(f"Webhook {event.webhook_id} is not active")
                return False
            
            # Prepare payload
            delivery_payload = {
                'event_id': event.event_id,
                'event_type': event.event_type.value,
                'timestamp': event.created_at.isoformat(),
                'tenant_id': event.tenant_id,
                'data': event.payload
            }
            
            # Generate signature
            signature = self._generate_signature(
                json.dumps(delivery_payload, sort_keys=True),
                webhook.secret
            )
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'MultiCloudCostAnalytics-Webhook/1.0',
                self.signature_header: signature,
                self.timestamp_header: str(int(datetime.utcnow().timestamp()))
            }
            headers.update(webhook.headers)
            
            # Deliver webhook
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=webhook.timeout_seconds)) as session:
                async with session.post(
                    webhook.url,
                    json=delivery_payload,
                    headers=headers
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        # Success
                        await self._update_event_status(event_id, DeliveryStatus.SUCCESS)
                        await self._update_webhook_stats(webhook.webhook_id, success=True)
                        logger.info(f"Successfully delivered webhook event {event_id}")
                        return True
                    else:
                        # HTTP error
                        error_message = f"HTTP {response.status}: {await response.text()}"
                        await self._handle_delivery_failure(event, error_message)
                        return False
            
        except asyncio.TimeoutError:
            error_message = "Request timeout"
            await self._handle_delivery_failure(event, error_message)
            return False
        except Exception as e:
            error_message = f"Delivery error: {str(e)}"
            await self._handle_delivery_failure(event, error_message)
            return False
    
    def list_tenant_webhooks(self, tenant_id: str) -> List[WebhookConfig]:
        """
        List all webhooks for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of WebhookConfig objects
        """
        try:
            response = self.table.query(
                IndexName='GSI2',
                KeyConditionExpression='GSI2PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f"TENANT#{tenant_id}"
                }
            )
            
            webhooks = []
            for item in response['Items']:
                webhook = WebhookConfig.from_dict(item)
                webhooks.append(webhook)
            
            return webhooks
            
        except Exception as e:
            logger.error(f"Failed to list webhooks for tenant {tenant_id}: {e}")
            return []
    
    def _generate_webhook_id(self) -> str:
        """Generate a unique webhook ID."""
        return f"wh_{secrets.token_urlsafe(16)}"
    
    def _generate_webhook_secret(self) -> str:
        """Generate a webhook secret."""
        return secrets.token_urlsafe(32)
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def _validate_webhook_config(self, user_id: str, tenant_id: str, name: str,
                                url: str, events: List[WebhookEventType]):
        """Validate webhook configuration."""
        if not user_id or not user_id.strip():
            raise ValidationError("User ID is required")
        
        if not tenant_id or not tenant_id.strip():
            raise ValidationError("Tenant ID is required")
        
        if not name or not name.strip():
            raise ValidationError("Webhook name is required")
        
        if len(name) > 100:
            raise ValidationError("Webhook name must be 100 characters or less")
        
        if not url or not url.strip():
            raise ValidationError("Webhook URL is required")
        
        if not url.startswith(('http://', 'https://')):
            raise ValidationError("Webhook URL must start with http:// or https://")
        
        if not events:
            raise ValidationError("At least one event type must be specified")
        
        # Validate event types
        valid_events = [e.value for e in WebhookEventType]
        for event in events:
            if not isinstance(event, WebhookEventType):
                raise ValidationError(f"Invalid event type: {event}")
    
    async def _create_webhook_event(self, webhook_id: str, event_type: WebhookEventType,
                                  payload: Dict[str, Any], tenant_id: str, user_id: str) -> Optional[str]:
        """Create a webhook event."""
        try:
            event_id = f"evt_{secrets.token_urlsafe(16)}"
            
            # Validate payload size
            payload_size = len(json.dumps(payload))
            if payload_size > self.max_payload_size:
                logger.error(f"Payload too large: {payload_size} bytes")
                return None
            
            # Store event in DynamoDB
            self.table.put_item(
                Item={
                    'PK': f"EVENT#{event_id}",
                    'SK': f"WEBHOOK#{webhook_id}",
                    'GSI1PK': f"WEBHOOK#{webhook_id}",
                    'GSI1SK': f"EVENT#{event_id}",
                    'event_id': event_id,
                    'webhook_id': webhook_id,
                    'event_type': event_type.value,
                    'payload': payload,
                    'created_at': datetime.utcnow().isoformat(),
                    'tenant_id': tenant_id,
                    'user_id': user_id,
                    'delivery_attempts': 0,
                    'delivery_status': DeliveryStatus.PENDING.value,
                    'ttl': int((datetime.utcnow() + timedelta(days=7)).timestamp())
                }
            )
            
            # Queue for delivery if SQS is available
            if self.queue_url:
                await self._queue_webhook_delivery(event_id)
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to create webhook event: {e}")
            return None
    
    async def _queue_webhook_delivery(self, event_id: str):
        """Queue webhook event for delivery."""
        try:
            self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps({
                    'event_id': event_id,
                    'action': 'deliver_webhook'
                }),
                DelaySeconds=0
            )
        except Exception as e:
            logger.error(f"Failed to queue webhook delivery: {e}")
    
    async def _get_webhook_event(self, event_id: str) -> Optional[WebhookEvent]:
        """Get webhook event details."""
        try:
            # This would need to be implemented based on your DynamoDB schema
            # For now, return None
            return None
        except Exception as e:
            logger.error(f"Failed to get webhook event: {e}")
            return None
    
    async def _update_event_status(self, event_id: str, status: DeliveryStatus):
        """Update webhook event delivery status."""
        try:
            # Implementation would update the event status in DynamoDB
            pass
        except Exception as e:
            logger.error(f"Failed to update event status: {e}")
    
    async def _update_webhook_stats(self, webhook_id: str, success: bool):
        """Update webhook delivery statistics."""
        try:
            if success:
                self.table.update_item(
                    Key={
                        'PK': f"WEBHOOK#{webhook_id}",
                        'SK': f"CONFIG#{webhook_id}"
                    },
                    UpdateExpression='SET success_count = success_count + :inc, last_delivery_at = :now',
                    ExpressionAttributeValues={
                        ':inc': 1,
                        ':now': datetime.utcnow().isoformat()
                    }
                )
            else:
                self.table.update_item(
                    Key={
                        'PK': f"WEBHOOK#{webhook_id}",
                        'SK': f"CONFIG#{webhook_id}"
                    },
                    UpdateExpression='SET failure_count = failure_count + :inc',
                    ExpressionAttributeValues={
                        ':inc': 1
                    }
                )
        except Exception as e:
            logger.error(f"Failed to update webhook stats: {e}")
    
    async def _handle_delivery_failure(self, event: WebhookEvent, error_message: str):
        """Handle webhook delivery failure."""
        try:
            event.delivery_attempts += 1
            event.last_attempt_at = datetime.utcnow()
            event.error_message = error_message
            
            # Get webhook config for retry settings
            webhook = self.get_webhook(event.webhook_id)
            
            if event.delivery_attempts < webhook.retry_count:
                # Schedule retry
                event.delivery_status = DeliveryStatus.RETRYING
                event.next_retry_at = datetime.utcnow() + timedelta(
                    seconds=webhook.retry_delay_seconds * (2 ** (event.delivery_attempts - 1))
                )
                
                # Queue for retry
                if self.queue_url:
                    self.sqs.send_message(
                        QueueUrl=self.queue_url,
                        MessageBody=json.dumps({
                            'event_id': event.event_id,
                            'action': 'deliver_webhook'
                        }),
                        DelaySeconds=int((event.next_retry_at - datetime.utcnow()).total_seconds())
                    )
            else:
                # Max retries reached
                event.delivery_status = DeliveryStatus.FAILED
            
            # Update webhook stats
            await self._update_webhook_stats(event.webhook_id, success=False)
            
            logger.warning(f"Webhook delivery failed for event {event.event_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to handle delivery failure: {e}")


# Webhook event payload templates
WEBHOOK_EVENT_TEMPLATES = {
    WebhookEventType.ANOMALY_DETECTED: {
        'anomaly_id': str,
        'severity': str,
        'description': str,
        'affected_services': list,
        'cost_impact': float,
        'detection_method': str,
        'confidence_score': float,
        'recommended_actions': list,
        'provider': str,
        'account_id': str,
        'detected_at': str
    },
    
    WebhookEventType.BUDGET_EXCEEDED: {
        'budget_id': str,
        'budget_name': str,
        'budget_amount': float,
        'actual_amount': float,
        'percentage_used': float,
        'period': str,
        'provider': str,
        'account_id': str,
        'exceeded_at': str
    },
    
    WebhookEventType.COST_SPIKE: {
        'spike_id': str,
        'service': str,
        'provider': str,
        'account_id': str,
        'current_cost': float,
        'previous_cost': float,
        'increase_percentage': float,
        'spike_duration': str,
        'detected_at': str
    }
}