"""
GCP Cost Adapter

This module implements the Google Cloud Platform-specific cost collection adapter
for the multi-cloud cost analytics platform. It integrates with GCP Billing API
and BigQuery to collect cost and usage data.
"""

import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging
import json

try:
    from google.cloud import billing_v1
    from google.cloud import bigquery
    from google.oauth2 import service_account
    from google.auth.exceptions import GoogleAuthError
    from google.api_core.exceptions import GoogleAPIError, PermissionDenied, Unauthenticated
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    billing_v1 = None
    bigquery = None
    service_account = None
    GoogleAuthError = Exception
    GoogleAPIError = Exception
    PermissionDenied = Exception
    Unauthenticated = Exception

from .cloud_provider_adapter import CloudProviderAdapter
from ..models.provider_models import (
    GCPCredentials, CredentialValidation, DateRange, ProviderCostData,
    CollectionResult, ProviderAccount, ProviderService, ProviderType,
    DataCollectionStatus, ValidationStatus, AuthenticationError,
    AuthorizationError, RateLimitError, ServiceUnavailableError
)
from ..models.multi_cloud_models import ServiceCategory, Currency


logger = logging.getLogger(__name__)


class GCPCostAdapter(CloudProviderAdapter):
    """GCP Billing API adapter for collecting cost data."""
    
    def __init__(self, credentials: GCPCredentials):
        """
        Initialize GCP cost adapter.
        
        Args:
            credentials: GCP credentials
        """
        if not GCP_AVAILABLE:
            raise ImportError(
                "Google Cloud libraries not available. Install with: "
                "pip install google-cloud-billing google-cloud-bigquery"
            )
        
        super().__init__(credentials)
        self.gcp_credentials = credentials
        self._billing_client = None
        self._bigquery_client = None
        self._credentials_obj = None
    
    @property
    def provider_name(self) -> str:
        """Get the human-readable provider name."""
        return "Google Cloud Platform"
    
    @property
    def supported_regions(self) -> List[str]:
        """Get list of supported GCP regions."""
        return [
            'us-central1', 'us-east1', 'us-east4', 'us-west1', 'us-west2', 'us-west3', 'us-west4',
            'europe-north1', 'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4', 'europe-west6',
            'asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2', 'asia-northeast3',
            'asia-south1', 'asia-southeast1', 'asia-southeast2', 'australia-southeast1',
            'northamerica-northeast1', 'southamerica-east1'
        ]
    
    @property
    def default_currency(self) -> str:
        """Get the default currency for GCP."""
        return "USD"
    
    async def _initialize_client(self):
        """Initialize GCP clients."""
        try:
            # Create credentials object
            if self.gcp_credentials.service_account_key:
                self._credentials_obj = service_account.Credentials.from_service_account_info(
                    self.gcp_credentials.service_account_key
                )
            elif self.gcp_credentials.key_file_path:
                self._credentials_obj = service_account.Credentials.from_service_account_file(
                    self.gcp_credentials.key_file_path
                )
            else:
                # Use default credentials (e.g., from environment)
                from google.auth import default
                self._credentials_obj, _ = default()
            
            # Initialize clients
            self._billing_client = billing_v1.CloudBillingClient(credentials=self._credentials_obj)
            self._bigquery_client = bigquery.Client(
                credentials=self._credentials_obj,
                project=self.gcp_credentials.project_id
            )
            
            self.logger.info("GCP clients initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize GCP clients: {e}")
            raise AuthenticationError(
                provider=ProviderType.GCP,
                message=f"Failed to initialize GCP clients: {str(e)}"
            )
    
    async def _cleanup_client(self):
        """Cleanup GCP clients."""
        if self._billing_client:
            self._billing_client.close()
        if self._bigquery_client:
            self._bigquery_client.close()
        self._billing_client = None
        self._bigquery_client = None
        self._credentials_obj = None
    
    async def validate_credentials(self) -> CredentialValidation:
        """
        Validate GCP credentials and permissions.
        
        Returns:
            CredentialValidation with validation results
        """
        start_time = datetime.utcnow()
        
        try:
            await self._initialize_client()
            
            permissions = []
            missing_permissions = []
            
            # Test billing account access
            try:
                billing_accounts = list(self._billing_client.list_billing_accounts())
                permissions.extend([
                    'cloudbilling.billingAccounts.list',
                    'cloudbilling.billingAccounts.get'
                ])
                
                if not billing_accounts:
                    missing_permissions.append('cloudbilling.billingAccounts.list')
                    
            except (PermissionDenied, Unauthenticated) as e:
                missing_permissions.extend([
                    'cloudbilling.billingAccounts.list',
                    'cloudbilling.billingAccounts.get'
                ])
            
            # Test BigQuery access (for detailed billing data)
            try:
                datasets = list(self._bigquery_client.list_datasets())
                permissions.extend([
                    'bigquery.datasets.get',
                    'bigquery.tables.get',
                    'bigquery.jobs.create'
                ])
            except (PermissionDenied, Unauthenticated):
                missing_permissions.extend([
                    'bigquery.datasets.get',
                    'bigquery.tables.get',
                    'bigquery.jobs.create'
                ])
            
            # Test project access
            try:
                if self.gcp_credentials.project_id:
                    # Try to access project information
                    from google.cloud import resource_manager
                    rm_client = resource_manager.Client(credentials=self._credentials_obj)
                    project = rm_client.fetch_project(self.gcp_credentials.project_id)
                    permissions.append('resourcemanager.projects.get')
            except Exception:
                missing_permissions.append('resourcemanager.projects.get')
            
            validation_duration = (datetime.utcnow() - start_time).total_seconds()
            
            is_valid = len(permissions) > 0 and 'cloudbilling.billingAccounts.list' in permissions
            status = ValidationStatus.VALID if is_valid else ValidationStatus.INSUFFICIENT_PERMISSIONS
            
            return CredentialValidation(
                status=status,
                is_valid=is_valid,
                permissions=permissions,
                missing_permissions=missing_permissions,
                validated_at=datetime.utcnow(),
                validation_duration_seconds=validation_duration,
                additional_info={
                    'project_id': self.gcp_credentials.project_id,
                    'service_account_email': self.gcp_credentials.service_account_email
                }
            )
            
        except GoogleAuthError as e:
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
        Collect cost data from GCP Billing API.
        
        Args:
            date_range: Date range for cost collection
            
        Returns:
            CollectionResult with GCP cost data
        """
        start_time = datetime.utcnow()
        api_calls = 0
        
        try:
            await self._initialize_client()
            
            # Get billing accounts
            billing_accounts = list(self._billing_client.list_billing_accounts())
            api_calls += 1
            
            if not billing_accounts:
                return CollectionResult(
                    status=DataCollectionStatus.FAILED,
                    provider=ProviderType.GCP,
                    client_id="unknown",
                    date_range=date_range,
                    error_message="No billing accounts found",
                    collection_duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    api_calls_made=api_calls,
                    started_at=start_time,
                    completed_at=datetime.utcnow()
                )
            
            total_cost = Decimal('0')
            services_data = {}
            accounts_data = {}
            regions_data = {}
            
            # For each billing account, try to get cost data
            for billing_account in billing_accounts:
                try:
                    # Try to get cost data using BigQuery if available
                    if self.gcp_credentials.project_id:
                        cost_data = await self._get_cost_data_from_bigquery(
                            billing_account.name, date_range
                        )
                        api_calls += 1
                        
                        if cost_data:
                            total_cost += cost_data['total_cost']
                            
                            # Merge services data
                            for service_name, service_cost in cost_data['services'].items():
                                if service_name not in services_data:
                                    services_data[service_name] = {
                                        'cost': Decimal('0'),
                                        'usage_metrics': {},
                                        'provider_data': {'service_name': service_name}
                                    }
                                services_data[service_name]['cost'] += service_cost
                            
                            # Merge regions data
                            for region_name, region_cost in cost_data['regions'].items():
                                if region_name not in regions_data:
                                    regions_data[region_name] = Decimal('0')
                                regions_data[region_name] += region_cost
                    
                    # Get projects associated with this billing account
                    projects = await self._get_projects_for_billing_account(billing_account.name)
                    api_calls += 1
                    
                    for project in projects:
                        if project['project_id'] not in accounts_data:
                            accounts_data[project['project_id']] = {
                                'account_id': project['project_id'],
                                'account_name': project.get('display_name', project['project_id']),
                                'cost': Decimal('0')
                            }
                
                except Exception as e:
                    self.logger.warning(f"Error processing billing account {billing_account.name}: {e}")
                    continue
            
            # Create provider accounts list
            provider_accounts = [
                ProviderAccount(
                    account_id=account_data['account_id'],
                    account_name=account_data['account_name'],
                    provider=ProviderType.GCP,
                    is_active=True
                )
                for account_data in accounts_data.values()
            ]
            
            # Create provider cost data
            provider_cost_data = ProviderCostData(
                client_id="unknown",  # Will be set by caller
                provider=ProviderType.GCP,
                date_range=date_range,
                total_cost=total_cost,
                currency=self.default_currency,
                accounts=provider_accounts,
                services=services_data,
                regions=regions_data,
                collection_metadata={
                    'api_calls': api_calls,
                    'duration': (datetime.utcnow() - start_time).total_seconds(),
                    'freshness_hours': 24,  # GCP billing data is typically 24 hours delayed
                    'data_source': 'billing_api_bigquery',
                    'billing_accounts_count': len(billing_accounts)
                }
            )
            
            completion_time = datetime.utcnow()
            
            return CollectionResult(
                status=DataCollectionStatus.SUCCESS,
                provider=ProviderType.GCP,
                client_id="unknown",  # Will be set by caller
                date_range=date_range,
                cost_data=provider_cost_data,
                collection_duration_seconds=(completion_time - start_time).total_seconds(),
                api_calls_made=api_calls,
                records_collected=len(services_data),
                started_at=start_time,
                completed_at=completion_time
            )
            
        except GoogleAPIError as e:
            if e.code == 429:  # Rate limit
                raise RateLimitError(
                    provider=ProviderType.GCP,
                    message=f"GCP API rate limit exceeded: {str(e)}",
                    retry_after=60
                )
            elif e.code == 403:  # Permission denied
                raise AuthorizationError(
                    provider=ProviderType.GCP,
                    message=f"Insufficient permissions: {str(e)}"
                )
            elif e.code == 401:  # Unauthenticated
                raise AuthenticationError(
                    provider=ProviderType.GCP,
                    message=f"Authentication failed: {str(e)}"
                )
            else:
                raise ServiceUnavailableError(
                    provider=ProviderType.GCP,
                    message=f"GCP service error: {str(e)}"
                )
        
        except Exception as e:
            self.logger.error(f"Unexpected error collecting GCP cost data: {e}")
            return CollectionResult(
                status=DataCollectionStatus.FAILED,
                provider=ProviderType.GCP,
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
    
    async def _get_cost_data_from_bigquery(
        self, 
        billing_account_name: str, 
        date_range: DateRange
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed cost data from BigQuery billing export.
        
        Args:
            billing_account_name: GCP billing account name
            date_range: Date range for cost collection
            
        Returns:
            Dictionary with cost data or None if not available
        """
        try:
            # Construct BigQuery query for billing data
            # Note: This assumes the billing export table exists
            # The actual table name would need to be configured per client
            query = f"""
            SELECT
                service.description as service_name,
                location.location as region,
                SUM(cost) as total_cost,
                currency
            FROM `{self.gcp_credentials.project_id}.billing.gcp_billing_export_v1_{billing_account_name.split('/')[-1]}`
            WHERE usage_start_time >= '{date_range.start_date}'
                AND usage_start_time < '{date_range.end_date + timedelta(days=1)}'
            GROUP BY service_name, region, currency
            ORDER BY total_cost DESC
            """
            
            query_job = self._bigquery_client.query(query)
            results = query_job.result()
            
            total_cost = Decimal('0')
            services = {}
            regions = {}
            
            for row in results:
                service_name = row.service_name or 'Unknown'
                region_name = row.region or 'global'
                cost = Decimal(str(row.total_cost or 0))
                
                total_cost += cost
                
                # Aggregate by service
                if service_name not in services:
                    services[service_name] = Decimal('0')
                services[service_name] += cost
                
                # Aggregate by region
                if region_name not in regions:
                    regions[region_name] = Decimal('0')
                regions[region_name] += cost
            
            return {
                'total_cost': total_cost,
                'services': services,
                'regions': regions,
                'currency': 'USD'  # Default, could be extracted from results
            }
            
        except Exception as e:
            self.logger.warning(f"Could not get BigQuery billing data: {e}")
            return None
    
    async def _get_projects_for_billing_account(self, billing_account_name: str) -> List[Dict[str, Any]]:
        """
        Get projects associated with a billing account.
        
        Args:
            billing_account_name: GCP billing account name
            
        Returns:
            List of project information
        """
        try:
            projects = []
            
            # List projects linked to the billing account
            request = billing_v1.ListProjectBillingInfoRequest(
                name=billing_account_name
            )
            
            page_result = self._billing_client.list_project_billing_info(request=request)
            
            for project_billing_info in page_result:
                if project_billing_info.billing_enabled:
                    projects.append({
                        'project_id': project_billing_info.project_id,
                        'display_name': project_billing_info.name,
                        'billing_enabled': project_billing_info.billing_enabled
                    })
            
            return projects
            
        except Exception as e:
            self.logger.warning(f"Could not get projects for billing account: {e}")
            return []
    
    async def get_accounts(self) -> List[ProviderAccount]:
        """
        Get list of GCP projects accessible with current credentials.
        
        Returns:
            List of GCP projects as accounts
        """
        try:
            await self._initialize_client()
            
            accounts = []
            
            # Get billing accounts
            billing_accounts = list(self._billing_client.list_billing_accounts())
            
            for billing_account in billing_accounts:
                # Get projects for each billing account
                projects = await self._get_projects_for_billing_account(billing_account.name)
                
                for project in projects:
                    accounts.append(ProviderAccount(
                        account_id=project['project_id'],
                        account_name=project.get('display_name', project['project_id']),
                        provider=ProviderType.GCP,
                        is_active=project.get('billing_enabled', True),
                        tags={'billing_account': billing_account.name}
                    ))
            
            return accounts
            
        except Exception as e:
            self.logger.error(f"Error getting GCP accounts: {e}")
            return []
        
        finally:
            await self._cleanup_client()
    
    async def get_services(self) -> List[ProviderService]:
        """
        Get list of GCP services.
        
        Returns:
            List of GCP services
        """
        try:
            await self._initialize_client()
            
            services = []
            service_mapping = self.get_service_mapping()
            
            # Get services from billing catalog
            try:
                catalog_client = billing_v1.CloudCatalogClient(credentials=self._credentials_obj)
                
                for service in catalog_client.list_services():
                    service_name = service.display_name
                    category = service_mapping.get(service_name, ServiceCategory.OTHER)
                    
                    services.append(ProviderService(
                        service_id=service.name.split('/')[-1],
                        service_name=service_name,
                        provider=ProviderType.GCP,
                        category=category.value,
                        description=service.business_entity_name,
                        regions_available=self.supported_regions
                    ))
                    
            except Exception as e:
                self.logger.warning(f"Could not get services from catalog: {e}")
                
                # Fallback to predefined service list
                for service_name, category in service_mapping.items():
                    services.append(ProviderService(
                        service_id=service_name.lower().replace(' ', '_'),
                        service_name=service_name,
                        provider=ProviderType.GCP,
                        category=category.value,
                        regions_available=self.supported_regions
                    ))
            
            return services
            
        except Exception as e:
            self.logger.error(f"Error getting GCP services: {e}")
            return []
        
        finally:
            await self._cleanup_client()
    
    def get_service_mapping(self) -> Dict[str, ServiceCategory]:
        """
        Get mapping of GCP services to unified categories.
        
        Returns:
            Dictionary mapping GCP service names to ServiceCategory enums
        """
        return {
            # Compute services
            'Compute Engine': ServiceCategory.COMPUTE,
            'Cloud Functions': ServiceCategory.SERVERLESS,
            'Cloud Run': ServiceCategory.CONTAINERS,
            'Google Kubernetes Engine': ServiceCategory.CONTAINERS,
            'App Engine': ServiceCategory.SERVERLESS,
            'Cloud GPUs': ServiceCategory.COMPUTE,
            
            # Storage services
            'Cloud Storage': ServiceCategory.STORAGE,
            'Persistent Disk': ServiceCategory.STORAGE,
            'Cloud Filestore': ServiceCategory.STORAGE,
            'Cloud Storage for Firebase': ServiceCategory.STORAGE,
            
            # Database services
            'Cloud SQL': ServiceCategory.DATABASE,
            'Cloud Firestore': ServiceCategory.DATABASE,
            'Cloud Bigtable': ServiceCategory.DATABASE,
            'BigQuery': ServiceCategory.ANALYTICS,
            'Cloud Memorystore': ServiceCategory.DATABASE,
            'Cloud Spanner': ServiceCategory.DATABASE,
            'Firebase Realtime Database': ServiceCategory.DATABASE,
            
            # Networking
            'Virtual Private Cloud': ServiceCategory.NETWORKING,
            'Cloud CDN': ServiceCategory.NETWORKING,
            'Cloud DNS': ServiceCategory.NETWORKING,
            'Cloud Load Balancing': ServiceCategory.NETWORKING,
            'Cloud Interconnect': ServiceCategory.NETWORKING,
            'Cloud VPN': ServiceCategory.NETWORKING,
            'Cloud NAT': ServiceCategory.NETWORKING,
            
            # Analytics
            'BigQuery': ServiceCategory.ANALYTICS,
            'Cloud Dataflow': ServiceCategory.ANALYTICS,
            'Cloud Dataproc': ServiceCategory.ANALYTICS,
            'Cloud Pub/Sub': ServiceCategory.ANALYTICS,
            'Cloud Composer': ServiceCategory.ANALYTICS,
            'Data Studio': ServiceCategory.ANALYTICS,
            'Cloud Datalab': ServiceCategory.ANALYTICS,
            
            # AI/ML
            'AI Platform': ServiceCategory.AI_ML,
            'AutoML': ServiceCategory.AI_ML,
            'Cloud Vision API': ServiceCategory.AI_ML,
            'Cloud Natural Language': ServiceCategory.AI_ML,
            'Cloud Translation': ServiceCategory.AI_ML,
            'Cloud Speech-to-Text': ServiceCategory.AI_ML,
            'Cloud Text-to-Speech': ServiceCategory.AI_ML,
            'Cloud Video Intelligence': ServiceCategory.AI_ML,
            'Dialogflow': ServiceCategory.AI_ML,
            
            # Security
            'Cloud Identity and Access Management': ServiceCategory.SECURITY,
            'Cloud Key Management Service': ServiceCategory.SECURITY,
            'Secret Manager': ServiceCategory.SECURITY,
            'Cloud Armor': ServiceCategory.SECURITY,
            'Security Command Center': ServiceCategory.SECURITY,
            'Cloud Asset Inventory': ServiceCategory.SECURITY,
            'Binary Authorization': ServiceCategory.SECURITY,
            
            # Management
            'Cloud Monitoring': ServiceCategory.MANAGEMENT,
            'Cloud Logging': ServiceCategory.MANAGEMENT,
            'Cloud Deployment Manager': ServiceCategory.MANAGEMENT,
            'Cloud Resource Manager': ServiceCategory.MANAGEMENT,
            'Cloud Shell': ServiceCategory.MANAGEMENT,
            'Cloud Console': ServiceCategory.MANAGEMENT,
        }
    
    async def test_connection(self) -> bool:
        """
        Test connection to GCP APIs.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            await self._initialize_client()
            
            # Test billing API access
            billing_accounts = list(self._billing_client.list_billing_accounts())
            
            return True
            
        except Exception as e:
            self.logger.error(f"GCP connection test failed: {e}")
            return False
        
        finally:
            await self._cleanup_client()


# Register the GCP adapter with the factory
from .cloud_provider_adapter import ProviderAdapterFactory
ProviderAdapterFactory.register_adapter(ProviderType.GCP, GCPCostAdapter)