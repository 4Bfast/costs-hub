"""
Lambda optimization utilities for the Cost Reporting System.

This module provides optimization utilities specifically designed for AWS Lambda
execution constraints including memory management, timeout handling, and
connection pooling.
"""

import gc
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import boto3
from botocore.config import Config

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from ..utils import create_logger


logger = create_logger(__name__)


class LambdaMemoryManager:
    """Memory management utilities for Lambda execution."""
    
    def __init__(self, memory_threshold_mb: int = 100):
        """
        Initialize memory manager.
        
        Args:
            memory_threshold_mb: Memory threshold in MB to trigger cleanup
        """
        self.memory_threshold_mb = memory_threshold_mb
        self.initial_memory = self._get_memory_usage()
        self.logger = create_logger(f"{__name__}.MemoryManager")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def check_memory_usage(self) -> Dict[str, float]:
        """
        Check current memory usage.
        
        Returns:
            Dictionary with memory statistics
        """
        current_memory = self._get_memory_usage()
        memory_increase = current_memory - self.initial_memory
        
        return {
            'current_mb': current_memory,
            'initial_mb': self.initial_memory,
            'increase_mb': memory_increase,
            'threshold_mb': self.memory_threshold_mb,
            'needs_cleanup': memory_increase > self.memory_threshold_mb
        }
    
    def cleanup_if_needed(self) -> bool:
        """
        Perform garbage collection if memory usage exceeds threshold.
        
        Returns:
            True if cleanup was performed
        """
        stats = self.check_memory_usage()
        
        if stats['needs_cleanup']:
            self.logger.info(f"Memory usage {stats['current_mb']:.1f}MB, performing cleanup")
            
            # Force garbage collection
            collected = gc.collect()
            
            # Check memory after cleanup
            new_stats = self.check_memory_usage()
            memory_freed = stats['current_mb'] - new_stats['current_mb']
            
            self.logger.info(
                f"Cleanup completed: {collected} objects collected, "
                f"{memory_freed:.1f}MB freed, current usage: {new_stats['current_mb']:.1f}MB"
            )
            
            return True
        
        return False
    
    def log_memory_stats(self) -> None:
        """Log current memory statistics."""
        stats = self.check_memory_usage()
        self.logger.info(
            f"Memory: {stats['current_mb']:.1f}MB current, "
            f"{stats['increase_mb']:.1f}MB increase from start"
        )


class LambdaTimeoutManager:
    """Timeout management for Lambda execution."""
    
    def __init__(self, total_timeout_seconds: int, buffer_seconds: int = 30):
        """
        Initialize timeout manager.
        
        Args:
            total_timeout_seconds: Total Lambda timeout in seconds
            buffer_seconds: Buffer time to reserve for cleanup
        """
        self.total_timeout = total_timeout_seconds
        self.buffer_seconds = buffer_seconds
        self.start_time = time.time()
        self.effective_timeout = total_timeout_seconds - buffer_seconds
        self.logger = create_logger(f"{__name__}.TimeoutManager")
    
    def get_remaining_time(self) -> float:
        """Get remaining execution time in seconds."""
        elapsed = time.time() - self.start_time
        return max(0, self.effective_timeout - elapsed)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed execution time in seconds."""
        return time.time() - self.start_time
    
    def is_timeout_approaching(self, threshold_seconds: int = 60) -> bool:
        """
        Check if timeout is approaching.
        
        Args:
            threshold_seconds: Threshold in seconds to consider timeout approaching
            
        Returns:
            True if timeout is approaching
        """
        return self.get_remaining_time() <= threshold_seconds
    
    def should_continue_processing(self, estimated_time_seconds: int = 30) -> bool:
        """
        Check if there's enough time to continue processing.
        
        Args:
            estimated_time_seconds: Estimated time needed for next operation
            
        Returns:
            True if there's enough time to continue
        """
        return self.get_remaining_time() >= estimated_time_seconds
    
    def log_time_stats(self) -> None:
        """Log current time statistics."""
        elapsed = self.get_elapsed_time()
        remaining = self.get_remaining_time()
        
        self.logger.info(
            f"Time: {elapsed:.1f}s elapsed, {remaining:.1f}s remaining "
            f"(timeout in {self.total_timeout}s)"
        )


class OptimizedConnectionPool:
    """Optimized connection pool for AWS services in Lambda."""
    
    def __init__(self, max_connections: int = 10, connection_timeout: int = 30):
        """
        Initialize connection pool.
        
        Args:
            max_connections: Maximum number of connections to maintain
            connection_timeout: Connection timeout in seconds
        """
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self._sessions: Dict[str, boto3.Session] = {}
        self._clients: Dict[str, boto3.client] = {}
        self._lock = threading.Lock()
        self.logger = create_logger(f"{__name__}.ConnectionPool")
        
        # Optimized boto3 configuration for Lambda
        self._boto_config = Config(
            region_name='us-east-1',
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=max_connections,
            connect_timeout=connection_timeout,
            read_timeout=60
        )
    
    def get_session(self, access_key_id: str, secret_access_key: str, region: str = 'us-east-1') -> boto3.Session:
        """
        Get or create a cached session.
        
        Args:
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            region: AWS region
            
        Returns:
            Boto3 session
        """
        cache_key = f"{access_key_id[:8]}_{region}"
        
        with self._lock:
            if cache_key not in self._sessions:
                # Limit cache size
                if len(self._sessions) >= self.max_connections:
                    # Remove oldest session
                    oldest_key = next(iter(self._sessions))
                    del self._sessions[oldest_key]
                    self.logger.debug(f"Removed oldest session {oldest_key} from cache")
                
                session = boto3.Session(
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    region_name=region
                )
                
                self._sessions[cache_key] = session
                self.logger.debug(f"Created new session {cache_key}")
            
            return self._sessions[cache_key]
    
    def get_cost_explorer_client(self, access_key_id: str, secret_access_key: str) -> boto3.client:
        """
        Get or create a cached Cost Explorer client.
        
        Args:
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            
        Returns:
            Cost Explorer client
        """
        cache_key = f"ce_{access_key_id[:8]}"
        
        with self._lock:
            if cache_key not in self._clients:
                # Limit cache size
                if len(self._clients) >= self.max_connections:
                    # Remove oldest client
                    oldest_key = next(iter(self._clients))
                    del self._clients[oldest_key]
                    self.logger.debug(f"Removed oldest client {oldest_key} from cache")
                
                session = self.get_session(access_key_id, secret_access_key, 'us-east-1')
                client = session.client('ce', config=self._boto_config)
                
                self._clients[cache_key] = client
                self.logger.debug(f"Created new Cost Explorer client {cache_key}")
            
            return self._clients[cache_key]
    
    def clear_cache(self) -> None:
        """Clear all cached connections."""
        with self._lock:
            self._sessions.clear()
            self._clients.clear()
            self.logger.info("Cleared connection cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            return {
                'sessions_cached': len(self._sessions),
                'clients_cached': len(self._clients),
                'max_connections': self.max_connections
            }


class LambdaOptimizedExecutor:
    """Optimized executor for Lambda with memory and timeout management."""
    
    def __init__(self, 
                 max_workers: int = 5,
                 memory_threshold_mb: int = 100,
                 timeout_seconds: int = 900,
                 buffer_seconds: int = 30):
        """
        Initialize optimized executor.
        
        Args:
            max_workers: Maximum number of worker threads
            memory_threshold_mb: Memory threshold for cleanup
            timeout_seconds: Total timeout in seconds
            buffer_seconds: Buffer time for cleanup
        """
        self.max_workers = max_workers
        self.memory_manager = LambdaMemoryManager(memory_threshold_mb)
        self.timeout_manager = LambdaTimeoutManager(timeout_seconds, buffer_seconds)
        self.connection_pool = OptimizedConnectionPool(max_workers * 2)
        self.logger = create_logger(f"{__name__}.OptimizedExecutor")
    
    def execute_with_constraints(self, 
                               tasks: List[Callable],
                               task_timeout: int = 60,
                               memory_check_interval: int = 5) -> List[Any]:
        """
        Execute tasks with Lambda constraints management.
        
        Args:
            tasks: List of callable tasks to execute
            task_timeout: Timeout per task in seconds
            memory_check_interval: Interval for memory checks
            
        Returns:
            List of results
        """
        results = []
        completed_tasks = 0
        
        self.logger.info(f"Starting execution of {len(tasks)} tasks")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(task): i for i, task in enumerate(tasks)}
            
            # Process completed tasks
            for future in as_completed(future_to_task, timeout=self.timeout_manager.get_remaining_time()):
                task_index = future_to_task[future]
                
                try:
                    # Check timeout before processing result
                    if not self.timeout_manager.should_continue_processing():
                        self.logger.warning("Timeout approaching, stopping task processing")
                        break
                    
                    result = future.result(timeout=task_timeout)
                    results.append((task_index, result))
                    completed_tasks += 1
                    
                    # Periodic memory check
                    if completed_tasks % memory_check_interval == 0:
                        self.memory_manager.cleanup_if_needed()
                    
                    self.logger.debug(f"Completed task {task_index + 1}/{len(tasks)}")
                    
                except Exception as e:
                    self.logger.error(f"Task {task_index} failed: {e}")
                    results.append((task_index, None))
                    completed_tasks += 1
        
        # Final cleanup
        self.memory_manager.cleanup_if_needed()
        self.timeout_manager.log_time_stats()
        self.memory_manager.log_memory_stats()
        
        self.logger.info(f"Completed {completed_tasks}/{len(tasks)} tasks")
        
        # Sort results by task index and return values only
        results.sort(key=lambda x: x[0])
        return [result[1] for result in results]
    
    def batch_process_with_limits(self,
                                items: List[Any],
                                process_func: Callable,
                                batch_size: int = 10,
                                max_batches: Optional[int] = None) -> List[Any]:
        """
        Process items in batches with Lambda constraints.
        
        Args:
            items: Items to process
            process_func: Function to process each item
            batch_size: Size of each batch
            max_batches: Maximum number of batches to process
            
        Returns:
            List of processed results
        """
        results = []
        batches_processed = 0
        
        # Create batches
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        if max_batches:
            batches = batches[:max_batches]
        
        self.logger.info(f"Processing {len(items)} items in {len(batches)} batches")
        
        for batch_index, batch in enumerate(batches):
            # Check constraints before processing batch
            if not self.timeout_manager.should_continue_processing(30):
                self.logger.warning(f"Timeout approaching, stopping at batch {batch_index + 1}/{len(batches)}")
                break
            
            try:
                # Process batch
                batch_tasks = [lambda item=item: process_func(item) for item in batch]
                batch_results = self.execute_with_constraints(batch_tasks)
                results.extend(batch_results)
                
                batches_processed += 1
                self.logger.info(f"Completed batch {batch_index + 1}/{len(batches)}")
                
                # Memory cleanup between batches
                self.memory_manager.cleanup_if_needed()
                
            except Exception as e:
                self.logger.error(f"Batch {batch_index + 1} failed: {e}")
                continue
        
        self.logger.info(f"Processed {batches_processed}/{len(batches)} batches, {len(results)} results")
        return results
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        return {
            'memory': self.memory_manager.check_memory_usage(),
            'time': {
                'elapsed_seconds': self.timeout_manager.get_elapsed_time(),
                'remaining_seconds': self.timeout_manager.get_remaining_time(),
                'timeout_approaching': self.timeout_manager.is_timeout_approaching()
            },
            'connections': self.connection_pool.get_cache_stats(),
            'max_workers': self.max_workers
        }
    
    def cleanup(self) -> None:
        """Perform final cleanup."""
        self.connection_pool.clear_cache()
        self.memory_manager.cleanup_if_needed()
        self.logger.info("Optimization cleanup completed")


def create_lambda_optimized_agent(client_config, lambda_context=None):
    """
    Factory function to create a Lambda-optimized cost agent.
    
    Args:
        client_config: Client configuration
        lambda_context: Lambda context object (if available)
        
    Returns:
        Optimized LambdaCostAgent instance
    """
    from .lambda_cost_agent import LambdaCostAgent
    
    # Determine timeout from Lambda context
    timeout_seconds = 900  # Default 15 minutes
    if lambda_context and hasattr(lambda_context, 'get_remaining_time_in_millis'):
        timeout_seconds = lambda_context.get_remaining_time_in_millis() // 1000
    
    # Create optimized agent with constraints
    max_workers = min(5, len(client_config.aws_accounts))  # Limit workers based on accounts
    
    agent = LambdaCostAgent(
        client_config=client_config,
        max_workers=max_workers,
        timeout_per_account=min(60, timeout_seconds // (len(client_config.aws_accounts) + 1))
    )
    
    # Add optimization components
    agent._optimizer = LambdaOptimizedExecutor(
        max_workers=max_workers,
        timeout_seconds=timeout_seconds
    )
    
    return agent