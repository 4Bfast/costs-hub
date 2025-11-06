"""
Feature Flag Manager

This module manages feature flags for gradual rollout of new functionality
and client migration control.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import json
import boto3
from botocore.exceptions import ClientError
from enum import Enum


logger = logging.getLogger(__name__)


class FeatureFlag(Enum):
    """Available feature flags."""
    USE_NEW_API = "use_new_api"
    MULTI_CLOUD_SUPPORT = "multi_cloud_support"
    AI_INSIGHTS = "ai_insights"
    ANOMALY_DETECTION = "anomaly_detection"
    ADVANCED_FORECASTING = "advanced_forecasting"
    REAL_TIME_MONITORING = "real_time_monitoring"
    ENHANCED_REPORTING = "enhanced_reporting"
    MIGRATION_MODE = "migration_mode"


class RolloutStrategy(Enum):
    """Feature rollout strategies."""
    ALL_USERS = "all_users"
    PERCENTAGE = "percentage"
    WHITELIST = "whitelist"
    GRADUAL = "gradual"
    BETA_USERS = "beta_users"


class FeatureFlagManager:
    """
    Manages feature flags for controlling new functionality rollout.
    """
    
    def __init__(self, dynamodb_table_name: str = "feature-flags"):
        """
        Initialize the feature flag manager.
        
        Args:
            dynamodb_table_name: Name of the DynamoDB table storing feature flags
        """
        self.table_name = dynamodb_table_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(dynamodb_table_name)
        
        # Cache for feature flags
        self._cache = {}
        self._cache_expiry = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Default feature flag configurations
        self.default_flags = {
            FeatureFlag.USE_NEW_API: {
                'enabled': False,
                'strategy': RolloutStrategy.PERCENTAGE,
                'percentage': 0,
                'whitelist': [],
                'description': 'Enable new multi-cloud API for clients'
            },
            FeatureFlag.MULTI_CLOUD_SUPPORT: {
                'enabled': False,
                'strategy': RolloutStrategy.BETA_USERS,
                'percentage': 0,
                'whitelist': [],
                'description': 'Enable multi-cloud provider support'
            },
            FeatureFlag.AI_INSIGHTS: {
                'enabled': False,
                'strategy': RolloutStrategy.GRADUAL,
                'percentage': 10,
                'whitelist': [],
                'description': 'Enable AI-powered cost insights'
            },
            FeatureFlag.ANOMALY_DETECTION: {
                'enabled': True,
                'strategy': RolloutStrategy.ALL_USERS,
                'percentage': 100,
                'whitelist': [],
                'description': 'Enable cost anomaly detection'
            },
            FeatureFlag.ADVANCED_FORECASTING: {
                'enabled': False,
                'strategy': RolloutStrategy.PERCENTAGE,
                'percentage': 25,
                'whitelist': [],
                'description': 'Enable advanced ML-based forecasting'
            },
            FeatureFlag.REAL_TIME_MONITORING: {
                'enabled': False,
                'strategy': RolloutStrategy.WHITELIST,
                'percentage': 0,
                'whitelist': [],
                'description': 'Enable real-time cost monitoring'
            },
            FeatureFlag.ENHANCED_REPORTING: {
                'enabled': True,
                'strategy': RolloutStrategy.ALL_USERS,
                'percentage': 100,
                'whitelist': [],
                'description': 'Enable enhanced reporting features'
            },
            FeatureFlag.MIGRATION_MODE: {
                'enabled': True,
                'strategy': RolloutStrategy.ALL_USERS,
                'percentage': 100,
                'whitelist': [],
                'description': 'Enable migration mode for backward compatibility'
            }
        }
    
    async def is_feature_enabled(
        self,
        feature: FeatureFlag,
        client_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Check if a feature is enabled for a specific client/user.
        
        Args:
            feature: The feature flag to check
            client_id: Client identifier
            user_id: Optional user identifier
            
        Returns:
            True if feature is enabled, False otherwise
        """
        try:
            flag_config = await self._get_feature_flag(feature)
            
            if not flag_config.get('enabled', False):
                return False
            
            strategy = RolloutStrategy(flag_config.get('strategy', RolloutStrategy.ALL_USERS.value))
            
            if strategy == RolloutStrategy.ALL_USERS:
                return True
            
            elif strategy == RolloutStrategy.WHITELIST:
                whitelist = flag_config.get('whitelist', [])
                return client_id in whitelist or (user_id and user_id in whitelist)
            
            elif strategy == RolloutStrategy.PERCENTAGE:
                percentage = flag_config.get('percentage', 0)
                return self._is_in_percentage(client_id, percentage)
            
            elif strategy == RolloutStrategy.GRADUAL:
                return await self._is_gradual_rollout_enabled(feature, client_id)
            
            elif strategy == RolloutStrategy.BETA_USERS:
                return await self._is_beta_user(client_id, user_id)
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking feature flag {feature.value}: {str(e)}")
            return False
    
    async def should_use_new_api(self, client_id: str) -> bool:
        """
        Check if a client should use the new multi-cloud API.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if client should use new API
        """
        return await self.is_feature_enabled(FeatureFlag.USE_NEW_API, client_id)
    
    async def enable_feature_for_client(
        self,
        feature: FeatureFlag,
        client_id: str,
        enabled: bool = True
    ) -> None:
        """
        Enable or disable a feature for a specific client.
        
        Args:
            feature: The feature flag to modify
            client_id: Client identifier
            enabled: Whether to enable or disable the feature
        """
        try:
            # Get current flag configuration
            flag_config = await self._get_feature_flag(feature)
            
            # Update whitelist
            whitelist = set(flag_config.get('whitelist', []))
            
            if enabled:
                whitelist.add(client_id)
            else:
                whitelist.discard(client_id)
            
            flag_config['whitelist'] = list(whitelist)
            
            # If we're adding to whitelist, ensure strategy supports it
            if enabled and flag_config.get('strategy') not in [
                RolloutStrategy.WHITELIST.value,
                RolloutStrategy.BETA_USERS.value
            ]:
                flag_config['strategy'] = RolloutStrategy.WHITELIST.value
            
            # Save updated configuration
            await self._save_feature_flag(feature, flag_config)
            
            # Clear cache
            self._clear_cache(feature)
            
            logger.info(f"Feature {feature.value} {'enabled' if enabled else 'disabled'} for client {client_id}")
        
        except Exception as e:
            logger.error(f"Error updating feature flag {feature.value} for client {client_id}: {str(e)}")
            raise
    
    async def set_feature_percentage(
        self,
        feature: FeatureFlag,
        percentage: int
    ) -> None:
        """
        Set the rollout percentage for a feature.
        
        Args:
            feature: The feature flag to modify
            percentage: Percentage of users to enable (0-100)
        """
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        
        try:
            flag_config = await self._get_feature_flag(feature)
            flag_config['percentage'] = percentage
            flag_config['strategy'] = RolloutStrategy.PERCENTAGE.value
            flag_config['enabled'] = percentage > 0
            
            await self._save_feature_flag(feature, flag_config)
            self._clear_cache(feature)
            
            logger.info(f"Feature {feature.value} set to {percentage}% rollout")
        
        except Exception as e:
            logger.error(f"Error setting percentage for feature {feature.value}: {str(e)}")
            raise
    
    async def get_feature_status(self, feature: FeatureFlag) -> Dict[str, Any]:
        """
        Get the current status of a feature flag.
        
        Args:
            feature: The feature flag to check
            
        Returns:
            Feature flag configuration and status
        """
        try:
            flag_config = await self._get_feature_flag(feature)
            
            # Add runtime statistics
            status = dict(flag_config)
            status['feature'] = feature.value
            status['last_updated'] = flag_config.get('updated_at')
            
            # Calculate estimated user coverage
            if flag_config.get('strategy') == RolloutStrategy.PERCENTAGE.value:
                status['estimated_coverage'] = f"{flag_config.get('percentage', 0)}%"
            elif flag_config.get('strategy') == RolloutStrategy.WHITELIST.value:
                status['estimated_coverage'] = f"{len(flag_config.get('whitelist', []))} clients"
            elif flag_config.get('strategy') == RolloutStrategy.ALL_USERS.value:
                status['estimated_coverage'] = "100%"
            else:
                status['estimated_coverage'] = "Variable"
            
            return status
        
        except Exception as e:
            logger.error(f"Error getting feature status for {feature.value}: {str(e)}")
            return {'error': str(e)}
    
    async def list_all_features(self) -> Dict[str, Dict[str, Any]]:
        """
        List all feature flags and their current status.
        
        Returns:
            Dictionary of all feature flags and their configurations
        """
        features = {}
        
        for feature in FeatureFlag:
            features[feature.value] = await self.get_feature_status(feature)
        
        return features
    
    async def migrate_client_to_new_api(self, client_id: str) -> Dict[str, Any]:
        """
        Migrate a specific client to the new API.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Migration status and next steps
        """
        try:
            # Enable new API for this client
            await self.enable_feature_for_client(FeatureFlag.USE_NEW_API, client_id, True)
            
            # Enable related features
            await self.enable_feature_for_client(FeatureFlag.MULTI_CLOUD_SUPPORT, client_id, True)
            await self.enable_feature_for_client(FeatureFlag.AI_INSIGHTS, client_id, True)
            
            # Log migration
            migration_record = {
                'client_id': client_id,
                'migrated_at': datetime.utcnow().isoformat(),
                'features_enabled': [
                    FeatureFlag.USE_NEW_API.value,
                    FeatureFlag.MULTI_CLOUD_SUPPORT.value,
                    FeatureFlag.AI_INSIGHTS.value
                ],
                'migration_status': 'completed'
            }
            
            await self._log_migration(migration_record)
            
            return {
                'status': 'success',
                'message': f'Client {client_id} successfully migrated to new API',
                'features_enabled': migration_record['features_enabled'],
                'next_steps': [
                    'Update API endpoints to v2',
                    'Test multi-cloud functionality',
                    'Enable additional AI features as needed'
                ]
            }
        
        except Exception as e:
            logger.error(f"Error migrating client {client_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to migrate client {client_id}: {str(e)}'
            }
    
    async def _get_feature_flag(self, feature: FeatureFlag) -> Dict[str, Any]:
        """Get feature flag configuration from cache or database."""
        # Check cache first
        if feature in self._cache:
            if datetime.utcnow() < self._cache_expiry.get(feature, datetime.min):
                return self._cache[feature]
        
        try:
            # Get from database
            response = self.table.get_item(
                Key={'feature_name': feature.value}
            )
            
            if 'Item' in response:
                flag_config = response['Item']
                # Remove DynamoDB-specific fields
                flag_config.pop('feature_name', None)
            else:
                # Use default configuration
                flag_config = self.default_flags.get(feature, {})
                # Save default to database
                await self._save_feature_flag(feature, flag_config)
            
            # Cache the result
            self._cache[feature] = flag_config
            self._cache_expiry[feature] = datetime.utcnow() + timedelta(seconds=self._cache_ttl)
            
            return flag_config
        
        except ClientError as e:
            logger.error(f"Error getting feature flag {feature.value} from database: {str(e)}")
            # Return default configuration
            return self.default_flags.get(feature, {})
    
    async def _save_feature_flag(self, feature: FeatureFlag, config: Dict[str, Any]) -> None:
        """Save feature flag configuration to database."""
        try:
            item = dict(config)
            item['feature_name'] = feature.value
            item['updated_at'] = datetime.utcnow().isoformat()
            
            self.table.put_item(Item=item)
        
        except ClientError as e:
            logger.error(f"Error saving feature flag {feature.value}: {str(e)}")
            raise
    
    def _clear_cache(self, feature: FeatureFlag) -> None:
        """Clear cache for a specific feature flag."""
        self._cache.pop(feature, None)
        self._cache_expiry.pop(feature, None)
    
    def _is_in_percentage(self, client_id: str, percentage: int) -> bool:
        """Determine if client is in the percentage rollout."""
        if percentage == 0:
            return False
        if percentage == 100:
            return True
        
        # Use hash of client_id to determine inclusion
        hash_value = hash(client_id) % 100
        return hash_value < percentage
    
    async def _is_gradual_rollout_enabled(self, feature: FeatureFlag, client_id: str) -> bool:
        """Check if gradual rollout is enabled for client."""
        # Gradual rollout increases percentage over time
        flag_config = await self._get_feature_flag(feature)
        base_percentage = flag_config.get('percentage', 0)
        
        # Increase percentage by 10% each week (example logic)
        created_at = flag_config.get('created_at')
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at)
                weeks_since_creation = (datetime.utcnow() - created_date).days // 7
                current_percentage = min(base_percentage + (weeks_since_creation * 10), 100)
                return self._is_in_percentage(client_id, current_percentage)
            except ValueError:
                pass
        
        return self._is_in_percentage(client_id, base_percentage)
    
    async def _is_beta_user(self, client_id: str, user_id: Optional[str] = None) -> bool:
        """Check if client/user is a beta user."""
        # This would integrate with user management system
        # For now, check if client is in beta whitelist
        flag_config = await self._get_feature_flag(FeatureFlag.USE_NEW_API)
        beta_users = flag_config.get('beta_users', [])
        return client_id in beta_users or (user_id and user_id in beta_users)
    
    async def _log_migration(self, migration_record: Dict[str, Any]) -> None:
        """Log client migration for audit purposes."""
        try:
            # This would typically go to a separate audit table
            logger.info(f"Client migration logged: {json.dumps(migration_record)}")
        except Exception as e:
            logger.error(f"Error logging migration: {str(e)}")
    
    async def create_feature_flag_table(self) -> None:
        """Create the DynamoDB table for feature flags (for setup)."""
        try:
            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'feature_name',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'feature_name',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            
            logger.info(f"Feature flags table {self.table_name} created successfully")
        
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"Feature flags table {self.table_name} already exists")
            else:
                logger.error(f"Error creating feature flags table: {str(e)}")
                raise