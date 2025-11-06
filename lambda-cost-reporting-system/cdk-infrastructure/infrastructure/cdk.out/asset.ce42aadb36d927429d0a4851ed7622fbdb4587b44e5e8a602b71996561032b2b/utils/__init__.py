"""
Utilities package for the Lambda Cost Reporting System.

This package contains utility functions and classes for common operations
like encryption, logging, and data processing.
"""

from .encryption import (
    EncryptionManager,
    SecureCredentialHandler,
    EncryptionError,
    KMSEncryptionError,
    KMSDecryptionError,
    create_encryption_manager,
    create_secure_credential_handler
)

from .logging import (
    create_logger,
    configure_lambda_logging,
    mask_sensitive_data,
    log_execution_time,
    log_async_execution_time
)

__all__ = [
    "EncryptionManager",
    "SecureCredentialHandler",
    "EncryptionError",
    "KMSEncryptionError",
    "KMSDecryptionError",
    "create_encryption_manager",
    "create_secure_credential_handler",
    "create_logger",
    "configure_lambda_logging",
    "mask_sensitive_data",
    "log_execution_time",
    "log_async_execution_time"
]