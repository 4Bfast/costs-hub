"""
Client Onboarding Service

This service handles the complete client onboarding workflow for multi-cloud
cost analytics, including provider validation, configuration setup, and
initial data collection testing.
"""

import boto3
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import json

from ..models.multi_tenant_models import (
    MultiCloudClient, CloudAccount, CloudProvider, OnboardingStatus,
    AWSCredentials, GCPCredentials, AzureCredentials, SubscriptionTier
)
from ..models.multi_cloud_models import UnifiedCostRecord
from ..services.multi_tenant_client_manager import MultiTenantClientManager
from ..services.aws_cost_adapter import AWSCostAdapter
from ..services.gcp_cost_adapter import GCPCostAdapter
from ..services.azure_cost_adapter import AzureCostAdapter


logger = logging.getLogger(__name__)


class OnboardingError(Exception):
    """Base exception for onboarding errors."""
    pass


class ProviderValidationError(OnboardingError):
    """Raised when provider validation fails."""
    pass


class ConfigurationError(OnboardingError):
    """Raised when configuration validation fails."""
    pass


class OnboardingWorkflowError(OnboardingError):
    """Raised when onboarding workflow fails."""
    pass


class ClientOnboardingService:
    """
    Manages the complete client onboarding workflow for multi-cloud environments.
    
    Provides step-by-step onboarding with validation, testing, and configuration
    setup across multiple cloud providers.
    """
    
    def __init__(self, client_manager: MultiTenantClientManager):
        """
        Initialize the ClientOnboardingService.
        
        Args:
            client_manager: MultiTenantClientManager instance
        """
        self.client_manager = client_manager
        self.aws_adapter = None
        self.gcp_adapter = None
        self.azure_adapter = None
    
    async def start_onboarding(self, client: MultiCloudClient) -> Dict[str, Any]:
        """
        Start the complete onboarding workflow for a new client.
        
        Args:
            client: MultiCloudClient to onboard
            
        Returns:
            Dictionary containing onboarding results and status
            
        Raises:
            OnboardingWorkflowError: If onboarding fails
        """
        logger.info(f"Starting onboarding workflow for client {client.client_id}")
        
        onboarding_results = {
            'client_id': client.client_id,
            'organization_name': client.organization_name,
            'started_at': datetime.utcnow().isoformat(),
            'status': OnboardingStatus.IN_PROGRESS.value,
            'steps': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Update client status
            client.onboarding_status = OnboardingStatus.IN_PROGRESS
            await self._update_client_async(client)
            
            # Step 1: Validate basic client configuration
            logger.info(f"Step 1: Validating basic configuration for client {client.client_id}")
            step1_result = await self._validate_basic_configuration(client)
            onboarding_results['steps']['basic_validation'] = step1_result
            
            if not step1_result['success']:
                raise ConfigurationError("Basic configuration validation failed")
            
            # Step 2: Validate cloud provider credentials
            logger.info(f"Step 2: Validating provider credentials for client {client.client_id}")
            step2_result = await self._validate_all_provider_credentials(client)
            onboarding_results['steps']['credential_validation'] = step2_result
            
            if not step2_result['success']:
                raise ProviderValidationError("Provider credential validation failed")
            
            # Step 3: Test data collection from each provider
            logger.info(f"Step 3: Testing data collection for client {client.client_id}")
            step3_result = await self._test_data_collection(client)
            onboarding_results['steps']['data_collection_test'] = step3_result
            
            # Step 4: Set up initial configuration and preferences
            logger.info(f"Step 4: Setting up initial configuration for client {client.client_id}")
            step4_result = await self._setup_initial_configuration(client)
            onboarding_results['steps']['initial_setup'] = step4_result
            
            # Step 5: Create initial cost baseline (if data collection succeeded)
            if step3_result['success']:
                logger.info(f"Step 5: Creating initial cost baseline for client {client.client_id}")
                step5_result = await self._create_initial_baseline(client)
                onboarding_results['steps']['baseline_creation'] = step5_result
            
            # Determine overall success
            critical_steps = ['basic_validation', 'credential_validation']
            overall_success = all(
                onboarding_results['steps'][step]['success'] 
                for step in critical_steps
            )
            
            if overall_success:
                client.onboarding_status = OnboardingStatus.COMPLETED
                client.complete_onboarding()
                onboarding_results['status'] = OnboardingStatus.COMPLETED.value
                logger.info(f"Onboarding completed successfully for client {client.client_id}")
            else:
                client.onboarding_status = OnboardingStatus.FAILED
                onboarding_results['status'] = OnboardingStatus.FAILED.value
                logger.error(f"Onboarding failed for client {client.client_id}")
            
            # Final client update
            await self._update_client_async(client)
            
            onboarding_results['completed_at'] = datetime.utcnow().isoformat()
            return onboarding_results
            
        except Exception as e:
            logger.error(f"Onboarding workflow failed for client {client.client_id}: {e}")
            
            client.onboarding_status = OnboardingStatus.FAILED
            await self._update_client_async(client)
            
            onboarding_results['status'] = OnboardingStatus.FAILED.value
            onboarding_results['errors'].append(str(e))
            onboarding_results['completed_at'] = datetime.utcnow().isoformat()
            
            raise OnboardingWorkflowError(f"Onboarding failed: {e}") from e
    
    async def _validate_basic_configuration(self, client: MultiCloudClient) -> Dict[str, Any]:
        """
        Validate basic client configuration.
        
        Args:
            client: MultiCloudClient to validate
            
        Returns:
            Dictionary containing validation results
        """
        result = {
            'success': True,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            # Validate organization name
            if not client.organization_name or len(client.organization_name.strip()) < 2:
                result['errors'].append("Organization name must be at least 2 characters")
                result['success'] = False
            
            # Validate subscription tier
            if client.subscription_tier == SubscriptionTier.FREE:
                result['warnings'].append("Free tier has limited features and data retention")
            
            # Validate cloud accounts exist
            total_accounts = sum(len(accounts) for accounts in client.cloud_accounts.values())
            if total_accounts == 0:
                result['errors'].append("At least one cloud account must be configured")
                result['success'] = False
            
            # Validate resource limits
            violations = client.validate_resource_usage()
            if violations:
                result['errors'].extend(violations)
                result['success'] = False
            
            # Validate notification preferences
            if client.notification_preferences.email_enabled:
                if not client.notification_preferences.email_recipients:
                    result['errors'].append("Email notifications enabled but no recipients specified")
                    result['success'] = False
            
            result['details'] = {
                'organization_name': client.organization_name,
                'subscription_tier': client.subscription_tier.value,
                'total_accounts': total_accounts,
                'providers': [p.value for p in client.get_providers()],
                'notification_channels': self._get_enabled_notification_channels(client)
            }
            
        except Exception as e:
            logger.error(f"Error during basic configuration validation: {e}")
            result['success'] = False
            result['errors'].append(f"Validation error: {e}")
        
        return result
    
    async def _validate_all_provider_credentials(self, client: MultiCloudClient) -> Dict[str, Any]:
        """
        Validate credentials for all configured cloud providers.
        
        Args:
            client: MultiCloudClient to validate
            
        Returns:
            Dictionary containing validation results for each provider
        """
        result = {
            'success': True,
            'errors': [],
            'warnings': [],
            'provider_results': {}
        }
        
        try:
            validation_tasks = []
            
            for provider, accounts in client.cloud_accounts.items():
                for account in accounts:
                    if account.is_active:
                        task = self._validate_provider_account(provider, account)
                        validation_tasks.append((provider, account.account_id, task))
            
            # Run validations concurrently
            for provider, account_id, task in validation_tasks:
                try:
                    account_result = await task
                    
                    provider_key = f"{provider.value}_{account_id}"
                    result['provider_results'][provider_key] = account_result
                    
                    if not account_result['success']:
                        result['success'] = False
                        result['errors'].extend([
                            f"{provider.value} account {account_id}: {error}"
                            for error in account_result['errors']
                        ])
                    
                    if account_result['warnings']:
                        result['warnings'].extend([
                            f"{provider.value} account {account_id}: {warning}"
                            for warning in account_result['warnings']
                        ])
                        
                except Exception as e:
                    logger.error(f"Error validating {provider.value} account {account_id}: {e}")
                    result['success'] = False
                    result['errors'].append(f"{provider.value} account {account_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error during provider credential validation: {e}")
            result['success'] = False
            result['errors'].append(f"Credential validation error: {e}")
        
        return result
    
    async def _validate_provider_account(self, provider: CloudProvider, account: CloudAccount) -> Dict[str, Any]:
        """
        Validate a specific provider account.
        
        Args:
            provider: Cloud provider
            account: Cloud account to validate
            
        Returns:
            Dictionary containing validation results
        """
        result = {
            'success': False,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            if provider == CloudProvider.AWS:
                result = await self._validate_aws_account(account)
            elif provider == CloudProvider.GCP:
                result = await self._validate_gcp_account(account)
            elif provider == CloudProvider.AZURE:
                result = await self._validate_azure_account(account)
            else:
                result['errors'].append(f"Unsupported provider: {provider.value}")
            
        except Exception as e:
            logger.error(f"Error validating {provider.value} account {account.account_id}: {e}")
            result['errors'].append(str(e))
        
        return result
    
    async def _validate_aws_account(self, account: CloudAccount) -> Dict[str, Any]:
        """Validate AWS account credentials and permissions."""
        result = {
            'success': False,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            creds = account.credentials
            if not isinstance(creds, AWSCredentials):
                result['errors'].append("Invalid AWS credentials type")
                return result
            
            # Create AWS adapter for validation
            if not self.aws_adapter:
                self.aws_adapter = AWSCostAdapter(creds)
            
            # Test basic connectivity
            validation_result = await self.aws_adapter.validate_credentials()
            
            if validation_result.is_valid:
                result['success'] = True
                result['details'] = {
                    'account_id': validation_result.account_id,
                    'account_alias': validation_result.account_alias,
                    'permissions': validation_result.permissions,
                    'regions': validation_result.available_regions
                }
                
                # Check for warnings
                if not validation_result.has_cost_explorer_access:
                    result['warnings'].append("Limited Cost Explorer access - some features may not work")
                
                if not validation_result.has_organizations_access:
                    result['warnings'].append("No Organizations access - multi-account features limited")
                    
            else:
                result['errors'].append(validation_result.error_message or "AWS credential validation failed")
            
        except Exception as e:
            logger.error(f"AWS account validation error: {e}")
            result['errors'].append(f"AWS validation error: {e}")
        
        return result
    
    async def _validate_gcp_account(self, account: CloudAccount) -> Dict[str, Any]:
        """Validate GCP account credentials and permissions."""
        result = {
            'success': False,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            creds = account.credentials
            if not isinstance(creds, GCPCredentials):
                result['errors'].append("Invalid GCP credentials type")
                return result
            
            # Create GCP adapter for validation
            if not self.gcp_adapter:
                self.gcp_adapter = GCPCostAdapter(creds)
            
            # Test basic connectivity
            validation_result = await self.gcp_adapter.validate_credentials()
            
            if validation_result.is_valid:
                result['success'] = True
                result['details'] = {
                    'project_id': validation_result.project_id,
                    'project_name': validation_result.project_name,
                    'permissions': validation_result.permissions,
                    'billing_account': validation_result.billing_account_id
                }
                
                # Check for warnings
                if not validation_result.has_billing_access:
                    result['warnings'].append("Limited billing access - cost data may be incomplete")
                    
            else:
                result['errors'].append(validation_result.error_message or "GCP credential validation failed")
            
        except Exception as e:
            logger.error(f"GCP account validation error: {e}")
            result['errors'].append(f"GCP validation error: {e}")
        
        return result
    
    async def _validate_azure_account(self, account: CloudAccount) -> Dict[str, Any]:
        """Validate Azure account credentials and permissions."""
        result = {
            'success': False,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            creds = account.credentials
            if not isinstance(creds, AzureCredentials):
                result['errors'].append("Invalid Azure credentials type")
                return result
            
            # Create Azure adapter for validation
            if not self.azure_adapter:
                self.azure_adapter = AzureCostAdapter(creds)
            
            # Test basic connectivity
            validation_result = await self.azure_adapter.validate_credentials()
            
            if validation_result.is_valid:
                result['success'] = True
                result['details'] = {
                    'subscription_id': validation_result.subscription_id,
                    'subscription_name': validation_result.subscription_name,
                    'tenant_id': validation_result.tenant_id,
                    'permissions': validation_result.permissions
                }
                
                # Check for warnings
                if not validation_result.has_cost_management_access:
                    result['warnings'].append("Limited Cost Management access - some features may not work")
                    
            else:
                result['errors'].append(validation_result.error_message or "Azure credential validation failed")
            
        except Exception as e:
            logger.error(f"Azure account validation error: {e}")
            result['errors'].append(f"Azure validation error: {e}")
        
        return result
    
    async def _test_data_collection(self, client: MultiCloudClient) -> Dict[str, Any]:
        """
        Test data collection from all configured providers.
        
        Args:
            client: MultiCloudClient to test
            
        Returns:
            Dictionary containing test results
        """
        result = {
            'success': True,
            'errors': [],
            'warnings': [],
            'provider_results': {}
        }
        
        try:
            # Test data collection from each provider
            for provider, accounts in client.cloud_accounts.items():
                for account in accounts:
                    if account.is_active:
                        try:
                            test_result = await self._test_provider_data_collection(provider, account)
                            
                            provider_key = f"{provider.value}_{account.account_id}"
                            result['provider_results'][provider_key] = test_result
                            
                            if not test_result['success']:
                                result['warnings'].append(
                                    f"Data collection test failed for {provider.value} account {account.account_id}"
                                )
                            
                        except Exception as e:
                            logger.error(f"Error testing data collection for {provider.value} account {account.account_id}: {e}")
                            result['warnings'].append(
                                f"Data collection test error for {provider.value} account {account.account_id}: {e}"
                            )
            
            # Data collection test failures are warnings, not errors
            # The client can still be onboarded even if initial data collection fails
            
        except Exception as e:
            logger.error(f"Error during data collection testing: {e}")
            result['warnings'].append(f"Data collection testing error: {e}")
        
        return result
    
    async def _test_provider_data_collection(self, provider: CloudProvider, account: CloudAccount) -> Dict[str, Any]:
        """
        Test data collection from a specific provider account.
        
        Args:
            provider: Cloud provider
            account: Cloud account to test
            
        Returns:
            Dictionary containing test results
        """
        result = {
            'success': False,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            # Test collecting last 7 days of data
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=7)
            
            if provider == CloudProvider.AWS and self.aws_adapter:
                cost_data = await self.aws_adapter.collect_cost_data({
                    'start_date': start_date,
                    'end_date': end_date
                })
                
                if cost_data and cost_data.total_cost >= 0:
                    result['success'] = True
                    result['details'] = {
                        'total_cost': float(cost_data.total_cost),
                        'currency': cost_data.currency.value,
                        'services_count': len(cost_data.services),
                        'date_range': f"{start_date} to {end_date}"
                    }
                else:
                    result['errors'].append("No cost data returned from AWS")
                    
            elif provider == CloudProvider.GCP and self.gcp_adapter:
                cost_data = await self.gcp_adapter.collect_cost_data({
                    'start_date': start_date,
                    'end_date': end_date
                })
                
                if cost_data and cost_data.total_cost >= 0:
                    result['success'] = True
                    result['details'] = {
                        'total_cost': float(cost_data.total_cost),
                        'currency': cost_data.currency.value,
                        'services_count': len(cost_data.services),
                        'date_range': f"{start_date} to {end_date}"
                    }
                else:
                    result['errors'].append("No cost data returned from GCP")
                    
            elif provider == CloudProvider.AZURE and self.azure_adapter:
                cost_data = await self.azure_adapter.collect_cost_data({
                    'start_date': start_date,
                    'end_date': end_date
                })
                
                if cost_data and cost_data.total_cost >= 0:
                    result['success'] = True
                    result['details'] = {
                        'total_cost': float(cost_data.total_cost),
                        'currency': cost_data.currency.value,
                        'services_count': len(cost_data.services),
                        'date_range': f"{start_date} to {end_date}"
                    }
                else:
                    result['errors'].append("No cost data returned from Azure")
            else:
                result['errors'].append(f"No adapter available for {provider.value}")
            
        except Exception as e:
            logger.error(f"Data collection test error for {provider.value}: {e}")
            result['errors'].append(str(e))
        
        return result
    
    async def _setup_initial_configuration(self, client: MultiCloudClient) -> Dict[str, Any]:
        """
        Set up initial configuration and preferences for the client.
        
        Args:
            client: MultiCloudClient to configure
            
        Returns:
            Dictionary containing setup results
        """
        result = {
            'success': True,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            # Set up default AI preferences based on subscription tier
            if client.subscription_tier in [SubscriptionTier.PROFESSIONAL, SubscriptionTier.ENTERPRISE]:
                client.ai_preferences.enable_anomaly_detection = True
                client.ai_preferences.enable_forecasting = True
                client.ai_preferences.enable_recommendations = True
                client.ai_preferences.enable_automated_insights = True
            else:
                client.ai_preferences.enable_automated_insights = False
                if client.subscription_tier == SubscriptionTier.FREE:
                    client.ai_preferences.enable_forecasting = False
            
            # Set up notification preferences
            if not client.notification_preferences.email_recipients:
                result['warnings'].append("No email recipients configured - notifications will not be sent")
            
            # Set up resource limits based on subscription tier
            client._apply_subscription_limits()
            
            # Initialize usage tracking
            client.reset_monthly_usage()
            
            result['details'] = {
                'ai_features_enabled': {
                    'anomaly_detection': client.ai_preferences.enable_anomaly_detection,
                    'forecasting': client.ai_preferences.enable_forecasting,
                    'recommendations': client.ai_preferences.enable_recommendations,
                    'automated_insights': client.ai_preferences.enable_automated_insights
                },
                'resource_limits': client.resource_limits.to_dict(),
                'notification_channels': self._get_enabled_notification_channels(client)
            }
            
        except Exception as e:
            logger.error(f"Error during initial configuration setup: {e}")
            result['success'] = False
            result['errors'].append(f"Configuration setup error: {e}")
        
        return result
    
    async def _create_initial_baseline(self, client: MultiCloudClient) -> Dict[str, Any]:
        """
        Create initial cost baseline for the client.
        
        Args:
            client: MultiCloudClient to create baseline for
            
        Returns:
            Dictionary containing baseline creation results
        """
        result = {
            'success': True,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        try:
            # Collect initial cost data for baseline
            baseline_data = {}
            total_baseline_cost = Decimal('0')
            
            for provider, accounts in client.cloud_accounts.items():
                provider_cost = Decimal('0')
                
                for account in accounts:
                    if account.is_active:
                        try:
                            # Get last 30 days of data for baseline
                            end_date = datetime.utcnow().date()
                            start_date = end_date - timedelta(days=30)
                            
                            if provider == CloudProvider.AWS and self.aws_adapter:
                                cost_data = await self.aws_adapter.collect_cost_data({
                                    'start_date': start_date,
                                    'end_date': end_date
                                })
                                if cost_data:
                                    provider_cost += cost_data.total_cost
                                    
                        except Exception as e:
                            logger.warning(f"Failed to collect baseline data for {provider.value} account {account.account_id}: {e}")
                
                baseline_data[provider.value] = float(provider_cost)
                total_baseline_cost += provider_cost
            
            result['details'] = {
                'total_baseline_cost': float(total_baseline_cost),
                'provider_breakdown': baseline_data,
                'baseline_period': '30 days',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Store baseline in client metadata (could be extended to separate table)
            # For now, just log the baseline creation
            logger.info(f"Created initial baseline for client {client.client_id}: ${total_baseline_cost}")
            
        except Exception as e:
            logger.error(f"Error creating initial baseline: {e}")
            result['success'] = False
            result['errors'].append(f"Baseline creation error: {e}")
        
        return result
    
    def _get_enabled_notification_channels(self, client: MultiCloudClient) -> List[str]:
        """Get list of enabled notification channels."""
        channels = []
        
        if client.notification_preferences.email_enabled:
            channels.append('email')
        if client.notification_preferences.slack_enabled:
            channels.append('slack')
        if client.notification_preferences.webhook_enabled:
            channels.append('webhook')
        
        return channels
    
    async def _update_client_async(self, client: MultiCloudClient) -> None:
        """Update client configuration asynchronously."""
        try:
            self.client_manager.update_client(client)
        except Exception as e:
            logger.error(f"Failed to update client {client.client_id}: {e}")
            # Don't raise exception here to avoid breaking the onboarding flow
    
    async def retry_failed_onboarding(self, client_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Retry onboarding for a client that previously failed.
        
        Args:
            client_id: Client ID to retry
            tenant_id: Tenant ID for isolation
            
        Returns:
            Dictionary containing retry results
            
        Raises:
            OnboardingWorkflowError: If retry fails
        """
        logger.info(f"Retrying onboarding for client {client_id}")
        
        try:
            # Get the client
            client = self.client_manager.get_client(client_id, tenant_id)
            
            if client.onboarding_status != OnboardingStatus.FAILED:
                raise OnboardingWorkflowError(
                    f"Client {client_id} is not in failed state (current: {client.onboarding_status.value})"
                )
            
            # Reset onboarding status
            client.onboarding_status = OnboardingStatus.PENDING
            
            # Start onboarding workflow
            return await self.start_onboarding(client)
            
        except Exception as e:
            logger.error(f"Failed to retry onboarding for client {client_id}: {e}")
            raise OnboardingWorkflowError(f"Onboarding retry failed: {e}") from e
    
    def get_onboarding_status(self, client_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Get current onboarding status for a client.
        
        Args:
            client_id: Client ID
            tenant_id: Tenant ID for isolation
            
        Returns:
            Dictionary containing onboarding status information
        """
        try:
            client = self.client_manager.get_client(client_id, tenant_id)
            
            return {
                'client_id': client_id,
                'organization_name': client.organization_name,
                'onboarding_status': client.onboarding_status.value,
                'created_at': client.created_at.isoformat(),
                'updated_at': client.updated_at.isoformat(),
                'onboarding_completed_at': client.onboarding_completed_at.isoformat() if client.onboarding_completed_at else None,
                'providers_configured': [p.value for p in client.get_providers()],
                'total_accounts': sum(len(accounts) for accounts in client.cloud_accounts.values()),
                'subscription_tier': client.subscription_tier.value
            }
            
        except Exception as e:
            logger.error(f"Error getting onboarding status for client {client_id}: {e}")
            raise OnboardingWorkflowError(f"Failed to get onboarding status: {e}") from e