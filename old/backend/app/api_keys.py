# app/api_keys.py

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from .models import APIKey, User, db
from .security import enhanced_token_required, admin_required, api_key_manager, rate_limit
import logging

logger = logging.getLogger(__name__)

api_keys_bp = Blueprint('api_keys_bp', __name__, url_prefix='/api/v1/api-keys')

@api_keys_bp.route('', methods=['POST'])
@rate_limit(limit=10, window=3600, per='user')  # 10 API key creations per hour per user
@admin_required
def create_api_key(current_user):
    """
    Create a new API key for external integrations.
    Only ADMIN users can create API keys.
    """
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Missing required field: name'}), 400
    
    # Validate input
    key_name = data.get('name', '').strip()
    if not key_name or len(key_name) < 3:
        return jsonify({'error': 'API key name must be at least 3 characters long'}), 400
    
    # Check for duplicate names within the organization
    existing_key = APIKey.query.filter_by(
        organization_id=current_user.organization_id,
        key_name=key_name,
        is_active=True
    ).first()
    
    if existing_key:
        return jsonify({'error': 'An active API key with this name already exists'}), 409
    
    # Parse optional fields
    permissions = data.get('permissions', ['read:costs', 'read:accounts'])
    scopes = data.get('scopes', ['organization'])
    expires_in_days = data.get('expires_in_days')
    rate_limit_per_hour = data.get('rate_limit_per_hour', 1000)
    rate_limit_per_day = data.get('rate_limit_per_day', 10000)
    
    # Validate permissions
    valid_permissions = [
        'read:costs', 'read:accounts', 'read:alarms', 'read:reports',
        'write:alarms', 'write:accounts'
    ]
    
    invalid_permissions = [p for p in permissions if p not in valid_permissions]
    if invalid_permissions:
        return jsonify({
            'error': 'Invalid permissions',
            'invalid_permissions': invalid_permissions,
            'valid_permissions': valid_permissions
        }), 400
    
    # Validate scopes
    valid_scopes = ['organization', 'account']
    invalid_scopes = [s for s in scopes if s not in valid_scopes]
    if invalid_scopes:
        return jsonify({
            'error': 'Invalid scopes',
            'invalid_scopes': invalid_scopes,
            'valid_scopes': valid_scopes
        }), 400
    
    # Validate rate limits
    if rate_limit_per_hour < 1 or rate_limit_per_hour > 10000:
        return jsonify({'error': 'Rate limit per hour must be between 1 and 10000'}), 400
    
    if rate_limit_per_day < 1 or rate_limit_per_day > 100000:
        return jsonify({'error': 'Rate limit per day must be between 1 and 100000'}), 400
    
    try:
        # Generate API key pair
        key_id, key_secret = api_key_manager.generate_api_key()
        secret_hash = api_key_manager.hash_secret(key_secret)
        
        # Calculate expiration date
        expires_at = None
        if expires_in_days:
            if expires_in_days < 1 or expires_in_days > 365:
                return jsonify({'error': 'Expiration must be between 1 and 365 days'}), 400
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create API key record
        api_key = APIKey(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            key_id=key_id,
            key_name=key_name,
            secret_hash=secret_hash,
            permissions=permissions,
            scopes=scopes,
            expires_at=expires_at,
            rate_limit_per_hour=rate_limit_per_hour,
            rate_limit_per_day=rate_limit_per_day,
            created_by_ip=request.remote_addr
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        logger.info(f"API key '{key_name}' created by user {current_user.email} for organization {current_user.organization_id}")
        
        # Return the API key (secret is only shown once)
        return jsonify({
            'message': 'API key created successfully',
            'api_key': {
                'key_id': key_id,
                'key_secret': key_secret,  # Only returned once!
                'name': key_name,
                'permissions': permissions,
                'scopes': scopes,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'rate_limit_per_hour': rate_limit_per_hour,
                'rate_limit_per_day': rate_limit_per_day,
                'created_at': api_key.created_at.isoformat()
            },
            'warning': 'Store the key_secret securely. It will not be shown again.'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating API key: {e}")
        return jsonify({'error': 'Failed to create API key'}), 500

@api_keys_bp.route('', methods=['GET'])
@rate_limit(limit=100, window=3600, per='user')
@enhanced_token_required(roles=['ADMIN'])
def list_api_keys(current_user):
    """
    List all API keys for the current organization.
    Only ADMIN users can list API keys.
    """
    try:
        # Query API keys for the organization
        api_keys = APIKey.query.filter_by(
            organization_id=current_user.organization_id
        ).order_by(APIKey.created_at.desc()).all()
        
        # Convert to list of dictionaries
        keys_data = []
        for key in api_keys:
            key_data = key.to_dict()
            # Add creator information
            creator = User.query.get(key.user_id)
            key_data['created_by'] = {
                'id': creator.id,
                'email': creator.email
            } if creator else None
            
            keys_data.append(key_data)
        
        return jsonify({
            'api_keys': keys_data,
            'total': len(keys_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        return jsonify({'error': 'Failed to list API keys'}), 500

@api_keys_bp.route('/<key_id>', methods=['GET'])
@rate_limit(limit=100, window=3600, per='user')
@enhanced_token_required(roles=['ADMIN'])
def get_api_key(current_user, key_id):
    """
    Get details of a specific API key.
    Only ADMIN users can view API key details.
    """
    try:
        # Find the API key
        api_key = APIKey.query.filter_by(
            key_id=key_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Get detailed information
        key_data = api_key.to_dict()
        
        # Add creator information
        creator = User.query.get(api_key.user_id)
        key_data['created_by'] = {
            'id': creator.id,
            'email': creator.email
        } if creator else None
        
        # Add revocation information if applicable
        if api_key.revoked_by_user_id:
            revoker = User.query.get(api_key.revoked_by_user_id)
            key_data['revoked_by'] = {
                'id': revoker.id,
                'email': revoker.email
            } if revoker else None
        
        return jsonify({'api_key': key_data}), 200
        
    except Exception as e:
        logger.error(f"Error getting API key {key_id}: {e}")
        return jsonify({'error': 'Failed to get API key'}), 500

@api_keys_bp.route('/<key_id>', methods=['PUT'])
@rate_limit(limit=50, window=3600, per='user')
@enhanced_token_required(roles=['ADMIN'])
def update_api_key(current_user, key_id):
    """
    Update an API key's properties.
    Only ADMIN users can update API keys.
    """
    try:
        # Find the API key
        api_key = APIKey.query.filter_by(
            key_id=key_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed fields
        if 'name' in data:
            new_name = data['name'].strip()
            if not new_name or len(new_name) < 3:
                return jsonify({'error': 'API key name must be at least 3 characters long'}), 400
            
            # Check for duplicate names
            existing_key = APIKey.query.filter_by(
                organization_id=current_user.organization_id,
                key_name=new_name,
                is_active=True
            ).filter(APIKey.id != api_key.id).first()
            
            if existing_key:
                return jsonify({'error': 'An active API key with this name already exists'}), 409
            
            api_key.key_name = new_name
        
        if 'permissions' in data:
            valid_permissions = [
                'read:costs', 'read:accounts', 'read:alarms', 'read:reports',
                'write:alarms', 'write:accounts'
            ]
            
            invalid_permissions = [p for p in data['permissions'] if p not in valid_permissions]
            if invalid_permissions:
                return jsonify({
                    'error': 'Invalid permissions',
                    'invalid_permissions': invalid_permissions,
                    'valid_permissions': valid_permissions
                }), 400
            
            api_key.permissions = data['permissions']
        
        if 'scopes' in data:
            valid_scopes = ['organization', 'account']
            invalid_scopes = [s for s in data['scopes'] if s not in valid_scopes]
            if invalid_scopes:
                return jsonify({
                    'error': 'Invalid scopes',
                    'invalid_scopes': invalid_scopes,
                    'valid_scopes': valid_scopes
                }), 400
            
            api_key.scopes = data['scopes']
        
        if 'rate_limit_per_hour' in data:
            rate_limit = data['rate_limit_per_hour']
            if rate_limit < 1 or rate_limit > 10000:
                return jsonify({'error': 'Rate limit per hour must be between 1 and 10000'}), 400
            api_key.rate_limit_per_hour = rate_limit
        
        if 'rate_limit_per_day' in data:
            rate_limit = data['rate_limit_per_day']
            if rate_limit < 1 or rate_limit > 100000:
                return jsonify({'error': 'Rate limit per day must be between 1 and 100000'}), 400
            api_key.rate_limit_per_day = rate_limit
        
        db.session.commit()
        
        logger.info(f"API key '{api_key.key_name}' updated by user {current_user.email}")
        
        return jsonify({
            'message': 'API key updated successfully',
            'api_key': api_key.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating API key {key_id}: {e}")
        return jsonify({'error': 'Failed to update API key'}), 500

@api_keys_bp.route('/<key_id>/revoke', methods=['POST'])
@rate_limit(limit=50, window=3600, per='user')
@enhanced_token_required(roles=['ADMIN'])
def revoke_api_key(current_user, key_id):
    """
    Revoke an API key.
    Only ADMIN users can revoke API keys.
    """
    try:
        # Find the API key
        api_key = APIKey.query.filter_by(
            key_id=key_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        if not api_key.is_active:
            return jsonify({'error': 'API key is already revoked'}), 400
        
        data = request.get_json() or {}
        reason = data.get('reason', 'Revoked by administrator')
        
        # Revoke the API key
        api_key.revoke(current_user.id, reason)
        
        logger.info(f"API key '{api_key.key_name}' revoked by user {current_user.email}. Reason: {reason}")
        
        return jsonify({
            'message': 'API key revoked successfully',
            'api_key': api_key.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error revoking API key {key_id}: {e}")
        return jsonify({'error': 'Failed to revoke API key'}), 500

@api_keys_bp.route('/<key_id>/regenerate', methods=['POST'])
@rate_limit(limit=5, window=3600, per='user')  # Very limited regeneration
@enhanced_token_required(roles=['ADMIN'])
def regenerate_api_key(current_user, key_id):
    """
    Regenerate the secret for an API key.
    Only ADMIN users can regenerate API keys.
    """
    try:
        # Find the API key
        api_key = APIKey.query.filter_by(
            key_id=key_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        if not api_key.is_active:
            return jsonify({'error': 'Cannot regenerate revoked API key'}), 400
        
        # Generate new secret
        _, new_secret = api_key_manager.generate_api_key()
        new_secret_hash = api_key_manager.hash_secret(new_secret)
        
        # Update the API key
        api_key.secret_hash = new_secret_hash
        api_key.usage_count = 0  # Reset usage count
        api_key.last_used_at = None  # Reset last used
        
        db.session.commit()
        
        logger.info(f"API key '{api_key.key_name}' secret regenerated by user {current_user.email}")
        
        return jsonify({
            'message': 'API key secret regenerated successfully',
            'api_key': {
                'key_id': api_key.key_id,
                'key_secret': new_secret,  # Only returned once!
                'name': api_key.key_name
            },
            'warning': 'Store the new key_secret securely. It will not be shown again.'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error regenerating API key {key_id}: {e}")
        return jsonify({'error': 'Failed to regenerate API key'}), 500