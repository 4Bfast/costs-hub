"""
Resource Allocation Manager

This service manages resource allocation and limits for multi-tenant clients,
including dynamic scaling, quota enforcement, and performance optimization.
"""

import boto3
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import asyncio
import json

from ..models.multi_tenant_models import MultiCloudClient, ResourceLimits, SubscriptionTier
from ..services.tenant_data_isolation_service import TenantDataIsolationService, ResourceQuota


logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources that can be allocated."""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    API_CALLS = "api_calls"


class AllocationStrategy(Enum):
    """Resource allocation strategies."""
    FIXED = "fixed"           # Fixed allocation based on subscription
    DYNAMIC = "dynamic"       # Dynamic allocation based on usage
    BURST = "burst"          # Allow bursting above limits
    RESERVED = "reserved"     # Reserved capacity allocation


@dataclass
class ResourceAllocation:
    """Resource allocation configuration for a tenant."""
    tenant_id: str
    resource_type: ResourceType
    allocated_amount: int
    used_amount: int
    reserved_amount: int
    burst_limit: int
    allocation_strategy: AllocationStrategy
    last_updated: datetime
    
    @property
    def utilization_percentage(self) -> float:
        """Calculate resource utilization percentage."""
        if self.allocated_amount == 0:
            return 0.0
        return (self.used_amount / self.allocated_amount) * 100.0
    
    @property
    def available_amount(self) -> int:
        """Calculate available resource amount."""
        return max(0, self.allocated_amount - self.used_amount)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'tenant_id': self.tenant_id,
            'resource_type': self.resource_type.value,
            'allocated_amount': self.allocated_amount,
            'used_amount': self.used_amount,
            'reserved_amount': self.reserved_amount,
            'burst_limit': self.burst_limit,
            'allocation_strategy': self.allocation_strategy.value,
            'last_updated': self.last_updated.isoformat(),
            'utilization_percentage': self.utilization_percentage,
            'available_amount': self.available_amount
        }


@dataclass
class ResourceUsageMetrics:
    """Resource usage metrics for monitoring and optimization."""
    tenant_id: str
    resource_type: ResourceType
    current_usage: int
    peak_usage: int
    average_usage: float
    usage_trend: str  # 'increasing', 'decreasing', 'stable'
    prediction_next_hour: int
    prediction_next_day: int
    last_calculated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'tenant_id': self.tenant_id,
            'resource_type': self.resource_type.value,
            'current_usage': self.current_usage,
            'peak_usage': self.peak_usage,
            'average_usage': self.average_usage,
            'usage_trend': self.usage_trend,
            'prediction_next_hour': self.prediction_next_hour,
            'prediction_next_day': self.prediction_next_day,
            'last_calculated': self.last_calculated.isoformat()
        }


class ResourceAllocationError(Exception):
    """Base exception for resource allocation errors."""
    pass


class InsufficientResourcesError(ResourceAllocationError):
    """Raised when insufficient resources are available."""
    pass


class QuotaExceededError(ResourceAllocationError):
    """Raised when resource quota is exceeded."""
    pass


class AllocationOptimizationError(ResourceAllocationError):
    """Raised when allocation optimization fails."""
    pass


class ResourceAllocationManager:
    """
    Manages resource allocation and optimization for multi-tenant clients.
    
    Provides dynamic resource allocation, quota enforcement, usage monitoring,
    and performance optimization across different resource types.
    """
    
    def __init__(self, isolation_service: TenantDataIsolationService, region: str = "us-east-1"):
        """
        Initialize the ResourceAllocationManager.
        
        Args:
            isolation_service: TenantDataIsolationService instance
            region: AWS region
        """
        self.isolation_service = isolation_service
        self.region = region
        self._dynamodb = None
        self._allocation_table = None
        self._metrics_table = None
        self._cloudwatch = None
        
        # Table names
        self.allocation_table_name = "resource-allocations"
        self.metrics_table_name = "resource-usage-metrics"
        
        # Cache for allocations and metrics
        self._allocation_cache: Dict[str, Dict[ResourceType, ResourceAllocation]] = {}
        self._metrics_cache: Dict[str, Dict[ResourceType, ResourceUsageMetrics]] = {}
        
        # Global resource pool tracking
        self._global_resource_pool = {
            ResourceType.COMPUTE: 10000,
            ResourceType.STORAGE: 100000,  # GB
            ResourceType.NETWORK: 50000,   # Mbps
            ResourceType.DATABASE: 5000,   # RCU/WCU
            ResourceType.API_CALLS: 1000000  # calls/month
        }
        
        self._allocated_resources = {
            ResourceType.COMPUTE: 0,
            ResourceType.STORAGE: 0,
            ResourceType.NETWORK: 0,
            ResourceType.DATABASE: 0,
            ResourceType.API_CALLS: 0
        }
    
    @property
    def dynamodb(self):
        """Lazy initialization of DynamoDB resource."""
        if self._dynamodb is None:
            self._dynamodb = boto3.resource('dynamodb', region_name=self.region)
        return self._dynamodb
    
    @property
    def allocation_table(self):
        """Lazy initialization of allocation table."""
        if self._allocation_table is None:
            self._allocation_table = self.dynamodb.Table(self.allocation_table_name)
        return self._allocation_table
    
    @property
    def metrics_table(self):
        """Lazy initialization of metrics table."""
        if self._metrics_table is None:
            self._metrics_table = self.dynamodb.Table(self.metrics_table_name)
        return self._metrics_table
    
    @property
    def cloudwatch(self):
        """Lazy initialization of CloudWatch client."""
        if self._cloudwatch is None:
            self._cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        return self._cloudwatch
    
    def allocate_resources_for_client(self, client: MultiCloudClient) -> Dict[ResourceType, ResourceAllocation]:
        """
        Allocate resources for a new client based on subscription tier and requirements.
        
        Args:
            client: MultiCloudClient to allocate resources for
            
        Returns:
            Dictionary mapping resource types to allocations
            
        Raises:
            InsufficientResourcesError: If insufficient resources are available
        """
        try:
            logger.info(f"Allocating resources for client {client.client_id}")
            
            allocations = {}
            
            # Calculate base allocations based on subscription tier
            base_allocations = self._calculate_base_allocations(client.subscription_tier)
            
            # Adjust allocations based on client requirements
            adjusted_allocations = self._adjust_allocations_for_client(client, base_allocations)
            
            # Check global resource availability
            self._validate_global_resource_availability(adjusted_allocations)
            
            # Create resource allocations
            for resource_type, amount in adjusted_allocations.items():
                allocation = ResourceAllocation(
                    tenant_id=client.tenant_id,
                    resource_type=resource_type,
                    allocated_amount=amount,
                    used_amount=0,
                    reserved_amount=int(amount * 0.1),  # 10% reserved
                    burst_limit=int(amount * 1.5),     # 50% burst capacity
                    allocation_strategy=self._get_allocation_strategy(client.subscription_tier),
                    last_updated=datetime.utcnow()
                )
                
                allocations[resource_type] = allocation
                
                # Store allocation
                self.allocation_table.put_item(
                    Item={
                        'tenant_id': client.tenant_id,
                        'resource_type': resource_type.value,
                        **allocation.to_dict()
                    }
                )
                
                # Update global allocation tracking
                self._allocated_resources[resource_type] += amount
            
            # Cache allocations
            self._allocation_cache[client.tenant_id] = allocations
            
            logger.info(f"Successfully allocated resources for client {client.client_id}: {len(allocations)} resource types")
            return allocations
            
        except Exception as e:
            logger.error(f"Failed to allocate resources for client {client.client_id}: {e}")
            raise ResourceAllocationError(f"Resource allocation failed: {e}") from e
    
    def get_client_allocations(self, tenant_id: str) -> Dict[ResourceType, ResourceAllocation]:
        """
        Get current resource allocations for a client.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Dictionary mapping resource types to allocations
        """
        try:
            # Check cache first
            if tenant_id in self._allocation_cache:
                return self._allocation_cache[tenant_id]
            
            # Query from database
            response = self.allocation_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('tenant_id').eq(tenant_id)
            )
            
            allocations = {}
            for item in response.get('Items', []):
                resource_type = ResourceType(item['resource_type'])
                allocation = ResourceAllocation(
                    tenant_id=item['tenant_id'],
                    resource_type=resource_type,
                    allocated_amount=item['allocated_amount'],
                    used_amount=item['used_amount'],
                    reserved_amount=item['reserved_amount'],
                    burst_limit=item['burst_limit'],
                    allocation_strategy=AllocationStrategy(item['allocation_strategy']),
                    last_updated=datetime.fromisoformat(item['last_updated'])
                )
                allocations[resource_type] = allocation
            
            # Cache allocations
            self._allocation_cache[tenant_id] = allocations
            return allocations
            
        except Exception as e:
            logger.error(f"Error getting client allocations for {tenant_id}: {e}")
            raise ResourceAllocationError(f"Failed to get client allocations: {e}") from e
    
    def update_resource_usage(self, tenant_id: str, resource_type: ResourceType, 
                            usage_delta: int, operation: str = "increment") -> ResourceAllocation:
        """
        Update resource usage for a tenant.
        
        Args:
            tenant_id: Tenant ID
            resource_type: Type of resource
            usage_delta: Change in usage amount
            operation: Operation type (increment, decrement, set)
            
        Returns:
            Updated ResourceAllocation
            
        Raises:
            QuotaExceededError: If usage would exceed quota
        """
        try:
            logger.debug(f"Updating resource usage for {tenant_id}: {resource_type.value} {operation} {usage_delta}")
            
            # Get current allocation
            allocations = self.get_client_allocations(tenant_id)
            
            if resource_type not in allocations:
                raise ResourceAllocationError(f"No allocation found for resource type {resource_type.value}")
            
            allocation = allocations[resource_type]
            
            # Calculate new usage
            if operation == "increment":
                new_usage = allocation.used_amount + usage_delta
            elif operation == "decrement":
                new_usage = max(0, allocation.used_amount - usage_delta)
            elif operation == "set":
                new_usage = usage_delta
            else:
                raise ValueError(f"Invalid operation: {operation}")
            
            # Check quota limits
            if new_usage > allocation.burst_limit:
                raise QuotaExceededError(
                    f"Resource usage would exceed burst limit: {new_usage} > {allocation.burst_limit}"
                )
            
            # Update allocation
            allocation.used_amount = new_usage
            allocation.last_updated = datetime.utcnow()
            
            # Update in database
            self.allocation_table.update_item(
                Key={
                    'tenant_id': tenant_id,
                    'resource_type': resource_type.value
                },
                UpdateExpression='SET used_amount = :usage, last_updated = :updated',
                ExpressionAttributeValues={
                    ':usage': new_usage,
                    ':updated': allocation.last_updated.isoformat()
                }
            )
            
            # Update cache
            self._allocation_cache[tenant_id][resource_type] = allocation
            
            # Send CloudWatch metrics
            self._send_usage_metrics(tenant_id, resource_type, allocation)
            
            # Check if optimization is needed
            if allocation.utilization_percentage > 80:
                asyncio.create_task(self._optimize_allocation_async(tenant_id, resource_type))
            
            return allocation
            
        except QuotaExceededError:
            raise
        except Exception as e:
            logger.error(f"Error updating resource usage for {tenant_id}: {e}")
            raise ResourceAllocationError(f"Failed to update resource usage: {e}") from e
    
    def optimize_allocations(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Optimize resource allocations based on usage patterns.
        
        Args:
            tenant_id: Optional tenant ID to optimize (if None, optimize all)
            
        Returns:
            Dictionary containing optimization results
        """
        try:
            logger.info(f"Optimizing resource allocations for {'all tenants' if not tenant_id else tenant_id}")
            
            optimization_results = {
                'optimized_tenants': [],
                'total_savings': 0,
                'recommendations': []
            }
            
            if tenant_id:
                tenant_ids = [tenant_id]
            else:
                # Get all tenant IDs (this would need to be implemented)
                tenant_ids = self._get_all_tenant_ids()
            
            for tid in tenant_ids:
                try:
                    tenant_result = self._optimize_tenant_allocations(tid)
                    optimization_results['optimized_tenants'].append(tenant_result)
                    optimization_results['total_savings'] += tenant_result.get('savings', 0)
                    optimization_results['recommendations'].extend(tenant_result.get('recommendations', []))
                    
                except Exception as e:
                    logger.error(f"Error optimizing allocations for tenant {tid}: {e}")
                    continue
            
            logger.info(f"Optimization completed: {len(optimization_results['optimized_tenants'])} tenants optimized")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Error during allocation optimization: {e}")
            raise AllocationOptimizationError(f"Allocation optimization failed: {e}") from e
    
    def get_resource_utilization_report(self, tenant_id: str) -> Dict[str, Any]:
        """
        Generate resource utilization report for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Dictionary containing utilization report
        """
        try:
            logger.info(f"Generating resource utilization report for {tenant_id}")
            
            allocations = self.get_client_allocations(tenant_id)
            metrics = self._get_usage_metrics(tenant_id)
            
            report = {
                'tenant_id': tenant_id,
                'generated_at': datetime.utcnow().isoformat(),
                'resource_utilization': {},
                'recommendations': [],
                'cost_optimization': {},
                'performance_insights': {}
            }
            
            total_allocated_cost = 0
            total_used_cost = 0
            
            for resource_type, allocation in allocations.items():
                utilization = allocation.utilization_percentage
                
                # Calculate cost (simplified pricing model)
                resource_cost_per_unit = self._get_resource_cost_per_unit(resource_type)
                allocated_cost = allocation.allocated_amount * resource_cost_per_unit
                used_cost = allocation.used_amount * resource_cost_per_unit
                
                total_allocated_cost += allocated_cost
                total_used_cost += used_cost
                
                resource_report = {
                    'allocated': allocation.allocated_amount,
                    'used': allocation.used_amount,
                    'available': allocation.available_amount,
                    'utilization_percentage': utilization,
                    'burst_limit': allocation.burst_limit,
                    'allocated_cost': allocated_cost,
                    'used_cost': used_cost,
                    'potential_savings': allocated_cost - used_cost
                }
                
                # Add metrics if available
                if resource_type in metrics:
                    metric = metrics[resource_type]
                    resource_report.update({
                        'peak_usage': metric.peak_usage,
                        'average_usage': metric.average_usage,
                        'usage_trend': metric.usage_trend,
                        'predicted_usage_next_hour': metric.prediction_next_hour,
                        'predicted_usage_next_day': metric.prediction_next_day
                    })
                
                report['resource_utilization'][resource_type.value] = resource_report
                
                # Generate recommendations
                if utilization < 30:
                    report['recommendations'].append({
                        'type': 'downsize',
                        'resource': resource_type.value,
                        'current_allocation': allocation.allocated_amount,
                        'recommended_allocation': int(allocation.allocated_amount * 0.7),
                        'potential_savings': (allocated_cost - used_cost) * 0.3
                    })
                elif utilization > 80:
                    report['recommendations'].append({
                        'type': 'upsize',
                        'resource': resource_type.value,
                        'current_allocation': allocation.allocated_amount,
                        'recommended_allocation': int(allocation.allocated_amount * 1.3),
                        'reason': 'High utilization detected'
                    })
            
            # Overall cost optimization
            report['cost_optimization'] = {
                'total_allocated_cost': total_allocated_cost,
                'total_used_cost': total_used_cost,
                'potential_monthly_savings': total_allocated_cost - total_used_cost,
                'cost_efficiency_percentage': (total_used_cost / total_allocated_cost * 100) if total_allocated_cost > 0 else 0
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating utilization report for {tenant_id}: {e}")
            raise ResourceAllocationError(f"Failed to generate utilization report: {e}") from e
    
    def _calculate_base_allocations(self, subscription_tier: SubscriptionTier) -> Dict[ResourceType, int]:
        """Calculate base resource allocations based on subscription tier."""
        base_allocations = {
            SubscriptionTier.FREE: {
                ResourceType.COMPUTE: 10,
                ResourceType.STORAGE: 100,
                ResourceType.NETWORK: 50,
                ResourceType.DATABASE: 25,
                ResourceType.API_CALLS: 10000
            },
            SubscriptionTier.BASIC: {
                ResourceType.COMPUTE: 50,
                ResourceType.STORAGE: 500,
                ResourceType.NETWORK: 200,
                ResourceType.DATABASE: 100,
                ResourceType.API_CALLS: 50000
            },
            SubscriptionTier.PROFESSIONAL: {
                ResourceType.COMPUTE: 200,
                ResourceType.STORAGE: 2000,
                ResourceType.NETWORK: 1000,
                ResourceType.DATABASE: 500,
                ResourceType.API_CALLS: 200000
            },
            SubscriptionTier.ENTERPRISE: {
                ResourceType.COMPUTE: 1000,
                ResourceType.STORAGE: 10000,
                ResourceType.NETWORK: 5000,
                ResourceType.DATABASE: 2500,
                ResourceType.API_CALLS: 1000000
            }
        }
        
        return base_allocations.get(subscription_tier, base_allocations[SubscriptionTier.FREE])
    
    def _adjust_allocations_for_client(self, client: MultiCloudClient, 
                                     base_allocations: Dict[ResourceType, int]) -> Dict[ResourceType, int]:
        """Adjust allocations based on client-specific requirements."""
        adjusted = base_allocations.copy()
        
        # Adjust based on number of cloud accounts
        total_accounts = sum(len(accounts) for accounts in client.cloud_accounts.values())
        account_multiplier = max(1.0, total_accounts / 5.0)  # Scale up for more accounts
        
        # Adjust based on enabled providers
        provider_count = len(client.get_providers())
        provider_multiplier = max(1.0, provider_count / 2.0)  # Scale up for more providers
        
        # Apply adjustments
        for resource_type in adjusted:
            if resource_type in [ResourceType.COMPUTE, ResourceType.DATABASE, ResourceType.API_CALLS]:
                adjusted[resource_type] = int(adjusted[resource_type] * account_multiplier)
            
            if resource_type in [ResourceType.STORAGE, ResourceType.NETWORK]:
                adjusted[resource_type] = int(adjusted[resource_type] * provider_multiplier)
        
        return adjusted
    
    def _validate_global_resource_availability(self, requested_allocations: Dict[ResourceType, int]) -> None:
        """Validate that requested allocations don't exceed global resource pool."""
        for resource_type, requested_amount in requested_allocations.items():
            available = self._global_resource_pool[resource_type] - self._allocated_resources[resource_type]
            
            if requested_amount > available:
                raise InsufficientResourcesError(
                    f"Insufficient {resource_type.value} resources: requested {requested_amount}, available {available}"
                )
    
    def _get_allocation_strategy(self, subscription_tier: SubscriptionTier) -> AllocationStrategy:
        """Get allocation strategy based on subscription tier."""
        if subscription_tier == SubscriptionTier.ENTERPRISE:
            return AllocationStrategy.RESERVED
        elif subscription_tier == SubscriptionTier.PROFESSIONAL:
            return AllocationStrategy.DYNAMIC
        else:
            return AllocationStrategy.FIXED
    
    def _send_usage_metrics(self, tenant_id: str, resource_type: ResourceType, allocation: ResourceAllocation) -> None:
        """Send usage metrics to CloudWatch."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace='MultiCloudCostAnalytics/ResourceUsage',
                MetricData=[
                    {
                        'MetricName': 'ResourceUtilization',
                        'Dimensions': [
                            {
                                'Name': 'TenantId',
                                'Value': tenant_id
                            },
                            {
                                'Name': 'ResourceType',
                                'Value': resource_type.value
                            }
                        ],
                        'Value': allocation.utilization_percentage,
                        'Unit': 'Percent',
                        'Timestamp': allocation.last_updated
                    },
                    {
                        'MetricName': 'ResourceUsage',
                        'Dimensions': [
                            {
                                'Name': 'TenantId',
                                'Value': tenant_id
                            },
                            {
                                'Name': 'ResourceType',
                                'Value': resource_type.value
                            }
                        ],
                        'Value': allocation.used_amount,
                        'Unit': 'Count',
                        'Timestamp': allocation.last_updated
                    }
                ]
            )
        except Exception as e:
            logger.warning(f"Failed to send CloudWatch metrics for {tenant_id}: {e}")
    
    async def _optimize_allocation_async(self, tenant_id: str, resource_type: ResourceType) -> None:
        """Asynchronously optimize allocation for a specific resource type."""
        try:
            logger.info(f"Optimizing {resource_type.value} allocation for tenant {tenant_id}")
            
            # Get current allocation and usage patterns
            allocations = self.get_client_allocations(tenant_id)
            allocation = allocations[resource_type]
            
            # Simple optimization: if utilization is consistently high, increase allocation
            if allocation.utilization_percentage > 80:
                new_allocation = int(allocation.allocated_amount * 1.2)
                
                # Check if we have global resources available
                available = (self._global_resource_pool[resource_type] - 
                           self._allocated_resources[resource_type] + 
                           allocation.allocated_amount)
                
                if new_allocation <= available:
                    # Update allocation
                    self.allocation_table.update_item(
                        Key={
                            'tenant_id': tenant_id,
                            'resource_type': resource_type.value
                        },
                        UpdateExpression='SET allocated_amount = :allocation, last_updated = :updated',
                        ExpressionAttributeValues={
                            ':allocation': new_allocation,
                            ':updated': datetime.utcnow().isoformat()
                        }
                    )
                    
                    # Update global tracking
                    self._allocated_resources[resource_type] += (new_allocation - allocation.allocated_amount)
                    
                    # Clear cache to force refresh
                    if tenant_id in self._allocation_cache:
                        del self._allocation_cache[tenant_id]
                    
                    logger.info(f"Optimized {resource_type.value} allocation for {tenant_id}: {allocation.allocated_amount} -> {new_allocation}")
                
        except Exception as e:
            logger.error(f"Error optimizing allocation for {tenant_id}: {e}")
    
    def _optimize_tenant_allocations(self, tenant_id: str) -> Dict[str, Any]:
        """Optimize allocations for a specific tenant."""
        result = {
            'tenant_id': tenant_id,
            'optimizations': [],
            'savings': 0,
            'recommendations': []
        }
        
        try:
            allocations = self.get_client_allocations(tenant_id)
            
            for resource_type, allocation in allocations.items():
                utilization = allocation.utilization_percentage
                
                if utilization < 30:  # Under-utilized
                    new_allocation = max(allocation.used_amount * 2, int(allocation.allocated_amount * 0.7))
                    savings = (allocation.allocated_amount - new_allocation) * self._get_resource_cost_per_unit(resource_type)
                    
                    result['optimizations'].append({
                        'resource_type': resource_type.value,
                        'action': 'downsize',
                        'old_allocation': allocation.allocated_amount,
                        'new_allocation': new_allocation,
                        'savings': savings
                    })
                    
                    result['savings'] += savings
                
                elif utilization > 90:  # Over-utilized
                    result['recommendations'].append({
                        'resource_type': resource_type.value,
                        'action': 'upsize',
                        'reason': f'High utilization: {utilization:.1f}%',
                        'recommended_increase': '20%'
                    })
            
        except Exception as e:
            logger.error(f"Error optimizing tenant allocations for {tenant_id}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _get_usage_metrics(self, tenant_id: str) -> Dict[ResourceType, ResourceUsageMetrics]:
        """Get usage metrics for a tenant."""
        # This would query the metrics table and return usage metrics
        # For now, return empty dict
        return {}
    
    def _get_resource_cost_per_unit(self, resource_type: ResourceType) -> float:
        """Get cost per unit for a resource type (simplified pricing)."""
        cost_per_unit = {
            ResourceType.COMPUTE: 0.10,      # $0.10 per compute unit
            ResourceType.STORAGE: 0.023,     # $0.023 per GB
            ResourceType.NETWORK: 0.05,      # $0.05 per Mbps
            ResourceType.DATABASE: 0.20,     # $0.20 per RCU/WCU
            ResourceType.API_CALLS: 0.0001   # $0.0001 per API call
        }
        
        return cost_per_unit.get(resource_type, 0.0)
    
    def _get_all_tenant_ids(self) -> List[str]:
        """Get all tenant IDs (placeholder implementation)."""
        # This would scan the allocation table to get all unique tenant IDs
        # For now, return empty list
        return []


# DynamoDB Table Schemas for Resource Allocation

RESOURCE_ALLOCATION_TABLE_SCHEMA = {
    "TableName": "resource-allocations",
    "KeySchema": [
        {
            "AttributeName": "tenant_id",
            "KeyType": "HASH"
        },
        {
            "AttributeName": "resource_type",
            "KeyType": "RANGE"
        }
    ],
    "AttributeDefinitions": [
        {
            "AttributeName": "tenant_id",
            "AttributeType": "S"
        },
        {
            "AttributeName": "resource_type",
            "AttributeType": "S"
        }
    ],
    "BillingMode": "PAY_PER_REQUEST",
    "Tags": [
        {
            "Key": "Project",
            "Value": "multi-cloud-cost-analytics"
        },
        {
            "Key": "Component",
            "Value": "resource-allocation"
        }
    ]
}

RESOURCE_USAGE_METRICS_TABLE_SCHEMA = {
    "TableName": "resource-usage-metrics",
    "KeySchema": [
        {
            "AttributeName": "tenant_id",
            "KeyType": "HASH"
        },
        {
            "AttributeName": "resource_type_timestamp",
            "KeyType": "RANGE"
        }
    ],
    "AttributeDefinitions": [
        {
            "AttributeName": "tenant_id",
            "AttributeType": "S"
        },
        {
            "AttributeName": "resource_type_timestamp",
            "AttributeType": "S"
        }
    ],
    "BillingMode": "PAY_PER_REQUEST",
    "TimeToLiveSpecification": {
        "AttributeName": "ttl",
        "Enabled": True
    },
    "Tags": [
        {
            "Key": "Project",
            "Value": "multi-cloud-cost-analytics"
        },
        {
            "Key": "Component",
            "Value": "resource-allocation"
        }
    ]
}