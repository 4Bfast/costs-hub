"""
Orchestration Integration Service

This module provides a unified interface for the cost collection orchestration system,
integrating the orchestrator, scheduler, and monitoring components into a cohesive service.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

from ..models.multi_cloud_models import CloudProvider
from ..models.provider_models import DateRange
from ..services.cost_collection_orchestrator import (
    CostCollectionOrchestrator, CollectionPriority, OrchestrationResult
)
from ..services.collection_scheduler import (
    CollectionScheduler, ScheduleFrequency, QueuePriority
)
from ..services.collection_monitoring_service import CollectionMonitoringService
from ..services.multi_tenant_client_manager import MultiTenantClientManager
from ..services.cost_normalization_service import CostNormalizationService
from ..services.cost_history_storage_service import CostHistoryService
from ..services.data_quality_engine import DataValidator
from ..utils.logging import create_logger


logger = create_logger(__name__)


@dataclass
class OrchestrationConfig:
    """Configuration for orchestration service."""
    max_concurrent_tasks: int = 10
    max_concurrent_per_provider: int = 3
    enable_monitoring: bool = True
    enable_xray: bool = True
    queue_prefix: str = "cost-collection"
    metrics_namespace: str = "CostAnalytics/Collection"
    region: str = "us-east-1"


class OrchestrationIntegrationService:
    """
    Unified orchestration integration service.
    
    Provides a single interface for:
    - Cost collection orchestration
    - Scheduling and queue management
    - Monitoring and observability
    - Health checks and diagnostics
    """
    
    def __init__(
        self,
        config: OrchestrationConfig,
        client_manager: MultiTenantClientManager,
        normalization_service: CostNormalizationService,
        storage_service: CostHistoryService,
        data_validator: DataValidator
    ):
        """
        Initialize the orchestration integration service.
        
        Args:
            config: Orchestration configuration
            client_manager: Multi-tenant client manager
            normalization_service: Cost normalization service
            storage_service: Cost history storage service
            data_validator: Data quality validator
        """
        self.config = config
        self.client_manager = client_manager
        self.normalization_service = normalization_service
        self.storage_service = storage_service
        self.data_validator = data_validator
        
        self.logger = create_logger(f"{__name__}.OrchestrationIntegrationService")
        
        # Initialize core components
        self.orchestrator = CostCollectionOrchestrator(
            client_manager=client_manager,
            normalization_service=normalization_service,
            storage_service=storage_service,
            data_validator=data_validator,
            max_concurrent_tasks=config.max_concurrent_tasks,
            max_concurrent_per_provider=config.max_concurrent_per_provider
        )
        
        self.scheduler = CollectionScheduler(
            client_manager=client_manager,
            orchestrator=self.orchestrator,
            region=config.region,
            queue_prefix=config.queue_prefix
        )
        
        if config.enable_monitoring:
            self.monitoring = CollectionMonitoringService(
                namespace=config.metrics_namespace,
                region=config.region,
                enable_xray=config.enable_xray
            )
        else:
            self.monitoring = None
        
        # Service state
        self.is_initialized = False
        self.background_tasks: List[asyncio.Task] = []
    
    async def initialize(self):
        """Initialize all orchestration components."""
        if self.is_initialized:
            return
        
        try:
            self.logger.info("Initializing orchestration integration service")
            
            # Initialize scheduler (creates queues and rules)
            await self.scheduler.initialize()
            
            # Create monitoring dashboard if enabled
            if self.monitoring:
                dashboard_name = f"cost-collection-{self.config.region}"
                self.monitoring.create_dashboard(dashboard_name)
                
                # Create default alarms
                await self._create_default_alarms()
            
            # Start background tasks
            await self._start_background_tasks()
            
            self.is_initialized = True
            self.logger.info("Orchestration integration service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing orchestration service: {str(e)}")
            raise
    
    async def _create_default_alarms(self):
        """Create default CloudWatch alarms."""
        if not self.monitoring:
            return
        
        # High failure rate alarm
        self.monitoring.create_custom_alarm(
            alarm_name="CostCollection-HighFailureRate",
            metric_name="OrchestrationSuccessRate",
            threshold=80.0,
            comparison_operator="LessThanThreshold",
            evaluation_periods=2,
            period=300,
            statistic="Average"
        )
        
        # Long duration alarm
        self.monitoring.create_custom_alarm(
            alarm_name="CostCollection-LongDuration",
            metric_name="OrchestrationDuration",
            threshold=1800.0,  # 30 minutes
            comparison_operator="GreaterThanThreshold",
            evaluation_periods=1,
            period=300,
            statistic="Maximum"
        )
        
        # High queue depth alarm
        self.monitoring.create_custom_alarm(
            alarm_name="CostCollection-HighQueueDepth",
            metric_name="QueueMessagesAvailable",
            threshold=100.0,
            comparison_operator="GreaterThanThreshold",
            evaluation_periods=3,
            period=300,
            statistic="Average",
            dimensions={"QueuePriority": "critical"}
        )
    
    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks."""
        # Queue processing task
        queue_task = asyncio.create_task(self._process_queues_continuously())
        self.background_tasks.append(queue_task)
        
        # Metrics monitoring task
        if self.monitoring:
            metrics_task = asyncio.create_task(self._monitor_metrics_continuously())
            self.background_tasks.append(metrics_task)
        
        # Cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_continuously())
        self.background_tasks.append(cleanup_task)
    
    async def _process_queues_continuously(self):
        """Continuously process queue messages."""
        while True:
            try:
                # Process each priority queue
                for priority in QueuePriority:
                    try:
                        results = await self.scheduler.process_queue_messages(
                            queue_priority=priority,
                            max_messages=5
                        )
                        
                        if results:
                            self.logger.info(
                                f"Processed {len(results)} messages from {priority.value} queue"
                            )
                    
                    except Exception as e:
                        self.logger.error(f"Error processing {priority.value} queue: {str(e)}")
                
                # Wait before next processing cycle
                await asyncio.sleep(30)  # Process every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in queue processing loop: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _monitor_metrics_continuously(self):
        """Continuously monitor and send metrics."""
        while True:
            try:
                # Get queue metrics
                queue_metrics = self.scheduler.get_queue_metrics()
                if self.monitoring:
                    self.monitoring.monitor_queue_metrics(queue_metrics)
                
                # Monitor active orchestrations
                active_orchestrations = self.orchestrator.get_active_orchestrations()
                if self.monitoring:
                    for orch in active_orchestrations:
                        # Send active orchestration metrics
                        pass  # Metrics are sent when orchestrations complete
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                self.logger.error(f"Error in metrics monitoring loop: {str(e)}")
                await asyncio.sleep(120)  # Wait longer on error
    
    async def _cleanup_continuously(self):
        """Continuously clean up old data."""
        while True:
            try:
                # Clean up old orchestrations
                cleaned_orchestrations = self.orchestrator.cleanup_completed_orchestrations(
                    max_age_hours=24
                )
                
                # Clean up old queue messages
                cleaned_messages = await self.scheduler.cleanup_old_messages(
                    max_age_hours=24
                )
                
                if cleaned_orchestrations > 0 or any(v > 0 for v in cleaned_messages.values()):
                    self.logger.info(
                        f"Cleanup completed: {cleaned_orchestrations} orchestrations, "
                        f"{sum(cleaned_messages.values())} messages"
                    )
                
                # Wait 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {str(e)}")
                await asyncio.sleep(3600)
    
    async def orchestrate_collection(
        self,
        client_id: str,
        date_range: DateRange,
        providers: Optional[List[CloudProvider]] = None,
        priority: CollectionPriority = CollectionPriority.NORMAL
    ) -> OrchestrationResult:
        """
        Orchestrate cost collection with full monitoring.
        
        Args:
            client_id: Client identifier
            date_range: Date range for collection
            providers: List of providers (None for all)
            priority: Collection priority
            
        Returns:
            OrchestrationResult with collection results
        """
        monitoring_id = None
        
        try:
            # Start orchestration
            result = await self.orchestrator.orchestrate_collection(
                client_id=client_id,
                date_range=date_range,
                providers=providers,
                priority=priority
            )
            
            # Start monitoring
            if self.monitoring:
                monitoring_id = self.monitoring.start_orchestration_monitoring(result)
            
            # Complete monitoring
            if self.monitoring and monitoring_id:
                self.monitoring.complete_orchestration_monitoring(monitoring_id, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in orchestrated collection: {str(e)}")
            
            # Create failed result
            failed_result = OrchestrationResult(
                orchestration_id="failed",
                client_id=client_id,
                date_range=date_range,
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=1,
                partial_tasks=0,
                status=CollectionStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                errors=[str(e)]
            )
            
            if self.monitoring and monitoring_id:
                self.monitoring.complete_orchestration_monitoring(monitoring_id, failed_result)
            
            return failed_result
    
    async def schedule_collection(
        self,
        client_id: str,
        frequency: ScheduleFrequency,
        providers: Optional[List[CloudProvider]] = None,
        priority: Optional[CollectionPriority] = None
    ) -> str:
        """
        Schedule a cost collection.
        
        Args:
            client_id: Client identifier
            frequency: Collection frequency
            providers: List of providers (None for all)
            priority: Collection priority (None for auto-detection)
            
        Returns:
            Message ID
        """
        return await self.scheduler.schedule_collection(
            client_id=client_id,
            frequency=frequency,
            providers=providers,
            priority=priority
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
        return await self.scheduler.schedule_batch_collection(
            client_ids=client_ids,
            frequency=frequency,
            priority=priority
        )
    
    def get_orchestration_status(self, orchestration_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific orchestration."""
        return self.orchestrator.get_orchestration_status(orchestration_id)
    
    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get current queue metrics."""
        return self.scheduler.get_queue_metrics()
    
    def get_performance_analytics(
        self,
        start_time: datetime,
        end_time: datetime,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get performance analytics."""
        if not self.monitoring:
            return {'error': 'Monitoring not enabled'}
        
        return self.monitoring.get_performance_analytics(
            start_time=start_time,
            end_time=end_time,
            client_id=client_id
        )
    
    def enable_schedule_rule(self, frequency: ScheduleFrequency) -> bool:
        """Enable a schedule rule."""
        return self.scheduler.enable_schedule_rule(frequency)
    
    def disable_schedule_rule(self, frequency: ScheduleFrequency) -> bool:
        """Disable a schedule rule."""
        return self.scheduler.disable_schedule_rule(frequency)
    
    async def cancel_orchestration(self, orchestration_id: str) -> bool:
        """Cancel an active orchestration."""
        return await self.orchestrator.cancel_orchestration(orchestration_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all components."""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'initialized': self.is_initialized,
            'components': {}
        }
        
        try:
            # Check orchestrator health
            orchestrator_health = await self.orchestrator.health_check()
            health_status['components']['orchestrator'] = orchestrator_health
            
            # Check scheduler health
            scheduler_health = await self.scheduler.health_check()
            health_status['components']['scheduler'] = scheduler_health
            
            # Check monitoring health
            if self.monitoring:
                monitoring_health = await self.monitoring.health_check()
                health_status['components']['monitoring'] = monitoring_health
            
            # Check background tasks
            active_tasks = sum(1 for task in self.background_tasks if not task.done())
            health_status['background_tasks'] = {
                'total': len(self.background_tasks),
                'active': active_tasks,
                'completed': len(self.background_tasks) - active_tasks
            }
            
            # Determine overall status
            component_statuses = [
                comp.get('status', 'unknown') 
                for comp in health_status['components'].values()
            ]
            
            if any(status in ['error', 'unhealthy'] for status in component_statuses):
                health_status['status'] = 'unhealthy'
            elif any(status == 'degraded' for status in component_statuses):
                health_status['status'] = 'degraded'
            
        except Exception as e:
            health_status['status'] = 'error'
            health_status['error'] = str(e)
            self.logger.error(f"Error in health check: {str(e)}")
        
        return health_status
    
    async def shutdown(self):
        """Gracefully shutdown the orchestration service."""
        self.logger.info("Shutting down orchestration integration service")
        
        try:
            # Cancel background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Flush any remaining metrics
            if self.monitoring:
                self.monitoring._flush_metrics()
            
            self.logger.info("Orchestration integration service shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        stats = {
            'timestamp': datetime.utcnow().isoformat(),
            'config': {
                'max_concurrent_tasks': self.config.max_concurrent_tasks,
                'max_concurrent_per_provider': self.config.max_concurrent_per_provider,
                'monitoring_enabled': self.config.enable_monitoring,
                'xray_enabled': self.config.enable_xray
            },
            'orchestrator': {
                'active_orchestrations': len(self.orchestrator.orchestrations),
                'total_orchestrations': len(self.orchestrator.orchestrations)
            },
            'scheduler': {
                'processing_messages': len(self.scheduler.processing_messages),
                'queue_count': len(self.scheduler.queue_urls)
            }
        }
        
        if self.monitoring:
            stats['monitoring'] = {
                'active_monitoring_sessions': len(self.monitoring.active_orchestrations),
                'metric_buffer_size': len(self.monitoring.metric_buffer)
            }
        
        return stats


# Factory function for creating the integration service
def create_orchestration_service(
    config: Optional[OrchestrationConfig] = None,
    client_manager: Optional[MultiTenantClientManager] = None,
    normalization_service: Optional[CostNormalizationService] = None,
    storage_service: Optional[CostHistoryService] = None,
    data_validator: Optional[DataValidator] = None
) -> OrchestrationIntegrationService:
    """
    Factory function to create orchestration integration service.
    
    Args:
        config: Orchestration configuration
        client_manager: Multi-tenant client manager
        normalization_service: Cost normalization service
        storage_service: Cost history storage service
        data_validator: Data quality validator
        
    Returns:
        OrchestrationIntegrationService instance
    """
    if config is None:
        config = OrchestrationConfig()
    
    # Create default services if not provided
    if client_manager is None:
        client_manager = MultiTenantClientManager()
    
    if normalization_service is None:
        normalization_service = CostNormalizationService()
    
    if storage_service is None:
        storage_service = CostHistoryService()
    
    if data_validator is None:
        data_validator = DataValidator()
    
    return OrchestrationIntegrationService(
        config=config,
        client_manager=client_manager,
        normalization_service=normalization_service,
        storage_service=storage_service,
        data_validator=data_validator
    )