"""
Notification Service for Real-Time Alerts

Handles delivery of real-time cost alerts through multiple channels
including email, Slack, webhooks, and SMS.
"""

import boto3
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio

try:
    from ..utils.logging import create_logger as get_logger
    from .real_time_monitoring_service import RealTimeAlert, AlertSeverity, AlertType
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from utils.logging import create_logger
    from real_time_monitoring_service import RealTimeAlert, AlertSeverity, AlertType
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    TEAMS = "teams"


@dataclass
class NotificationConfig:
    """Notification configuration for a client"""
    client_id: str
    channel: NotificationChannel
    enabled: bool
    config: Dict[str, Any]  # Channel-specific configuration
    severity_filter: List[AlertSeverity]  # Which severities to notify
    alert_type_filter: List[AlertType]  # Which alert types to notify
    quiet_hours: Optional[Dict[str, str]]  # Start and end times for quiet hours
    rate_limit: Optional[Dict[str, int]]  # Rate limiting configuration


class EmailNotificationHandler:
    """Email notification handler using AWS SES"""
    
    def __init__(self, region: str = "us-east-1"):
        """Initialize email handler"""
        self.ses_client = boto3.client('ses', region_name=region)
        self.sender_email = "alerts@cost-analytics.com"  # Configure as needed
    
    async def send_notification(
        self, 
        alert: RealTimeAlert, 
        config: NotificationConfig
    ) -> bool:
        """Send email notification"""
        try:
            recipient_email = config.config.get('email_address')
            if not recipient_email:
                logger.error(f"No email address configured for client {alert.client_id}")
                return False
            
            subject = f"[{alert.severity.value.upper()}] {alert.title}"
            body = self._generate_email_body(alert)
            
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [recipient_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': body, 'Charset': 'UTF-8'},
                        'Text': {'Data': self._generate_text_body(alert), 'Charset': 'UTF-8'}
                    }
                }
            )
            
            logger.info(f"Email notification sent for alert {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Email notification failed for alert {alert.alert_id}: {e}")
            return False
    
    def _generate_email_body(self, alert: RealTimeAlert) -> str:
        """Generate HTML email body"""
        severity_colors = {
            'critical': '#dc3545',
            'high': '#fd7e14',
            'medium': '#ffc107',
            'low': '#28a745',
            'info': '#17a2b8'
        }
        
        color = severity_colors.get(alert.severity.value, '#6c757d')
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">{alert.title}</h2>
                    <p style="margin: 5px 0 0 0;">Severity: {alert.severity.value.upper()}</p>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none;">
                    <h3>Alert Details</h3>
                    <p><strong>Description:</strong> {alert.description}</p>
                    <p><strong>Current Value:</strong> ${alert.current_value:.2f}</p>
                    {f'<p><strong>Threshold:</strong> ${alert.threshold_value:.2f}</p>' if alert.threshold_value else ''}
                    <p><strong>Affected Services:</strong> {', '.join(alert.affected_services)}</p>
                    <p><strong>Timestamp:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    
                    {self._generate_ai_context_html(alert.ai_context) if alert.ai_context else ''}
                    
                    <h3>Recommended Actions</h3>
                    <ul>
                        {''.join(f'<li>{action}</li>' for action in alert.recommended_actions)}
                    </ul>
                </div>
                
                <div style="background-color: #e9ecef; padding: 10px; border-radius: 0 0 5px 5px; text-align: center; font-size: 12px; color: #6c757d;">
                    Cost Analytics Alert System - Client: {alert.client_id}
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_text_body(self, alert: RealTimeAlert) -> str:
        """Generate plain text email body"""
        text = f"""
COST ALERT - {alert.severity.value.upper()}

{alert.title}

Description: {alert.description}
Current Value: ${alert.current_value:.2f}
"""
        
        if alert.threshold_value:
            text += f"Threshold: ${alert.threshold_value:.2f}\n"
        
        text += f"""
Affected Services: {', '.join(alert.affected_services)}
Timestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

Recommended Actions:
"""
        
        for i, action in enumerate(alert.recommended_actions, 1):
            text += f"{i}. {action}\n"
        
        text += f"\nClient: {alert.client_id}\nAlert ID: {alert.alert_id}"
        
        return text
    
    def _generate_ai_context_html(self, ai_context: Dict[str, Any]) -> str:
        """Generate AI context HTML section"""
        if not ai_context:
            return ""
        
        html = "<h3>AI Analysis</h3><ul>"
        
        if 'confidence_score' in ai_context:
            html += f"<li><strong>Confidence:</strong> {ai_context['confidence_score']:.1%}</li>"
        
        if 'risk_level' in ai_context:
            html += f"<li><strong>Risk Level:</strong> {ai_context['risk_level'].title()}</li>"
        
        if 'anomaly_score' in ai_context:
            html += f"<li><strong>Anomaly Score:</strong> {ai_context['anomaly_score']:.2f}</li>"
        
        if 'trend_indicator' in ai_context:
            html += f"<li><strong>Trend:</strong> {ai_context['trend_indicator'].title()}</li>"
        
        html += "</ul>"
        return html


class SlackNotificationHandler:
    """Slack notification handler"""
    
    async def send_notification(
        self, 
        alert: RealTimeAlert, 
        config: NotificationConfig
    ) -> bool:
        """Send Slack notification"""
        try:
            webhook_url = config.config.get('webhook_url')
            if not webhook_url:
                logger.error(f"No Slack webhook URL configured for client {alert.client_id}")
                return False
            
            payload = self._generate_slack_payload(alert)
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Slack notification sent for alert {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Slack notification failed for alert {alert.alert_id}: {e}")
            return False
    
    def _generate_slack_payload(self, alert: RealTimeAlert) -> Dict[str, Any]:
        """Generate Slack message payload"""
        severity_colors = {
            'critical': '#dc3545',
            'high': '#fd7e14',
            'medium': '#ffc107',
            'low': '#28a745',
            'info': '#17a2b8'
        }
        
        color = severity_colors.get(alert.severity.value, '#6c757d')
        
        fields = [
            {
                "title": "Current Value",
                "value": f"${alert.current_value:.2f}",
                "short": True
            },
            {
                "title": "Affected Services",
                "value": ', '.join(alert.affected_services[:3]) + ('...' if len(alert.affected_services) > 3 else ''),
                "short": True
            }
        ]
        
        if alert.threshold_value:
            fields.append({
                "title": "Threshold",
                "value": f"${alert.threshold_value:.2f}",
                "short": True
            })
        
        if alert.ai_context and 'confidence_score' in alert.ai_context:
            fields.append({
                "title": "AI Confidence",
                "value": f"{alert.ai_context['confidence_score']:.1%}",
                "short": True
            })
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"🚨 {alert.title}",
                    "text": alert.description,
                    "fields": fields,
                    "footer": f"Cost Analytics | Client: {alert.client_id}",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        if alert.recommended_actions:
            actions_text = "\n".join(f"• {action}" for action in alert.recommended_actions[:3])
            payload["attachments"][0]["text"] += f"\n\n*Recommended Actions:*\n{actions_text}"
        
        return payload


class WebhookNotificationHandler:
    """Generic webhook notification handler"""
    
    async def send_notification(
        self, 
        alert: RealTimeAlert, 
        config: NotificationConfig
    ) -> bool:
        """Send webhook notification"""
        try:
            webhook_url = config.config.get('webhook_url')
            if not webhook_url:
                logger.error(f"No webhook URL configured for client {alert.client_id}")
                return False
            
            payload = {
                'alert_id': alert.alert_id,
                'client_id': alert.client_id,
                'alert_type': alert.alert_type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'description': alert.description,
                'current_value': alert.current_value,
                'threshold_value': alert.threshold_value,
                'affected_services': alert.affected_services,
                'timestamp': alert.timestamp.isoformat(),
                'ai_context': alert.ai_context,
                'recommended_actions': alert.recommended_actions,
                'metadata': alert.metadata
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'CostAnalytics-AlertSystem/1.0'
            }
            
            # Add custom headers if configured
            custom_headers = config.config.get('headers', {})
            headers.update(custom_headers)
            
            response = requests.post(
                webhook_url, 
                json=payload, 
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Webhook notification sent for alert {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Webhook notification failed for alert {alert.alert_id}: {e}")
            return False


class NotificationService:
    """Main notification service"""
    
    def __init__(self, region: str = "us-east-1"):
        """Initialize notification service"""
        self.region = region
        self.handlers = {
            NotificationChannel.EMAIL: EmailNotificationHandler(region),
            NotificationChannel.SLACK: SlackNotificationHandler(),
            NotificationChannel.WEBHOOK: WebhookNotificationHandler()
        }
        
        # Client notification configurations
        self.client_configs: Dict[str, List[NotificationConfig]] = {}
        
        # Rate limiting state
        self.rate_limit_state: Dict[str, Dict[str, Any]] = {}
    
    def add_notification_config(self, config: NotificationConfig):
        """Add notification configuration for a client"""
        if config.client_id not in self.client_configs:
            self.client_configs[config.client_id] = []
        
        # Remove existing config for same channel if exists
        self.client_configs[config.client_id] = [
            c for c in self.client_configs[config.client_id] 
            if c.channel != config.channel
        ]
        
        self.client_configs[config.client_id].append(config)
        logger.info(f"Added {config.channel.value} notification config for client {config.client_id}")
    
    def remove_notification_config(self, client_id: str, channel: NotificationChannel):
        """Remove notification configuration"""
        if client_id in self.client_configs:
            self.client_configs[client_id] = [
                c for c in self.client_configs[client_id] 
                if c.channel != channel
            ]
            logger.info(f"Removed {channel.value} notification config for client {client_id}")
    
    async def send_alert_notifications(self, alert: RealTimeAlert) -> Dict[str, bool]:
        """Send notifications for an alert through all configured channels"""
        results = {}
        
        client_configs = self.client_configs.get(alert.client_id, [])
        if not client_configs:
            logger.warning(f"No notification configs found for client {alert.client_id}")
            return results
        
        for config in client_configs:
            if not config.enabled:
                continue
            
            # Check severity filter
            if config.severity_filter and alert.severity not in config.severity_filter:
                continue
            
            # Check alert type filter
            if config.alert_type_filter and alert.alert_type not in config.alert_type_filter:
                continue
            
            # Check quiet hours
            if self._is_quiet_hours(config):
                logger.info(f"Skipping notification for {config.channel.value} due to quiet hours")
                continue
            
            # Check rate limiting
            if not self._check_rate_limit(alert.client_id, config):
                logger.info(f"Rate limit exceeded for {config.channel.value} notifications")
                continue
            
            # Send notification
            handler = self.handlers.get(config.channel)
            if handler:
                try:
                    success = await handler.send_notification(alert, config)
                    results[config.channel.value] = success
                    
                    if success:
                        self._update_rate_limit_state(alert.client_id, config)
                        
                except Exception as e:
                    logger.error(f"Notification handler failed for {config.channel.value}: {e}")
                    results[config.channel.value] = False
            else:
                logger.error(f"No handler found for channel {config.channel.value}")
                results[config.channel.value] = False
        
        return results
    
    def _is_quiet_hours(self, config: NotificationConfig) -> bool:
        """Check if current time is within quiet hours"""
        if not config.quiet_hours:
            return False
        
        try:
            current_time = datetime.utcnow().time()
            start_time = datetime.strptime(config.quiet_hours['start'], '%H:%M').time()
            end_time = datetime.strptime(config.quiet_hours['end'], '%H:%M').time()
            
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:  # Quiet hours span midnight
                return current_time >= start_time or current_time <= end_time
                
        except Exception as e:
            logger.error(f"Quiet hours check failed: {e}")
            return False
    
    def _check_rate_limit(self, client_id: str, config: NotificationConfig) -> bool:
        """Check if rate limit allows sending notification"""
        if not config.rate_limit:
            return True
        
        key = f"{client_id}_{config.channel.value}"
        current_time = datetime.utcnow()
        
        if key not in self.rate_limit_state:
            self.rate_limit_state[key] = {
                'count': 0,
                'window_start': current_time
            }
        
        state = self.rate_limit_state[key]
        window_minutes = config.rate_limit.get('window_minutes', 60)
        max_notifications = config.rate_limit.get('max_notifications', 10)
        
        # Reset window if expired
        if (current_time - state['window_start']).total_seconds() > window_minutes * 60:
            state['count'] = 0
            state['window_start'] = current_time
        
        return state['count'] < max_notifications
    
    def _update_rate_limit_state(self, client_id: str, config: NotificationConfig):
        """Update rate limit state after successful notification"""
        if not config.rate_limit:
            return
        
        key = f"{client_id}_{config.channel.value}"
        if key in self.rate_limit_state:
            self.rate_limit_state[key]['count'] += 1
    
    def get_notification_status(self, client_id: str) -> Dict[str, Any]:
        """Get notification status for a client"""
        configs = self.client_configs.get(client_id, [])
        
        return {
            'configured_channels': [config.channel.value for config in configs if config.enabled],
            'total_configs': len(configs),
            'enabled_configs': len([c for c in configs if c.enabled]),
            'rate_limit_status': {
                key.split('_', 1)[1]: state for key, state in self.rate_limit_state.items()
                if key.startswith(f"{client_id}_")
            }
        }
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get notification service metrics"""
        total_configs = sum(len(configs) for configs in self.client_configs.values())
        enabled_configs = sum(
            len([c for c in configs if c.enabled]) 
            for configs in self.client_configs.values()
        )
        
        return {
            'total_clients': len(self.client_configs),
            'total_configs': total_configs,
            'enabled_configs': enabled_configs,
            'supported_channels': [channel.value for channel in NotificationChannel],
            'active_rate_limits': len(self.rate_limit_state)
        }