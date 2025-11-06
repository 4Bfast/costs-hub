"""
Collection Monitoring and Observability Service

This module implements comprehensive logging with structured data, CloudWatch metrics
for collection performance, and distributed tracing with X-Ray integration for the
cost collection orchestration system.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import boto3
from botocore.exceptions import ClientError
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.core.models import subsegment

from ..models.multi_cloud_models import CloudProvider
from ..services.cost_collection_orchestrator import (
    OrchestrationResult, CollectionStatus, CollectionPriority
)
from ..services.collection_scheduler import ScheduleFrequency, QueuePriority
from ..utils.logging import create_logger


# Patch AWS SDK for X-Ray tracing
patch_all()

logger = create_logger(__name__)


class MetricType(Enum):
    """CloudWatch metric types."""
    COUNT = "Count"
    GAUGE = "None"
    RATE = "Count/Second"
    DURATION = "Seconds"
    PERCENTAGE = "Percent"


class AlarmSeverity(Enum):
    """Alarm severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricData:
    """CloudWatch metric data point."""
    metric_name: str
    value: Union[int, float]
    unit: MetricType
    dimensions: Dict[str, str] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_cloudwatch_metric(self) -> Dict[str, Any]:
        """Convert to CloudWatch metric format."""
        metric_data = {
            'MetricName': self.metric_name,
            'Value': self.value,
            'Unit': self.unit.value,
            'Timestamp': self.timestamp
        }
        
        if self.dimensions:
            metric_data['Dimensions'] = [
                {'Name': name, 'Value': value}
                for name, value in self.dimensions.items()
            ]
        
        return metric_data


@dataclass
class PerformanceMetrics:
    """Collection performance metrics."""
    orchestration_id: str
    client_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0
    providers_processed: List[CloudProvider] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def calculate_metrics(self):
        """Calculate derived metrics."""
        if self.end_time and self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        
        if self.total_tasks > 0:
            self.success_rate = self.completed_tasks / self.total_tasks * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'orchestration_id': self.orchestration_id,
            'client_id': self.client_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'success_rate': self.success_rate,
            'providers_processed': [p.value for p in self.providers_processed],
            'error_count': len(self.errors)
        }


class CollectionMonitoringService:
    """
    Comprehensive monitoring and observability service for cost collection.
    
    Provides:
    - Structured logging with correlation IDs
    - CloudWatch metrics for performance monitoring
    - X-Ray distributed tracing
    - Custom alarms and notifications
    - Performance analytics and reporting
    """
    
    def __init__(
        self,
        namespace: str = "CostAnalytics/Collection",
        region: str = "us-east-1",
        enable_xray: bool = True
    ):
        """
        Initialize the monitoring service.
        
        Args:
            namespace: CloudWatch metrics namespace
            region: AWS region
            enable_xray: Enable X-Ray tracing
        """
        self.namespace = namespace
        self.region = region
        self.enable_xray = enable_xray
        
        self.logger = create_logger(f"{__name__}.CollectionMonitoringService")
        
        # AWS clients
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.logs = boto3.client('logs', region_name=region)
        
        # Monitoring state
        self.active_orchestrations: Dict[str, PerformanceMetrics] = {}
        self.metric_buffer: List[MetricData] = []
        self.log_group_name = f"/aws/lambda/cost-collection-orchestrator"
        
        # Initialize log group
        self._ensure_log_group_exists()
    
    def _ensure_log_group_exists(self):
        """Ensure CloudWatch log group exists."""
        try:
            self.logs.create_log_group(
                logGroupName=self.log_group_name,
                tags={'Service': 'CostAnalytics', 'Component': 'Collection'}
            )
            self.logger.info(f"Created log group: {self.log_group_name}")
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                self.logger.error(f"Error creating log group: {str(e)}")
    
    @xray_recorder.capture('start_orchestration_monitoring')
    def start_orchestration_monitoring(
        self,
        orchestration_result: OrchestrationResult
    ) -> str:
        """
        Start monitoring an orchestration.
        
        Args:
            orchestration_result: Orchestration result to monitor
            
        Returns:
            Monitoring session ID
        """
        monitoring_id = str(uuid.uuid4())
        
        # Create performance metrics
        metrics = PerformanceMetrics(
            orchestration_id=orchestration_result.orchestration_id,
            client_id=orchestration_result.client_id,
            start_time=orchestration_result.started_at,
            total_tasks=orchestration_result.total_tasks,
            providers_processed=orchestration_result.providers_processed
        )
        
        self.active_orchestrations[monitoring_id] = metrics
        
        # Log orchestration start
        self._log_structured_event(
            event_type="orchestration_started",
            orchestration_id=orchestration_result.orchestration_id,
            client_id=orchestration_result.client_id,
            data={
                'monitoring_id': monitoring_id,
                'total_tasks': orchestration_result.total_tasks,
                'providers': [p.value for p in orchestration_result.providers_processed]
            }
        )
        
        # Send start metrics
        self._send_metric(
            MetricData(
                metric_name="OrchestrationStarted",
                value=1,
                unit=MetricType.COUNT,
                dimensions={
                    'ClientId': orchestration_result.client_id,
                    'Status': 'Started'
                }
            )
        )
        
        return monitoring_id
    
    @xray_recorder.capture('complete_orchestration_monitoring')
    def complete_orchestration_monitoring(
        self,
        monitoring_id: str,
        orchestration_result: OrchestrationResult
    ):
        """
        Complete monitoring for an orchestration.
        
        Args:
            monitoring_id: Monitoring session ID
            orchestration_result: Final orchestration result
        """
        if monitoring_id not in self.active_orchestrations:
            self.logger.warning(f"Monitoring session {monitoring_id} not found")
            return
        
        metrics = self.active_orchestrations[monitoring_id]
        
        # Update metrics
        metrics.end_time = orchestration_result.completed_at or datetime.utcnow()
        metrics.completed_tasks = orchestration_result.completed_tasks
        metrics.failed_tasks = orchestration_result.failed_tasks
        metrics.errors = orchestration_result.errors
        metrics.calculate_metrics()
        
        # Log orchestration completion
        self._log_structured_event(
            event_type="orchestration_completed",
            orchestration_id=orchestration_result.orchestration_id,
            client_id=orchestration_result.client_id,
            data=metrics.to_dict()
        )
        
        # Send completion metrics
        self._send_orchestration_metrics(metrics, orchestration_result.status)
        
        # Clean up
        del self.active_orchestrations[monitoring_id]
    
    def _send_orchestration_metrics(
        self,
        metrics: PerformanceMetrics,
        status: CollectionStatus
    ):
        """Send orchestration completion metrics."""
        base_dimensions = {
            'ClientId': metrics.client_id,
            'Status': status.value
        }
        
        # Duration metric
        if metrics.duration_seconds:
            self._send_metric(
                MetricData(
                    metric_name="OrchestrationDuration",
                    value=metrics.duration_seconds,
                    unit=MetricType.DURATION,
                    dimensions=base_dimensions
                )
            )
        
        # Success rate metric
        self._send_metric(
            MetricData(
                metric_name="OrchestrationSuccessRate",
                value=metrics.success_rate,
                unit=MetricType.PERCENTAGE,
                dimensions=base_dimensions
            )
        )
        
        # Task metrics
        self._send_metric(
            MetricData(
                metric_name="TasksCompleted",
                value=metrics.completed_tasks,
                unit=MetricType.COUNT,
                dimensions=base_dimensions
            )
        )
        
        self._send_metric(
            MetricData(
                metric_name="TasksFailed",
                value=metrics.failed_tasks,
                unit=MetricType.COUNT,
                dimensions=base_dimensions
            )
        )
        
        # Provider-specific metrics
        for provider in metrics.providers_processed:
            provider_dimensions = {
                **base_dimensions,
                'Provider': provider.value
            }
            
            self._send_metric(
                MetricData(
                    metric_name="ProviderProcessed",
                    value=1,
                    unit=MetricType.COUNT,
                    dimensions=provider_dimensions
                )
            )
    
    @xray_recorder.capture('monitor_queue_metrics')
    def monitor_queue_metrics(self, queue_metrics: Dict[str, Any]):
        """
        Monitor SQS queue metrics.
        
        Args:
            queue_metrics: Queue metrics from scheduler
        """
        for priority, metrics in queue_metrics.items():
            if 'error' in metrics:
                continue
            
            dimensions = {'QueuePriority': priority}
            
            # Messages available
            self._send_metric(
                MetricData(
                    metric_name="QueueMessagesAvailable",
                    value=metrics.get('messages_available', 0),
                    unit=MetricType.GAUGE,
                    dimensions=dimensions
                )
            )
            
            # Messages in flight
            self._send_metric(
                MetricData(
                    metric_name="QueueMessagesInFlight",
                    value=metrics.get('messages_in_flight', 0),
                    unit=MetricType.GAUGE,
                    dimensions=dimensions
                )
            )
            
            # Messages delayed
            self._send_metric(
                MetricData(
                    metric_name="QueueMessagesDelayed",
                    value=metrics.get('messages_delayed', 0),
                    unit=MetricType.GAUGE,
                    dimensions=dimensions
                )
            )
    
    @xray_recorder.capture('monitor_provider_performance')
    def monitor_provider_performance(
        self,
        provider: CloudProvider,
        client_id: str,
        duration_seconds: float,
        success: bool,
        error_message: Optional[str] = None
    ):
        """
        Monitor individual provider performance.
        
        Args:
            provider: Cloud provider
            client_id: Client identifier
            duration_seconds: Collection duration
            success: Whether collection was successful
            error_message: Error message if failed
        """
        dimensions = {
            'Provider': provider.value,
            'ClientId': client_id,
            'Status': 'Success' if success else 'Failed'
        }
        
        # Duration metric
        self._send_metric(
            MetricData(
                metric_name="ProviderCollectionDuration",
                value=duration_seconds,
                unit=MetricType.DURATION,
                dimensions=dimensions
            )
        )
        
        # Success/failure count
        self._send_metric(
            MetricData(
                metric_name="ProviderCollectionResult",
                value=1,
                unit=MetricType.COUNT,
                dimensions=dimensions
            )
        )
        
        # Log provider performance
        self._log_structured_event(
            event_type="provider_collection_completed",
            client_id=client_id,
            data={
                'provider': provider.value,
                'duration_seconds': duration_seconds,
                'success': success,
                'error_message': error_message
            }
        )
    
    def _send_metric(self, metric: MetricData):
        """Send a single metric to CloudWatch."""
        self.metric_buffer.append(metric)
        
        # Flush buffer if it's getting full
        if len(self.metric_buffer) >= 20:  # CloudWatch limit is 20 metrics per call
            self._flush_metrics()
    
    def _flush_metrics(self):
        """Flush metric buffer to CloudWatch."""
        if not self.metric_buffer:
            return
        
        try:
            # Convert metrics to CloudWatch format
            metric_data = [metric.to_cloudwatch_metric() for metric in self.metric_buffer]
            
            # Send to CloudWatch
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )
            
            self.logger.debug(f"Sent {len(metric_data)} metrics to CloudWatch")
            self.metric_buffer.clear()
            
        except Exception as e:
            self.logger.error(f"Error sending metrics to CloudWatch: {str(e)}")
    
    def _log_structured_event(
        self,
        event_type: str,
        client_id: Optional[str] = None,
        orchestration_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """Log structured event with correlation IDs."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'service': 'cost-collection-orchestrator',
            'version': '1.0.0'
        }
        
        if client_id:
            log_entry['client_id'] = client_id
        
        if orchestration_id:
            log_entry['orchestration_id'] = orchestration_id
        
        # Add X-Ray trace ID if available
        if self.enable_xray:
            trace_id = xray_recorder.current_trace_id()
            if trace_id:
                log_entry['trace_id'] = trace_id
        
        if data:
            log_entry['data'] = data
        
        # Log as JSON for structured logging
        self.logger.info(json.dumps(log_entry))
    
    @xray_recorder.capture('create_custom_alarm')
    def create_custom_alarm(
        self,
        alarm_name: str,
        metric_name: str,
        threshold: float,
        comparison_operator: str = "GreaterThanThreshold",
        evaluation_periods: int = 2,
        period: int = 300,
        statistic: str = "Average",
        dimensions: Optional[Dict[str, str]] = None,
        alarm_actions: Optional[List[str]] = None
    ) -> bool:
        """
        Create a custom CloudWatch alarm.
        
        Args:
            alarm_name: Name of the alarm
            metric_name: Metric to monitor
            threshold: Alarm threshold
            comparison_operator: Comparison operator
            evaluation_periods: Number of evaluation periods
            period: Period in seconds
            statistic: Statistic to use
            dimensions: Metric dimensions
            alarm_actions: SNS topics to notify
            
        Returns:
            True if alarm was created successfully
        """
        try:
            alarm_config = {
                'AlarmName': alarm_name,
                'ComparisonOperator': comparison_operator,
                'EvaluationPeriods': evaluation_periods,
                'MetricName': metric_name,
                'Namespace': self.namespace,
                'Period': period,
                'Statistic': statistic,
                'Threshold': threshold,
                'ActionsEnabled': True,
                'AlarmDescription': f'Custom alarm for {metric_name}',
                'Unit': 'None'
            }
            
            if dimensions:
                alarm_config['Dimensions'] = [
                    {'Name': name, 'Value': value}
                    for name, value in dimensions.items()
                ]
            
            if alarm_actions:
                alarm_config['AlarmActions'] = alarm_actions
            
            self.cloudwatch.put_metric_alarm(**alarm_config)
            
            self.logger.info(f"Created alarm: {alarm_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating alarm {alarm_name}: {str(e)}")
            return False
    
    def get_performance_analytics(
        self,
        start_time: datetime,
        end_time: datetime,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get performance analytics for a time period.
        
        Args:
            start_time: Start time for analytics
            end_time: End time for analytics
            client_id: Optional client filter
            
        Returns:
            Performance analytics data
        """
        try:
            # Build metric queries
            queries = []
            
            # Orchestration duration
            queries.append({
                'Id': 'orchestration_duration',
                'MetricStat': {
                    'Metric': {
                        'Namespace': self.namespace,
                        'MetricName': 'OrchestrationDuration',
                        'Dimensions': [{'Name': 'ClientId', 'Value': client_id}] if client_id else []
                    },
                    'Period': 3600,  # 1 hour
                    'Stat': 'Average'
                }
            })
            
            # Success rate
            queries.append({
                'Id': 'success_rate',
                'MetricStat': {
                    'Metric': {
                        'Namespace': self.namespace,
                        'MetricName': 'OrchestrationSuccessRate',
                        'Dimensions': [{'Name': 'ClientId', 'Value': client_id}] if client_id else []
                    },
                    'Period': 3600,
                    'Stat': 'Average'
                }
            })
            
            # Get metric data
            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=queries,
                StartTime=start_time,
                EndTime=end_time
            )
            
            # Process results
            analytics = {
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'client_id': client_id,
                'metrics': {}
            }
            
            for result in response['MetricDataResults']:
                analytics['metrics'][result['Id']] = {
                    'timestamps': [ts.isoformat() for ts in result['Timestamps']],
                    'values': result['Values'],
                    'status': result['StatusCode']
                }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting performance analytics: {str(e)}")
            return {'error': str(e)}
    
    @xray_recorder.capture('trace_collection_workflow')
    def trace_collection_workflow(
        self,
        workflow_name: str,
        client_id: str,
        providers: List[CloudProvider]
    ):
        """
        Create X-Ray subsegment for collection workflow tracing.
        
        Args:
            workflow_name: Name of the workflow
            client_id: Client identifier
            providers: List of providers being processed
            
        Returns:
            X-Ray subsegment context manager
        """
        if not self.enable_xray:
            return subsegment.DummySubsegment()
        
        segment = xray_recorder.begin_subsegment(workflow_name)
        segment.put_annotation('client_id', client_id)
        segment.put_annotation('provider_count', len(providers))
        
        for i, provider in enumerate(providers):
            segment.put_annotation(f'provider_{i}', provider.value)
        
        return segment
    
    def create_dashboard(self, dashboard_name: str) -> bool:
        """
        Create CloudWatch dashboard for cost collection monitoring.
        
        Args:
            dashboard_name: Name of the dashboard
            
        Returns:
            True if dashboard was created successfully
        """
        try:
            dashboard_body = {
                "widgets": [
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "OrchestrationDuration", "Status", "Completed"],
                                [".", "OrchestrationDuration", "Status", "Failed"]
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": self.region,
                            "title": "Orchestration Duration"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "OrchestrationSuccessRate"]
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": self.region,
                            "title": "Success Rate"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 6,
                        "width": 24,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "QueueMessagesAvailable", "QueuePriority", "critical"],
                                [".", "QueueMessagesAvailable", "QueuePriority", "high"],
                                [".", "QueueMessagesAvailable", "QueuePriority", "normal"],
                                [".", "QueueMessagesAvailable", "QueuePriority", "low"]
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": self.region,
                            "title": "Queue Depth by Priority"
                        }
                    }
                ]
            }
            
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            self.logger.info(f"Created dashboard: {dashboard_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating dashboard {dashboard_name}: {str(e)}")
            return False
    
    def cleanup_old_metrics(self, days_to_keep: int = 30):
        """
        Clean up old metric data (CloudWatch handles this automatically).
        
        Args:
            days_to_keep: Number of days to keep metrics
        """
        # CloudWatch automatically manages metric retention
        # This method is for future custom cleanup logic
        self.logger.info(f"Metric cleanup configured for {days_to_keep} days retention")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush any remaining metrics."""
        self._flush_metrics()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on monitoring service."""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'active_orchestrations': len(self.active_orchestrations),
            'metric_buffer_size': len(self.metric_buffer),
            'xray_enabled': self.enable_xray,
            'namespace': self.namespace
        }
        
        # Test CloudWatch connectivity
        try:
            self.cloudwatch.list_metrics(Namespace=self.namespace, MaxRecords=1)
            health_status['cloudwatch_connectivity'] = 'healthy'
        except Exception as e:
            health_status['cloudwatch_connectivity'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        return health_status