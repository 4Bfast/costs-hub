"""
Real-Time Integration Service

Integrates real-time monitoring with the existing cost analytics system,
providing a unified interface for real-time cost monitoring and alerting.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio

try:
    from ..models.multi_cloud_models import UnifiedCostRecord
    from ..models.config_models import ClientConfig
    from ..utils.logging import create_logger as get_logger
    from .real_time_monitoring_service import (
        RealTimeMonitoringService, MonitoringThreshold, AlertSeverity, AlertType
    )
    from .notification_service import (
        NotificationService, NotificationConfig, NotificationChannel
    )
    from .ai_insights_service import AIInsightsService
    from .cost_history_storage_service import CostHistoryStorageService
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.multi_cloud_models import UnifiedCostRecord
    from models.config_models import ClientConfig
    from utils.logging import create_logger
    from real_time_monitoring_service import (
        RealTimeMonitoringService, MonitoringThreshold, AlertSeverity, AlertType
    )
    from notification_service import (
        NotificationService, NotificationConfig, NotificationChannel
    )
    from ai_insights_service import AIInsightsService
    from cost_history_storage_service import CostHistoryStorageService
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class RealTimeIntegrationService:
    """
    Main integration service for real-time cost monitoring
    
    Provides a unified interface that integrates:
    - Real-time monitoring and alerting
    - AI-powered insights
    - Multi-channel notifications
    - Historical data storage
    - EventBridge integration
    """
    
    def __init__(self, use_ai: bool = True, region: str = "us-east-1"):
        """
        Initialize real-time integration service
        
        Args:
            use_ai: Whether to use AI-powered features
            region: AWS region for services
        """
        self.use_ai = use_ai
        self.region = region
        
        # Initialize core services
        self.monitoring_service = RealTimeMonitoringService(use_ai=use_ai, region=region)
        self.notification_service = NotificationService(region=region)
        self.ai_insights_service = AIInsightsService(use_ai=use_ai)
        self.storage_service = CostHistoryStorageService()
        
        # Setup alert callback
        self.monitoring_service.add_alert_callback(self._handle_alert_callback)
        
        # Service state
        self.client_configurations: Dict[str, Dict[str, Any]] = {}
        self.processing_queue = asyncio.Queue()
        self.is_running = False
    
    async def start_service(self):
        """Start the real-time integration service"""
        if self.is_running:
            logger.warning("Service is already running")
            return
        
        self.is_running = True
        logger.info("Starting real-time integration service")
        
        # Start background processing
        asyncio.create_task(self._process_queue())
        
        logger.info("Real-time integration service started successfully")
    
    async def stop_service(self):
        """Stop the real-time integration service"""
        self.is_running = False
        logger.info("Real-time integration service stopped")
    
    async def setup_client_monitoring(
        self,
        client_id: str,
        client_config: ClientConfig,
        monitoring_config: Dict[str, Any]
    ):
        """
        Setup comprehensive monitoring for a client
        
        Args:
            client_id: Client identifier
            client_config: Client configuration
            monitoring_config: Monitoring configuration including thresholds and notifications
        """
        try:
            logger.info(f"Setting up monitoring for client {client_id}")
            
            # Store client configuration
            self.client_configurations[client_id] = {
                'client_config': client_config,
                'monitoring_config': monitoring_config,
                'setup_timestamp': datetime.utcnow()
            }
            
            # Enable monitoring
            self.monitoring_service.enable_monitoring(client_id)
            
            # Setup thresholds
            await self._setup_client_thresholds(client_id, monitoring_config.get('thresholds', []))
            
            # Setup notifications
            await self._setup_client_notifications(client_id, monitoring_config.get('notifications', []))
            
            logger.info(f"Monitoring setup completed for client {client_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup monitoring for client {client_id}: {e}")
            raise
    
    async def process_cost_data(
        self,
        client_id: str,
        cost_record: UnifiedCostRecord,
        store_historical: bool = True
    ) -> Dict[str, Any]:
        """
        Process new cost data through the real-time monitoring pipeline
        
        Args:
            client_id: Client identifier
            cost_record: New cost record to process
            store_historical: Whether to store in historical database
            
        Returns:
            Processing results including alerts generated
        """
        try:
            processing_start = datetime.utcnow()
            
            # Store historical data if requested
            if store_historical:
                await self.storage_service.store_cost_record(cost_record)
            
            # Get historical context
            historical_data = await self._get_historical_context(client_id, cost_record.date)
            
            # Process through monitoring service
            alerts = await self.monitoring_service.process_cost_update(
                client_id, cost_record, historical_data
            )
            
            # Calculate processing metrics
            processing_time = (datetime.utcnow() - processing_start).total_seconds()
            
            result = {
                'client_id': client_id,
                'processing_timestamp': processing_start.isoformat(),
                'processing_time_seconds': processing_time,
                'alerts_generated': len(alerts),
                'alerts': [
                    {
                        'alert_id': alert.alert_id,
                        'type': alert.alert_type.value,
                        'severity': alert.severity.value,
                        'title': alert.title
                    } for alert in alerts
                ],
                'cost_record': {
                    'date': cost_record.date,
                    'total_cost': cost_record.total_cost,
                    'provider': cost_record.provider.value,
                    'services_count': len(cost_record.services)
                },
                'monitoring_status': self.monitoring_service.get_monitoring_status(client_id)
            }
            
            logger.info(f"Processed cost data for client {client_id}: {len(alerts)} alerts generated")
            return result
            
        except Exception as e:
            logger.error(f"Cost data processing failed for client {client_id}: {e}")
            raise
    
    async def get_real_time_insights(
        self,
        client_id: str,
        include_ai_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive real-time insights for a client
        
        Args:
            client_id: Client identifier
            include_ai_analysis: Whether to include AI-powered analysis
            
        Returns:
            Real-time insights and monitoring status
        """
        try:
            # Get monitoring status
            monitoring_status = self.monitoring_service.get_monitoring_status(client_id)
            
            # Get active alerts
            active_alerts = self.monitoring_service.get_active_alerts(client_id)
            
            # Get notification status
            notification_status = self.notification_service.get_notification_status(client_id)
            
            insights = {
                'client_id': client_id,
                'timestamp': datetime.utcnow().isoformat(),
                'monitoring_status': monitoring_status,
                'active_alerts': [
                    {
                        'alert_id': alert.alert_id,
                        'type': alert.alert_type.value,
                        'severity': alert.severity.value,
                        'title': alert.title,
                        'timestamp': alert.timestamp.isoformat(),
                        'affected_services': alert.affected_services
                    } for alert in active_alerts
                ],
                'notification_status': notification_status
            }
            
            # Add AI analysis if requested and available
            if include_ai_analysis and self.use_ai:
                try:
                    historical_data = await self._get_historical_context(client_id)
                    if historical_data and len(historical_data) >= 7:
                        ai_insights = self.ai_insights_service.generate_insights(
                            client_id, historical_data[-30:]  # Last 30 days
                        )
                        
                        insights['ai_analysis'] = {
                            'confidence_score': ai_insights.confidence_score,
                            'risk_level': ai_insights.risk_assessment.get('overall_risk_level', 'unknown'),
                            'key_insights': ai_insights.key_insights[:5],
                            'recommendations_count': len(ai_insights.recommendations),
                            'anomalies_count': len(ai_insights.anomalies)
                        }
                except Exception as e:
                    logger.error(f"AI analysis failed for client {client_id}: {e}")
                    insights['ai_analysis'] = {'error': 'AI analysis unavailable'}
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get real-time insights for client {client_id}: {e}")
            raise
    
    async def update_monitoring_configuration(
        self,
        client_id: str,
        config_updates: Dict[str, Any]
    ):
        """
        Update monitoring configuration for a client
        
        Args:
            client_id: Client identifier
            config_updates: Configuration updates to apply
        """
        try:
            if client_id not in self.client_configurations:
                raise ValueError(f"Client {client_id} not configured for monitoring")
            
            current_config = self.client_configurations[client_id]['monitoring_config']
            
            # Update thresholds if provided
            if 'thresholds' in config_updates:
                # Remove existing thresholds
                for threshold in current_config.get('thresholds', []):
                    self.monitoring_service.remove_threshold(client_id, threshold['threshold_id'])
                
                # Add new thresholds
                await self._setup_client_thresholds(client_id, config_updates['thresholds'])
                current_config['thresholds'] = config_updates['thresholds']
            
            # Update notifications if provided
            if 'notifications' in config_updates:
                # Remove existing notification configs
                for notification in current_config.get('notifications', []):
                    channel = NotificationChannel(notification['channel'])
                    self.notification_service.remove_notification_config(client_id, channel)
                
                # Add new notification configs
                await self._setup_client_notifications(client_id, config_updates['notifications'])
                current_config['notifications'] = config_updates['notifications']
            
            # Update monitoring enabled status
            if 'enabled' in config_updates:
                if config_updates['enabled']:
                    self.monitoring_service.enable_monitoring(client_id)
                else:
                    self.monitoring_service.disable_monitoring(client_id)
                current_config['enabled'] = config_updates['enabled']
            
            # Update timestamp
            self.client_configurations[client_id]['last_updated'] = datetime.utcnow()
            
            logger.info(f"Updated monitoring configuration for client {client_id}")
            
        except Exception as e:
            logger.error(f"Failed to update monitoring configuration for client {client_id}: {e}")
            raise
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get overall service status and metrics"""
        return {
            'service_running': self.is_running,
            'region': self.region,
            'ai_enabled': self.use_ai,
            'clients_configured': len(self.client_configurations),
            'monitoring_metrics': self.monitoring_service.get_performance_metrics(),
            'notification_metrics': self.notification_service.get_service_metrics(),
            'queue_size': self.processing_queue.qsize() if hasattr(self.processing_queue, 'qsize') else 0
        }
    
    async def _setup_client_thresholds(self, client_id: str, threshold_configs: List[Dict[str, Any]]):
        """Setup monitoring thresholds for a client"""
        for threshold_config in threshold_configs:
            threshold = MonitoringThreshold(
                threshold_id=threshold_config['threshold_id'],
                client_id=client_id,
                threshold_type=threshold_config['threshold_type'],
                threshold_value=threshold_config['threshold_value'],
                comparison_operator=threshold_config['comparison_operator'],
                time_window_minutes=threshold_config.get('time_window_minutes', 5),
                evaluation_periods=threshold_config.get('evaluation_periods', 1),
                alert_severity=AlertSeverity(threshold_config.get('alert_severity', 'medium')),
                enabled=threshold_config.get('enabled', True),
                metadata=threshold_config.get('metadata', {})
            )
            
            self.monitoring_service.add_threshold(threshold)
    
    async def _setup_client_notifications(self, client_id: str, notification_configs: List[Dict[str, Any]]):
        """Setup notification configurations for a client"""
        for notification_config in notification_configs:
            config = NotificationConfig(
                client_id=client_id,
                channel=NotificationChannel(notification_config['channel']),
                enabled=notification_config.get('enabled', True),
                config=notification_config['config'],
                severity_filter=[
                    AlertSeverity(s) for s in notification_config.get('severity_filter', [])
                ],
                alert_type_filter=[
                    AlertType(t) for t in notification_config.get('alert_type_filter', [])
                ],
                quiet_hours=notification_config.get('quiet_hours'),
                rate_limit=notification_config.get('rate_limit')
            )
            
            self.notification_service.add_notification_config(config)
    
    async def _get_historical_context(
        self, 
        client_id: str, 
        current_date: Optional[str] = None
    ) -> List[UnifiedCostRecord]:
        """Get historical cost data for context"""
        try:
            # Get last 60 days of data for context
            end_date = datetime.fromisoformat(current_date) if current_date else datetime.utcnow()
            start_date = end_date - timedelta(days=60)
            
            historical_data = await self.storage_service.get_cost_records(
                client_id=client_id,
                start_date=start_date.isoformat()[:10],
                end_date=end_date.isoformat()[:10]
            )
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Failed to get historical context for client {client_id}: {e}")
            return []
    
    def _handle_alert_callback(self, alert):
        """Handle alert callback from monitoring service"""
        # Queue alert for notification processing
        asyncio.create_task(self._process_alert_notifications(alert))
    
    async def _process_alert_notifications(self, alert):
        """Process alert notifications asynchronously"""
        try:
            results = await self.notification_service.send_alert_notifications(alert)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Alert {alert.alert_id} notifications: {success_count}/{total_count} successful")
            
        except Exception as e:
            logger.error(f"Alert notification processing failed for {alert.alert_id}: {e}")
    
    async def _process_queue(self):
        """Background queue processing"""
        while self.is_running:
            try:
                # Process any queued items
                await asyncio.sleep(1)  # Simple polling for now
                
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(5)  # Wait before retrying