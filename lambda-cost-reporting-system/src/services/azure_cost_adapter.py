"""
Azure Cost Adapter

This module implements the Microsoft Azure-specific cost collection adapter
for the multi-cloud cost analytics platform. It integrates with Azure Cost
Management API to collect cost and usage data.
"""

import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging
import json

try:
    from azure.identity import ClientSecretCredential, ManagedIdentityCredential, DefaultAzureCredential
    from azure.mgmt.costmanagement import CostManagementClient
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.subscription import SubscriptionClient
    from azure.core.exceptions import (
        ClientAuthenticationError, HttpResponseError, ResourceNotFoundError
    )
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    ClientSecretCredential = None
    ManagedIdentityCredential = None
    DefaultAzureCredential = None
    CostManagementClient = None
    ResourceManagementClient = None
    SubscriptionClient = None
    ClientAuthenticationError = Exception
    HttpResponseError = Exception
    ResourceNotFoundError = Exception

from .cloud_provider_adapter import CloudProviderAdapter
from ..models.provider_models import (
    AzureCredentials, CredentialValidation, DateRange, ProviderCostData,
    CollectionResult, ProviderAccount, ProviderService, ProviderType,
    DataCollectionStatus, ValidationStatus, AuthenticationError,
    AuthorizationError, RateLimitError, ServiceUnavailableError
)
from ..models.multi_cloud_models import ServiceCategory, Currency


logger = logging.getLogger(__name__)


class AzureCostAdapter(CloudProviderAdapter):
    """Azure Cost Management API adapter for collecting cost data."""
    
    def __init__(self, credentials: AzureCredentials):
        """
        Initialize Azure cost adapter.
        
        Args:
            credentials: Azure credentials
        """
        if not AZURE_AVAILABLE:
            raise ImportError(
                "Azure libraries not available. Install with: "
                "pip install azure-mgmt-costmanagement azure-mgmt-resource azure-mgmt-subscription azure-identity"
            )
        
        super().__init__(credentials)
        self.azure_credentials = credentials
        self._cost_client = None
        self._resource_client = None
        self._subscription_client = None
        self._credential_obj = None
    
    @property
    def provider_name(self) -> str:
        """Get the human-readable provider name."""
        return "Microsoft Azure"
    
    @property
    def supported_regions(self) -> List[str]:
        """Get list of supported Azure regions."""
        return [
            'eastus', 'eastus2', 'westus', 'westus2', 'westus3', 'centralus', 'northcentralus', 'southcentralus',
            'westcentralus', 'canadacentral', 'canadaeast', 'brazilsouth', 'northeurope', 'westeurope',
            'uksouth', 'ukwest', 'francecentral', 'francesouth', 'germanywestcentral', 'norwayeast',
            'switzerlandnorth', 'swedencentral', 'eastasia', 'southeastasia', 'japaneast', 'japanwest',
            'koreacentral', 'koreasouth', 'southindia', 'centralindia', 'westindia', 'australiaeast',
            'australiasoutheast', 'australiacentral', 'southafricanorth', 'uaenorth'
        ]
    
    @property
    def default_currency(self) -> str:
        """Get the default currency for Azure."""
        return "USD"
    
    async def _initialize_client(self):
        """Initialize Azure clients."""
        try:
            # Create credential object based on credential type
            if self.azure_credentials.credential_type.value == 'client_secret':
                self._credential_obj = ClientSecretCredential(
                    tenant_id=self.azure_credentials.tenant_id,
                    client_id=self.azure_credentials.client_id,
                    client_secret=self.azure_credentials.client_secret
                )
            elif self.azure_credentials.credential_type.value == 'managed_identity':
                if self.azure_credentials.managed_identity_client_id:
                    self._credential_obj = ManagedIdentityCredential(
                        client_id=self.azure_credentials.managed_identity_client_id
                    )
                else:
                    self._credential_obj = ManagedIdentityCredential()
            else:
                # Use default credential chain
                self._credential_obj = DefaultAzureCredential()
            
            # Initialize clients
            self._cost_client = CostManagementClient(
                credential=self._credential_obj,
                subscription_id=self.azure_credentials.subscription_id
            )
            self._resource_client = ResourceManagementClient(
                credential=self._credential_obj,
                subscription_id=self.azure_credentials.subscription_id
            )
            self._subscription_client = SubscriptionClient(
                credential=self._credential_obj
            )
            
            self.logger.info("Azure clients initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure clients: {e}")
            raise AuthenticationError(
                provider=ProviderType.AZURE,
                message=f"Failed to initialize Azure clients: {str(e)}"
            )
    
    async def _cleanup_client(self):
        """Cleanup Azure clients."""
        if self._cost_client:
            self._cost_client.close()
        if self._resource_client:
            self._resource_client.close()
        if self._subscription_client:
            self._subscription_client.close()
        self._cost_client = None
        self._resource_client = None
        self._subscription_client = None
        self._credential_obj = None
    
    async def validate_credentials(self) -> CredentialValidation:
        """
        Validate Azure credentials and permissions.
        
        Returns:
            CredentialValidation with validation results
        """
        start_time = datetime.utcnow()
        
        try:
            await self._initialize_client()
            
            permissions = []
            missing_permissions = []
            
            # Test subscription access
            try:
                subscription = self._subscription_client.subscriptions.get(
                    self.azure_credentials.subscription_id
                )
                permissions.append('Microsoft.Resources/subscriptions/read')
            except (ClientAuthenticationError, HttpResponseError) as e:
                if e.status_code == 403:
                    missing_permissions.append('Microsoft.Resources/subscriptions/read')
                else:
                    raise
            
            # Test Cost Management access
            try:
                # Try to get usage details for a small date range
                scope = f"/subscriptions/{self.azure_credentials.subscription_id}"
                
                # Create a query for the last day
                end_date = date.today()
                start_date = end_date - timedelta(days=1)
                
                query_definition = {
                    "type": "Usage",
                    "timeframe": "Custom",
                    "timePeriod": {
                        "from": start_date.strftime('%Y-%m-%d'),
                        "to": end_date.strftime('%Y-%m-%d')
                    },
                    "dataset": {
                        "granularity": "Daily",
                        "aggregation": {
                            "totalCost": {
                                "name": "PreTaxCost",
                                "function": "Sum"
                            }
                        },
                        "grouping": [
                            {
                                "type": "Dimension",
                                "name": "ServiceName"
                            }
                        ]
                    }
                }
                
                result = self._cost_client.query.usage(scope=scope, parameters=query_definition)
                permissions.extend([
                    'Microsoft.CostManagement/query/action',
                    'Microsoft.Consumption/usageDetails/read'
                ])
                
            except (ClientAuthenticationError, HttpResponseError) as e:
                if e.status_code == 403:
                    missing_permissions.extend([
                        'Microsoft.CostManagement/query/action',
                        'Microsoft.Consumption/usageDetails/read'
                    ])
                else:
                    raise
            
            # Test Resource Management access
            try:
                resource_groups = list(self._resource_client.resource_groups.list())
                permissions.append('Microsoft.Resources/subscriptions/resourceGroups/read')
            except (ClientAuthenticationError, HttpResponseError) as e:
                if e.status_code == 403:
                    missing_permissions.append('Microsoft.Resources/subscriptions/resourceGroups/read')
            
            validation_duration = (datetime.utcnow() - start_time).total_seconds()
            
            is_valid = len(permissions) > 0 and 'Microsoft.CostManagement/query/action' in permissions
            status = ValidationStatus.VALID if is_valid else ValidationStatus.INSUFFICIENT_PERMISSIONS
            
            return CredentialValidation(
                status=status,
                is_valid=is_valid,
                permissions=permissions,
                missing_permissions=missing_permissions,
                validated_at=datetime.utcnow(),
                validation_duration_seconds=validation_duration,
                additional_info={
                    'subscription_id': self.azure_credentials.subscription_id,
                    'tenant_id': self.azure_credentials.tenant_id,
                    'credential_type': self.azure_credentials.credential_type.value
                }
            )
            
        except ClientAuthenticationError as e:
            return CredentialValidation(
                status=ValidationStatus.INVALID,
                is_valid=False,
                error_message=f"Authentication failed: {str(e)}",
                validated_at=datetime.utcnow(),
                validation_duration_seconds=(datetime.utcnow() - start_time).total_seconds()
            )
        
        except Exception as e:
            validation_duration = (datetime.utcnow() - start_time).total_seconds()
            return CredentialValidation(
                status=ValidationStatus.UNKNOWN,
                is_valid=False,
                error_message=f"Validation failed: {str(e)}",
                validated_at=datetime.utcnow(),
                validation_duration_seconds=validation_duration
            )
        finally:
            await self._cleanup_client()
    
    async def collect_cost_data(self, date_range: DateRange) -> CollectionResult:
        """
        Collect cost data from Azure Cost Management API.
        
        Args:
            date_range: Date range for cost collection
            
        Returns:
            CollectionResult with Azure cost data
        """
        start_time = datetime.utcnow()
        api_calls = 0
        
        try:
            await self._initialize_client()
            
            scope = f"/subscriptions/{self.azure_credentials.subscription_id}"
            
            # Create query definition
            query_definition = {
                "type": "Usage",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": date_range.start_date.strftime('%Y-%m-%d'),
                    "to": date_range.end_date.strftime('%Y-%m-%d')
                },
                "dataset": {
                    "granularity": "Daily",
                    "aggregation": {
                        "totalCost": {
                            "name": "PreTaxCost",
                            "function": "Sum"
                        }
                    },
                    "grouping": [
                        {
                            "type": "Dimension",
                            "name": "ServiceName"
                        },
                        {
                            "type": "Dimension",
                            "name": "ResourceLocation"
                        },
                        {
                            "type": "Dimension",
                            "name": "ResourceGroupName"
                        }
                    ]
                }
            }
            
            # Execute query
            result = self._cost_client.query.usage(scope=scope, parameters=query_definition)
            api_calls += 1
            
            total_cost = Decimal('0')
            services_data = {}
            accounts_data = {}
            regions_data = {}
            
            # Process results
            if hasattr(result, 'rows') and result.rows:
                for row in result.rows:
                    # Azure query results structure: [cost, service_name, location, resource_group, ...]
                    cost_amount = Decimal(str(row[0])) if row[0] else Decimal('0')
                    service_name = row[1] if len(row) > 1 else 'Unknown'
                    location = row[2] if len(row) > 2 else 'Unknown'
                    resource_group = row[3] if len(row) > 3 else 'Unknown'
                    
                    total_cost += cost_amount
                    
                    # Aggregate by service
                    if service_name not in services_data:
                        services_data[service_name] = {
                            'cost': Decimal('0'),
                            'usage_metrics': {},
                            'provider_data': {'service_name': service_name}
                        }
                    services_data[service_name]['cost'] += cost_amount
                    
                    # Aggregate by region
                    if location and location != 'Unknown':
                        if location not in regions_data:
                            regions_data[location] = Decimal('0')
                        regions_data[location] += cost_amount
                    
                    # Use resource groups as account-like entities
                    if resource_group and resource_group != 'Unknown':
                        if resource_group not in accounts_data:
                            accounts_data[resource_group] = {
                                'account_id': resource_group,
                                'account_name': resource_group,
                                'cost': Decimal('0')
                            }
                        accounts_data[resource_group]['cost'] += cost_amount
            
            # Get subscription information
            try:
                subscription = self._subscription_client.subscriptions.get(
                    self.azure_credentials.subscription_id
                )
                api_calls += 1
                
                # Add subscription as main account if no resource groups found
                if not accounts_data:
                    accounts_data[self.azure_credentials.subscription_id] = {
                        'account_id': self.azure_credentials.subscription_id,
                        'account_name': subscription.display_name,
                        'cost': total_cost
                    }
                    
            except Exception as e:
                self.logger.warning(f"Could not get subscription information: {e}")
                # Add subscription as fallback
                accounts_data[self.azure_credentials.subscription_id] = {
                    'account_id': self.azure_credentials.subscription_id,
                    'account_name': 'Azure Subscription',
                    'cost': total_cost
                }
            
            # Create provider accounts list
            provider_accounts = [
                ProviderAccount(
                    account_id=account_data['account_id'],
                    account_name=account_data['account_name'],
                    provider=ProviderType.AZURE,
                    is_active=True
                )
                for account_data in accounts_data.values()
            ]
            
            # Create provider cost data
            provider_cost_data = ProviderCostData(
                client_id="unknown",  # Will be set by caller
                provider=ProviderType.AZURE,
                date_range=date_range,
                total_cost=total_cost,
                currency=self.default_currency,
                accounts=provider_accounts,
                services=services_data,
                regions=regions_data,
                collection_metadata={
                    'api_calls': api_calls,
                    'duration': (datetime.utcnow() - start_time).total_seconds(),
                    'freshness_hours': 24,  # Azure cost data is typically 24 hours delayed
                    'data_source': 'cost_management_api',
                    'subscription_id': self.azure_credentials.subscription_id
                }
            )
            
            completion_time = datetime.utcnow()
            
            return CollectionResult(
                status=DataCollectionStatus.SUCCESS,
                provider=ProviderType.AZURE,
                client_id="unknown",  # Will be set by caller
                date_range=date_range,
                cost_data=provider_cost_data,
                collection_duration_seconds=(completion_time - start_time).total_seconds(),
                api_calls_made=api_calls,
                records_collected=len(services_data),
                started_at=start_time,
                completed_at=completion_time
            )
            
        except HttpResponseError as e:
            if e.status_code == 429:  # Rate limit
                raise RateLimitError(
                    provider=ProviderType.AZURE,
                    message=f"Azure API rate limit exceeded: {str(e)}",
                    retry_after=60
                )
            elif e.status_code == 403:  # Permission denied
                raise AuthorizationError(
                    provider=ProviderType.AZURE,
                    message=f"Insufficient permissions: {str(e)}"
                )
            elif e.status_code == 401:  # Unauthenticated
                raise AuthenticationError(
                    provider=ProviderType.AZURE,
                    message=f"Authentication failed: {str(e)}"
                )
            else:
                raise ServiceUnavailableError(
                    provider=ProviderType.AZURE,
                    message=f"Azure service error: {str(e)}"
                )
        
        except Exception as e:
            self.logger.error(f"Unexpected error collecting Azure cost data: {e}")
            return CollectionResult(
                status=DataCollectionStatus.FAILED,
                provider=ProviderType.AZURE,
                client_id="unknown",
                date_range=date_range,
                error_message=str(e),
                collection_duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                api_calls_made=api_calls,
                started_at=start_time,
                completed_at=datetime.utcnow()
            )
        
        finally:
            await self._cleanup_client()
    
    async def get_accounts(self) -> List[ProviderAccount]:
        """
        Get list of Azure subscriptions and resource groups accessible with current credentials.
        
        Returns:
            List of Azure subscriptions and resource groups as accounts
        """
        try:
            await self._initialize_client()
            
            accounts = []
            
            # Get subscription information
            try:
                subscription = self._subscription_client.subscriptions.get(
                    self.azure_credentials.subscription_id
                )
                
                accounts.append(ProviderAccount(
                    account_id=subscription.subscription_id,
                    account_name=subscription.display_name,
                    provider=ProviderType.AZURE,
                    is_active=subscription.state == 'Enabled',
                    tags={'subscription_id': subscription.subscription_id}
                ))
                
            except Exception as e:
                self.logger.warning(f"Could not get subscription information: {e}")
                # Add subscription as fallback
                accounts.append(ProviderAccount(
                    account_id=self.azure_credentials.subscription_id,
                    account_name='Azure Subscription',
                    provider=ProviderType.AZURE,
                    is_active=True
                ))
            
            # Get resource groups
            try:
                resource_groups = list(self._resource_client.resource_groups.list())
                
                for rg in resource_groups:
                    accounts.append(ProviderAccount(
                        account_id=rg.name,
                        account_name=rg.name,
                        provider=ProviderType.AZURE,
                        is_active=True,
                        regions=[rg.location] if rg.location else [],
                        tags=rg.tags or {}
                    ))
                    
            except Exception as e:
                self.logger.warning(f"Could not get resource groups: {e}")
            
            return accounts
            
        except Exception as e:
            self.logger.error(f"Error getting Azure accounts: {e}")
            return []
        
        finally:
            await self._cleanup_client()
    
    async def get_services(self) -> List[ProviderService]:
        """
        Get list of Azure services.
        
        Returns:
            List of Azure services
        """
        try:
            await self._initialize_client()
            
            services = []
            service_mapping = self.get_service_mapping()
            
            # Azure doesn't have a direct API to list all services
            # We'll use the predefined service mapping
            for service_name, category in service_mapping.items():
                services.append(ProviderService(
                    service_id=service_name.lower().replace(' ', '_'),
                    service_name=service_name,
                    provider=ProviderType.AZURE,
                    category=category.value,
                    regions_available=self.supported_regions
                ))
            
            return services
            
        except Exception as e:
            self.logger.error(f"Error getting Azure services: {e}")
            return []
        
        finally:
            await self._cleanup_client()
    
    def get_service_mapping(self) -> Dict[str, ServiceCategory]:
        """
        Get mapping of Azure services to unified categories.
        
        Returns:
            Dictionary mapping Azure service names to ServiceCategory enums
        """
        return {
            # Compute services
            'Virtual Machines': ServiceCategory.COMPUTE,
            'Azure Functions': ServiceCategory.SERVERLESS,
            'Container Instances': ServiceCategory.CONTAINERS,
            'Azure Kubernetes Service': ServiceCategory.CONTAINERS,
            'App Service': ServiceCategory.SERVERLESS,
            'Batch': ServiceCategory.COMPUTE,
            'Cloud Services': ServiceCategory.COMPUTE,
            'Service Fabric': ServiceCategory.CONTAINERS,
            
            # Storage services
            'Storage': ServiceCategory.STORAGE,
            'Blob Storage': ServiceCategory.STORAGE,
            'File Storage': ServiceCategory.STORAGE,
            'Disk Storage': ServiceCategory.STORAGE,
            'Archive Storage': ServiceCategory.STORAGE,
            'Data Lake Storage': ServiceCategory.STORAGE,
            
            # Database services
            'SQL Database': ServiceCategory.DATABASE,
            'Azure Cosmos DB': ServiceCategory.DATABASE,
            'Azure Database for MySQL': ServiceCategory.DATABASE,
            'Azure Database for PostgreSQL': ServiceCategory.DATABASE,
            'Azure Database for MariaDB': ServiceCategory.DATABASE,
            'Azure Cache for Redis': ServiceCategory.DATABASE,
            'Azure Synapse Analytics': ServiceCategory.ANALYTICS,
            'Azure SQL Managed Instance': ServiceCategory.DATABASE,
            
            # Networking
            'Virtual Network': ServiceCategory.NETWORKING,
            'Content Delivery Network': ServiceCategory.NETWORKING,
            'DNS': ServiceCategory.NETWORKING,
            'Load Balancer': ServiceCategory.NETWORKING,
            'Application Gateway': ServiceCategory.NETWORKING,
            'ExpressRoute': ServiceCategory.NETWORKING,
            'VPN Gateway': ServiceCategory.NETWORKING,
            'Traffic Manager': ServiceCategory.NETWORKING,
            'Azure Firewall': ServiceCategory.NETWORKING,
            
            # Analytics
            'Azure Synapse Analytics': ServiceCategory.ANALYTICS,
            'Data Factory': ServiceCategory.ANALYTICS,
            'HDInsight': ServiceCategory.ANALYTICS,
            'Event Hubs': ServiceCategory.ANALYTICS,
            'Stream Analytics': ServiceCategory.ANALYTICS,
            'Power BI Embedded': ServiceCategory.ANALYTICS,
            'Azure Databricks': ServiceCategory.ANALYTICS,
            'Data Lake Analytics': ServiceCategory.ANALYTICS,
            
            # AI/ML
            'Machine Learning': ServiceCategory.AI_ML,
            'Cognitive Services': ServiceCategory.AI_ML,
            'Bot Service': ServiceCategory.AI_ML,
            'Computer Vision': ServiceCategory.AI_ML,
            'Text Analytics': ServiceCategory.AI_ML,
            'Speech Services': ServiceCategory.AI_ML,
            'Language Understanding': ServiceCategory.AI_ML,
            'Translator': ServiceCategory.AI_ML,
            'Form Recognizer': ServiceCategory.AI_ML,
            
            # Security
            'Azure Active Directory': ServiceCategory.SECURITY,
            'Key Vault': ServiceCategory.SECURITY,
            'Security Center': ServiceCategory.SECURITY,
            'Azure Sentinel': ServiceCategory.SECURITY,
            'Azure Information Protection': ServiceCategory.SECURITY,
            'Azure DDoS Protection': ServiceCategory.SECURITY,
            'Azure Bastion': ServiceCategory.SECURITY,
            
            # Management
            'Azure Monitor': ServiceCategory.MANAGEMENT,
            'Log Analytics': ServiceCategory.MANAGEMENT,
            'Azure Resource Manager': ServiceCategory.MANAGEMENT,
            'Azure Automation': ServiceCategory.MANAGEMENT,
            'Azure Backup': ServiceCategory.MANAGEMENT,
            'Azure Site Recovery': ServiceCategory.MANAGEMENT,
            'Azure Policy': ServiceCategory.MANAGEMENT,
            'Azure Advisor': ServiceCategory.MANAGEMENT,
        }
    
    async def test_connection(self) -> bool:
        """
        Test connection to Azure APIs.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            await self._initialize_client()
            
            # Test subscription access
            subscription = self._subscription_client.subscriptions.get(
                self.azure_credentials.subscription_id
            )
            
            # Test Cost Management access with a simple query
            scope = f"/subscriptions/{self.azure_credentials.subscription_id}"
            end_date = date.today()
            start_date = end_date - timedelta(days=1)
            
            query_definition = {
                "type": "Usage",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date.strftime('%Y-%m-%d'),
                    "to": end_date.strftime('%Y-%m-%d')
                },
                "dataset": {
                    "granularity": "Daily",
                    "aggregation": {
                        "totalCost": {
                            "name": "PreTaxCost",
                            "function": "Sum"
                        }
                    }
                }
            }
            
            result = self._cost_client.query.usage(scope=scope, parameters=query_definition)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Azure connection test failed: {e}")
            return False
        
        finally:
            await self._cleanup_client()


# Register the Azure adapter with the factory
from .cloud_provider_adapter import ProviderAdapterFactory
ProviderAdapterFactory.register_adapter(ProviderType.AZURE, AzureCostAdapter)