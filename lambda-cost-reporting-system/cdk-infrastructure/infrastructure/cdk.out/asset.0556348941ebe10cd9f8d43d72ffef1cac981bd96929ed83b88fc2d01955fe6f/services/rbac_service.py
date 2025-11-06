"""
Role-Based Access Control (RBAC) Service

This service provides comprehensive role-based access control for multi-tenant
cost analytics, including user management, permission enforcement, and audit logging.
"""

import boto3
import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import uuid

from ..models.multi_tenant_models import MultiCloudClient, ClientRole


logger = logging.getLogger(__name__)


class Permission(Enum):
    """System permissions."""
    # Client management
    CLIENT_CREATE = "client:create"
    CLIENT_READ = "client:read"
    CLIENT_UPDATE = "client:update"
    CLIENT_DELETE = "client:delete"
    
    # Cost data access
    COST_DATA_READ = "cost_data:read"
    COST_DATA_WRITE = "cost_data:write"
    COST_DATA_DELETE = "cost_data:delete"
    
    # AI insights
    AI_INSIGHTS_READ = "ai_insights:read"
    AI_INSIGHTS_CONFIGURE = "ai_insights:configure"
    
    # Reports
    REPORTS_READ = "reports:read"
    REPORTS_CREATE = "reports:create"
    REPORTS_DELETE = "reports:delete"
    
    # User management
    USERS_READ = "users:read"
    USERS_INVITE = "users:invite"
    USERS_MANAGE = "users:manage"
    USERS_DELETE = "users:delete"
    
    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"
    
    # Billing
    BILLING_READ = "billing:read"
    BILLING_MANAGE = "billing:manage"
    
    # Audit logs
    AUDIT_READ = "audit:read"
    
    # System admin (super admin only)
    SYSTEM_ADMIN = "system:admin"


class ResourceType(Enum):
    """Resource types for permission checking."""
    CLIENT = "client"
    COST_DATA = "cost_data"
    AI_INSIGHTS = "ai_insights"
    REPORTS = "reports"
    USERS = "users"
    SETTINGS = "settings"
    BILLING = "billing"
    AUDIT_LOGS = "audit_logs"
    SYSTEM = "system"


class ActionType(Enum):
    """Action types for audit logging."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class User:
    """User entity with RBAC information."""
    user_id: str
    email: str
    tenant_id: str
    roles: Set[ClientRole] = field(default_factory=set)
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    is_system_admin: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    login_count: int = 0
    
    def __post_init__(self):
        """Initialize user with default permissions based on roles."""
        if not self.user_id:
            self.user_id = str(uuid.uuid4())
        
        # Add permissions based on roles
        for role in self.roles:
            self.permissions.update(self._get_role_permissions(role))
        
        # System admins get all permissions
        if self.is_system_admin:
            self.permissions = set(Permission)
    
    def _get_role_permissions(self, role: ClientRole) -> Set[Permission]:
        """Get permissions for a specific role."""
        role_permissions = {
            ClientRole.ADMIN: {
                Permission.CLIENT_READ, Permission.CLIENT_UPDATE,
                Permission.COST_DATA_READ, Permission.COST_DATA_WRITE,
                Permission.AI_INSIGHTS_READ, Permission.AI_INSIGHTS_CONFIGURE,
                Permission.REPORTS_READ, Permission.REPORTS_CREATE, Permission.REPORTS_DELETE,
                Permission.USERS_READ, Permission.USERS_INVITE, Permission.USERS_MANAGE,
                Permission.SETTINGS_READ, Permission.SETTINGS_UPDATE,
                Permission.BILLING_READ, Permission.BILLING_MANAGE,
                Permission.AUDIT_READ
            },
            ClientRole.MEMBER: {
                Permission.CLIENT_READ,
                Permission.COST_DATA_READ,
                Permission.AI_INSIGHTS_READ,
                Permission.REPORTS_READ, Permission.REPORTS_CREATE,
                Permission.SETTINGS_READ
            },
            ClientRole.VIEWER: {
                Permission.CLIENT_READ,
                Permission.COST_DATA_READ,
                Permission.AI_INSIGHTS_READ,
                Permission.REPORTS_READ
            }
        }
        
        return role_permissions.get(role, set())
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions or self.is_system_admin
    
    def has_role(self, role: ClientRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def add_role(self, role: ClientRole) -> None:
        """Add a role to the user."""
        self.roles.add(role)
        self.permissions.update(self._get_role_permissions(role))
        self.updated_at = datetime.utcnow()
    
    def remove_role(self, role: ClientRole) -> None:
        """Remove a role from the user."""
        if role in self.roles:
            self.roles.remove(role)
            # Recalculate permissions
            self.permissions = set()
            for r in self.roles:
                self.permissions.update(self._get_role_permissions(r))
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'tenant_id': self.tenant_id,
            'roles': [role.value for role in self.roles],
            'permissions': [perm.value for perm in self.permissions],
            'is_active': self.is_active,
            'is_system_admin': self.is_system_admin,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_count': self.login_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary."""
        user = cls(
            user_id=data['user_id'],
            email=data['email'],
            tenant_id=data['tenant_id'],
            roles={ClientRole(role) for role in data.get('roles', [])},
            is_active=data.get('is_active', True),
            is_system_admin=data.get('is_system_admin', False),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            last_login=datetime.fromisoformat(data['last_login']) if data.get('last_login') else None,
            login_count=data.get('login_count', 0)
        )
        
        # Override permissions from stored data
        user.permissions = {Permission(perm) for perm in data.get('permissions', [])}
        
        return user


@dataclass
class AuditLogEntry:
    """Audit log entry for tracking user actions."""
    log_id: str
    user_id: str
    tenant_id: str
    action: ActionType
    resource_type: ResourceType
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    
    def __post_init__(self):
        """Initialize audit log entry."""
        if not self.log_id:
            self.log_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'log_id': self.log_id,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'action': self.action.value,
            'resource_type': self.resource_type.value,
            'resource_id': self.resource_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat(),
            'success': self.success
        }


class RBACError(Exception):
    """Base exception for RBAC errors."""
    pass


class PermissionDeniedError(RBACError):
    """Raised when permission is denied."""
    pass


class UserNotFoundError(RBACError):
    """Raised when user is not found."""
    pass


class InvalidRoleError(RBACError):
    """Raised when an invalid role is specified."""
    pass


class RBACService:
    """
    Role-Based Access Control service for multi-tenant cost analytics.
    
    Provides comprehensive user management, permission enforcement,
    and audit logging capabilities.
    """
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the RBACService.
        
        Args:
            region: AWS region for DynamoDB operations
        """
        self.region = region
        self._dynamodb = None
        self._users_table = None
        self._audit_table = None
        
        # Table names
        self.users_table_name = "rbac-users"
        self.audit_table_name = "rbac-audit-logs"
        
        # Cache for users and permissions
        self._user_cache: Dict[str, User] = {}
        self._permission_cache: Dict[str, Set[Permission]] = {}
        
        # Cache TTL (5 minutes)
        self._cache_ttl = timedelta(minutes=5)
        self._cache_timestamps: Dict[str, datetime] = {}
    
    @property
    def dynamodb(self):
        """Lazy initialization of DynamoDB resource."""
        if self._dynamodb is None:
            self._dynamodb = boto3.resource('dynamodb', region_name=self.region)
        return self._dynamodb
    
    @property
    def users_table(self):
        """Lazy initialization of users table."""
        if self._users_table is None:
            self._users_table = self.dynamodb.Table(self.users_table_name)
        return self._users_table
    
    @property
    def audit_table(self):
        """Lazy initialization of audit table."""
        if self._audit_table is None:
            self._audit_table = self.dynamodb.Table(self.audit_table_name)
        return self._audit_table
    
    def create_user(self, email: str, tenant_id: str, roles: List[ClientRole], 
                   created_by: str, is_system_admin: bool = False) -> User:
        """
        Create a new user with specified roles.
        
        Args:
            email: User email address
            tenant_id: Tenant ID
            roles: List of roles to assign
            created_by: User ID of the creator
            is_system_admin: Whether user is a system admin
            
        Returns:
            Created User object
            
        Raises:
            RBACError: If user creation fails
        """
        try:
            logger.info(f"Creating user {email} for tenant {tenant_id}")
            
            # Create user
            user = User(
                email=email,
                tenant_id=tenant_id,
                roles=set(roles),
                is_system_admin=is_system_admin
            )
            
            # Store user
            self.users_table.put_item(
                Item={
                    'user_id': user.user_id,
                    'email': email,
                    'tenant_id': tenant_id,
                    **user.to_dict()
                },
                ConditionExpression='attribute_not_exists(user_id)'
            )
            
            # Cache user
            self._user_cache[user.user_id] = user
            self._cache_timestamps[user.user_id] = datetime.utcnow()
            
            # Log audit entry
            self._log_audit_entry(
                user_id=created_by,
                tenant_id=tenant_id,
                action=ActionType.CREATE,
                resource_type=ResourceType.USERS,
                resource_id=user.user_id,
                details={
                    'created_user_email': email,
                    'assigned_roles': [role.value for role in roles],
                    'is_system_admin': is_system_admin
                }
            )
            
            logger.info(f"Successfully created user {user.user_id} ({email})")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user {email}: {e}")
            raise RBACError(f"User creation failed: {e}") from e
    
    def get_user(self, user_id: str) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object
            
        Raises:
            UserNotFoundError: If user is not found
        """
        try:
            # Check cache first
            if user_id in self._user_cache:
                cache_time = self._cache_timestamps.get(user_id)
                if cache_time and datetime.utcnow() - cache_time < self._cache_ttl:
                    return self._user_cache[user_id]
            
            # Query from database
            response = self.users_table.get_item(
                Key={'user_id': user_id}
            )
            
            if 'Item' not in response:
                raise UserNotFoundError(f"User not found: {user_id}")
            
            user = User.from_dict(response['Item'])
            
            # Cache user
            self._user_cache[user_id] = user
            self._cache_timestamps[user_id] = datetime.utcnow()
            
            return user
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise RBACError(f"Failed to get user: {e}") from e
    
    def get_user_by_email(self, email: str, tenant_id: str) -> User:
        """
        Get user by email and tenant ID.
        
        Args:
            email: User email
            tenant_id: Tenant ID
            
        Returns:
            User object
            
        Raises:
            UserNotFoundError: If user is not found
        """
        try:
            # Query using GSI on email and tenant_id
            response = self.users_table.query(
                IndexName='email-tenant-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('email').eq(email) & 
                                     boto3.dynamodb.conditions.Key('tenant_id').eq(tenant_id)
            )
            
            items = response.get('Items', [])
            if not items:
                raise UserNotFoundError(f"User not found: {email} in tenant {tenant_id}")
            
            user = User.from_dict(items[0])
            
            # Cache user
            self._user_cache[user.user_id] = user
            self._cache_timestamps[user.user_id] = datetime.utcnow()
            
            return user
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise RBACError(f"Failed to get user by email: {e}") from e
    
    def update_user_roles(self, user_id: str, roles: List[ClientRole], updated_by: str) -> User:
        """
        Update user roles.
        
        Args:
            user_id: User ID
            roles: New list of roles
            updated_by: User ID of the updater
            
        Returns:
            Updated User object
            
        Raises:
            UserNotFoundError: If user is not found
        """
        try:
            logger.info(f"Updating roles for user {user_id}")
            
            # Get current user
            user = self.get_user(user_id)
            old_roles = list(user.roles)
            
            # Update roles
            user.roles = set(roles)
            user.permissions = set()
            for role in user.roles:
                user.permissions.update(user._get_role_permissions(role))
            user.updated_at = datetime.utcnow()
            
            # Update in database
            self.users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET roles = :roles, permissions = :permissions, updated_at = :updated',
                ExpressionAttributeValues={
                    ':roles': [role.value for role in user.roles],
                    ':permissions': [perm.value for perm in user.permissions],
                    ':updated': user.updated_at.isoformat()
                }
            )
            
            # Update cache
            self._user_cache[user_id] = user
            self._cache_timestamps[user_id] = datetime.utcnow()
            
            # Log audit entry
            self._log_audit_entry(
                user_id=updated_by,
                tenant_id=user.tenant_id,
                action=ActionType.UPDATE,
                resource_type=ResourceType.USERS,
                resource_id=user_id,
                details={
                    'old_roles': [role.value for role in old_roles],
                    'new_roles': [role.value for role in roles]
                }
            )
            
            logger.info(f"Successfully updated roles for user {user_id}")
            return user
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update user roles for {user_id}: {e}")
            raise RBACError(f"User role update failed: {e}") from e
    
    def check_permission(self, user_id: str, permission: Permission, 
                        resource_id: Optional[str] = None) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_id: User ID
            permission: Permission to check
            resource_id: Optional resource ID for resource-specific permissions
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            user = self.get_user(user_id)
            
            # Check if user is active
            if not user.is_active:
                return False
            
            # System admins have all permissions
            if user.is_system_admin:
                return True
            
            # Check permission
            has_permission = user.has_permission(permission)
            
            # Log permission check
            self._log_audit_entry(
                user_id=user_id,
                tenant_id=user.tenant_id,
                action=ActionType.PERMISSION_GRANTED if has_permission else ActionType.PERMISSION_DENIED,
                resource_type=ResourceType.SYSTEM,
                resource_id=resource_id,
                details={
                    'permission': permission.value,
                    'granted': has_permission
                },
                success=has_permission
            )
            
            return has_permission
            
        except UserNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking permission for user {user_id}: {e}")
            return False
    
    def require_permission(self, user_id: str, permission: Permission, 
                          resource_id: Optional[str] = None) -> None:
        """
        Require user to have a specific permission, raise exception if not.
        
        Args:
            user_id: User ID
            permission: Required permission
            resource_id: Optional resource ID
            
        Raises:
            PermissionDeniedError: If user doesn't have permission
        """
        if not self.check_permission(user_id, permission, resource_id):
            raise PermissionDeniedError(
                f"User {user_id} does not have permission {permission.value}"
            )
    
    def list_tenant_users(self, tenant_id: str, requesting_user_id: str) -> List[User]:
        """
        List all users in a tenant.
        
        Args:
            tenant_id: Tenant ID
            requesting_user_id: User ID making the request
            
        Returns:
            List of User objects
            
        Raises:
            PermissionDeniedError: If user doesn't have permission
        """
        try:
            # Check permission
            self.require_permission(requesting_user_id, Permission.USERS_READ)
            
            # Query users by tenant
            response = self.users_table.query(
                IndexName='tenant-created-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('tenant_id').eq(tenant_id)
            )
            
            users = []
            for item in response.get('Items', []):
                try:
                    user = User.from_dict(item)
                    users.append(user)
                except Exception as e:
                    logger.warning(f"Failed to parse user {item.get('user_id', 'unknown')}: {e}")
                    continue
            
            # Log audit entry
            self._log_audit_entry(
                user_id=requesting_user_id,
                tenant_id=tenant_id,
                action=ActionType.READ,
                resource_type=ResourceType.USERS,
                details={'users_count': len(users)}
            )
            
            return users
            
        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(f"Error listing tenant users for {tenant_id}: {e}")
            raise RBACError(f"Failed to list tenant users: {e}") from e
    
    def deactivate_user(self, user_id: str, deactivated_by: str) -> User:
        """
        Deactivate a user.
        
        Args:
            user_id: User ID to deactivate
            deactivated_by: User ID performing the deactivation
            
        Returns:
            Updated User object
            
        Raises:
            PermissionDeniedError: If user doesn't have permission
            UserNotFoundError: If user is not found
        """
        try:
            # Check permission
            self.require_permission(deactivated_by, Permission.USERS_MANAGE)
            
            # Get user
            user = self.get_user(user_id)
            
            # Deactivate user
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            # Update in database
            self.users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET is_active = :active, updated_at = :updated',
                ExpressionAttributeValues={
                    ':active': False,
                    ':updated': user.updated_at.isoformat()
                }
            )
            
            # Update cache
            self._user_cache[user_id] = user
            self._cache_timestamps[user_id] = datetime.utcnow()
            
            # Log audit entry
            self._log_audit_entry(
                user_id=deactivated_by,
                tenant_id=user.tenant_id,
                action=ActionType.UPDATE,
                resource_type=ResourceType.USERS,
                resource_id=user_id,
                details={'action': 'deactivate', 'user_email': user.email}
            )
            
            logger.info(f"Successfully deactivated user {user_id}")
            return user
            
        except (PermissionDeniedError, UserNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {e}")
            raise RBACError(f"User deactivation failed: {e}") from e
    
    def record_user_login(self, user_id: str, ip_address: Optional[str] = None, 
                         user_agent: Optional[str] = None) -> User:
        """
        Record user login.
        
        Args:
            user_id: User ID
            ip_address: User's IP address
            user_agent: User's user agent string
            
        Returns:
            Updated User object
        """
        try:
            user = self.get_user(user_id)
            
            # Update login information
            user.last_login = datetime.utcnow()
            user.login_count += 1
            
            # Update in database
            self.users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET last_login = :login, login_count = login_count + :inc',
                ExpressionAttributeValues={
                    ':login': user.last_login.isoformat(),
                    ':inc': 1
                }
            )
            
            # Update cache
            self._user_cache[user_id] = user
            self._cache_timestamps[user_id] = datetime.utcnow()
            
            # Log audit entry
            self._log_audit_entry(
                user_id=user_id,
                tenant_id=user.tenant_id,
                action=ActionType.LOGIN,
                resource_type=ResourceType.SYSTEM,
                details={'login_count': user.login_count},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to record login for user {user_id}: {e}")
            raise RBACError(f"Login recording failed: {e}") from e
    
    def get_audit_logs(self, tenant_id: str, requesting_user_id: str, 
                      start_date: Optional[datetime] = None, 
                      end_date: Optional[datetime] = None,
                      limit: int = 100) -> List[AuditLogEntry]:
        """
        Get audit logs for a tenant.
        
        Args:
            tenant_id: Tenant ID
            requesting_user_id: User ID making the request
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of logs to return
            
        Returns:
            List of AuditLogEntry objects
            
        Raises:
            PermissionDeniedError: If user doesn't have permission
        """
        try:
            # Check permission
            self.require_permission(requesting_user_id, Permission.AUDIT_READ)
            
            # Build query
            key_condition = boto3.dynamodb.conditions.Key('tenant_id').eq(tenant_id)
            
            if start_date and end_date:
                key_condition = key_condition & boto3.dynamodb.conditions.Key('timestamp').between(
                    start_date.isoformat(), end_date.isoformat()
                )
            elif start_date:
                key_condition = key_condition & boto3.dynamodb.conditions.Key('timestamp').gte(
                    start_date.isoformat()
                )
            elif end_date:
                key_condition = key_condition & boto3.dynamodb.conditions.Key('timestamp').lte(
                    end_date.isoformat()
                )
            
            # Query audit logs
            response = self.audit_table.query(
                IndexName='tenant-timestamp-index',
                KeyConditionExpression=key_condition,
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            
            audit_logs = []
            for item in response.get('Items', []):
                try:
                    log_entry = AuditLogEntry(
                        log_id=item['log_id'],
                        user_id=item['user_id'],
                        tenant_id=item['tenant_id'],
                        action=ActionType(item['action']),
                        resource_type=ResourceType(item['resource_type']),
                        resource_id=item.get('resource_id'),
                        details=item.get('details', {}),
                        ip_address=item.get('ip_address'),
                        user_agent=item.get('user_agent'),
                        timestamp=datetime.fromisoformat(item['timestamp']),
                        success=item.get('success', True)
                    )
                    audit_logs.append(log_entry)
                except Exception as e:
                    logger.warning(f"Failed to parse audit log {item.get('log_id', 'unknown')}: {e}")
                    continue
            
            return audit_logs
            
        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(f"Error getting audit logs for tenant {tenant_id}: {e}")
            raise RBACError(f"Failed to get audit logs: {e}") from e
    
    def _log_audit_entry(self, user_id: str, tenant_id: str, action: ActionType,
                        resource_type: ResourceType, resource_id: Optional[str] = None,
                        details: Optional[Dict[str, Any]] = None,
                        ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                        success: bool = True) -> None:
        """Log an audit entry."""
        try:
            log_entry = AuditLogEntry(
                log_id=str(uuid.uuid4()),
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                success=success
            )
            
            # Store audit log
            self.audit_table.put_item(
                Item={
                    'log_id': log_entry.log_id,
                    'tenant_id': tenant_id,
                    'timestamp': log_entry.timestamp.isoformat(),
                    **log_entry.to_dict(),
                    'ttl': int((log_entry.timestamp + timedelta(days=2555)).timestamp())  # 7 years retention
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")
            # Don't raise exception here to avoid breaking the main operation


# DynamoDB Table Schemas for RBAC

RBAC_USERS_TABLE_SCHEMA = {
    "TableName": "rbac-users",
    "KeySchema": [
        {
            "AttributeName": "user_id",
            "KeyType": "HASH"
        }
    ],
    "AttributeDefinitions": [
        {
            "AttributeName": "user_id",
            "AttributeType": "S"
        },
        {
            "AttributeName": "email",
            "AttributeType": "S"
        },
        {
            "AttributeName": "tenant_id",
            "AttributeType": "S"
        },
        {
            "AttributeName": "created_at",
            "AttributeType": "S"
        }
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "email-tenant-index",
            "KeySchema": [
                {
                    "AttributeName": "email",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "tenant_id",
                    "KeyType": "RANGE"
                }
            ],
            "Projection": {
                "ProjectionType": "ALL"
            },
            "BillingMode": "PAY_PER_REQUEST"
        },
        {
            "IndexName": "tenant-created-index",
            "KeySchema": [
                {
                    "AttributeName": "tenant_id",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "created_at",
                    "KeyType": "RANGE"
                }
            ],
            "Projection": {
                "ProjectionType": "ALL"
            },
            "BillingMode": "PAY_PER_REQUEST"
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
            "Value": "rbac"
        }
    ]
}

RBAC_AUDIT_LOGS_TABLE_SCHEMA = {
    "TableName": "rbac-audit-logs",
    "KeySchema": [
        {
            "AttributeName": "log_id",
            "KeyType": "HASH"
        }
    ],
    "AttributeDefinitions": [
        {
            "AttributeName": "log_id",
            "AttributeType": "S"
        },
        {
            "AttributeName": "tenant_id",
            "AttributeType": "S"
        },
        {
            "AttributeName": "timestamp",
            "AttributeType": "S"
        }
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "tenant-timestamp-index",
            "KeySchema": [
                {
                    "AttributeName": "tenant_id",
                    "KeyType": "HASH"
                },
                {
                    "AttributeName": "timestamp",
                    "KeyType": "RANGE"
                }
            ],
            "Projection": {
                "ProjectionType": "ALL"
            },
            "BillingMode": "PAY_PER_REQUEST"
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
            "Value": "rbac"
        }
    ]
}