"""
Client Migration Manager

This module manages the gradual migration of clients from the legacy system
to the new multi-cloud platform.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import boto3
from botocore.exceptions import ClientError

from .feature_flags import FeatureFlagManager, FeatureFlag
from ..migration.data_migrator import DataMigrator
from ..migration.validation_tools import MigrationValidator


logger = logging.getLogger(__name__)


class MigrationPhase(Enum):
    """Migration phases for clients."""
    NOT_STARTED = "not_started"
    DATA_MIGRATION = "data_migration"
    COMPATIBILITY_MODE = "compatibility_mode"
    FEATURE_TESTING = "feature_testing"
    FULL_MIGRATION = "full_migration"
    COMPLETED = "completed"
    ROLLBACK = "rollback"


class MigrationStatus(Enum):
    """Status of migration operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class ClientMigrationManager:
    """
    Manages the migration of clients from legacy system to multi-cloud platform.
    """
    
    def __init__(
        self,
        feature_flag_manager: FeatureFlagManager,
        data_migrator: DataMigrator,
        migration_validator: MigrationValidator,
        migration_table_name: str = "client-migrations"
    ):
        """
        Initialize the client migration manager.
        
        Args:
            feature_flag_manager: Manager for feature flags
            data_migrator: Data migration service
            migration_validator: Migration validation service
            migration_table_name: DynamoDB table for migration tracking
        """
        self.feature_flags = feature_flag_manager
        self.data_migrator = data_migrator
        self.validator = migration_validator
        self.table_name = migration_table_name
        
        # Initialize DynamoDB
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(migration_table_name)
        
        # Migration configuration
        self.migration_config = {
            'batch_size': 50,
            'validation_threshold': 0.99,  # 99% accuracy required
            'rollback_timeout_hours': 24,
            'max_retry_attempts': 3,
            'notification_endpoints': []
        }
    
    async def start_client_migration(
        self,
        client_id: str,
        migration_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start the migration process for a client.
        
        Args:
            client_id: Client identifier
            migration_options: Optional migration configuration
            
        Returns:
            Migration initiation result
        """
        logger.info(f"Starting migration for client {client_id}")
        
        try:
            # Check if migration is already in progress
            existing_migration = await self._get_migration_record(client_id)
            if existing_migration and existing_migration['status'] in [
                MigrationStatus.IN_PROGRESS.value,
                MigrationStatus.PENDING.value
            ]:
                return {
                    'status': 'error',
                    'message': f'Migration already in progress for client {client_id}',
                    'existing_migration_id': existing_migration['migration_id']
                }
            
            # Create migration record
            migration_record = await self._create_migration_record(client_id, migration_options)
            
            # Start migration phases
            result = await self._execute_migration_phases(client_id, migration_record)
            
            return {
                'status': 'success',
                'migration_id': migration_record['migration_id'],
                'client_id': client_id,
                'current_phase': result['current_phase'],
                'estimated_completion': result['estimated_completion'],
                'next_steps': result['next_steps']
            }
        
        except Exception as e:
            logger.error(f"Error starting migration for client {client_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to start migration: {str(e)}'
            }
    
    async def get_migration_status(self, client_id: str) -> Dict[str, Any]:
        """
        Get the current migration status for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Current migration status and progress
        """
        try:
            migration_record = await self._get_migration_record(client_id)
            
            if not migration_record:
                return {
                    'client_id': client_id,
                    'status': MigrationStatus.PENDING.value,
                    'phase': MigrationPhase.NOT_STARTED.value,
                    'progress_percentage': 0,
                    'message': 'No migration started for this client'
                }
            
            # Calculate progress
            progress = await self._calculate_migration_progress(migration_record)
            
            return {
                'client_id': client_id,
                'migration_id': migration_record['migration_id'],
                'status': migration_record['status'],
                'phase': migration_record['current_phase'],
                'progress_percentage': progress['percentage'],
                'started_at': migration_record['started_at'],
                'estimated_completion': migration_record.get('estimated_completion'),
                'last_updated': migration_record['updated_at'],
                'phases_completed': progress['phases_completed'],
                'total_phases': progress['total_phases'],
                'current_step': migration_record.get('current_step'),
                'errors': migration_record.get('errors', []),
                'warnings': migration_record.get('warnings', [])
            }
        
        except Exception as e:
            logger.error(f"Error getting migration status for client {client_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to get migration status: {str(e)}'
            }
    
    async def pause_migration(self, client_id: str, reason: str) -> Dict[str, Any]:
        """
        Pause an ongoing migration.
        
        Args:
            client_id: Client identifier
            reason: Reason for pausing
            
        Returns:
            Pause operation result
        """
        try:
            migration_record = await self._get_migration_record(client_id)
            
            if not migration_record:
                return {
                    'status': 'error',
                    'message': 'No active migration found for client'
                }
            
            if migration_record['status'] != MigrationStatus.IN_PROGRESS.value:
                return {
                    'status': 'error',
                    'message': f'Cannot pause migration in status: {migration_record["status"]}'
                }
            
            # Update migration record
            await self._update_migration_record(client_id, {
                'status': MigrationStatus.PAUSED.value,
                'paused_at': datetime.utcnow().isoformat(),
                'pause_reason': reason,
                'updated_at': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Migration paused for client {client_id}: {reason}")
            
            return {
                'status': 'success',
                'message': f'Migration paused for client {client_id}',
                'reason': reason
            }
        
        except Exception as e:
            logger.error(f"Error pausing migration for client {client_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to pause migration: {str(e)}'
            }
    
    async def resume_migration(self, client_id: str) -> Dict[str, Any]:
        """
        Resume a paused migration.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Resume operation result
        """
        try:
            migration_record = await self._get_migration_record(client_id)
            
            if not migration_record:
                return {
                    'status': 'error',
                    'message': 'No migration found for client'
                }
            
            if migration_record['status'] != MigrationStatus.PAUSED.value:
                return {
                    'status': 'error',
                    'message': f'Cannot resume migration in status: {migration_record["status"]}'
                }
            
            # Update migration record
            await self._update_migration_record(client_id, {
                'status': MigrationStatus.IN_PROGRESS.value,
                'resumed_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            })
            
            # Continue migration from current phase
            result = await self._execute_migration_phases(client_id, migration_record)
            
            logger.info(f"Migration resumed for client {client_id}")
            
            return {
                'status': 'success',
                'message': f'Migration resumed for client {client_id}',
                'current_phase': result['current_phase']
            }
        
        except Exception as e:
            logger.error(f"Error resuming migration for client {client_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to resume migration: {str(e)}'
            }
    
    async def rollback_migration(
        self,
        client_id: str,
        reason: str,
        target_phase: Optional[MigrationPhase] = None
    ) -> Dict[str, Any]:
        """
        Rollback a migration to a previous phase or completely.
        
        Args:
            client_id: Client identifier
            reason: Reason for rollback
            target_phase: Phase to rollback to (None for complete rollback)
            
        Returns:
            Rollback operation result
        """
        logger.warning(f"Rolling back migration for client {client_id}: {reason}")
        
        try:
            migration_record = await self._get_migration_record(client_id)
            
            if not migration_record:
                return {
                    'status': 'error',
                    'message': 'No migration found for client'
                }
            
            # Perform rollback operations
            rollback_steps = []
            
            current_phase = MigrationPhase(migration_record['current_phase'])
            
            # Disable new features
            if current_phase in [MigrationPhase.FEATURE_TESTING, MigrationPhase.FULL_MIGRATION, MigrationPhase.COMPLETED]:
                await self.feature_flags.enable_feature_for_client(
                    FeatureFlag.USE_NEW_API, client_id, False
                )
                rollback_steps.append("Disabled new API")
            
            # Rollback to compatibility mode if needed
            if target_phase == MigrationPhase.COMPATIBILITY_MODE or target_phase is None:
                await self.feature_flags.enable_feature_for_client(
                    FeatureFlag.MIGRATION_MODE, client_id, True
                )
                rollback_steps.append("Enabled compatibility mode")
            
            # Update migration record
            await self._update_migration_record(client_id, {
                'status': MigrationStatus.ROLLBACK.value,
                'current_phase': target_phase.value if target_phase else MigrationPhase.NOT_STARTED.value,
                'rollback_reason': reason,
                'rollback_at': datetime.utcnow().isoformat(),
                'rollback_steps': rollback_steps,
                'updated_at': datetime.utcnow().isoformat()
            })
            
            return {
                'status': 'success',
                'message': f'Migration rolled back for client {client_id}',
                'reason': reason,
                'rollback_steps': rollback_steps,
                'target_phase': target_phase.value if target_phase else 'not_started'
            }
        
        except Exception as e:
            logger.error(f"Error rolling back migration for client {client_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to rollback migration: {str(e)}'
            }
    
    async def list_client_migrations(
        self,
        status_filter: Optional[MigrationStatus] = None,
        phase_filter: Optional[MigrationPhase] = None
    ) -> List[Dict[str, Any]]:
        """
        List all client migrations with optional filtering.
        
        Args:
            status_filter: Filter by migration status
            phase_filter: Filter by migration phase
            
        Returns:
            List of migration records
        """
        try:
            # Scan the migration table
            scan_kwargs = {}
            
            if status_filter:
                scan_kwargs['FilterExpression'] = boto3.dynamodb.conditions.Attr('status').eq(status_filter.value)
            
            response = self.table.scan(**scan_kwargs)
            migrations = response['Items']
            
            # Apply phase filter if specified
            if phase_filter:
                migrations = [
                    m for m in migrations 
                    if m.get('current_phase') == phase_filter.value
                ]
            
            # Sort by started_at descending
            migrations.sort(key=lambda x: x.get('started_at', ''), reverse=True)
            
            return migrations
        
        except Exception as e:
            logger.error(f"Error listing client migrations: {str(e)}")
            return []
    
    async def _create_migration_record(
        self,
        client_id: str,
        migration_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new migration record."""
        migration_id = f"migration-{client_id}-{int(datetime.utcnow().timestamp())}"
        
        record = {
            'client_id': client_id,
            'migration_id': migration_id,
            'status': MigrationStatus.PENDING.value,
            'current_phase': MigrationPhase.NOT_STARTED.value,
            'started_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'options': migration_options or {},
            'phases_completed': [],
            'errors': [],
            'warnings': []
        }
        
        # Save to DynamoDB
        self.table.put_item(Item=record)
        
        return record
    
    async def _get_migration_record(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get migration record for a client."""
        try:
            response = self.table.get_item(
                Key={'client_id': client_id}
            )
            return response.get('Item')
        except ClientError:
            return None
    
    async def _update_migration_record(
        self,
        client_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """Update migration record."""
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        # Build update expression
        update_expression = "SET "
        expression_values = {}
        
        for key, value in updates.items():
            update_expression += f"{key} = :{key}, "
            expression_values[f":{key}"] = value
        
        update_expression = update_expression.rstrip(", ")
        
        self.table.update_item(
            Key={'client_id': client_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
    
    async def _execute_migration_phases(
        self,
        client_id: str,
        migration_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute migration phases for a client."""
        current_phase = MigrationPhase(migration_record.get('current_phase', MigrationPhase.NOT_STARTED.value))
        
        try:
            # Update status to in progress
            await self._update_migration_record(client_id, {
                'status': MigrationStatus.IN_PROGRESS.value
            })
            
            # Execute phases in order
            if current_phase == MigrationPhase.NOT_STARTED:
                await self._execute_data_migration_phase(client_id)
                current_phase = MigrationPhase.DATA_MIGRATION
            
            if current_phase == MigrationPhase.DATA_MIGRATION:
                await self._execute_compatibility_mode_phase(client_id)
                current_phase = MigrationPhase.COMPATIBILITY_MODE
            
            if current_phase == MigrationPhase.COMPATIBILITY_MODE:
                await self._execute_feature_testing_phase(client_id)
                current_phase = MigrationPhase.FEATURE_TESTING
            
            if current_phase == MigrationPhase.FEATURE_TESTING:
                await self._execute_full_migration_phase(client_id)
                current_phase = MigrationPhase.FULL_MIGRATION
            
            if current_phase == MigrationPhase.FULL_MIGRATION:
                await self._execute_completion_phase(client_id)
                current_phase = MigrationPhase.COMPLETED
            
            # Update final status
            await self._update_migration_record(client_id, {
                'status': MigrationStatus.COMPLETED.value,
                'current_phase': current_phase.value,
                'completed_at': datetime.utcnow().isoformat()
            })
            
            return {
                'current_phase': current_phase.value,
                'estimated_completion': datetime.utcnow().isoformat(),
                'next_steps': ['Migration completed successfully']
            }
        
        except Exception as e:
            # Update error status
            await self._update_migration_record(client_id, {
                'status': MigrationStatus.FAILED.value,
                'error_message': str(e),
                'failed_at': datetime.utcnow().isoformat()
            })
            raise
    
    async def _execute_data_migration_phase(self, client_id: str) -> None:
        """Execute data migration phase."""
        logger.info(f"Executing data migration phase for client {client_id}")
        
        # This would integrate with the data migrator
        # For now, we'll simulate the process
        await self._update_migration_record(client_id, {
            'current_phase': MigrationPhase.DATA_MIGRATION.value,
            'current_step': 'Migrating historical cost data'
        })
        
        # Simulate data migration (in real implementation, call data_migrator)
        # migration_result = await self.data_migrator.migrate_client_data(client_id)
        
        await self._update_migration_record(client_id, {
            'phases_completed': [MigrationPhase.DATA_MIGRATION.value]
        })
    
    async def _execute_compatibility_mode_phase(self, client_id: str) -> None:
        """Execute compatibility mode phase."""
        logger.info(f"Executing compatibility mode phase for client {client_id}")
        
        await self._update_migration_record(client_id, {
            'current_phase': MigrationPhase.COMPATIBILITY_MODE.value,
            'current_step': 'Enabling compatibility mode'
        })
        
        # Enable compatibility mode
        await self.feature_flags.enable_feature_for_client(
            FeatureFlag.MIGRATION_MODE, client_id, True
        )
    
    async def _execute_feature_testing_phase(self, client_id: str) -> None:
        """Execute feature testing phase."""
        logger.info(f"Executing feature testing phase for client {client_id}")
        
        await self._update_migration_record(client_id, {
            'current_phase': MigrationPhase.FEATURE_TESTING.value,
            'current_step': 'Enabling new features for testing'
        })
        
        # Enable new features gradually
        await self.feature_flags.enable_feature_for_client(
            FeatureFlag.AI_INSIGHTS, client_id, True
        )
        await self.feature_flags.enable_feature_for_client(
            FeatureFlag.ENHANCED_REPORTING, client_id, True
        )
    
    async def _execute_full_migration_phase(self, client_id: str) -> None:
        """Execute full migration phase."""
        logger.info(f"Executing full migration phase for client {client_id}")
        
        await self._update_migration_record(client_id, {
            'current_phase': MigrationPhase.FULL_MIGRATION.value,
            'current_step': 'Switching to new API'
        })
        
        # Enable new API
        await self.feature_flags.enable_feature_for_client(
            FeatureFlag.USE_NEW_API, client_id, True
        )
        await self.feature_flags.enable_feature_for_client(
            FeatureFlag.MULTI_CLOUD_SUPPORT, client_id, True
        )
    
    async def _execute_completion_phase(self, client_id: str) -> None:
        """Execute completion phase."""
        logger.info(f"Executing completion phase for client {client_id}")
        
        await self._update_migration_record(client_id, {
            'current_phase': MigrationPhase.COMPLETED.value,
            'current_step': 'Migration completed'
        })
        
        # Disable compatibility mode
        await self.feature_flags.enable_feature_for_client(
            FeatureFlag.MIGRATION_MODE, client_id, False
        )
    
    async def _calculate_migration_progress(self, migration_record: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate migration progress percentage."""
        total_phases = len(MigrationPhase) - 1  # Exclude NOT_STARTED
        current_phase = MigrationPhase(migration_record['current_phase'])
        
        phase_order = [
            MigrationPhase.DATA_MIGRATION,
            MigrationPhase.COMPATIBILITY_MODE,
            MigrationPhase.FEATURE_TESTING,
            MigrationPhase.FULL_MIGRATION,
            MigrationPhase.COMPLETED
        ]
        
        if current_phase == MigrationPhase.NOT_STARTED:
            completed_phases = 0
        elif current_phase in phase_order:
            completed_phases = phase_order.index(current_phase) + 1
        else:
            completed_phases = 0
        
        percentage = (completed_phases / total_phases) * 100
        
        return {
            'percentage': min(percentage, 100),
            'phases_completed': completed_phases,
            'total_phases': total_phases
        }