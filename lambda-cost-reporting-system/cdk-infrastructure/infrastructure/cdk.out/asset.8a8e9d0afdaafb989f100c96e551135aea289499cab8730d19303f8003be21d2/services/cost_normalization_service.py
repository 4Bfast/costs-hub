"""
Cost Normalization Service

This module implements the cost normalization service for the multi-cloud cost analytics platform.
It provides functionality to normalize cost data from different cloud providers into a unified format,
including currency conversion, data transformation, and provider-specific data handling.
"""

import logging
import asyncio
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import json
import aiohttp
from enum import Enum

from ..models.multi_cloud_models import (
    UnifiedCostRecord, ServiceCost, AccountCost, RegionCost,
    CloudProvider, ServiceCategory, Currency, DataQuality, DataQualityLevel,
    CollectionMetadata
)
from ..models.provider_models import ProviderCostData, ProviderType
from ..services.service_mapper import ServiceMapper, get_unified_service_category


logger = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Base exception for normalization errors."""
    pass


class CurrencyConversionError(NormalizationError):
    """Exception for currency conversion errors."""
    pass


class DataTransformationError(NormalizationError):
    """Exception for data transformation errors."""
    pass


@dataclass
class CurrencyRate:
    """Currency exchange rate information."""
    from_currency: Currency
    to_currency: Currency
    rate: Decimal
    timestamp: datetime
    source: str = "external_api"
    
    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Check if the rate is expired."""
        age_hours = (datetime.utcnow() - self.timestamp).total_seconds() / 3600
        return age_hours > max_age_hours


@dataclass
class NormalizationConfig:
    """Configuration for cost normalization."""
    target_currency: Currency = Currency.USD
    enable_currency_conversion: bool = True
    currency_api_key: Optional[str] = None
    currency_cache_hours: int = 24
    enable_fuzzy_service_matching: bool = True
    data_quality_threshold: float = 0.7
    enable_cost_validation: bool = True
    max_cost_variance_percent: float = 10.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'target_currency': self.target_currency.value,
            'enable_currency_conversion': self.enable_currency_conversion,
            'currency_cache_hours': self.currency_cache_hours,
            'enable_fuzzy_service_matching': self.enable_fuzzy_service_matching,
            'data_quality_threshold': self.data_quality_threshold,
            'enable_cost_validation': self.enable_cost_validation,
            'max_cost_variance_percent': self.max_cost_variance_percent
        }


class CurrencyConverter:
    """Currency conversion service with caching and fallback rates."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize currency converter."""
        self.api_key = api_key
        self.rate_cache: Dict[str, CurrencyRate] = {}
        self.logger = logging.getLogger(f"{__name__}.CurrencyConverter")
        
        # Fallback rates (updated periodically)
        self.fallback_rates = {
            'EUR': Decimal('1.08'),
            'GBP': Decimal('1.27'),
            'JPY': Decimal('0.0067'),
            'BRL': Decimal('0.18'),
            'CAD': Decimal('0.74'),
            'AUD': Decimal('0.66'),
            'CHF': Decimal('1.11'),
            'CNY': Decimal('0.14'),
            'INR': Decimal('0.012')
        }
    
    async def get_exchange_rate(
        self, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> CurrencyRate:
        """
        Get exchange rate between two currencies.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            CurrencyRate object
            
        Raises:
            CurrencyConversionError: If rate cannot be obtained
        """
        if from_currency == to_currency:
            return CurrencyRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=Decimal('1.0'),
                timestamp=datetime.utcnow(),
                source="identity"
            )
        
        cache_key = f"{from_currency.value}_{to_currency.value}"
        
        # Check cache first
        if cache_key in self.rate_cache:
            cached_rate = self.rate_cache[cache_key]
            if not cached_rate.is_expired():
                return cached_rate
        
        # Try to get rate from external API
        try:
            rate = await self._fetch_rate_from_api(from_currency, to_currency)
            if rate:
                self.rate_cache[cache_key] = rate
                return rate
        except Exception as e:
            self.logger.warning(f"Failed to fetch rate from API: {e}")
        
        # Fall back to static rates
        fallback_rate = self._get_fallback_rate(from_currency, to_currency)
        if fallback_rate:
            self.rate_cache[cache_key] = fallback_rate
            return fallback_rate
        
        raise CurrencyConversionError(
            f"Unable to get exchange rate from {from_currency.value} to {to_currency.value}"
        )
    
    async def _fetch_rate_from_api(
        self, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> Optional[CurrencyRate]:
        """
        Fetch exchange rate from external API.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            CurrencyRate if successful, None otherwise
        """
        if not self.api_key:
            return None
        
        # Using exchangerate-api.com as an example
        url = f"https://v6.exchangerate-api.com/v6/{self.api_key}/pair/{from_currency.value}/{to_currency.value}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('result') == 'success':
                            rate_value = Decimal(str(data['conversion_rate']))
                            return CurrencyRate(
                                from_currency=from_currency,
                                to_currency=to_currency,
                                rate=rate_value,
                                timestamp=datetime.utcnow(),
                                source="exchangerate_api"
                            )
        except Exception as e:
            self.logger.error(f"API request failed: {e}")
        
        return None
    
    def _get_fallback_rate(
        self, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> Optional[CurrencyRate]:
        """
        Get fallback exchange rate from static rates.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            CurrencyRate if available, None otherwise
        """
        # Convert to USD first, then to target currency
        if to_currency == Currency.USD:
            if from_currency.value in self.fallback_rates:
                return CurrencyRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=self.fallback_rates[from_currency.value],
                    timestamp=datetime.utcnow(),
                    source="fallback"
                )
        elif from_currency == Currency.USD:
            if to_currency.value in self.fallback_rates:
                # Inverse rate
                rate = Decimal('1.0') / self.fallback_rates[to_currency.value]
                return CurrencyRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    timestamp=datetime.utcnow(),
                    source="fallback"
                )
        else:
            # Convert through USD
            from_to_usd = self.fallback_rates.get(from_currency.value)
            usd_to_target = self.fallback_rates.get(to_currency.value)
            
            if from_to_usd and usd_to_target:
                # from_currency -> USD -> to_currency
                rate = from_to_usd / usd_to_target
                return CurrencyRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    timestamp=datetime.utcnow(),
                    source="fallback_cross"
                )
        
        return None
    
    async def convert_amount(
        self, 
        amount: Decimal, 
        from_currency: Currency, 
        to_currency: Currency
    ) -> Decimal:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Converted amount
        """
        if amount == 0:
            return Decimal('0')
        
        rate = await self.get_exchange_rate(from_currency, to_currency)
        converted = amount * rate.rate
        
        # Round to 2 decimal places
        return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class CostNormalizationService:
    """
    Service for normalizing cost data from different cloud providers into a unified format.
    
    This service handles:
    1. Currency conversion to a target currency
    2. Service mapping to unified categories
    3. Data validation and quality scoring
    4. Provider-specific data transformation
    """
    
    def __init__(self, config: Optional[NormalizationConfig] = None):
        """Initialize the cost normalization service."""
        self.config = config or NormalizationConfig()
        self.currency_converter = CurrencyConverter(self.config.currency_api_key)
        self.service_mapper = ServiceMapper()
        self.logger = logging.getLogger(f"{__name__}.CostNormalizationService")
        
        # Statistics tracking
        self.normalization_stats = {
            'total_records_processed': 0,
            'successful_normalizations': 0,
            'failed_normalizations': 0,
            'currency_conversions': 0,
            'service_mappings': 0
        }
    
    async def normalize_cost_data(
        self, 
        provider_data: ProviderCostData,
        client_id: Optional[str] = None
    ) -> UnifiedCostRecord:
        """
        Normalize provider-specific cost data to unified format.
        
        Args:
            provider_data: Raw cost data from provider
            client_id: Optional client ID for custom mappings
            
        Returns:
            UnifiedCostRecord with normalized data
            
        Raises:
            NormalizationError: If normalization fails
        """
        try:
            self.logger.info(f"Starting normalization for {provider_data.provider.value} data")
            start_time = datetime.utcnow()
            
            # Convert provider type to cloud provider
            cloud_provider = self._convert_provider_type(provider_data.provider)
            
            # Create base unified record
            unified_record = UnifiedCostRecord(
                client_id=provider_data.client_id,
                provider=cloud_provider,
                date=provider_data.date_range.start_date.isoformat()
            )
            
            # Step 1: Normalize currency
            target_currency = Currency(provider_data.currency) if hasattr(Currency, provider_data.currency) else Currency.USD
            if self.config.enable_currency_conversion and target_currency != self.config.target_currency:
                normalized_total_cost = await self.currency_converter.convert_amount(
                    provider_data.total_cost,
                    target_currency,
                    self.config.target_currency
                )
                unified_record.currency = self.config.target_currency
                self.normalization_stats['currency_conversions'] += 1
            else:
                normalized_total_cost = provider_data.total_cost
                unified_record.currency = target_currency
            
            unified_record.total_cost = normalized_total_cost
            
            # Step 2: Normalize services
            await self._normalize_services(
                unified_record, 
                provider_data, 
                cloud_provider, 
                client_id
            )
            
            # Step 3: Normalize accounts
            await self._normalize_accounts(
                unified_record, 
                provider_data, 
                cloud_provider, 
                client_id
            )
            
            # Step 4: Normalize regions
            await self._normalize_regions(
                unified_record, 
                provider_data, 
                target_currency
            )
            
            # Step 5: Create collection metadata
            unified_record.collection_metadata = self._create_collection_metadata(
                provider_data, start_time
            )
            
            # Step 6: Calculate data quality
            unified_record.data_quality = await self._calculate_data_quality(
                unified_record, provider_data
            )
            
            # Step 7: Validate normalized data
            if self.config.enable_cost_validation:
                await self._validate_normalized_data(unified_record, provider_data)
            
            # Store raw provider data for debugging
            unified_record.raw_provider_data = provider_data.raw_data
            
            self.normalization_stats['total_records_processed'] += 1
            self.normalization_stats['successful_normalizations'] += 1
            
            self.logger.info(f"Successfully normalized {provider_data.provider.value} data")
            return unified_record
            
        except Exception as e:
            self.normalization_stats['total_records_processed'] += 1
            self.normalization_stats['failed_normalizations'] += 1
            self.logger.error(f"Failed to normalize cost data: {e}")
            raise NormalizationError(f"Normalization failed: {str(e)}") from e
    
    def _convert_provider_type(self, provider_type: ProviderType) -> CloudProvider:
        """Convert ProviderType to CloudProvider."""
        mapping = {
            ProviderType.AWS: CloudProvider.AWS,
            ProviderType.GCP: CloudProvider.GCP,
            ProviderType.AZURE: CloudProvider.AZURE
        }
        return mapping.get(provider_type, CloudProvider.AWS)
    
    async def _normalize_services(
        self,
        unified_record: UnifiedCostRecord,
        provider_data: ProviderCostData,
        cloud_provider: CloudProvider,
        client_id: Optional[str]
    ):
        """Normalize service costs."""
        for service_name, service_data in provider_data.services.items():
            try:
                # Get service cost (handle different data structures)
                if isinstance(service_data, dict):
                    service_cost_amount = Decimal(str(service_data.get('cost', 0)))
                    usage_metrics = service_data.get('usage_metrics', {})
                    provider_specific = service_data.get('provider_specific_data', {})
                else:
                    service_cost_amount = Decimal(str(service_data))
                    usage_metrics = {}
                    provider_specific = {}
                
                # Convert currency if needed
                if self.config.enable_currency_conversion:
                    source_currency = Currency(provider_data.currency) if hasattr(Currency, provider_data.currency) else Currency.USD
                    if source_currency != self.config.target_currency:
                        service_cost_amount = await self.currency_converter.convert_amount(
                            service_cost_amount,
                            source_currency,
                            self.config.target_currency
                        )
                
                # Map service to unified category
                unified_category = get_unified_service_category(
                    cloud_provider, service_name, client_id
                )
                
                # Create service cost object
                service_cost = ServiceCost(
                    service_name=service_name,
                    unified_category=unified_category,
                    cost=service_cost_amount,
                    currency=self.config.target_currency,
                    usage_metrics=usage_metrics,
                    provider_specific_data=provider_specific
                )
                
                unified_record.add_service_cost(service_cost)
                self.normalization_stats['service_mappings'] += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to normalize service {service_name}: {e}")
    
    async def _normalize_accounts(
        self,
        unified_record: UnifiedCostRecord,
        provider_data: ProviderCostData,
        cloud_provider: CloudProvider,
        client_id: Optional[str]
    ):
        """Normalize account costs."""
        for account in provider_data.accounts:
            try:
                # Convert account cost
                account_cost_amount = account.cost if hasattr(account, 'cost') else Decimal('0')
                
                if self.config.enable_currency_conversion:
                    source_currency = Currency(provider_data.currency) if hasattr(Currency, provider_data.currency) else Currency.USD
                    if source_currency != self.config.target_currency:
                        account_cost_amount = await self.currency_converter.convert_amount(
                            account_cost_amount,
                            source_currency,
                            self.config.target_currency
                        )
                
                # Create account cost object
                account_cost = AccountCost(
                    account_id=account.account_id,
                    account_name=account.account_name,
                    cost=account_cost_amount,
                    currency=self.config.target_currency
                )
                
                # Add service breakdown if available
                if hasattr(account, 'services') and account.services:
                    for service_name, service_cost_value in account.services.items():
                        service_cost_amount = Decimal(str(service_cost_value))
                        
                        if self.config.enable_currency_conversion:
                            if source_currency != self.config.target_currency:
                                service_cost_amount = await self.currency_converter.convert_amount(
                                    service_cost_amount,
                                    source_currency,
                                    self.config.target_currency
                                )
                        
                        unified_category = get_unified_service_category(
                            cloud_provider, service_name, client_id
                        )
                        
                        service_cost = ServiceCost(
                            service_name=service_name,
                            unified_category=unified_category,
                            cost=service_cost_amount,
                            currency=self.config.target_currency
                        )
                        
                        account_cost.add_service_cost(service_cost)
                
                # Add region breakdown if available
                if hasattr(account, 'regions') and account.regions:
                    for region_name, region_cost_value in account.regions.items():
                        region_cost_amount = Decimal(str(region_cost_value))
                        
                        if self.config.enable_currency_conversion:
                            if source_currency != self.config.target_currency:
                                region_cost_amount = await self.currency_converter.convert_amount(
                                    region_cost_amount,
                                    source_currency,
                                    self.config.target_currency
                                )
                        
                        account_cost.regions[region_name] = region_cost_amount
                
                unified_record.add_account_cost(account_cost)
                
            except Exception as e:
                self.logger.warning(f"Failed to normalize account {account.account_id}: {e}")
    
    async def _normalize_regions(
        self,
        unified_record: UnifiedCostRecord,
        provider_data: ProviderCostData,
        source_currency: Currency
    ):
        """Normalize region costs."""
        for region_name, region_cost_value in provider_data.regions.items():
            try:
                region_cost_amount = Decimal(str(region_cost_value))
                
                if self.config.enable_currency_conversion:
                    if source_currency != self.config.target_currency:
                        region_cost_amount = await self.currency_converter.convert_amount(
                            region_cost_amount,
                            source_currency,
                            self.config.target_currency
                        )
                
                region_cost = RegionCost(
                    region_name=region_name,
                    cost=region_cost_amount,
                    currency=self.config.target_currency
                )
                
                unified_record.add_region_cost(region_cost)
                
            except Exception as e:
                self.logger.warning(f"Failed to normalize region {region_name}: {e}")
    
    def _create_collection_metadata(
        self,
        provider_data: ProviderCostData,
        start_time: datetime
    ) -> CollectionMetadata:
        """Create collection metadata."""
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        return CollectionMetadata(
            collection_timestamp=start_time,
            collection_duration_seconds=duration,
            api_calls_made=provider_data.collection_metadata.get('api_calls_made', 0),
            accounts_processed=len(provider_data.accounts),
            services_discovered=len(provider_data.services),
            data_freshness_hours=provider_data.collection_metadata.get('data_freshness_hours', 0),
            collection_method=provider_data.collection_metadata.get('collection_method', 'api'),
            collector_version="1.0.0"
        )
    
    async def _calculate_data_quality(
        self,
        unified_record: UnifiedCostRecord,
        provider_data: ProviderCostData
    ) -> DataQuality:
        """Calculate data quality metrics."""
        errors = []
        warnings = []
        
        # Completeness score
        completeness_score = 1.0
        if not unified_record.services and not unified_record.accounts:
            completeness_score -= 0.5
            errors.append("No service or account cost data available")
        
        if unified_record.total_cost == 0:
            completeness_score -= 0.3
            warnings.append("Total cost is zero")
        
        # Accuracy score
        accuracy_score = 1.0
        
        # Check cost consistency
        if unified_record.services:
            service_total = sum(s.cost for s in unified_record.services.values())
            if abs(unified_record.total_cost - service_total) > Decimal('0.01'):
                accuracy_score -= 0.2
                warnings.append(f"Total cost mismatch: {unified_record.total_cost} vs {service_total}")
        
        # Timeliness score (based on data freshness)
        timeliness_score = 1.0
        if unified_record.collection_metadata:
            freshness_hours = unified_record.collection_metadata.data_freshness_hours
            if freshness_hours > 48:
                timeliness_score -= 0.3
            elif freshness_hours > 24:
                timeliness_score -= 0.1
        
        # Consistency score
        consistency_score = 1.0
        
        # Check for negative costs
        if unified_record.total_cost < 0:
            consistency_score -= 0.5
            errors.append("Negative total cost detected")
        
        for service in unified_record.services.values():
            if service.cost < 0:
                consistency_score -= 0.1
                errors.append(f"Negative cost for service {service.service_name}")
        
        # Determine confidence level
        overall_score = (completeness_score + accuracy_score + timeliness_score + consistency_score) / 4
        
        if overall_score >= 0.9:
            confidence_level = DataQualityLevel.HIGH
        elif overall_score >= 0.7:
            confidence_level = DataQualityLevel.MEDIUM
        elif overall_score >= 0.5:
            confidence_level = DataQualityLevel.LOW
        else:
            confidence_level = DataQualityLevel.UNKNOWN
        
        return DataQuality(
            completeness_score=max(0.0, completeness_score),
            accuracy_score=max(0.0, accuracy_score),
            timeliness_score=max(0.0, timeliness_score),
            consistency_score=max(0.0, consistency_score),
            confidence_level=confidence_level,
            validation_errors=errors,
            validation_warnings=warnings
        )
    
    async def _validate_normalized_data(
        self,
        unified_record: UnifiedCostRecord,
        provider_data: ProviderCostData
    ):
        """Validate normalized data against original data."""
        # Check for significant cost variance
        original_total = provider_data.total_cost
        normalized_total = unified_record.total_cost
        
        if original_total > 0:
            variance_percent = abs(float((normalized_total - original_total) / original_total)) * 100
            
            if variance_percent > self.config.max_cost_variance_percent:
                raise DataTransformationError(
                    f"Cost variance too high: {variance_percent:.2f}% "
                    f"(original: {original_total}, normalized: {normalized_total})"
                )
    
    def get_normalization_statistics(self) -> Dict[str, Any]:
        """Get normalization statistics."""
        return {
            **self.normalization_stats,
            'success_rate': (
                self.normalization_stats['successful_normalizations'] / 
                max(1, self.normalization_stats['total_records_processed'])
            ) * 100,
            'currency_converter_cache_size': len(self.currency_converter.rate_cache),
            'service_mapper_stats': self.service_mapper.get_mapping_statistics()
        }
    
    def reset_statistics(self):
        """Reset normalization statistics."""
        self.normalization_stats = {
            'total_records_processed': 0,
            'successful_normalizations': 0,
            'failed_normalizations': 0,
            'currency_conversions': 0,
            'service_mappings': 0
        }
    
    async def batch_normalize(
        self,
        provider_data_list: List[ProviderCostData],
        client_id: Optional[str] = None,
        max_concurrent: int = 10
    ) -> List[UnifiedCostRecord]:
        """
        Normalize multiple provider cost data records concurrently.
        
        Args:
            provider_data_list: List of provider cost data to normalize
            client_id: Optional client ID for custom mappings
            max_concurrent: Maximum concurrent normalizations
            
        Returns:
            List of normalized cost records
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def normalize_with_semaphore(provider_data):
            async with semaphore:
                return await self.normalize_cost_data(provider_data, client_id)
        
        tasks = [normalize_with_semaphore(data) for data in provider_data_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        normalized_records = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to normalize record {i}: {result}")
            else:
                normalized_records.append(result)
        
        return normalized_records


# Convenience functions
async def normalize_provider_cost_data(
    provider_data: ProviderCostData,
    client_id: Optional[str] = None,
    config: Optional[NormalizationConfig] = None
) -> UnifiedCostRecord:
    """
    Convenience function to normalize a single provider cost data record.
    
    Args:
        provider_data: Provider cost data to normalize
        client_id: Optional client ID for custom mappings
        config: Optional normalization configuration
        
    Returns:
        Normalized unified cost record
    """
    service = CostNormalizationService(config)
    return await service.normalize_cost_data(provider_data, client_id)


async def batch_normalize_provider_data(
    provider_data_list: List[ProviderCostData],
    client_id: Optional[str] = None,
    config: Optional[NormalizationConfig] = None,
    max_concurrent: int = 10
) -> List[UnifiedCostRecord]:
    """
    Convenience function to normalize multiple provider cost data records.
    
    Args:
        provider_data_list: List of provider cost data to normalize
        client_id: Optional client ID for custom mappings
        config: Optional normalization configuration
        max_concurrent: Maximum concurrent normalizations
        
    Returns:
        List of normalized unified cost records
    """
    service = CostNormalizationService(config)
    return await service.batch_normalize(provider_data_list, client_id, max_concurrent)