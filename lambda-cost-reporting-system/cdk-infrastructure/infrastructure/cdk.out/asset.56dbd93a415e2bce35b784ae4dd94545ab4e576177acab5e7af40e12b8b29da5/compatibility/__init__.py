"""
Backward Compatibility Package

This package provides backward compatibility layers for existing API endpoints
and gradual migration support for existing clients.
"""

from .api_compatibility import CompatibilityAPIHandler
from .feature_flags import FeatureFlagManager
from .client_migration import ClientMigrationManager

__all__ = [
    'CompatibilityAPIHandler',
    'FeatureFlagManager',
    'ClientMigrationManager'
]