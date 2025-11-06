"""
Collection Scheduler and Queue Management

This module implements EventBridge-based scheduling for different collection frequencies,
SQS queues for asynchronous processing, and priority-based processing for critical clients.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import boto3
from botocore.exceptions import ClientError

from ..models.multi_cloud_models import CloudProvider
from ..models.provider_models import DateRange
from ..models.multi_tenant_models import MultiCloudClient
from ..services.cost_collection_orchestrator import (
    CostCollectionOrchestrator, CollectionPriority, CollectionStatus
)
from ..services.multi_tenant_client_manager import MultiTenantClientManager
from ..utils.logging import create_logger


logger = create_logger(__name__)


class ScheduleFrequency(Enum):
    """Schedule frequency options."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class QueuePriority(Enum):
    """Queue priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ScheduleRule:
    """EventBridge schedule rule configuration."""
    rule_name: str
    frequency: ScheduleFrequency
    cron_expression: str
    target_queue: str
    priority: QueuePriority = QueuePriority.NORMAL
    enabled: bool = True
    description: Optional[str] = None
    
    def to_eventbridge_rule(self) -> Dict[str, Any]:
        """Convert to EventBridge rule format."""
        return {
            'Name': self.rule_name,
            'ScheduleExpression': self.cron_expression,
            'Description': self.description or f"{self.frequency.value} cost collection",
            'State': 'ENABLED' if self.enabled else 'DISABLED'
        }


@dataclass
class QueueMessage:
    """SQS queue message for cost collection."""
    message_id: str
    client_id: str
    providers: List[CloudProvider]
    date_range: DateRange
    priority: CollectionPriority
    frequency: ScheduleFrequency
    created_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 3
    
    def to_sqs_message(self) -> Dict[str, Any]:
        """Convert to SQS message format."""
        return {
            'Id': self.message_id,
            'MessageBody': json.dumps({
                'message_id': self.message_id,
                'client_id': self.client_id,
                'providers': [p.value for p in self.providers],
                'date_range': {
                    'start_date': self.date_range.start_date.isoformat(),
                    'end_date': self.date_range.end_date.isoformat()
                },
                'priority': self.priority.value,
                'frequency': self.frequency.value,
                'created_at': self.created_at.isoformat(),
                'retry_count': self.retry_count,
                'max_retries': self.max_retries
            }),
            'MessageAttributes': {
                'Priority': {
                    'StringValue': self.priority.value,
                    'DataType': 'String'
                },
                'ClientId': {
                    'StringValue': self.client_id,
                    'DataType': 'String'
                },
                'Frequency': {
                    'StringValue': self.frequency.value,
                    'DataType': 'String'
                }
            }
        }
    
    @classmethod
    def from_sqs_message(cls, message: Dict[str, Any]) -> 'QueueMessage':
        """Create QueueMessage from SQS message."""
        body = json.loads(message['Body'])
        
        return cls(
            message_id=body['message_id'],
            client_id=body['client_id'],
            providers=[CloudProvider(p) for p in body['providers']],
            date_range=DateRange(
                start_date=datetime.fromisoformat(body['date_range']['start_date']),
                end_date=datetime.fromisoformat(body['date_range']['end_date'])
            ),
            priority=CollectionPriority(body['priority']),
            frequency=ScheduleFrequency(body['frequency']),
            created_at=datetime.fromisoformat(body['created_at']),
            retry_count=body.get('retry_count', 0),
            max_retries=body.get('max_retries', 3)
        )


class CollectionScheduler:
    """
    EventBridge-based scheduler for cost collection operations.
    
    Manages:
    - EventBridge rules for different collection frequencies
    - SQS queues for asynchronous processing
    - Priority-based message routing
    - Client-specific scheduling preferences
    """
    
    def __init__(
        self,
        client_manager: MultiTenantClientManager,
        orchestrator: CostCollectionOrchestrator,
        region: str = 'us-east-1',
        queue_prefix: str = 'cost-collection'
    ):
        """
        Initialize the collection scheduler.
        
        Args:
            client_manager: Multi-tenant client manager
            orchestrator: Cost collection orchestrator
            region: AWS region
            queue_prefix: SQS queue name prefix
        """
        self.client_manager = client_manager
        self.orchestrator = orchestrator
        self.region = region
        self.queue_prefix = queue_prefix
        
        self.logger = create_logger(f"{__name__}.CollectionScheduler")
        
        # AWS clients
        self.eventbridge = boto3.client('events', region_name=region)
        self.sqs = boto3.client('sqs', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        
        # Queue URLs
        self.queue_urls: Dict[QueuePriority, str] = {}
        
        # Schedule rules
        self.schedule_rules: Dict[ScheduleFrequency, ScheduleRule] = {}
        
        # Processing state
        self.processing_messages: Set[str] = set()
    
    async def initialize(self):
        """Initialize scheduler resources."""
        await self._create_queues()
        await self._create_schedule_rules()
        self.logger.info("Collection scheduler initialized")
    
    async def _create_queues(self):
        """Create SQS queues for different priorities."""
        queue_configs = {
            QueuePriority.CRITICAL: {
                'VisibilityTimeoutSeconds': '300',
                'MessageRetentionPeriod': '1209600',  # 14 days
                'ReceiveMessageWaitTimeSeconds': '20',  # Long polling
                'DelaySeconds': '0'
            },
            QueuePriority.HIGH: {
                'VisibilityTimeoutSeconds': '600',
                'MessageRetentionPeriod': '1209600',
                'ReceiveMessageWaitTimeSeconds': '20',
                'DelaySeconds': '0'
            },
            QueuePriority.NORMAL: {
                'VisibilityTimeoutSeconds': '900',
                'MessageRetentionPeriod': '1209600',
                'ReceiveMessageWaitTimeSeconds': '20',
                'DelaySeconds': '0'
            },
            QueuePriority.LOW: {
                'VisibilityTimeoutSeconds': '1800',
                'MessageRetentionPeriod': '1209600',
                'ReceiveMessageWaitTimeSeconds': '20',
                'DelaySeconds': '300'  # 5 minute delay for low priority
            }
        }
        
        for priority, config in queue_configs.items():
            queue_name = f"{self.queue_prefix}-{priority.value}"
            
            try:
                # Try to get existing queue
                response = self.sqs.get_queue_url(QueueName=queue_name)
                queue_url = response['QueueUrl']
                self.logger.info(f"Using existing queue: {queue_name}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                    # Create new queue
                    response = self.sqs.create_queue(
                        QueueName=queue_name,
                        Attributes=config
                    )
                    queue_url = response['QueueUrl']
                    self.logger.info(f"Created new queue: {queue_name}")
                else:
                    raise
            
            self.queue_urls[priority] = queue_url
            
            # Create DLQ for failed messages
            dlq_name = f"{queue_name}-dlq"
            try:
                dlq_response = self.sqs.get_queue_url(QueueName=dlq_name)
            except ClientError as e:
                if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                    dlq_response = self.sqs.create_queue(
                        QueueName=dlq_name,
                        Attributes={
                            'MessageRetentionPeriod': '1209600',
                            'ReceiveMessageWaitTimeSeconds': '20'
                        }
                    )
                    self.logger.info(f"Created DLQ: {dlq_name}")
    
    async def _create_schedule_rules(self):
        """Create EventBridge schedule rules."""
        # Define standard schedule rules
        rules = [
            ScheduleRule(
                rule_name=f"{self.queue_prefix}-hourly",
                frequency=ScheduleFrequency.HOURLY,
                cron_expression="cron(0 * * * ? *)",  # Every hour
                target_queue=self.queue_urls[QueuePriority.HIGH],
                priority=QueuePriority.HIGH,
                description="Hourly cost collection for critical clients"
            ),
            ScheduleRule(
                rule_name=f"{self.queue_prefix}-daily",
                frequency=ScheduleFrequency.DAILY,
                cron_expression="cron(0 6 * * ? *)",  # Daily at 6 AM UTC
                target_queue=self.queue_urls[QueuePriority.NORMAL],
                priority=QueuePriority.NORMAL,
                description="Daily cost collection for standard clients"
            ),
            ScheduleRule(
                rule_name=f"{self.queue_prefix}-weekly",
                frequency=ScheduleFrequency.WEEKLY,
                cron_expression="cron(0 8 ? * MON *)",  # Weekly on Monday at 8 AM UTC
                target_queue=self.queue_urls[QueuePriority.NORMAL],
                priority=QueuePriority.NORMAL,
                description="Weekly cost collection for all clients"
            ),
            ScheduleRule(
                rule_name=f"{self.queue_prefix}-monthly",
                frequency=ScheduleFrequency.MONTHLY,
                cron_expression="cron(0 10 1 * ? *)",  # Monthly on 1st at 10 AM UTC
                target_queue=self.queue_urls[QueuePriority.LOW],
                priority=QueuePriority.LOW,
                description="Monthly cost collection for all clients"
            )
        ]
        
        for rule in rules:
            try:
                # Create or update EventBridge rule
                self.eventbridge.put_rule(**rule.to_eventbridge_rule())
                
                # Add SQS target
                self.eventbridge.put_targets(
                    Rule=rule.rule_name,
                    Targets=[
                        {
                            'Id': '1',
                            'Arn': self._get_queue_arn(rule.target_queue),
                            'SqsParameters': {
                                'MessageGroupId': rule.frequency.value
                            }
                        }
                    ]
                )
                
                self.schedule_rules[rule.frequency] = rule
                self.logger.info(f"Created/updated schedule rule: {rule.rule_name}")
                
            except ClientError as e:
                self.logger.error(f"Error creating schedule rule {rule.rule_name}: {str(e)}")
                raise
    
    def _get_queue_arn(self, queue_url: str) -> str:
        """Get queue ARN from URL."""
        # Extract queue name from URL
        queue_name = queue_url.split('/')[-1]
        # Construct ARN
        account_id = boto3.client('sts').get_caller_identity()['Account']
        return f"arn:aws:sqs:{self.region}:{account_id}:{queue_name}"
    
    async def schedule_collection(
        self,
        client_id: str,
        frequency: ScheduleFrequency,
        providers: Optional[List[CloudProvider]] = None,
        priority: Optional[CollectionPriority] = None
    ) -> str:
        """
        Schedule a cost collection for a client.
        
        Args:
            client_id: Client identifier
            frequency: Collection frequency
            providers: List of providers (None for all)
            priority: Collection priority (None for auto-detection)
            
        Returns:
            Message ID
        """
        try:
            # Get client configuration
            client = await self.client_manager.get_client(client_id)
            if not client:
                raise ValueError(f"Client {client_id} not found")
            
            # Determine providers
            if providers is None:
                providers = list(client.cloud_accounts.keys())
            
            # Determine priority
            if priority is None:
                priority = self._determine_priority(client, frequency)
            
            # Calculate date range based on frequency
            date_range = self._calculate_date_range(frequency)
            
            # Create queue message
            message = QueueMessage(
                message_id=str(uuid.uuid4()),
                client_id=client_id,
                providers=providers,
                date_range=date_range,
                priority=priority,
                frequency=frequency
            )
            
            # Send to appropriate queue
            queue_priority = self._map_collection_to_queue_priority(priority)
            queue_url = self.queue_urls[queue_priority]
            
            response = self.sqs.send_message(
                QueueUrl=queue_url,
                **message.to_sqs_message()
            )
            
            self.logger.info(
                f"Scheduled collection for client {client_id}",
                extra={
                    'message_id': message.message_id,
                    'frequency': frequency.value,
                    'priority': priority.value,
                    'providers': [p.value for p in providers]
                }
            )
            
            return message.message_id
            
        except Exception as e:
            self.logger.error(f"Error scheduling collection for client {client_id}: {str(e)}")
            raise
    
    def _determine_priority(
        self,
        client: MultiCloudClient,
        frequency: ScheduleFrequency
    ) -> CollectionPriority:
        """Determine collection priority based on client and frequency."""
        # Critical clients get high priority
        if hasattr(client, 'tier') and client.tier == 'enterprise':
            return CollectionPriority.CRITICAL
        
        # Frequent collections get higher priority
        if frequency == ScheduleFrequency.HOURLY:
            return CollectionPriority.HIGH
        elif frequency == ScheduleFrequency.DAILY:
            return CollectionPriority.NORMAL
        else:
            return CollectionPriority.LOW
    
    def _calculate_date_range(self, frequency: ScheduleFrequency) -> DateRange:
        """Calculate date range based on frequency."""
        end_date = datetime.utcnow().date()
        
        if frequency == ScheduleFrequency.HOURLY:
            start_date = end_date - timedelta(days=1)
        elif frequency == ScheduleFrequency.DAILY:
            start_date = end_date - timedelta(days=1)
        elif frequency == ScheduleFrequency.WEEKLY:
            start_date = end_date - timedelta(days=7)
        elif frequency == ScheduleFrequency.MONTHLY:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=1)
        
        return DateRange(start_date=start_date, end_date=end_date)
    
    def _map_collection_to_queue_priority(
        self,
        collection_priority: CollectionPriority
    ) -> QueuePriority:
        """Map collection priority to queue priority."""
        mapping = {
            CollectionPriority.CRITICAL: QueuePriority.CRITICAL,
            CollectionPriority.HIGH: QueuePriority.HIGH,
            CollectionPriority.NORMAL: QueuePriority.NORMAL,
            CollectionPriority.LOW: QueuePriority.LOW
        }
        return mapping.get(collection_priority, QueuePriority.NORMAL)
    
    async def process_queue_messages(
        self,
        queue_priority: QueuePriority,
        max_messages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Process messages from a specific priority queue.
        
        Args:
            queue_priority: Queue priority to process
            max_messages: Maximum messages to process
            
        Returns:
            List of processing results
        """
        queue_url = self.queue_urls.get(queue_priority)
        if not queue_url:
            raise ValueError(f"Queue not found for priority: {queue_priority.value}")
        
        try:
            # Receive messages from queue
            response = self.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=20,  # Long polling
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            if not messages:
                return []
            
            self.logger.info(
                f"Processing {len(messages)} messages from {queue_priority.value} queue"
            )
            
            results = []
            
            for sqs_message in messages:
                try:
                    # Parse queue message
                    queue_message = QueueMessage.from_sqs_message(sqs_message)
                    
                    # Check if already processing
                    if queue_message.message_id in self.processing_messages:
                        continue
                    
                    self.processing_messages.add(queue_message.message_id)
                    
                    # Process the collection
                    result = await self._process_collection_message(queue_message)
                    results.append(result)
                    
                    # Delete message if successful
                    if result.get('success', False):
                        self.sqs.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=sqs_message['ReceiptHandle']
                        )
                    else:
                        # Handle retry logic
                        await self._handle_message_retry(
                            queue_url, sqs_message, queue_message, result
                        )
                    
                except Exception as e:
                    self.logger.error(f"Error processing message: {str(e)}")
                    results.append({
                        'message_id': sqs_message.get('MessageId', 'unknown'),
                        'success': False,
                        'error': str(e)
                    })
                finally:
                    # Remove from processing set
                    if queue_message.message_id in self.processing_messages:
                        self.processing_messages.remove(queue_message.message_id)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing queue {queue_priority.value}: {str(e)}")
            raise
    
    async def _process_collection_message(self, message: QueueMessage) -> Dict[str, Any]:
        """Process a single collection message."""
        try:
            self.logger.info(
                f"Processing collection message",
                extra={
                    'message_id': message.message_id,
                    'client_id': message.client_id,
                    'frequency': message.frequency.value
                }
            )
            
            # Execute cost collection orchestration
            orchestration_result = await self.orchestrator.orchestrate_collection(
                client_id=message.client_id,
                date_range=message.date_range,
                providers=message.providers,
                priority=message.priority
            )
            
            success = orchestration_result.status in [
                CollectionStatus.COMPLETED,
                CollectionStatus.PARTIAL
            ]
            
            return {
                'message_id': message.message_id,
                'orchestration_id': orchestration_result.orchestration_id,
                'success': success,
                'status': orchestration_result.status.value,
                'completed_tasks': orchestration_result.completed_tasks,
                'failed_tasks': orchestration_result.failed_tasks,
                'success_rate': orchestration_result.success_rate,
                'duration_seconds': orchestration_result.duration_seconds
            }
            
        except Exception as e:
            self.logger.error(
                f"Error processing collection message {message.message_id}: {str(e)}"
            )
            return {
                'message_id': message.message_id,
                'success': False,
                'error': str(e)
            }
    
    async def _handle_message_retry(
        self,
        queue_url: str,
        sqs_message: Dict[str, Any],
        queue_message: QueueMessage,
        result: Dict[str, Any]
    ):
        """Handle message retry logic."""
        queue_message.retry_count += 1
        
        if queue_message.retry_count <= queue_message.max_retries:
            # Calculate retry delay
            delay_seconds = min(60 * (2 ** queue_message.retry_count), 900)  # Max 15 minutes
            
            # Send back to queue with delay
            retry_message = queue_message.to_sqs_message()
            retry_message['DelaySeconds'] = delay_seconds
            
            self.sqs.send_message(QueueUrl=queue_url, **retry_message)
            
            self.logger.info(
                f"Retrying message {queue_message.message_id} in {delay_seconds} seconds"
            )
        else:
            # Send to DLQ
            dlq_url = queue_url + '-dlq'
            try:
                self.sqs.send_message(
                    QueueUrl=dlq_url,
                    MessageBody=json.dumps({
                        **json.loads(queue_message.to_sqs_message()['MessageBody']),
                        'final_error': result.get('error', 'Unknown error'),
                        'moved_to_dlq_at': datetime.utcnow().isoformat()
                    })
                )
                self.logger.warning(
                    f"Moved message {queue_message.message_id} to DLQ after {queue_message.retry_count} retries"
                )
            except Exception as e:
                self.logger.error(f"Error moving message to DLQ: {str(e)}")
        
        # Delete original message
        self.sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=sqs_message['ReceiptHandle']
        )
    
    async def schedule_batch_collection(
        self,
        client_ids: List[str],
        frequency: ScheduleFrequency,
        priority: CollectionPriority = CollectionPriority.NORMAL
    ) -> List[str]:
        """
        Schedule batch collection for multiple clients.
        
        Args:
            client_ids: List of client identifiers
            frequency: Collection frequency
            priority: Collection priority
            
        Returns:
            List of message IDs
        """
        message_ids = []
        
        for client_id in client_ids:
            try:
                message_id = await self.schedule_collection(
                    client_id=client_id,
                    frequency=frequency,
                    priority=priority
                )
                message_ids.append(message_id)
            except Exception as e:
                self.logger.error(f"Error scheduling collection for client {client_id}: {str(e)}")
        
        self.logger.info(f"Scheduled batch collection for {len(message_ids)} clients")
        return message_ids
    
    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get metrics for all queues."""
        metrics = {}
        
        for priority, queue_url in self.queue_urls.items():
            try:
                # Get queue attributes
                response = self.sqs.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=[
                        'ApproximateNumberOfMessages',
                        'ApproximateNumberOfMessagesNotVisible',
                        'ApproximateNumberOfMessagesDelayed'
                    ]
                )
                
                attributes = response['Attributes']
                metrics[priority.value] = {
                    'queue_url': queue_url,
                    'messages_available': int(attributes.get('ApproximateNumberOfMessages', 0)),
                    'messages_in_flight': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                    'messages_delayed': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0))
                }
                
            except Exception as e:
                self.logger.error(f"Error getting metrics for {priority.value} queue: {str(e)}")
                metrics[priority.value] = {'error': str(e)}
        
        return metrics
    
    def enable_schedule_rule(self, frequency: ScheduleFrequency) -> bool:
        """Enable a schedule rule."""
        rule = self.schedule_rules.get(frequency)
        if not rule:
            return False
        
        try:
            self.eventbridge.enable_rule(Name=rule.rule_name)
            rule.enabled = True
            self.logger.info(f"Enabled schedule rule: {rule.rule_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error enabling rule {rule.rule_name}: {str(e)}")
            return False
    
    def disable_schedule_rule(self, frequency: ScheduleFrequency) -> bool:
        """Disable a schedule rule."""
        rule = self.schedule_rules.get(frequency)
        if not rule:
            return False
        
        try:
            self.eventbridge.disable_rule(Name=rule.rule_name)
            rule.enabled = False
            self.logger.info(f"Disabled schedule rule: {rule.rule_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error disabling rule {rule.rule_name}: {str(e)}")
            return False
    
    async def cleanup_old_messages(self, max_age_hours: int = 24) -> Dict[str, int]:
        """Clean up old messages from queues."""
        cleanup_results = {}
        
        for priority, queue_url in self.queue_urls.items():
            try:
                # This is a simplified cleanup - in practice, you'd need to
                # implement message age tracking or use SQS message attributes
                cleanup_results[priority.value] = 0
                self.logger.info(f"Cleanup completed for {priority.value} queue")
                
            except Exception as e:
                self.logger.error(f"Error cleaning up {priority.value} queue: {str(e)}")
                cleanup_results[priority.value] = -1
        
        return cleanup_results
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the scheduler."""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'queues': {},
            'schedule_rules': {},
            'processing_messages': len(self.processing_messages)
        }
        
        # Check queue health
        for priority, queue_url in self.queue_urls.items():
            try:
                # Simple connectivity test
                self.sqs.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['ApproximateNumberOfMessages']
                )
                health_status['queues'][priority.value] = 'healthy'
            except Exception as e:
                health_status['queues'][priority.value] = f'error: {str(e)}'
                health_status['status'] = 'degraded'
        
        # Check schedule rules
        for frequency, rule in self.schedule_rules.items():
            try:
                response = self.eventbridge.describe_rule(Name=rule.rule_name)
                health_status['schedule_rules'][frequency.value] = {
                    'state': response['State'],
                    'enabled': rule.enabled
                }
            except Exception as e:
                health_status['schedule_rules'][frequency.value] = f'error: {str(e)}'
                health_status['status'] = 'degraded'
        
        return health_status