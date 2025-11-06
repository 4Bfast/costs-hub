"""
Cost Collection Orchestrator

This module implements the multi-provider cost collection orchestrator that coordinates
cost data collection across AWS, GCP, and Azure providers with parallel processing,
error handling, and retry logic with exponential backoff.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json
import time
import random

from ..models.multi_cloud_models import CloudProvider, UnifiedCostRecord
from ..models.provider_models import (
    DateRange, CollectionResult, DataCollectionStatus, ProviderError
)
from ..models.multi_tenant_models import MultiCloudClient
from ..services.cloud_provider_adapter import CloudProviderAdapter, adapter_manager
from ..services.multi_tenant_client_manager import MultiTenantClientManager
from ..services.cost_normalization_service import CostNormalizationService
from ..services.cost_history_storage_service import CostHistoryService
from ..services.data_quality_engine import DataValidator
from ..utils.logging import create_logger
from ..utils.provider_error_handler import ProviderErrorHandler


logger = create_logger(__name__)


class CollectionPriority(Enum):
    """Collection priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CollectionStatus(Enum):
    """Collection orchestration status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class CollectionTask:
    """Individual collection task for a client and provider."""
    task_id: str
    client_id: str
    provider: CloudProvider
    date_range: DateRange
    priority: CollectionPriority = CollectionPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: CollectionStatus = CollectionStatus.PENDING
    error_message: Optional[str] = None
    result: Optional[CollectionResult] = None
    
    def __post_init__(self):
        """Initialize task ID if not provided."""
        if not self.task_id:
            self.task_id = str(uuid.uuid4())
    
    @property
    def is_retryable(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries and self.status == CollectionStatus.FAILED
    
    @property
    def next_retry_delay(self) -> float:
        """Calculate next retry delay with exponential backoff."""
        base_delay = 2.0  # Base delay in seconds
        max_delay = 300.0  # Maximum delay (5 minutes)
        jitter = random.uniform(0.8, 1.2)  # Add jitter to prevent thundering herd
        
        delay = min(base_delay * (2 ** self.retry_count) * jitter, max_delay)
        return delay
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'client_id': self.client_id,
            'provider': self.provider.value,
            'date_range': {
                'start_date': self.date_range.start_date.isoformat(),
                'end_date': self.date_range.end_date.isoformat()
            },
            'priority': self.priority.value,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status.value,
            'error_message': self.error_message
        }


@dataclass
class OrchestrationResult:
    """Result of cost collection orchestration."""
    orchestration_id: str
    client_id: str
    date_range: DateRange
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    partial_tasks: int
    status: CollectionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    providers_processed: List[CloudProvider] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    unified_records: List[UnifiedCostRecord] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'orchestration_id': self.orchestration_id,
            'client_id': self.client_id,
            'date_range': {
                'start_date': self.date_range.start_date.isoformat(),
                'end_date': self.date_range.end_date.isoformat()
            },
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'partial_tasks': self.partial_tasks,
            'status': self.status.value,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'success_rate': self.success_rate,
            'providers_processed': [p.value for p in self.providers_processed],
            'errors': self.errors,
            'unified_records_count': len(self.unified_records)
        }


class CostCollectionOrchestrator:
    """
    Multi-provider cost collection orchestrator.
    
    Coordinates cost data collection across multiple cloud providers with:
    - Parallel processing for multiple clients and providers
    - Error handling and retry logic with exponential backoff
    - Priority-based task scheduling
    - Data normalization and quality validation
    - Comprehensive monitoring and logging
    """
    
    def __init__(
        self,
        client_manager: MultiTenantClientManager,
        normalization_service: CostNormalizationService,
        storage_service: CostHistoryService,
        data_validator: DataValidator,
        max_concurrent_tasks: int = 10,
        max_concurrent_per_provider: int = 3
    ):
        """
        Initialize the cost collection orchestrator.
        
        Args:
            client_manager: Multi-tenant client manager
            normalization_service: Cost normalization service
            storage_service: Cost history storage service
            data_validator: Data quality validator
            max_concurrent_tasks: Maximum concurrent tasks
            max_concurrent_per_provider: Maximum concurrent tasks per provider
        """
        self.client_manager = client_manager
        self.normalization_service = normalization_service
        self.storage_service = storage_service
        self.data_validator = data_validator
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_concurrent_per_provider = max_concurrent_per_provider
        
        self.logger = create_logger(f"{__name__}.CostCollectionOrchestrator")
        self.error_handler = ProviderErrorHandler()
        
        # Task management
        self.active_tasks: Dict[str, CollectionTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.retry_queue: asyncio.Queue = asyncio.Queue()
        
        # Semaphores for concurrency control
        self.task_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.provider_semaphores = {
            provider: asyncio.Semaphore(max_concurrent_per_provider)
            for provider in CloudProvider
        }
        
        # Orchestration tracking
        self.orchestrations: Dict[str, OrchestrationResult] = {}
    
    async def orchestrate_collection(
        self,
        client_id: str,
        date_range: DateRange,
        providers: Optional[List[CloudProvider]] = None,
        priority: CollectionPriority = CollectionPriority.NORMAL
    ) -> OrchestrationResult:
        """
        Orchestrate cost collection for a client across multiple providers.
        
        Args:
            client_id: Client identifier
            date_range: Date range for collection
            providers: List of providers to collect from (None for all)
            priority: Collection priority
            
        Returns:
            OrchestrationResult with collection results
        """
        orchestration_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        
        self.logger.info(
            f"Starting cost collection orchestration",
            extra={
                'orchestration_id': orchestration_id,
                'client_id': client_id,
                'date_range': f"{date_range.start_date} to {date_range.end_date}",
                'priority': priority.value
            }
        )
        
        try:
            # Get client configuration
            client = await self.client_manager.get_client(client_id)
            if not client:
                raise ValueError(f"Client {client_id} not found")
            
            # Determine providers to collect from
            if providers is None:
                providers = list(client.cloud_accounts.keys())
            
            # Create collection tasks
            tasks = self._create_collection_tasks(
                client_id, date_range, providers, priority
            )
            
            if not tasks:
                raise ValueError(f"No collection tasks created for client {client_id}")
            
            # Initialize orchestration result
            orchestration_result = OrchestrationResult(
                orchestration_id=orchestration_id,
                client_id=client_id,
                date_range=date_range,
                total_tasks=len(tasks),
                completed_tasks=0,
                failed_tasks=0,
                partial_tasks=0,
                status=CollectionStatus.RUNNING,
                started_at=started_at,
                providers_processed=providers
            )
            
            self.orchestrations[orchestration_id] = orchestration_result
            
            # Execute tasks in parallel
            task_results = await self._execute_tasks_parallel(tasks)
            
            # Process results
            await self._process_task_results(orchestration_result, task_results)
            
            # Finalize orchestration
            orchestration_result.completed_at = datetime.utcnow()
            orchestration_result.duration_seconds = (
                orchestration_result.completed_at - orchestration_result.started_at
            ).total_seconds()
            
            # Determine final status
            if orchestration_result.failed_tasks == 0:
                orchestration_result.status = CollectionStatus.COMPLETED
            elif orchestration_result.completed_tasks > 0:
                orchestration_result.status = CollectionStatus.PARTIAL
            else:
                orchestration_result.status = CollectionStatus.FAILED
            
            self.logger.info(
                f"Completed cost collection orchestration",
                extra={
                    'orchestration_id': orchestration_id,
                    'status': orchestration_result.status.value,
                    'success_rate': orchestration_result.success_rate,
                    'duration_seconds': orchestration_result.duration_seconds
                }
            )
            
            return orchestration_result
            
        except Exception as e:
            error_msg = f"Error in cost collection orchestration: {str(e)}"
            self.logger.error(error_msg, extra={'orchestration_id': orchestration_id})
            
            # Create failed orchestration result
            orchestration_result = OrchestrationResult(
                orchestration_id=orchestration_id,
                client_id=client_id,
                date_range=date_range,
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=1,
                partial_tasks=0,
                status=CollectionStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                errors=[error_msg]
            )
            
            self.orchestrations[orchestration_id] = orchestration_result
            return orchestration_result
    
    def _create_collection_tasks(
        self,
        client_id: str,
        date_range: DateRange,
        providers: List[CloudProvider],
        priority: CollectionPriority
    ) -> List[CollectionTask]:
        """Create collection tasks for each provider."""
        tasks = []
        
        for provider in providers:
            task = CollectionTask(
                task_id=str(uuid.uuid4()),
                client_id=client_id,
                provider=provider,
                date_range=date_range,
                priority=priority
            )
            tasks.append(task)
        
        return tasks
    
    async def _execute_tasks_parallel(self, tasks: List[CollectionTask]) -> List[CollectionTask]:
        """Execute collection tasks in parallel with concurrency control."""
        # Sort tasks by priority
        tasks.sort(key=lambda t: self._get_priority_weight(t.priority), reverse=True)
        
        # Create coroutines for each task
        task_coroutines = [self._execute_single_task(task) for task in tasks]
        
        # Execute with concurrency control
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)
        
        # Handle exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tasks[i].status = CollectionStatus.FAILED
                tasks[i].error_message = str(result)
                tasks[i].completed_at = datetime.utcnow()
        
        return tasks
    
    async def _execute_single_task(self, task: CollectionTask) -> CollectionTask:
        """Execute a single collection task with retry logic."""
        async with self.task_semaphore:
            async with self.provider_semaphores[task.provider]:
                return await self._execute_task_with_retry(task)
    
    async def _execute_task_with_retry(self, task: CollectionTask) -> CollectionTask:
        """Execute task with exponential backoff retry logic."""
        while True:
            try:
                task.started_at = datetime.utcnow()
                task.status = CollectionStatus.RUNNING
                
                self.logger.info(
                    f"Executing collection task",
                    extra={
                        'task_id': task.task_id,
                        'client_id': task.client_id,
                        'provider': task.provider.value,
                        'retry_count': task.retry_count
                    }
                )
                
                # Get provider adapter
                adapter = adapter_manager.get_adapter(task.client_id, task.provider)
                if not adapter:
                    raise ValueError(f"No adapter found for {task.provider.value}")
                
                # Collect cost data
                collection_result = await adapter.collect_cost_data(task.date_range)
                
                # Validate and normalize data
                if collection_result.status == DataCollectionStatus.SUCCESS:
                    unified_record = await self._process_collection_result(
                        task, collection_result
                    )
                    collection_result.unified_record = unified_record
                
                task.result = collection_result
                task.status = CollectionStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                
                self.logger.info(
                    f"Successfully completed collection task",
                    extra={
                        'task_id': task.task_id,
                        'provider': task.provider.value,
                        'status': collection_result.status.value
                    }
                )
                
                return task
                
            except Exception as e:
                task.retry_count += 1
                task.error_message = str(e)
                
                self.logger.error(
                    f"Collection task failed",
                    extra={
                        'task_id': task.task_id,
                        'provider': task.provider.value,
                        'retry_count': task.retry_count,
                        'error': str(e)
                    }
                )
                
                # Check if we should retry
                if task.is_retryable:
                    delay = task.next_retry_delay
                    self.logger.info(
                        f"Retrying task in {delay:.2f} seconds",
                        extra={'task_id': task.task_id}
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    task.status = CollectionStatus.FAILED
                    task.completed_at = datetime.utcnow()
                    return task
    
    async def _process_collection_result(
        self,
        task: CollectionTask,
        collection_result: CollectionResult
    ) -> Optional[UnifiedCostRecord]:
        """Process and normalize collection result."""
        try:
            if not collection_result.cost_data:
                return None
            
            # Normalize cost data
            unified_record = self.normalization_service.normalize_cost_data(
                collection_result.cost_data
            )
            
            # Validate data quality
            quality_score = self.data_validator.calculate_quality_score(
                collection_result.cost_data
            )
            unified_record.data_quality = quality_score
            
            # Store in cost history
            await self.storage_service.store_cost_record(unified_record)
            
            return unified_record
            
        except Exception as e:
            self.logger.error(
                f"Error processing collection result for task {task.task_id}: {str(e)}"
            )
            return None
    
    async def _process_task_results(
        self,
        orchestration_result: OrchestrationResult,
        tasks: List[CollectionTask]
    ):
        """Process task results and update orchestration result."""
        for task in tasks:
            if task.status == CollectionStatus.COMPLETED:
                orchestration_result.completed_tasks += 1
                if task.result and hasattr(task.result, 'unified_record'):
                    if task.result.unified_record:
                        orchestration_result.unified_records.append(
                            task.result.unified_record
                        )
            elif task.status == CollectionStatus.FAILED:
                orchestration_result.failed_tasks += 1
                if task.error_message:
                    orchestration_result.errors.append(
                        f"{task.provider.value}: {task.error_message}"
                    )
            elif task.status == CollectionStatus.PARTIAL:
                orchestration_result.partial_tasks += 1
    
    def _get_priority_weight(self, priority: CollectionPriority) -> int:
        """Get numeric weight for priority sorting."""
        weights = {
            CollectionPriority.CRITICAL: 4,
            CollectionPriority.HIGH: 3,
            CollectionPriority.NORMAL: 2,
            CollectionPriority.LOW: 1
        }
        return weights.get(priority, 2)
    
    async def orchestrate_batch_collection(
        self,
        client_ids: List[str],
        date_range: DateRange,
        priority: CollectionPriority = CollectionPriority.NORMAL
    ) -> List[OrchestrationResult]:
        """
        Orchestrate cost collection for multiple clients.
        
        Args:
            client_ids: List of client identifiers
            date_range: Date range for collection
            priority: Collection priority
            
        Returns:
            List of OrchestrationResult objects
        """
        self.logger.info(
            f"Starting batch cost collection for {len(client_ids)} clients",
            extra={'client_count': len(client_ids)}
        )
        
        # Create orchestration tasks
        orchestration_tasks = [
            self.orchestrate_collection(client_id, date_range, None, priority)
            for client_id in client_ids
        ]
        
        # Execute orchestrations concurrently
        results = await asyncio.gather(*orchestration_tasks, return_exceptions=True)
        
        # Handle exceptions
        orchestration_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Batch orchestration failed for client {client_ids[i]}: {str(result)}"
                )
                # Create failed result
                failed_result = OrchestrationResult(
                    orchestration_id=str(uuid.uuid4()),
                    client_id=client_ids[i],
                    date_range=date_range,
                    total_tasks=0,
                    completed_tasks=0,
                    failed_tasks=1,
                    partial_tasks=0,
                    status=CollectionStatus.FAILED,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    errors=[str(result)]
                )
                orchestration_results.append(failed_result)
            else:
                orchestration_results.append(result)
        
        return orchestration_results
    
    def get_orchestration_status(self, orchestration_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific orchestration."""
        orchestration = self.orchestrations.get(orchestration_id)
        if not orchestration:
            return None
        
        return orchestration.to_dict()
    
    def get_active_orchestrations(self) -> List[Dict[str, Any]]:
        """Get all active orchestrations."""
        active = [
            orchestration.to_dict()
            for orchestration in self.orchestrations.values()
            if orchestration.status == CollectionStatus.RUNNING
        ]
        return active
    
    async def cancel_orchestration(self, orchestration_id: str) -> bool:
        """Cancel an active orchestration."""
        orchestration = self.orchestrations.get(orchestration_id)
        if not orchestration or orchestration.status != CollectionStatus.RUNNING:
            return False
        
        # Mark as failed (cancellation)
        orchestration.status = CollectionStatus.FAILED
        orchestration.completed_at = datetime.utcnow()
        orchestration.errors.append("Orchestration cancelled by user")
        
        self.logger.info(f"Cancelled orchestration {orchestration_id}")
        return True
    
    def cleanup_completed_orchestrations(self, max_age_hours: int = 24) -> int:
        """Clean up old completed orchestrations."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        orchestrations_to_remove = [
            orch_id for orch_id, orch in self.orchestrations.items()
            if orch.completed_at and orch.completed_at < cutoff_time
            and orch.status in [CollectionStatus.COMPLETED, CollectionStatus.FAILED]
        ]
        
        for orch_id in orchestrations_to_remove:
            del self.orchestrations[orch_id]
        
        if orchestrations_to_remove:
            self.logger.info(f"Cleaned up {len(orchestrations_to_remove)} old orchestrations")
        
        return len(orchestrations_to_remove)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the orchestrator."""
        return {
            'status': 'healthy',
            'active_orchestrations': len([
                o for o in self.orchestrations.values()
                if o.status == CollectionStatus.RUNNING
            ]),
            'total_orchestrations': len(self.orchestrations),
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'max_concurrent_per_provider': self.max_concurrent_per_provider,
            'timestamp': datetime.utcnow().isoformat()
        }