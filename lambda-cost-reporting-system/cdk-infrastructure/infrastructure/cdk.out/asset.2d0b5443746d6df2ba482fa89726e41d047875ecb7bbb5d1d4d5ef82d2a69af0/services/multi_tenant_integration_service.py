"""
Multi-Tenant Integration Service

This service provides a unified interface for all multi-tenant operations,
integrating client management, data isolation, RBAC, and resource allocation.
"""

import boto3
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio

from ..models.multi_tenant_models import MultiCloudClient, CloudAccount, ClientRole, SubscriptionTier
from ..models.multi_cloud_models import UnifiedCostRecord, CloudProvider
from ..services.multi_tenant_client_manager import MultiTenantClientManager
from ..services.client_onboarding_service import ClientOnboardingService
from ..services.tenant_data_isolation_service import TenantDataIsolationService
from ..services.resource_allocation_manager import ResourceAllocationManager
from ..services.rbac_service import RBACService, Permission, User
from ..services.api_access_control import APIAccessControl


logger = logging.getLogger(__name__)


class MultiTenantIntegrationError(Exception):
    """Base exception for multi-tenant integration errors."""
    pass


class MultiTenantIntegrationService:
    """
    Unified service for multi-tenant operations.
    
    Provides a single interface for all multi-tenant functionality including
    client management, onboarding, data isolation, RBAC, and resource allocation.
    """
    
    def __init__(self, region: str = "us-east-1", kms_key_id: Optional[str] = None,
                 jwt_secret: Optional[str] = None):
        """
        Initialize the MultiTenantIntegrationService.
        
        Args:
            region: AWS region
            kms_key_id: KMS key ID for encryption
            jwt_secret: JWT secret for API access control
        """
        self.region = region
        self.kms_key_id = kms_key_id
        
        # Initialize core services
        self.client_manager = MultiTenantClientManager(
            region=region,
            kms_key_id=kms_key_id
        )
        
        self.isolation_service = TenantDataIsolationService(region=region)
        
        self.resource_manager = ResourceAllocationManager(
            isolation_service=self.isolation_service,
            region=region
        )
        
        self.rbac_service = RBACService(region=region)
        
        self.onboarding_service = ClientOnboardingService(
            client_manager=self.client_manager
        )
        
        # Initialize API access control if JWT secret is provided
        self.api_access_control = None
        if jwt_secret:
            self.api_access_control = APIAccessControl(
                rbac_service=self.rbac_service,
                jwt_secret=jwt_secret
            )
    
    async def create_complete_tenant(self, organization_name: str, admin_email: str,
                                   cloud_accounts: List[CloudAccount],
                                   subscription_tier: SubscriptionTier = SubscriptionTier.FREE) -> Dict[str, Any]:
        """
        Create a complete tenant with all necessary components.
        
        Args:
            organization_name: Organization name
            admin_email: Admin user email
            cloud_accounts: List of cloud accounts to configure
            subscription_tier: Subscription tier
            
        Returns:
            Dictionary containing tenant creation results
        """
        try:
            logger.info(f"Creating complete tenant for organization {organization_name}")
            
            result = {
                'organization_name': organization_name,
                'admin_email': admin_email,
                'subscription_tier': subscription_tier.value,
                'created_at': datetime.utcnow().isoformat(),
                'components': {},
                'errors': [],
                'warnings': []
            }
            
            # Step 1: Create multi-cloud client
            logger.info("Step 1: Creating multi-cloud client")
            client = MultiCloudClient(
                client_id="",  # Will be auto-generated
                organization_name=organization_name,
                subscription_tier=subscription_tier
            )
            
            # Add cloud accounts
            for account in cloud_accounts:
                client.add_cloud_account(account)
            
            # Create client
            created_client = self.client_manager.create_client(client)
            result['components']['client'] = {
                'client_id': created_client.client_id,
                'tenant_id': created_client.tenant_id,
                'status': 'created'
            }
            
            # Step 2: Create tenant data partition
            logger.info("Step 2: Creating tenant data partition")
            try:
                partition = self.isolation_service.create_tenant_partition(created_client)
                result['components']['data_partition'] = {
                    'partition_key': partition.partition_key,
                    'isolation_level': partition.isolation_level.value,
                    'status': 'created'
                }
            except Exception as e:
                logger.error(f"Failed to create data partition: {e}")
                result['errors'].append(f"Data partition creation failed: {e}")
            
            # Step 3: Allocate resources
            logger.info("Step 3: Allocating resources")
            try:
                allocations = self.resource_manager.allocate_resources_for_client(created_client)
                result['components']['resource_allocation'] = {
                    'allocated_resources': {
                        resource_type.value: allocation.allocated_amount
                        for resource_type, allocation in allocations.items()
                    },
                    'status': 'created'
                }
            except Exception as e:
                logger.error(f"Failed to allocate resources: {e}")
                result['errors'].append(f"Resource allocation failed: {e}")
            
            # Step 4: Create admin user
            logger.info("Step 4: Creating admin user")
            try:
                admin_user = self.rbac_service.create_user(
                    email=admin_email,
                    tenant_id=created_client.tenant_id,
                    roles=[ClientRole.ADMIN],
                    created_by="system",  # System-created user
                    is_system_admin=False
                )
                result['components']['admin_user'] = {
                    'user_id': admin_user.user_id,
                    'email': admin_user.email,
                    'roles': [role.value for role in admin_user.roles],
                    'status': 'created'
                }
            except Exception as e:
                logger.error(f"Failed to create admin user: {e}")
                result['errors'].append(f"Admin user creation failed: {e}")
            
            # Step 5: Start onboarding workflow
            logger.info("Step 5: Starting onboarding workflow")
            try:
                onboarding_result = await self.onboarding_service.start_onboarding(created_client)
                result['components']['onboarding'] = {
                    'status': onboarding_result['status'],
                    'steps_completed': list(onboarding_result['steps'].keys()),
                    'success': onboarding_result['status'] == 'completed'
                }
                
                if onboarding_result.get('errors'):
                    result['warnings'].extend(onboarding_result['errors'])
                    
            except Exception as e:
                logger.error(f"Onboarding workflow failed: {e}")
                result['errors'].append(f"Onboarding failed: {e}")
                result['components']['onboarding'] = {
                    'status': 'failed',
                    'error': str(e)
                }
            
            # Determine overall success
            result['success'] = len(result['errors']) == 0
            result['tenant_id'] = created_client.tenant_id
            result['client_id'] = created_client.client_id
            
            logger.info(f"Tenant creation {'completed successfully' if result['success'] else 'completed with errors'}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create complete tenant: {e}")
            raise MultiTenantIntegrationError(f"Tenant creation failed: {e}") from e
    
    def get_tenant_overview(self, tenant_id: str, requesting_user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive tenant overview.
        
        Args:
            tenant_id: Tenant ID
            requesting_user_id: User ID making the request
            
        Returns:
            Dictionary containing tenant overview
        """
        try:
            logger.info(f"Getting tenant overview for {tenant_id}")
            
            # Check permissions
            self.rbac_service.require_permission(requesting_user_id, Permission.CLIENT_READ)
            
            overview = {
                'tenant_id': tenant_id,
                'generated_at': datetime.utcnow().isoformat(),
                'client_info': {},
                'users': {},
                'resource_usage': {},
                'data_statistics': {},
                'recent_activity': {}
            }
            
            # Get client information
            try:
                client = self.client_manager.get_client("", tenant_id)  # Get by tenant_id
                overview['client_info'] = {
                    'client_id': client.client_id,
                    'organization_name': client.organization_name,
                    'subscription_tier': client.subscription_tier.value,
                    'status': client.status.value,
                    'onboarding_status': client.onboarding_status.value,
                    'providers': [p.value for p in client.get_providers()],
                    'total_accounts': sum(len(accounts) for accounts in client.cloud_accounts.values()),
                    'created_at': client.created_at.isoformat(),
                    'last_activity': client.last_activity.isoformat() if client.last_activity else None
                }
            except Exception as e:
                logger.warning(f"Failed to get client info: {e}")
                overview['client_info'] = {'error': str(e)}
            
            # Get user information
            try:
                users = self.rbac_service.list_tenant_users(tenant_id, requesting_user_id)
                overview['users'] = {
                    'total_count': len(users),
                    'active_count': sum(1 for u in users if u.is_active),
                    'role_distribution': self._get_role_distribution(users),
                    'recent_logins': sum(1 for u in users if u.last_login and 
                                       u.last_login > datetime.utcnow() - timedelta(days=7))
                }
            except Exception as e:
                logger.warning(f"Failed to get user info: {e}")
                overview['users'] = {'error': str(e)}
            
            # Get resource usage
            try:
                allocations = self.resource_manager.get_client_allocations(tenant_id)
                overview['resource_usage'] = {
                    resource_type.value: {
                        'allocated': allocation.allocated_amount,
                        'used': allocation.used_amount,
                        'utilization_percentage': allocation.utilization_percentage,
                        'available': allocation.available_amount
                    }
                    for resource_type, allocation in allocations.items()
                }
            except Exception as e:
                logger.warning(f"Failed to get resource usage: {e}")
                overview['resource_usage'] = {'error': str(e)}
            
            # Get data statistics (simplified)
            try:
                partition = self.isolation_service.get_tenant_partition(tenant_id)
                overview['data_statistics'] = {
                    'data_size_bytes': partition.data_size_bytes,
                    'record_count': partition.record_count,
                    'last_accessed': partition.last_accessed.isoformat() if partition.last_accessed else None,
                    'isolation_level': partition.isolation_level.value
                }
            except Exception as e:
                logger.warning(f"Failed to get data statistics: {e}")
                overview['data_statistics'] = {'error': str(e)}
            
            # Get recent activity (audit logs)
            try:
                recent_logs = self.rbac_service.get_audit_logs(
                    tenant_id=tenant_id,
                    requesting_user_id=requesting_user_id,
                    start_date=datetime.utcnow() - timedelta(days=7),
                    limit=10
                )
                overview['recent_activity'] = {
                    'total_actions': len(recent_logs),
                    'recent_actions': [
                        {
                            'action': log.action.value,
                            'resource_type': log.resource_type.value,
                            'timestamp': log.timestamp.isoformat(),
                            'success': log.success
                        }
                        for log in recent_logs[:5]  # Last 5 actions
                    ]
                }
            except Exception as e:
                logger.warning(f"Failed to get recent activity: {e}")
                overview['recent_activity'] = {'error': str(e)}
            
            return overview
            
        except Exception as e:
            logger.error(f"Failed to get tenant overview: {e}")
            raise MultiTenantIntegrationError(f"Tenant overview failed: {e}") from e
    
    def update_tenant_subscription(self, tenant_id: str, new_tier: SubscriptionTier,
                                 updated_by: str) -> Dict[str, Any]:
        """
        Update tenant subscription tier and adjust resources accordingly.
        
        Args:
            tenant_id: Tenant ID
            new_tier: New subscription tier
            updated_by: User ID performing the update
            
        Returns:
            Dictionary containing update results
        """
        try:
            logger.info(f"Updating subscription for tenant {tenant_id} to {new_tier.value}")
            
            # Check permissions
            self.rbac_service.require_permission(updated_by, Permission.BILLING_MANAGE)
            
            result = {
                'tenant_id': tenant_id,
                'old_tier': None,
                'new_tier': new_tier.value,
                'updated_at': datetime.utcnow().isoformat(),
                'changes': {},
                'errors': []
            }
            
            # Get current client
            client = self.client_manager.get_client("", tenant_id)
            result['old_tier'] = client.subscription_tier.value
            
            # Update subscription tier
            client.subscription_tier = new_tier
            client._apply_subscription_limits()  # Apply new resource limits
            
            # Update client
            updated_client = self.client_manager.update_client(client)
            result['changes']['client'] = 'updated'
            
            # Update resource allocations
            try:
                # This would involve reallocating resources based on new tier
                # For now, just log the change
                logger.info(f"Resource limits updated for new tier: {client.resource_limits.to_dict()}")
                result['changes']['resource_limits'] = client.resource_limits.to_dict()
            except Exception as e:
                logger.error(f"Failed to update resource allocations: {e}")
                result['errors'].append(f"Resource allocation update failed: {e}")
            
            result['success'] = len(result['errors']) == 0
            
            logger.info(f"Subscription update {'completed successfully' if result['success'] else 'completed with errors'}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update tenant subscription: {e}")
            raise MultiTenantIntegrationError(f"Subscription update failed: {e}") from e
    
    def delete_complete_tenant(self, tenant_id: str, deleted_by: str,
                             confirm_deletion: bool = False) -> Dict[str, Any]:
        """
        Delete a complete tenant and all associated data.
        
        Args:
            tenant_id: Tenant ID to delete
            deleted_by: User ID performing the deletion
            confirm_deletion: Confirmation flag for safety
            
        Returns:
            Dictionary containing deletion results
        """
        try:
            if not confirm_deletion:
                raise MultiTenantIntegrationError("Deletion not confirmed - set confirm_deletion=True")
            
            logger.info(f"Deleting complete tenant {tenant_id}")
            
            # Check permissions (must be system admin for tenant deletion)
            requesting_user = self.rbac_service.get_user(deleted_by)
            if not requesting_user.is_system_admin:
                raise MultiTenantIntegrationError("Only system administrators can delete tenants")
            
            result = {
                'tenant_id': tenant_id,
                'deleted_at': datetime.utcnow().isoformat(),
                'deleted_by': deleted_by,
                'components_deleted': {},
                'errors': []
            }
            
            # Step 1: Delete all tenant data
            logger.info("Step 1: Deleting tenant data")
            try:
                deletion_counts = self.isolation_service.delete_tenant_data(tenant_id)
                result['components_deleted']['data'] = deletion_counts
            except Exception as e:
                logger.error(f"Failed to delete tenant data: {e}")
                result['errors'].append(f"Data deletion failed: {e}")
            
            # Step 2: Delete all users
            logger.info("Step 2: Deleting tenant users")
            try:
                users = self.rbac_service.list_tenant_users(tenant_id, deleted_by)
                for user in users:
                    self.rbac_service.deactivate_user(user.user_id, deleted_by)
                result['components_deleted']['users'] = len(users)
            except Exception as e:
                logger.error(f"Failed to delete users: {e}")
                result['errors'].append(f"User deletion failed: {e}")
            
            # Step 3: Delete client configuration
            logger.info("Step 3: Deleting client configuration")
            try:
                self.client_manager.delete_client("", tenant_id)  # Delete by tenant_id
                result['components_deleted']['client'] = 1
            except Exception as e:
                logger.error(f"Failed to delete client: {e}")
                result['errors'].append(f"Client deletion failed: {e}")
            
            result['success'] = len(result['errors']) == 0
            
            logger.info(f"Tenant deletion {'completed successfully' if result['success'] else 'completed with errors'}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete complete tenant: {e}")
            raise MultiTenantIntegrationError(f"Tenant deletion failed: {e}") from e
    
    def get_system_health_report(self, requesting_user_id: str) -> Dict[str, Any]:
        """
        Get system-wide health report (system admin only).
        
        Args:
            requesting_user_id: User ID making the request
            
        Returns:
            Dictionary containing system health information
        """
        try:
            # Check permissions (system admin only)
            requesting_user = self.rbac_service.get_user(requesting_user_id)
            if not requesting_user.is_system_admin:
                raise MultiTenantIntegrationError("System health report requires system admin privileges")
            
            logger.info("Generating system health report")
            
            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'generated_by': requesting_user_id,
                'system_status': 'healthy',  # Will be updated based on checks
                'components': {},
                'metrics': {},
                'alerts': []
            }
            
            # Check client manager health
            try:
                active_clients = self.client_manager.get_active_clients()
                report['components']['client_manager'] = {
                    'status': 'healthy',
                    'active_clients': len(active_clients),
                    'total_tenants': len(set(c.tenant_id for c in active_clients))
                }
            except Exception as e:
                report['components']['client_manager'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                report['alerts'].append(f"Client manager unhealthy: {e}")
            
            # Check resource allocation health
            try:
                # This would check resource pool utilization
                report['components']['resource_manager'] = {
                    'status': 'healthy',
                    'global_utilization': 'normal'  # Placeholder
                }
            except Exception as e:
                report['components']['resource_manager'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                report['alerts'].append(f"Resource manager unhealthy: {e}")
            
            # Check RBAC service health
            try:
                # This would check user authentication and authorization
                report['components']['rbac_service'] = {
                    'status': 'healthy',
                    'active_sessions': 'normal'  # Placeholder
                }
            except Exception as e:
                report['components']['rbac_service'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                report['alerts'].append(f"RBAC service unhealthy: {e}")
            
            # Determine overall system status
            unhealthy_components = [
                name for name, info in report['components'].items()
                if info.get('status') == 'unhealthy'
            ]
            
            if unhealthy_components:
                report['system_status'] = 'degraded' if len(unhealthy_components) < len(report['components']) / 2 else 'unhealthy'
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate system health report: {e}")
            raise MultiTenantIntegrationError(f"Health report generation failed: {e}") from e
    
    def _get_role_distribution(self, users: List[User]) -> Dict[str, int]:
        """Get distribution of roles among users."""
        role_counts = {}
        for user in users:
            for role in user.roles:
                role_counts[role.value] = role_counts.get(role.value, 0) + 1
        return role_counts
    
    def get_api_access_control(self) -> Optional[APIAccessControl]:
        """Get API access control instance if available."""
        return self.api_access_control
    
    def create_jwt_token_for_user(self, user_id: str) -> Optional[str]:
        """Create JWT token for a user if API access control is available."""
        if not self.api_access_control:
            return None
        
        try:
            user = self.rbac_service.get_user(user_id)
            return self.api_access_control.create_jwt_token(
                user_id=user.user_id,
                email=user.email,
                tenant_id=user.tenant_id,
                roles=[role.value for role in user.roles]
            )
        except Exception as e:
            logger.error(f"Failed to create JWT token for user {user_id}: {e}")
            return None