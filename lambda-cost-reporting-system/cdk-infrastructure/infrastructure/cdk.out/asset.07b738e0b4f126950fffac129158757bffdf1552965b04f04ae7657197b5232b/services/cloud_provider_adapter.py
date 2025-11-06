"""
Cloud Provider Adapter Base Classes

This module defines the abstract base classes and interfaces for cloud provider
adapters in the multi-cloud cost analytics platform.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncIterator
from datetime import datetime, timedelta
import logging
import asyncio
from contextlib import asynccontextmanager

from ..models.provider_models import (
    ProviderCredentials, CredentialValidation, DateRange, ProviderCostData,
    CollectionResult, ProviderAccount, ProviderService, ProviderType,
    DataCollectionStatus, ValidationStatus, ProviderError
)
from ..models.multi_cloud_models import UnifiedCostRecord, ServiceCategory


logger = logging.getLogger(__name__)


class CloudProviderAdapter(ABC):
    """
    Abstract base class for cloud provider adapters.
    
    This class defines the interface that all cloud provider adapters must implement
    to integrate with the multi-cloud cost analytics platform.
    """
    
    def __init__(self, credentials: ProviderCredentials):
        """
        Initialize the cloud provider adapter.
        
        Args:
            credentials: Provider-specific credentials
        """
        self.credentials = credentials
        self.provider = credentials.provider
        self._client = None
        self._session = None
        self.logger = logging.getLogger(f"{__name__}.{self.provider.value}")
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the human-readable provider name."""
        pass
    
    @property
    @abstractmethod
    def supported_regions(self) -> List[str]:
        """Get list of supported regions for this provider."""
        pass
    
    @property
    @abstractmethod
    def default_currency(self) -> str:
        """Get the default currency for this provider."""
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> CredentialValidation:
        """
        Validate the provider credentials.
        
        Returns:
            CredentialValidation object with validation results
        """
        pass
    
    @abstractmethod
    async def collect_cost_data(self, date_range: DateRange) -> CollectionResult:
        """
        Collect cost data from the provider for the specified date range.
        
        Args:
            date_range: Date range for cost data collection
            
        Returns:
            CollectionResult with cost data and collection metadata
        """
        pass
    
    @abstractmethod
    async def get_accounts(self) -> List[ProviderAccount]:
        """
        Get list of accounts accessible with current credentials.
        
        Returns:
            List of ProviderAccount objects
        """
        pass
    
    @abstractmethod
    async def get_services(self) -> List[ProviderService]:
        """
        Get list of services available from this provider.
        
        Returns:
            List of ProviderService objects
        """
        pass
    
    @abstractmethod
    def get_service_mapping(self) -> Dict[str, ServiceCategory]:
        """
        Get mapping of provider-specific services to unified categories.
        
        Returns:
            Dictionary mapping service names to ServiceCategory enums
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to the provider API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    # Optional methods with default implementations
    
    async def get_cost_data_incremental(
        self, 
        date_range: DateRange,
        batch_size: int = 7
    ) -> AsyncIterator[CollectionResult]:
        """
        Collect cost data incrementally in batches.
        
        Args:
            date_range: Date range for cost data collection
            batch_size: Number of days to collect in each batch
            
        Yields:
            CollectionResult for each batch
        """
        current_date = date_range.start_date
        
        while current_date <= date_range.end_date:
            batch_end_date = min(
                current_date + timedelta(days=batch_size - 1),
                date_range.end_date
            )
            
            batch_range = DateRange(start_date=current_date, end_date=batch_end_date)
            
            try:
                result = await self.collect_cost_data(batch_range)
                yield result
            except Exception as e:
                self.logger.error(f"Error collecting batch {current_date} to {batch_end_date}: {e}")
                yield CollectionResult(
                    status=DataCollectionStatus.FAILED,
                    provider=self.provider,
                    client_id="unknown",
                    date_range=batch_range,
                    error_message=str(e)
                )
            
            current_date = batch_end_date + timedelta(days=1)
    
    async def get_cost_forecast(
        self, 
        date_range: DateRange,
        forecast_days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Get cost forecast from provider (if supported).
        
        Args:
            date_range: Historical date range for forecast basis
            forecast_days: Number of days to forecast
            
        Returns:
            Forecast data or None if not supported
        """
        self.logger.info(f"Cost forecasting not implemented for {self.provider.value}")
        return None
    
    async def get_cost_anomalies(
        self, 
        date_range: DateRange
    ) -> List[Dict[str, Any]]:
        """
        Get cost anomalies from provider (if supported).
        
        Args:
            date_range: Date range to check for anomalies
            
        Returns:
            List of anomaly data
        """
        self.logger.info(f"Anomaly detection not implemented for {self.provider.value}")
        return []
    
    async def get_budget_information(self) -> List[Dict[str, Any]]:
        """
        Get budget information from provider (if supported).
        
        Returns:
            List of budget data
        """
        self.logger.info(f"Budget information not implemented for {self.provider.value}")
        return []
    
    def normalize_cost_data(self, raw_data: ProviderCostData) -> UnifiedCostRecord:
        """
        Convert provider-specific cost data to unified format.
        
        Args:
            raw_data: Raw cost data from provider
            
        Returns:
            UnifiedCostRecord in unified format
        """
        from ..models.multi_cloud_models import (
            UnifiedCostRecord, ServiceCost, AccountCost, RegionCost,
            CollectionMetadata, DataQuality, DataQualityLevel, Currency
        )
        
        # Create unified cost record
        unified_record = UnifiedCostRecord(
            client_id=raw_data.client_id,
            provider=raw_data.provider,
            date=raw_data.date_range.start_date.isoformat(),
            total_cost=raw_data.total_cost,
            currency=Currency(raw_data.currency)
        )
        
        # Convert services
        service_mapping = self.get_service_mapping()
        for service_name, service_data in raw_data.services.items():
            if isinstance(service_data, dict):
                cost = service_data.get('cost', 0)
                usage_metrics = service_data.get('usage_metrics', {})
                provider_data = service_data.get('provider_data', {})
            else:
                cost = service_data
                usage_metrics = {}
                provider_data = {}
            
            service_cost = ServiceCost(
                service_name=service_name,
                unified_category=service_mapping.get(service_name, ServiceCategory.OTHER),
                cost=cost if isinstance(cost, type(raw_data.total_cost)) else type(raw_data.total_cost)(str(cost)),
                currency=Currency(raw_data.currency),
                usage_metrics=usage_metrics,
                provider_specific_data=provider_data
            )
            unified_record.add_service_cost(service_cost)
        
        # Convert accounts
        for account in raw_data.accounts:
            account_cost = AccountCost(
                account_id=account.account_id,
                account_name=account.account_name,
                cost=type(raw_data.total_cost)('0'),  # Will be calculated from services
                currency=Currency(raw_data.currency)
            )
            unified_record.add_account_cost(account_cost)
        
        # Convert regions
        for region_name, region_cost in raw_data.regions.items():
            region_cost_obj = RegionCost(
                region_name=region_name,
                cost=region_cost,
                currency=Currency(raw_data.currency)
            )
            unified_record.add_region_cost(region_cost_obj)
        
        # Add collection metadata
        if raw_data.collection_metadata:
            unified_record.collection_metadata = CollectionMetadata(
                collection_timestamp=datetime.utcnow(),
                collection_duration_seconds=raw_data.collection_metadata.get('duration', 0),
                api_calls_made=raw_data.collection_metadata.get('api_calls', 0),
                accounts_processed=len(raw_data.accounts),
                services_discovered=len(raw_data.services),
                data_freshness_hours=raw_data.collection_metadata.get('freshness_hours', 24),
                collection_method='api',
                collector_version='1.0.0'
            )
        
        # Add basic data quality assessment
        unified_record.data_quality = DataQuality(
            completeness_score=0.9,  # Default, should be calculated
            accuracy_score=0.95,     # Default, should be calculated
            timeliness_score=0.9,    # Default, should be calculated
            consistency_score=0.95,  # Default, should be calculated
            confidence_level=DataQualityLevel.HIGH
        )
        
        return unified_record
    
    @asynccontextmanager
    async def connection_context(self):
        """
        Async context manager for managing provider connections.
        
        Usage:
            async with adapter.connection_context():
                # Perform operations
                pass
        """
        try:
            await self._initialize_client()
            yield self
        except Exception as e:
            self.logger.error(f"Error in connection context: {e}")
            raise
        finally:
            await self._cleanup_client()
    
    async def _initialize_client(self):
        """Initialize the provider client. Override in subclasses."""
        pass
    
    async def _cleanup_client(self):
        """Cleanup the provider client. Override in subclasses."""
        pass
    
    def _handle_provider_error(self, error: Exception) -> ProviderError:
        """
        Convert provider-specific errors to standardized ProviderError.
        
        Args:
            error: Original provider error
            
        Returns:
            Standardized ProviderError
        """
        # Default implementation - override in subclasses for provider-specific handling
        return ProviderError(
            provider=self.provider,
            error_code="UNKNOWN_ERROR",
            message=str(error),
            details={'original_error': str(error)},
            is_retryable=False
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the provider connection.
        
        Returns:
            Dictionary with health check results
        """
        health_status = {
            'provider': self.provider.value,
            'status': 'unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        try:
            # Test basic connection
            connection_ok = await self.test_connection()
            health_status['checks']['connection'] = {
                'status': 'pass' if connection_ok else 'fail',
                'message': 'Connection test successful' if connection_ok else 'Connection test failed'
            }
            
            # Test credential validation
            validation = await self.validate_credentials()
            health_status['checks']['credentials'] = {
                'status': 'pass' if validation.is_valid else 'fail',
                'message': validation.error_message or 'Credentials valid'
            }
            
            # Overall status
            all_checks_pass = all(
                check['status'] == 'pass' 
                for check in health_status['checks'].values()
            )
            health_status['status'] = 'healthy' if all_checks_pass else 'unhealthy'
            
        except Exception as e:
            health_status['status'] = 'error'
            health_status['error'] = str(e)
            self.logger.error(f"Health check failed for {self.provider.value}: {e}")
        
        return health_status


class ProviderAdapterFactory:
    """Factory class for creating provider adapters."""
    
    _adapters: Dict[ProviderType, type] = {}
    
    @classmethod
    def register_adapter(cls, provider: ProviderType, adapter_class: type):
        """
        Register a provider adapter class.
        
        Args:
            provider: Provider type
            adapter_class: Adapter class to register
        """
        cls._adapters[provider] = adapter_class
    
    @classmethod
    def create_adapter(cls, credentials: ProviderCredentials) -> CloudProviderAdapter:
        """
        Create a provider adapter instance.
        
        Args:
            credentials: Provider credentials
            
        Returns:
            Provider adapter instance
        """
        adapter_class = cls._adapters.get(credentials.provider)
        if not adapter_class:
            raise ValueError(f"No adapter registered for provider: {credentials.provider}")
        
        return adapter_class(credentials)
    
    @classmethod
    def get_supported_providers(cls) -> List[ProviderType]:
        """
        Get list of supported providers.
        
        Returns:
            List of supported provider types
        """
        return list(cls._adapters.keys())


class ProviderAdapterManager:
    """Manager class for handling multiple provider adapters."""
    
    def __init__(self):
        """Initialize the adapter manager."""
        self.adapters: Dict[str, CloudProviderAdapter] = {}
        self.logger = logging.getLogger(f"{__name__}.ProviderAdapterManager")
    
    def add_adapter(self, client_id: str, adapter: CloudProviderAdapter):
        """
        Add a provider adapter for a client.
        
        Args:
            client_id: Client identifier
            adapter: Provider adapter instance
        """
        key = f"{client_id}:{adapter.provider.value}"
        self.adapters[key] = adapter
        self.logger.info(f"Added adapter for client {client_id}, provider {adapter.provider.value}")
    
    def get_adapter(self, client_id: str, provider: ProviderType) -> Optional[CloudProviderAdapter]:
        """
        Get a provider adapter for a client.
        
        Args:
            client_id: Client identifier
            provider: Provider type
            
        Returns:
            Provider adapter or None if not found
        """
        key = f"{client_id}:{provider.value}"
        return self.adapters.get(key)
    
    def remove_adapter(self, client_id: str, provider: ProviderType):
        """
        Remove a provider adapter for a client.
        
        Args:
            client_id: Client identifier
            provider: Provider type
        """
        key = f"{client_id}:{provider.value}"
        if key in self.adapters:
            del self.adapters[key]
            self.logger.info(f"Removed adapter for client {client_id}, provider {provider.value}")
    
    async def collect_all_cost_data(
        self, 
        client_id: str, 
        date_range: DateRange
    ) -> List[CollectionResult]:
        """
        Collect cost data from all providers for a client.
        
        Args:
            client_id: Client identifier
            date_range: Date range for collection
            
        Returns:
            List of collection results
        """
        results = []
        client_adapters = [
            adapter for key, adapter in self.adapters.items()
            if key.startswith(f"{client_id}:")
        ]
        
        if not client_adapters:
            self.logger.warning(f"No adapters found for client {client_id}")
            return results
        
        # Collect data from all providers concurrently
        tasks = [
            adapter.collect_cost_data(date_range)
            for adapter in client_adapters
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    adapter = client_adapters[i]
                    self.logger.error(f"Error collecting data from {adapter.provider.value}: {result}")
                    results[i] = CollectionResult(
                        status=DataCollectionStatus.FAILED,
                        provider=adapter.provider,
                        client_id=client_id,
                        date_range=date_range,
                        error_message=str(result)
                    )
        
        except Exception as e:
            self.logger.error(f"Error in concurrent collection for client {client_id}: {e}")
        
        return results
    
    async def validate_all_credentials(self, client_id: str) -> Dict[ProviderType, CredentialValidation]:
        """
        Validate credentials for all providers for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dictionary mapping provider types to validation results
        """
        validations = {}
        client_adapters = [
            adapter for key, adapter in self.adapters.items()
            if key.startswith(f"{client_id}:")
        ]
        
        for adapter in client_adapters:
            try:
                validation = await adapter.validate_credentials()
                validations[adapter.provider] = validation
            except Exception as e:
                self.logger.error(f"Error validating {adapter.provider.value} credentials: {e}")
                validations[adapter.provider] = CredentialValidation(
                    status=ValidationStatus.UNKNOWN,
                    is_valid=False,
                    error_message=str(e)
                )
        
        return validations
    
    async def health_check_all(self, client_id: str) -> Dict[ProviderType, Dict[str, Any]]:
        """
        Perform health checks on all adapters for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dictionary mapping provider types to health check results
        """
        health_checks = {}
        client_adapters = [
            adapter for key, adapter in self.adapters.items()
            if key.startswith(f"{client_id}:")
        ]
        
        for adapter in client_adapters:
            try:
                health_check = await adapter.health_check()
                health_checks[adapter.provider] = health_check
            except Exception as e:
                self.logger.error(f"Error in health check for {adapter.provider.value}: {e}")
                health_checks[adapter.provider] = {
                    'provider': adapter.provider.value,
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return health_checks


# Global adapter manager instance
adapter_manager = ProviderAdapterManager()