"""
API Key Management Service

This service provides comprehensive API key management functionality
including creation, validation, rotation, and access control.
"""

import boto3
import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from enum import Enum

from ..models.multi_tenant_models import ClientRole
from ..services.rbac_service import Permission
from ..utils.api_response import ValidationError, NotFoundError


logger = logging.getLogger(__name__)


class APIKeyStatus(Enum):
    """API key status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class APIKeyInfo:
    """API key information structure."""
    key_id: str
    name: str
    description: str
    user_id: str
    tenant_id: str
    permissions: List[str]
    status: APIKeyStatus
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    rate_limit: Optional[int] = None
    allowed_ips: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'key_id': self.key_id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'permissions': self.permissions,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'usage_count': self.usage_count,
            'rate_limit': self.rate_limit,
            'allowed_ips': self.allowed_ips,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIKeyInfo':
        """Create from dictionary representation."""
        return cls(
            key_id=data['key_id'],
            name=data['name'],
            description=data['description'],
            user_id=data['user_id'],
            tenant_id=data['tenant_id'],
            permissions=data['permissions'],
            status=APIKeyStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            last_used_at=datetime.fromisoformat(data['last_used_at']) if data.get('last_used_at') else None,
            usage_count=data.get('usage_count', 0),
            rate_limit=data.get('rate_limit'),
            allowed_ips=data.get('allowed_ips', []),
            metadata=data.get('metadata', {})
        )


class APIKeyManagementService:
    """
    Comprehensive API key management service.
    
    Provides functionality for creating, validating, rotating, and managing
    API keys with fine-grained permissions and security controls.
    """
    
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize the API key management service.
        
        Args:
            table_name: DynamoDB table name for API key storage
            region: AWS region
        """
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        
        # Default settings
        self.default_key_length = 64
        self.default_expiry_days = 365
        self.max_keys_per_user = 50
        self.key_prefix = "mcca_"  # Multi-Cloud Cost Analytics
    
    def create_api_key(self, user_id: str, tenant_id: str, name: str,
                      description: str = "", permissions: List[str] = None,
                      expires_at: Optional[datetime] = None,
                      rate_limit: Optional[int] = None,
                      allowed_ips: List[str] = None,
                      metadata: Dict[str, Any] = None) -> Tuple[str, str]:
        """
        Create a new API key.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            name: API key name
            description: API key description
            permissions: List of permissions
            expires_at: Optional expiration date
            rate_limit: Optional rate limit (requests per hour)
            allowed_ips: Optional list of allowed IP addresses
            metadata: Optional metadata dictionary
            
        Returns:
            Tuple of (key_id, key_secret)
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate inputs
        self._validate_create_request(user_id, tenant_id, name, permissions)
        
        # Check user's API key limit
        existing_keys = self.list_user_api_keys(user_id)
        active_keys = [k for k in existing_keys if k.status == APIKeyStatus.ACTIVE]
        
        if len(active_keys) >= self.max_keys_per_user:
            raise ValidationError(f"Maximum number of API keys ({self.max_keys_per_user}) reached")
        
        # Generate key components
        key_id = self._generate_key_id()
        key_secret = self._generate_key_secret()
        key_hash = self._hash_key_secret(key_secret)
        
        # Set default expiration if not provided
        if not expires_at:
            expires_at = datetime.utcnow() + timedelta(days=self.default_expiry_days)
        
        # Create API key info
        api_key_info = APIKeyInfo(
            key_id=key_id,
            name=name,
            description=description or "",
            user_id=user_id,
            tenant_id=tenant_id,
            permissions=permissions or [],
            status=APIKeyStatus.ACTIVE,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            rate_limit=rate_limit,
            allowed_ips=allowed_ips or [],
            metadata=metadata or {}
        )
        
        # Store in DynamoDB
        try:
            self.table.put_item(
                Item={
                    'PK': f"APIKEY#{key_id}",
                    'SK': f"INFO#{key_id}",
                    'GSI1PK': f"USER#{user_id}",
                    'GSI1SK': f"APIKEY#{key_id}",
                    'GSI2PK': f"TENANT#{tenant_id}",
                    'GSI2SK': f"APIKEY#{key_id}",
                    'key_id': key_id,
                    'key_hash': key_hash,
                    'name': name,
                    'description': description,
                    'user_id': user_id,
                    'tenant_id': tenant_id,
                    'permissions': permissions or [],
                    'status': api_key_info.status.value,
                    'created_at': api_key_info.created_at.isoformat(),
                    'expires_at': expires_at.isoformat() if expires_at else None,
                    'rate_limit': rate_limit,
                    'allowed_ips': allowed_ips or [],
                    'metadata': metadata or {},
                    'usage_count': 0,
                    'ttl': int(expires_at.timestamp()) + 86400 if expires_at else None
                }
            )
            
            logger.info(f"Created API key {key_id} for user {user_id}")
            return key_id, key_secret
            
        except ClientError as e:
            logger.error(f"Failed to create API key: {e}")
            raise ValidationError("Failed to create API key")
    
    def validate_api_key(self, key_id: str, key_secret: str, 
                        client_ip: Optional[str] = None) -> APIKeyInfo:
        """
        Validate an API key.
        
        Args:
            key_id: API key identifier
            key_secret: API key secret
            client_ip: Optional client IP address for validation
            
        Returns:
            APIKeyInfo object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Get API key from database
            response = self.table.get_item(
                Key={
                    'PK': f"APIKEY#{key_id}",
                    'SK': f"INFO#{key_id}"
                }
            )
            
            if 'Item' not in response:
                raise ValidationError("Invalid API key")
            
            item = response['Item']
            
            # Verify key secret
            stored_hash = item.get('key_hash')
            if not self._verify_key_secret(key_secret, stored_hash):
                raise ValidationError("Invalid API key secret")
            
            # Create APIKeyInfo object
            api_key_info = APIKeyInfo(
                key_id=item['key_id'],
                name=item['name'],
                description=item['description'],
                user_id=item['user_id'],
                tenant_id=item['tenant_id'],
                permissions=item.get('permissions', []),
                status=APIKeyStatus(item['status']),
                created_at=datetime.fromisoformat(item['created_at']),
                expires_at=datetime.fromisoformat(item['expires_at']) if item.get('expires_at') else None,
                last_used_at=datetime.fromisoformat(item['last_used_at']) if item.get('last_used_at') else None,
                usage_count=item.get('usage_count', 0),
                rate_limit=item.get('rate_limit'),
                allowed_ips=item.get('allowed_ips', []),
                metadata=item.get('metadata', {})
            )
            
            # Validate API key status
            if api_key_info.status != APIKeyStatus.ACTIVE:
                raise ValidationError(f"API key is {api_key_info.status.value}")
            
            # Check expiration
            if api_key_info.expires_at and datetime.utcnow() > api_key_info.expires_at:
                # Update status to expired
                self._update_key_status(key_id, APIKeyStatus.EXPIRED)
                raise ValidationError("API key has expired")
            
            # Validate IP address if restricted
            if api_key_info.allowed_ips and client_ip:
                if client_ip not in api_key_info.allowed_ips:
                    raise ValidationError(f"API key not allowed from IP {client_ip}")
            
            # Update usage statistics
            self._update_key_usage(key_id)
            
            return api_key_info
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            raise ValidationError("API key validation failed")
    
    def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: API key identifier
            user_id: User identifier (for authorization)
            
        Returns:
            True if revocation was successful
            
        Raises:
            NotFoundError: If API key not found
            ValidationError: If user doesn't own the key
        """
        try:
            # Get API key to verify ownership
            api_key_info = self.get_api_key_info(key_id)
            
            if api_key_info.user_id != user_id:
                raise ValidationError("You don't have permission to revoke this API key")
            
            # Update status to revoked
            success = self._update_key_status(key_id, APIKeyStatus.REVOKED)
            
            if success:
                logger.info(f"Revoked API key {key_id} for user {user_id}")
            
            return success
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to revoke API key {key_id}: {e}")
            return False
    
    def rotate_api_key(self, key_id: str, user_id: str) -> Tuple[str, str]:
        """
        Rotate an API key (generate new secret).
        
        Args:
            key_id: API key identifier
            user_id: User identifier (for authorization)
            
        Returns:
            Tuple of (key_id, new_key_secret)
            
        Raises:
            NotFoundError: If API key not found
            ValidationError: If user doesn't own the key
        """
        try:
            # Get API key to verify ownership
            api_key_info = self.get_api_key_info(key_id)
            
            if api_key_info.user_id != user_id:
                raise ValidationError("You don't have permission to rotate this API key")
            
            if api_key_info.status != APIKeyStatus.ACTIVE:
                raise ValidationError(f"Cannot rotate {api_key_info.status.value} API key")
            
            # Generate new secret
            new_secret = self._generate_key_secret()
            new_hash = self._hash_key_secret(new_secret)
            
            # Update the key with new hash
            self.table.update_item(
                Key={
                    'PK': f"APIKEY#{key_id}",
                    'SK': f"INFO#{key_id}"
                },
                UpdateExpression='SET key_hash = :hash, last_rotated_at = :now',
                ExpressionAttributeValues={
                    ':hash': new_hash,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Rotated API key {key_id} for user {user_id}")
            return key_id, new_secret
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to rotate API key {key_id}: {e}")
            raise ValidationError("Failed to rotate API key")
    
    def get_api_key_info(self, key_id: str) -> APIKeyInfo:
        """
        Get API key information.
        
        Args:
            key_id: API key identifier
            
        Returns:
            APIKeyInfo object
            
        Raises:
            NotFoundError: If API key not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': f"APIKEY#{key_id}",
                    'SK': f"INFO#{key_id}"
                }
            )
            
            if 'Item' not in response:
                raise NotFoundError("API key not found")
            
            item = response['Item']
            
            return APIKeyInfo(
                key_id=item['key_id'],
                name=item['name'],
                description=item['description'],
                user_id=item['user_id'],
                tenant_id=item['tenant_id'],
                permissions=item.get('permissions', []),
                status=APIKeyStatus(item['status']),
                created_at=datetime.fromisoformat(item['created_at']),
                expires_at=datetime.fromisoformat(item['expires_at']) if item.get('expires_at') else None,
                last_used_at=datetime.fromisoformat(item['last_used_at']) if item.get('last_used_at') else None,
                usage_count=item.get('usage_count', 0),
                rate_limit=item.get('rate_limit'),
                allowed_ips=item.get('allowed_ips', []),
                metadata=item.get('metadata', {})
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get API key info: {e}")
            raise NotFoundError("API key not found")
    
    def list_user_api_keys(self, user_id: str, status_filter: Optional[APIKeyStatus] = None) -> List[APIKeyInfo]:
        """
        List API keys for a user.
        
        Args:
            user_id: User identifier
            status_filter: Optional status filter
            
        Returns:
            List of APIKeyInfo objects
        """
        try:
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f"USER#{user_id}"
                }
            )
            
            api_keys = []
            for item in response['Items']:
                api_key_info = APIKeyInfo(
                    key_id=item['key_id'],
                    name=item['name'],
                    description=item['description'],
                    user_id=item['user_id'],
                    tenant_id=item['tenant_id'],
                    permissions=item.get('permissions', []),
                    status=APIKeyStatus(item['status']),
                    created_at=datetime.fromisoformat(item['created_at']),
                    expires_at=datetime.fromisoformat(item['expires_at']) if item.get('expires_at') else None,
                    last_used_at=datetime.fromisoformat(item['last_used_at']) if item.get('last_used_at') else None,
                    usage_count=item.get('usage_count', 0),
                    rate_limit=item.get('rate_limit'),
                    allowed_ips=item.get('allowed_ips', []),
                    metadata=item.get('metadata', {})
                )
                
                # Apply status filter if specified
                if status_filter is None or api_key_info.status == status_filter:
                    api_keys.append(api_key_info)
            
            return api_keys
            
        except Exception as e:
            logger.error(f"Failed to list API keys for user {user_id}: {e}")
            return []
    
    def list_tenant_api_keys(self, tenant_id: str) -> List[APIKeyInfo]:
        """
        List all API keys for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of APIKeyInfo objects
        """
        try:
            response = self.table.query(
                IndexName='GSI2',
                KeyConditionExpression='GSI2PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f"TENANT#{tenant_id}"
                }
            )
            
            api_keys = []
            for item in response['Items']:
                api_key_info = APIKeyInfo(
                    key_id=item['key_id'],
                    name=item['name'],
                    description=item['description'],
                    user_id=item['user_id'],
                    tenant_id=item['tenant_id'],
                    permissions=item.get('permissions', []),
                    status=APIKeyStatus(item['status']),
                    created_at=datetime.fromisoformat(item['created_at']),
                    expires_at=datetime.fromisoformat(item['expires_at']) if item.get('expires_at') else None,
                    last_used_at=datetime.fromisoformat(item['last_used_at']) if item.get('last_used_at') else None,
                    usage_count=item.get('usage_count', 0),
                    rate_limit=item.get('rate_limit'),
                    allowed_ips=item.get('allowed_ips', []),
                    metadata=item.get('metadata', {})
                )
                api_keys.append(api_key_info)
            
            return api_keys
            
        except Exception as e:
            logger.error(f"Failed to list API keys for tenant {tenant_id}: {e}")
            return []
    
    def update_api_key(self, key_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update API key properties.
        
        Args:
            key_id: API key identifier
            user_id: User identifier (for authorization)
            updates: Dictionary of updates to apply
            
        Returns:
            True if update was successful
            
        Raises:
            NotFoundError: If API key not found
            ValidationError: If user doesn't own the key or updates are invalid
        """
        try:
            # Get API key to verify ownership
            api_key_info = self.get_api_key_info(key_id)
            
            if api_key_info.user_id != user_id:
                raise ValidationError("You don't have permission to update this API key")
            
            # Validate allowed updates
            allowed_fields = ['name', 'description', 'rate_limit', 'allowed_ips', 'metadata']
            update_expression_parts = []
            expression_values = {}
            
            for field, value in updates.items():
                if field not in allowed_fields:
                    raise ValidationError(f"Field '{field}' cannot be updated")
                
                update_expression_parts.append(f"{field} = :{field}")
                expression_values[f":{field}"] = value
            
            if not update_expression_parts:
                raise ValidationError("No valid updates provided")
            
            # Add updated timestamp
            update_expression_parts.append("updated_at = :updated_at")
            expression_values[":updated_at"] = datetime.utcnow().isoformat()
            
            # Perform update
            self.table.update_item(
                Key={
                    'PK': f"APIKEY#{key_id}",
                    'SK': f"INFO#{key_id}"
                },
                UpdateExpression=f"SET {', '.join(update_expression_parts)}",
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"Updated API key {key_id} for user {user_id}")
            return True
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to update API key {key_id}: {e}")
            return False
    
    def cleanup_expired_keys(self) -> int:
        """
        Clean up expired API keys.
        
        Returns:
            Number of keys cleaned up
        """
        try:
            current_time = datetime.utcnow()
            cleaned_count = 0
            
            # Scan for expired keys
            response = self.table.scan(
                FilterExpression='expires_at < :current_time AND #status = :active',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':current_time': current_time.isoformat(),
                    ':active': APIKeyStatus.ACTIVE.value
                }
            )
            
            # Update expired keys
            for item in response['Items']:
                key_id = item['key_id']
                self._update_key_status(key_id, APIKeyStatus.EXPIRED)
                cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired API keys")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired keys: {e}")
            return 0
    
    def _generate_key_id(self) -> str:
        """Generate a unique API key ID."""
        return f"{self.key_prefix}{secrets.token_urlsafe(16)}"
    
    def _generate_key_secret(self) -> str:
        """Generate a secure API key secret."""
        return secrets.token_urlsafe(self.default_key_length)
    
    def _hash_key_secret(self, secret: str) -> str:
        """Hash an API key secret."""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    def _verify_key_secret(self, secret: str, stored_hash: str) -> bool:
        """Verify an API key secret against its hash."""
        return hashlib.sha256(secret.encode()).hexdigest() == stored_hash
    
    def _update_key_status(self, key_id: str, status: APIKeyStatus) -> bool:
        """Update API key status."""
        try:
            self.table.update_item(
                Key={
                    'PK': f"APIKEY#{key_id}",
                    'SK': f"INFO#{key_id}"
                },
                UpdateExpression='SET #status = :status, updated_at = :now',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': status.value,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            return True
            
        except ClientError as e:
            logger.error(f"Failed to update key status: {e}")
            return False
    
    def _update_key_usage(self, key_id: str):
        """Update API key usage statistics."""
        try:
            self.table.update_item(
                Key={
                    'PK': f"APIKEY#{key_id}",
                    'SK': f"INFO#{key_id}"
                },
                UpdateExpression='SET last_used_at = :now, usage_count = usage_count + :inc',
                ExpressionAttributeValues={
                    ':now': datetime.utcnow().isoformat(),
                    ':inc': 1
                }
            )
        except ClientError as e:
            logger.error(f"Failed to update key usage: {e}")
    
    def _validate_create_request(self, user_id: str, tenant_id: str, 
                                name: str, permissions: List[str]):
        """Validate API key creation request."""
        if not user_id or not user_id.strip():
            raise ValidationError("User ID is required")
        
        if not tenant_id or not tenant_id.strip():
            raise ValidationError("Tenant ID is required")
        
        if not name or not name.strip():
            raise ValidationError("API key name is required")
        
        if len(name) > 100:
            raise ValidationError("API key name must be 100 characters or less")
        
        if permissions:
            # Validate permissions against known permissions
            valid_permissions = [p.value for p in Permission]
            invalid_permissions = [p for p in permissions if p not in valid_permissions]
            if invalid_permissions:
                raise ValidationError(f"Invalid permissions: {', '.join(invalid_permissions)}")


# Permission sets for different API key types
API_KEY_PERMISSION_SETS = {
    'read_only': [
        Permission.COST_DATA_READ.value,
        Permission.AI_INSIGHTS_READ.value,
        Permission.CLIENT_CONFIG_READ.value
    ],
    'analytics': [
        Permission.COST_DATA_READ.value,
        Permission.AI_INSIGHTS_READ.value,
        Permission.AI_INSIGHTS_WRITE.value,
        Permission.CLIENT_CONFIG_READ.value
    ],
    'full_access': [
        Permission.COST_DATA_READ.value,
        Permission.COST_DATA_WRITE.value,
        Permission.AI_INSIGHTS_READ.value,
        Permission.AI_INSIGHTS_WRITE.value,
        Permission.CLIENT_CONFIG_READ.value,
        Permission.CLIENT_CONFIG_WRITE.value,
        Permission.NOTIFICATION_MANAGE.value
    ]
}