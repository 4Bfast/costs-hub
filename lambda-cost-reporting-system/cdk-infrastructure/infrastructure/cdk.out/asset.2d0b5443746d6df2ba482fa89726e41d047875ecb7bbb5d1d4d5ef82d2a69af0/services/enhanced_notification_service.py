"""
Enhanced Notification Service

This service provides comprehensive notification functionality with support
for multiple channels (email, Slack, webhooks, SMS) and intelligent routing.
"""

import boto3
import json
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from botocore.exceptions import ClientError

from ..models.multi_cloud_models import CloudProvider
from ..models.multi_tenant_models import NotificationPreferences
from ..services.webhook_service import WebhookService, WebhookEventType
from ..utils.api_response import ValidationError


logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    TEAMS = "teams"
    DISCORD = "discord"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NotificationTemplate:
    """Notification template structure."""
    template_id: str
    name: str
    channel: NotificationChannel
    subject_template: str
    body_template: str
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationRequest:
    """Notification request structure."""
    notification_id: str
    tenant_id: str
    user_id: Optional[str]
    channel: NotificationChannel
    priority: NotificationPriority
    template_id: str
    variables: Dict[str, Any]
    recipients: List[str]
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: NotificationStatus = NotificationStatus.PENDING
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedNotificationService:
    """
    Enhanced notification service with multi-channel support.
    
    Provides intelligent notification routing, template management,
    delivery tracking, and retry mechanisms across multiple channels.
    """
    
    def __init__(self, region: str = 'us-east-1', table_name: str = 'notifications',
                 webhook_service: Optional[WebhookService] = None):
        """
        Initialize the enhanced notification service.
        
        Args:
            region: AWS region
            table_name: DynamoDB table for notification tracking
            webhook_service: Optional webhook service instance
        """
        self.region = region
        self.table_name = table_name
        self.webhook_service = webhook_service
        
        # Initialize AWS services
        self.ses = boto3.client('ses', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        
        # Configuration
        self.max_retries = 3
        self.retry_delays = [60, 300, 900]  # 1min, 5min, 15min
        self.default_expiry_hours = 24
        
        # Templates
        self.templates = self._load_default_templates()
    
    async def send_notification(self, tenant_id: str, template_id: str,
                              variables: Dict[str, Any], recipients: List[str],
                              channels: List[NotificationChannel] = None,
                              priority: NotificationPriority = NotificationPriority.MEDIUM,
                              user_id: Optional[str] = None,
                              scheduled_at: Optional[datetime] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Send notification through specified channels.
        
        Args:
            tenant_id: Tenant identifier
            template_id: Notification template ID
            variables: Template variables
            recipients: List of recipients
            channels: List of channels to use (if None, uses preferences)
            priority: Notification priority
            user_id: Optional user identifier
            scheduled_at: Optional scheduled delivery time
            metadata: Optional metadata
            
        Returns:
            List of notification IDs created
        """
        try:
            # Get notification preferences if channels not specified
            if not channels:
                channels = await self._get_preferred_channels(tenant_id, user_id, priority)
            
            # Validate template
            template = self._get_template(template_id)
            if not template:
                raise ValidationError(f"Template {template_id} not found")
            
            # Create notification requests
            notification_ids = []
            for channel in channels:
                # Filter recipients by channel
                channel_recipients = await self._filter_recipients_by_channel(
                    recipients, channel, tenant_id
                )
                
                if not channel_recipients:
                    continue
                
                # Create notification request
                notification_id = await self._create_notification_request(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    channel=channel,
                    priority=priority,
                    template_id=template_id,
                    variables=variables,
                    recipients=channel_recipients,
                    scheduled_at=scheduled_at,
                    metadata=metadata or {}
                )
                
                if notification_id:
                    notification_ids.append(notification_id)
                    
                    # Send immediately if not scheduled
                    if not scheduled_at:
                        await self._deliver_notification(notification_id)
            
            return notification_ids
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return []
    
    async def send_anomaly_notification(self, tenant_id: str, anomaly_data: Dict[str, Any],
                                      user_id: Optional[str] = None) -> List[str]:
        """
        Send anomaly detection notification.
        
        Args:
            tenant_id: Tenant identifier
            anomaly_data: Anomaly information
            user_id: Optional user identifier
            
        Returns:
            List of notification IDs
        """
        # Determine priority based on severity
        severity = anomaly_data.get('severity', 'medium').lower()
        priority_map = {
            'low': NotificationPriority.LOW,
            'medium': NotificationPriority.MEDIUM,
            'high': NotificationPriority.HIGH,
            'critical': NotificationPriority.CRITICAL
        }
        priority = priority_map.get(severity, NotificationPriority.MEDIUM)
        
        # Get recipients from tenant preferences
        recipients = await self._get_notification_recipients(tenant_id, 'anomaly')
        
        # Send notification
        notification_ids = await self.send_notification(
            tenant_id=tenant_id,
            template_id='anomaly_detected',
            variables=anomaly_data,
            recipients=recipients,
            priority=priority,
            user_id=user_id,
            metadata={'event_type': 'anomaly_detected'}
        )
        
        # Also trigger webhook if configured
        if self.webhook_service:
            await self.webhook_service.trigger_webhook_event(
                tenant_id=tenant_id,
                event_type=WebhookEventType.ANOMALY_DETECTED,
                payload=anomaly_data,
                user_id=user_id
            )
        
        return notification_ids
    
    async def send_budget_alert(self, tenant_id: str, budget_data: Dict[str, Any],
                              user_id: Optional[str] = None) -> List[str]:
        """
        Send budget exceeded notification.
        
        Args:
            tenant_id: Tenant identifier
            budget_data: Budget information
            user_id: Optional user identifier
            
        Returns:
            List of notification IDs
        """
        # Budget alerts are always high priority
        priority = NotificationPriority.HIGH
        
        # Get recipients
        recipients = await self._get_notification_recipients(tenant_id, 'budget_alert')
        
        # Send notification
        notification_ids = await self.send_notification(
            tenant_id=tenant_id,
            template_id='budget_exceeded',
            variables=budget_data,
            recipients=recipients,
            priority=priority,
            user_id=user_id,
            metadata={'event_type': 'budget_exceeded'}
        )
        
        # Trigger webhook
        if self.webhook_service:
            await self.webhook_service.trigger_webhook_event(
                tenant_id=tenant_id,
                event_type=WebhookEventType.BUDGET_EXCEEDED,
                payload=budget_data,
                user_id=user_id
            )
        
        return notification_ids
    
    async def send_forecast_notification(self, tenant_id: str, forecast_data: Dict[str, Any],
                                       user_id: Optional[str] = None) -> List[str]:
        """
        Send forecast update notification.
        
        Args:
            tenant_id: Tenant identifier
            forecast_data: Forecast information
            user_id: Optional user identifier
            
        Returns:
            List of notification IDs
        """
        priority = NotificationPriority.MEDIUM
        
        # Get recipients
        recipients = await self._get_notification_recipients(tenant_id, 'forecast')
        
        # Send notification
        notification_ids = await self.send_notification(
            tenant_id=tenant_id,
            template_id='forecast_updated',
            variables=forecast_data,
            recipients=recipients,
            priority=priority,
            user_id=user_id,
            metadata={'event_type': 'forecast_updated'}
        )
        
        # Trigger webhook
        if self.webhook_service:
            await self.webhook_service.trigger_webhook_event(
                tenant_id=tenant_id,
                event_type=WebhookEventType.FORECAST_UPDATED,
                payload=forecast_data,
                user_id=user_id
            )
        
        return notification_ids
    
    async def send_cost_spike_notification(self, tenant_id: str, spike_data: Dict[str, Any],
                                         user_id: Optional[str] = None) -> List[str]:
        """
        Send cost spike notification.
        
        Args:
            tenant_id: Tenant identifier
            spike_data: Cost spike information
            user_id: Optional user identifier
            
        Returns:
            List of notification IDs
        """
        # Cost spikes are high priority
        priority = NotificationPriority.HIGH
        
        # Get recipients
        recipients = await self._get_notification_recipients(tenant_id, 'anomaly')
        
        # Send notification
        notification_ids = await self.send_notification(
            tenant_id=tenant_id,
            template_id='cost_spike',
            variables=spike_data,
            recipients=recipients,
            priority=priority,
            user_id=user_id,
            metadata={'event_type': 'cost_spike'}
        )
        
        # Trigger webhook
        if self.webhook_service:
            await self.webhook_service.trigger_webhook_event(
                tenant_id=tenant_id,
                event_type=WebhookEventType.COST_SPIKE,
                payload=spike_data,
                user_id=user_id
            )
        
        return notification_ids
    
    async def _deliver_notification(self, notification_id: str) -> bool:
        """
        Deliver a notification.
        
        Args:
            notification_id: Notification identifier
            
        Returns:
            True if delivery was successful
        """
        try:
            # Get notification request
            request = await self._get_notification_request(notification_id)
            if not request:
                logger.error(f"Notification request {notification_id} not found")
                return False
            
            # Check if expired
            if request.expires_at and datetime.utcnow() > request.expires_at:
                await self._update_notification_status(
                    notification_id, NotificationStatus.FAILED, "Notification expired"
                )
                return False
            
            # Get template
            template = self._get_template(request.template_id)
            if not template:
                await self._update_notification_status(
                    notification_id, NotificationStatus.FAILED, "Template not found"
                )
                return False
            
            # Render template
            subject = self._render_template(template.subject_template, request.variables)
            body = self._render_template(template.body_template, request.variables)
            
            # Deliver based on channel
            success = False
            error_message = None
            
            try:
                if request.channel == NotificationChannel.EMAIL:
                    success = await self._deliver_email(request.recipients, subject, body)
                elif request.channel == NotificationChannel.SLACK:
                    success = await self._deliver_slack(request.recipients, subject, body, request.variables)
                elif request.channel == NotificationChannel.SMS:
                    success = await self._deliver_sms(request.recipients, body)
                elif request.channel == NotificationChannel.TEAMS:
                    success = await self._deliver_teams(request.recipients, subject, body, request.variables)
                else:
                    error_message = f"Unsupported channel: {request.channel.value}"
                    
            except Exception as e:
                error_message = str(e)
                success = False
            
            # Update status
            if success:
                await self._update_notification_status(notification_id, NotificationStatus.SENT)
                logger.info(f"Successfully delivered notification {notification_id}")
            else:
                await self._handle_delivery_failure(request, error_message or "Delivery failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to deliver notification {notification_id}: {e}")
            return False
    
    async def _deliver_email(self, recipients: List[str], subject: str, body: str) -> bool:
        """Deliver email notification."""
        try:
            # Send email using SES
            response = self.ses.send_email(
                Source='noreply@multicloudsanalytics.com',  # Configure this
                Destination={'ToAddresses': recipients},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': body, 'Charset': 'UTF-8'},
                        'Text': {'Data': self._html_to_text(body), 'Charset': 'UTF-8'}
                    }
                }
            )
            
            return 'MessageId' in response
            
        except ClientError as e:
            logger.error(f"SES email delivery failed: {e}")
            return False
    
    async def _deliver_slack(self, recipients: List[str], subject: str, body: str, variables: Dict[str, Any]) -> bool:
        """Deliver Slack notification."""
        try:
            # Format Slack message
            slack_message = {
                'text': subject,
                'blocks': [
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': f"*{subject}*"
                        }
                    },
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': self._html_to_markdown(body)
                        }
                    }
                ]
            }
            
            # Add fields for structured data
            if 'cost_impact' in variables:
                slack_message['blocks'].append({
                    'type': 'section',
                    'fields': [
                        {
                            'type': 'mrkdwn',
                            'text': f"*Cost Impact:* ${variables['cost_impact']:.2f}"
                        },
                        {
                            'type': 'mrkdwn',
                            'text': f"*Provider:* {variables.get('provider', 'N/A')}"
                        }
                    ]
                })
            
            # Send to each webhook URL (recipients are webhook URLs for Slack)
            success_count = 0
            for webhook_url in recipients:
                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=slack_message) as response:
                        if response.status == 200:
                            success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Slack delivery failed: {e}")
            return False
    
    async def _deliver_sms(self, recipients: List[str], message: str) -> bool:
        """Deliver SMS notification."""
        try:
            # Truncate message for SMS
            sms_message = message[:160] if len(message) > 160 else message
            
            success_count = 0
            for phone_number in recipients:
                try:
                    response = self.sns.publish(
                        PhoneNumber=phone_number,
                        Message=sms_message
                    )
                    if 'MessageId' in response:
                        success_count += 1
                except ClientError as e:
                    logger.error(f"SMS delivery failed for {phone_number}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"SMS delivery failed: {e}")
            return False
    
    async def _deliver_teams(self, recipients: List[str], subject: str, body: str, variables: Dict[str, Any]) -> bool:
        """Deliver Microsoft Teams notification."""
        try:
            # Format Teams message
            teams_message = {
                '@type': 'MessageCard',
                '@context': 'http://schema.org/extensions',
                'themeColor': '0076D7',
                'summary': subject,
                'sections': [
                    {
                        'activityTitle': subject,
                        'activitySubtitle': 'Multi-Cloud Cost Analytics',
                        'text': self._html_to_text(body),
                        'facts': []
                    }
                ]
            }
            
            # Add facts for structured data
            if 'cost_impact' in variables:
                teams_message['sections'][0]['facts'].extend([
                    {'name': 'Cost Impact', 'value': f"${variables['cost_impact']:.2f}"},
                    {'name': 'Provider', 'value': variables.get('provider', 'N/A')}
                ])
            
            # Send to each webhook URL
            success_count = 0
            for webhook_url in recipients:
                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=teams_message) as response:
                        if response.status == 200:
                            success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Teams delivery failed: {e}")
            return False
    
    async def _get_preferred_channels(self, tenant_id: str, user_id: Optional[str],
                                    priority: NotificationPriority) -> List[NotificationChannel]:
        """Get preferred notification channels based on tenant/user preferences."""
        # This would typically query the tenant/user preferences
        # For now, return default channels based on priority
        if priority == NotificationPriority.CRITICAL:
            return [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.SLACK]
        elif priority == NotificationPriority.HIGH:
            return [NotificationChannel.EMAIL, NotificationChannel.SLACK]
        else:
            return [NotificationChannel.EMAIL]
    
    async def _get_notification_recipients(self, tenant_id: str, notification_type: str) -> List[str]:
        """Get notification recipients for a tenant and notification type."""
        # This would typically query the tenant's notification preferences
        # For now, return a default list
        return ['admin@example.com']  # Configure this based on tenant preferences
    
    async def _filter_recipients_by_channel(self, recipients: List[str], channel: NotificationChannel,
                                          tenant_id: str) -> List[str]:
        """Filter recipients based on channel capabilities."""
        if channel == NotificationChannel.EMAIL:
            # Filter for valid email addresses
            return [r for r in recipients if '@' in r]
        elif channel == NotificationChannel.SMS:
            # Filter for phone numbers
            return [r for r in recipients if r.startswith('+') or r.isdigit()]
        elif channel in [NotificationChannel.SLACK, NotificationChannel.TEAMS]:
            # These would be webhook URLs from tenant configuration
            return await self._get_webhook_urls(tenant_id, channel)
        else:
            return recipients
    
    async def _get_webhook_urls(self, tenant_id: str, channel: NotificationChannel) -> List[str]:
        """Get webhook URLs for a tenant and channel."""
        # This would query tenant configuration for webhook URLs
        return []
    
    def _get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get notification template by ID."""
        return self.templates.get(template_id)
    
    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Render template with variables."""
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        # Simple HTML to text conversion
        import re
        text = re.sub('<[^<]+?>', '', html)
        return text.strip()
    
    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown for Slack."""
        # Simple HTML to Markdown conversion
        import re
        markdown = html
        markdown = re.sub(r'<strong>(.*?)</strong>', r'*\1*', markdown)
        markdown = re.sub(r'<b>(.*?)</b>', r'*\1*', markdown)
        markdown = re.sub(r'<em>(.*?)</em>', r'_\1_', markdown)
        markdown = re.sub(r'<i>(.*?)</i>', r'_\1_', markdown)
        markdown = re.sub('<[^<]+?>', '', markdown)
        return markdown.strip()
    
    def _load_default_templates(self) -> Dict[str, NotificationTemplate]:
        """Load default notification templates."""
        return {
            'anomaly_detected': NotificationTemplate(
                template_id='anomaly_detected',
                name='Anomaly Detected',
                channel=NotificationChannel.EMAIL,
                subject_template='Cost Anomaly Detected - {severity} Priority',
                body_template='''
                <h2>Cost Anomaly Detected</h2>
                <p><strong>Severity:</strong> {severity}</p>
                <p><strong>Description:</strong> {description}</p>
                <p><strong>Cost Impact:</strong> ${cost_impact:.2f}</p>
                <p><strong>Provider:</strong> {provider}</p>
                <p><strong>Affected Services:</strong> {affected_services}</p>
                <p><strong>Detection Method:</strong> {detection_method}</p>
                <p><strong>Confidence Score:</strong> {confidence_score:.2%}</p>
                <h3>Recommended Actions:</h3>
                <ul>
                {recommended_actions}
                </ul>
                ''',
                variables=['severity', 'description', 'cost_impact', 'provider', 'affected_services', 
                          'detection_method', 'confidence_score', 'recommended_actions']
            ),
            
            'budget_exceeded': NotificationTemplate(
                template_id='budget_exceeded',
                name='Budget Exceeded',
                channel=NotificationChannel.EMAIL,
                subject_template='Budget Alert - {budget_name} Exceeded',
                body_template='''
                <h2>Budget Alert</h2>
                <p><strong>Budget Name:</strong> {budget_name}</p>
                <p><strong>Budget Amount:</strong> ${budget_amount:.2f}</p>
                <p><strong>Actual Amount:</strong> ${actual_amount:.2f}</p>
                <p><strong>Percentage Used:</strong> {percentage_used:.1f}%</p>
                <p><strong>Period:</strong> {period}</p>
                <p><strong>Provider:</strong> {provider}</p>
                <p><strong>Account:</strong> {account_id}</p>
                ''',
                variables=['budget_name', 'budget_amount', 'actual_amount', 'percentage_used', 
                          'period', 'provider', 'account_id']
            ),
            
            'forecast_updated': NotificationTemplate(
                template_id='forecast_updated',
                name='Forecast Updated',
                channel=NotificationChannel.EMAIL,
                subject_template='Cost Forecast Updated',
                body_template='''
                <h2>Cost Forecast Updated</h2>
                <p><strong>Forecast Period:</strong> {forecast_period}</p>
                <p><strong>Predicted Cost:</strong> ${predicted_cost:.2f}</p>
                <p><strong>Confidence Level:</strong> {confidence_level}</p>
                <p><strong>Trend:</strong> {trend}</p>
                <p><strong>Provider:</strong> {provider}</p>
                ''',
                variables=['forecast_period', 'predicted_cost', 'confidence_level', 'trend', 'provider']
            ),
            
            'cost_spike': NotificationTemplate(
                template_id='cost_spike',
                name='Cost Spike Detected',
                channel=NotificationChannel.EMAIL,
                subject_template='Cost Spike Alert - {service}',
                body_template='''
                <h2>Cost Spike Detected</h2>
                <p><strong>Service:</strong> {service}</p>
                <p><strong>Provider:</strong> {provider}</p>
                <p><strong>Account:</strong> {account_id}</p>
                <p><strong>Current Cost:</strong> ${current_cost:.2f}</p>
                <p><strong>Previous Cost:</strong> ${previous_cost:.2f}</p>
                <p><strong>Increase:</strong> {increase_percentage:.1f}%</p>
                <p><strong>Duration:</strong> {spike_duration}</p>
                ''',
                variables=['service', 'provider', 'account_id', 'current_cost', 'previous_cost', 
                          'increase_percentage', 'spike_duration']
            )
        }
    
    async def _create_notification_request(self, tenant_id: str, user_id: Optional[str],
                                         channel: NotificationChannel, priority: NotificationPriority,
                                         template_id: str, variables: Dict[str, Any],
                                         recipients: List[str], scheduled_at: Optional[datetime],
                                         metadata: Dict[str, Any]) -> Optional[str]:
        """Create a notification request."""
        try:
            import secrets
            notification_id = f"notif_{secrets.token_urlsafe(16)}"
            
            expires_at = datetime.utcnow() + timedelta(hours=self.default_expiry_hours)
            
            # Store in DynamoDB
            self.table.put_item(
                Item={
                    'PK': f"NOTIFICATION#{notification_id}",
                    'SK': f"REQUEST#{notification_id}",
                    'GSI1PK': f"TENANT#{tenant_id}",
                    'GSI1SK': f"NOTIFICATION#{notification_id}",
                    'notification_id': notification_id,
                    'tenant_id': tenant_id,
                    'user_id': user_id,
                    'channel': channel.value,
                    'priority': priority.value,
                    'template_id': template_id,
                    'variables': variables,
                    'recipients': recipients,
                    'created_at': datetime.utcnow().isoformat(),
                    'scheduled_at': scheduled_at.isoformat() if scheduled_at else None,
                    'expires_at': expires_at.isoformat(),
                    'status': NotificationStatus.PENDING.value,
                    'attempts': 0,
                    'metadata': metadata,
                    'ttl': int(expires_at.timestamp())
                }
            )
            
            return notification_id
            
        except Exception as e:
            logger.error(f"Failed to create notification request: {e}")
            return None
    
    async def _get_notification_request(self, notification_id: str) -> Optional[NotificationRequest]:
        """Get notification request by ID."""
        try:
            response = self.table.get_item(
                Key={
                    'PK': f"NOTIFICATION#{notification_id}",
                    'SK': f"REQUEST#{notification_id}"
                }
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            return NotificationRequest(
                notification_id=item['notification_id'],
                tenant_id=item['tenant_id'],
                user_id=item.get('user_id'),
                channel=NotificationChannel(item['channel']),
                priority=NotificationPriority(item['priority']),
                template_id=item['template_id'],
                variables=item['variables'],
                recipients=item['recipients'],
                created_at=datetime.fromisoformat(item['created_at']),
                scheduled_at=datetime.fromisoformat(item['scheduled_at']) if item.get('scheduled_at') else None,
                expires_at=datetime.fromisoformat(item['expires_at']),
                status=NotificationStatus(item['status']),
                attempts=item.get('attempts', 0),
                last_attempt_at=datetime.fromisoformat(item['last_attempt_at']) if item.get('last_attempt_at') else None,
                error_message=item.get('error_message'),
                metadata=item.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Failed to get notification request: {e}")
            return None
    
    async def _update_notification_status(self, notification_id: str, status: NotificationStatus,
                                        error_message: Optional[str] = None):
        """Update notification status."""
        try:
            update_expression = 'SET #status = :status, last_attempt_at = :now, attempts = attempts + :inc'
            expression_values = {
                ':status': status.value,
                ':now': datetime.utcnow().isoformat(),
                ':inc': 1
            }
            expression_names = {'#status': 'status'}
            
            if error_message:
                update_expression += ', error_message = :error'
                expression_values[':error'] = error_message
            
            self.table.update_item(
                Key={
                    'PK': f"NOTIFICATION#{notification_id}",
                    'SK': f"REQUEST#{notification_id}"
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            
        except Exception as e:
            logger.error(f"Failed to update notification status: {e}")
    
    async def _handle_delivery_failure(self, request: NotificationRequest, error_message: str):
        """Handle notification delivery failure."""
        try:
            if request.attempts < self.max_retries:
                # Schedule retry
                await self._update_notification_status(
                    request.notification_id, NotificationStatus.RETRYING, error_message
                )
                
                # Schedule retry (this would typically use SQS with delay)
                retry_delay = self.retry_delays[min(request.attempts, len(self.retry_delays) - 1)]
                logger.info(f"Scheduling retry for notification {request.notification_id} in {retry_delay} seconds")
                
            else:
                # Max retries reached
                await self._update_notification_status(
                    request.notification_id, NotificationStatus.FAILED, error_message
                )
                logger.error(f"Notification {request.notification_id} failed after {request.attempts} attempts")
                
        except Exception as e:
            logger.error(f"Failed to handle delivery failure: {e}")