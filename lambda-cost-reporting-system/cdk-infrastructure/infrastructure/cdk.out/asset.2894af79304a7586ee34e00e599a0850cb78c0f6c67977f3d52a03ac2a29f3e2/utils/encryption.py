"""
Encryption utilities for sensitive data handling.

This module provides encryption and decryption utilities using AWS KMS
for securing sensitive configuration data like AWS access keys.
"""

import boto3
import base64
import logging
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, BotoCoreError


logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption operations."""
    pass


class KMSEncryptionError(EncryptionError):
    """Raised when KMS encryption operations fail."""
    pass


class KMSDecryptionError(EncryptionError):
    """Raised when KMS decryption operations fail."""
    pass


class EncryptionManager:
    """
    Manages encryption and decryption of sensitive data using AWS KMS.
    
    This class provides methods to encrypt and decrypt sensitive configuration data
    such as AWS access keys and secrets using AWS Key Management Service (KMS).
    """
    
    def __init__(self, kms_key_id: str, region: str = "us-east-1"):
        """
        Initialize the EncryptionManager.
        
        Args:
            kms_key_id: AWS KMS key ID or ARN for encryption/decryption
            region: AWS region for KMS operations
        """
        self.kms_key_id = kms_key_id
        self.region = region
        self._kms_client = None
    
    @property
    def kms_client(self):
        """Lazy initialization of KMS client."""
        if self._kms_client is None:
            self._kms_client = boto3.client('kms', region_name=self.region)
        return self._kms_client
    
    def encrypt(self, plaintext: str, encryption_context: Optional[Dict[str, str]] = None) -> str:
        """
        Encrypt a plaintext string using KMS.
        
        Args:
            plaintext: The plaintext string to encrypt
            encryption_context: Optional encryption context for additional security
            
        Returns:
            Base64-encoded encrypted data
            
        Raises:
            KMSEncryptionError: If encryption fails
        """
        try:
            logger.debug("Encrypting data with KMS")
            
            if not plaintext:
                raise ValueError("Plaintext cannot be empty")
            
            # Prepare encryption parameters
            encrypt_params = {
                'KeyId': self.kms_key_id,
                'Plaintext': plaintext.encode('utf-8')
            }
            
            if encryption_context:
                encrypt_params['EncryptionContext'] = encryption_context
            
            # Encrypt the data
            response = self.kms_client.encrypt(**encrypt_params)
            
            # Encode the ciphertext as base64 for storage
            encrypted_data = base64.b64encode(response['CiphertextBlob']).decode('utf-8')
            
            logger.debug("Successfully encrypted data")
            return encrypted_data
            
        except ClientError as e:
            error_msg = f"KMS encryption failed: {e}"
            logger.error(error_msg)
            raise KMSEncryptionError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during encryption: {e}"
            logger.error(error_msg)
            raise EncryptionError(error_msg) from e
    
    def decrypt(self, encrypted_data: str, encryption_context: Optional[Dict[str, str]] = None) -> str:
        """
        Decrypt encrypted data using KMS.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            encryption_context: Optional encryption context that was used during encryption
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            KMSDecryptionError: If decryption fails
        """
        try:
            logger.debug("Decrypting data with KMS")
            
            if not encrypted_data:
                raise ValueError("Encrypted data cannot be empty")
            
            # Decode the base64-encoded ciphertext
            try:
                ciphertext_blob = base64.b64decode(encrypted_data.encode('utf-8'))
            except Exception as e:
                raise ValueError(f"Invalid base64 encrypted data: {e}")
            
            # Prepare decryption parameters
            decrypt_params = {
                'CiphertextBlob': ciphertext_blob
            }
            
            if encryption_context:
                decrypt_params['EncryptionContext'] = encryption_context
            
            # Decrypt the data
            response = self.kms_client.decrypt(**decrypt_params)
            
            # Decode the plaintext
            plaintext = response['Plaintext'].decode('utf-8')
            
            logger.debug("Successfully decrypted data")
            return plaintext
            
        except ClientError as e:
            error_msg = f"KMS decryption failed: {e}"
            logger.error(error_msg)
            raise KMSDecryptionError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during decryption: {e}"
            logger.error(error_msg)
            raise EncryptionError(error_msg) from e
    
    def encrypt_dict(self, data: Dict[str, Any], fields_to_encrypt: list, 
                    encryption_context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data to encrypt
            fields_to_encrypt: List of field names to encrypt
            encryption_context: Optional encryption context
            
        Returns:
            Dictionary with specified fields encrypted
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            logger.debug(f"Encrypting fields {fields_to_encrypt} in dictionary")
            
            encrypted_data = data.copy()
            
            for field in fields_to_encrypt:
                if field in encrypted_data and encrypted_data[field]:
                    # Create field-specific encryption context
                    field_context = encryption_context.copy() if encryption_context else {}
                    field_context['field'] = field
                    
                    encrypted_data[field] = self.encrypt(
                        str(encrypted_data[field]), 
                        field_context
                    )
                    
                    # Mark field as encrypted for identification
                    encrypted_data[f"{field}_encrypted"] = True
            
            logger.debug(f"Successfully encrypted {len(fields_to_encrypt)} fields")
            return encrypted_data
            
        except Exception as e:
            error_msg = f"Failed to encrypt dictionary fields: {e}"
            logger.error(error_msg)
            raise EncryptionError(error_msg) from e
    
    def decrypt_dict(self, data: Dict[str, Any], fields_to_decrypt: list,
                    encryption_context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields_to_decrypt: List of field names to decrypt
            encryption_context: Optional encryption context
            
        Returns:
            Dictionary with specified fields decrypted
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            logger.debug(f"Decrypting fields {fields_to_decrypt} in dictionary")
            
            decrypted_data = data.copy()
            
            for field in fields_to_decrypt:
                if field in decrypted_data and decrypted_data[field]:
                    # Check if field is marked as encrypted
                    if not decrypted_data.get(f"{field}_encrypted", False):
                        logger.warning(f"Field {field} is not marked as encrypted, skipping decryption")
                        continue
                    
                    # Create field-specific encryption context
                    field_context = encryption_context.copy() if encryption_context else {}
                    field_context['field'] = field
                    
                    decrypted_data[field] = self.decrypt(
                        decrypted_data[field],
                        field_context
                    )
                    
                    # Remove encryption marker
                    decrypted_data.pop(f"{field}_encrypted", None)
            
            logger.debug(f"Successfully decrypted {len(fields_to_decrypt)} fields")
            return decrypted_data
            
        except Exception as e:
            error_msg = f"Failed to decrypt dictionary fields: {e}"
            logger.error(error_msg)
            raise EncryptionError(error_msg) from e
    
    def is_encrypted(self, data: str) -> bool:
        """
        Check if a string appears to be encrypted (base64 encoded).
        
        Args:
            data: String to check
            
        Returns:
            True if data appears to be encrypted, False otherwise
        """
        try:
            if not data:
                return False
            
            # Try to decode as base64
            decoded = base64.b64decode(data.encode('utf-8'))
            
            # Check if it's a reasonable length for encrypted data (at least 32 bytes)
            if len(decoded) < 32:
                return False
            
            # Additional heuristics could be added here
            return True
            
        except Exception:
            return False


class SecureCredentialHandler:
    """
    Handles secure storage and retrieval of AWS credentials.
    
    This class provides methods to securely store and retrieve AWS credentials
    with automatic encryption/decryption using the EncryptionManager.
    """
    
    def __init__(self, encryption_manager: EncryptionManager):
        """
        Initialize the SecureCredentialHandler.
        
        Args:
            encryption_manager: EncryptionManager instance for encryption operations
        """
        self.encryption_manager = encryption_manager
    
    def encrypt_aws_credentials(self, account_config_dict: Dict[str, Any], 
                              client_id: str) -> Dict[str, Any]:
        """
        Encrypt AWS credentials in an account configuration dictionary.
        
        Args:
            account_config_dict: Dictionary containing AWS account configuration
            client_id: Client ID for encryption context
            
        Returns:
            Dictionary with encrypted credentials
        """
        try:
            logger.info(f"Encrypting AWS credentials for client {client_id}")
            
            # Create encryption context with client information
            encryption_context = {
                'client_id': client_id,
                'data_type': 'aws_credentials'
            }
            
            # Fields to encrypt
            sensitive_fields = ['secret_access_key']
            
            encrypted_config = self.encryption_manager.encrypt_dict(
                account_config_dict,
                sensitive_fields,
                encryption_context
            )
            
            logger.info(f"Successfully encrypted AWS credentials for client {client_id}")
            return encrypted_config
            
        except Exception as e:
            error_msg = f"Failed to encrypt AWS credentials for client {client_id}: {e}"
            logger.error(error_msg)
            raise EncryptionError(error_msg) from e
    
    def decrypt_aws_credentials(self, encrypted_config_dict: Dict[str, Any],
                              client_id: str) -> Dict[str, Any]:
        """
        Decrypt AWS credentials in an account configuration dictionary.
        
        Args:
            encrypted_config_dict: Dictionary containing encrypted AWS account configuration
            client_id: Client ID for encryption context
            
        Returns:
            Dictionary with decrypted credentials
        """
        try:
            logger.debug(f"Decrypting AWS credentials for client {client_id}")
            
            # Create encryption context with client information
            encryption_context = {
                'client_id': client_id,
                'data_type': 'aws_credentials'
            }
            
            # Fields to decrypt
            sensitive_fields = ['secret_access_key']
            
            decrypted_config = self.encryption_manager.decrypt_dict(
                encrypted_config_dict,
                sensitive_fields,
                encryption_context
            )
            
            logger.debug(f"Successfully decrypted AWS credentials for client {client_id}")
            return decrypted_config
            
        except Exception as e:
            error_msg = f"Failed to decrypt AWS credentials for client {client_id}: {e}"
            logger.error(error_msg)
            raise EncryptionError(error_msg) from e
    
    def encrypt_client_config(self, client_config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive data in a complete client configuration.
        
        Args:
            client_config_dict: Complete client configuration dictionary
            
        Returns:
            Dictionary with encrypted sensitive data
        """
        try:
            client_id = client_config_dict.get('client_id', 'unknown')
            logger.info(f"Encrypting client configuration for {client_id}")
            
            encrypted_config = client_config_dict.copy()
            
            # Encrypt AWS account credentials
            if 'aws_accounts' in encrypted_config:
                encrypted_accounts = []
                for account in encrypted_config['aws_accounts']:
                    encrypted_account = self.encrypt_aws_credentials(account, client_id)
                    encrypted_accounts.append(encrypted_account)
                encrypted_config['aws_accounts'] = encrypted_accounts
            
            logger.info(f"Successfully encrypted client configuration for {client_id}")
            return encrypted_config
            
        except Exception as e:
            error_msg = f"Failed to encrypt client configuration: {e}"
            logger.error(error_msg)
            raise EncryptionError(error_msg) from e
    
    def decrypt_client_config(self, encrypted_config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive data in a complete client configuration.
        
        Args:
            encrypted_config_dict: Complete encrypted client configuration dictionary
            
        Returns:
            Dictionary with decrypted sensitive data
        """
        try:
            client_id = encrypted_config_dict.get('client_id', 'unknown')
            logger.debug(f"Decrypting client configuration for {client_id}")
            
            decrypted_config = encrypted_config_dict.copy()
            
            # Decrypt AWS account credentials
            if 'aws_accounts' in decrypted_config:
                decrypted_accounts = []
                for account in decrypted_config['aws_accounts']:
                    decrypted_account = self.decrypt_aws_credentials(account, client_id)
                    decrypted_accounts.append(decrypted_account)
                decrypted_config['aws_accounts'] = decrypted_accounts
            
            logger.debug(f"Successfully decrypted client configuration for {client_id}")
            return decrypted_config
            
        except Exception as e:
            error_msg = f"Failed to decrypt client configuration: {e}"
            logger.error(error_msg)
            raise EncryptionError(error_msg) from e


# Utility functions for easy access
def create_encryption_manager(kms_key_id: str, region: str = "us-east-1") -> EncryptionManager:
    """
    Create an EncryptionManager instance.
    
    Args:
        kms_key_id: AWS KMS key ID or ARN
        region: AWS region
        
    Returns:
        EncryptionManager instance
    """
    return EncryptionManager(kms_key_id, region)


def create_secure_credential_handler(kms_key_id: str, region: str = "us-east-1") -> SecureCredentialHandler:
    """
    Create a SecureCredentialHandler instance.
    
    Args:
        kms_key_id: AWS KMS key ID or ARN
        region: AWS region
        
    Returns:
        SecureCredentialHandler instance
    """
    encryption_manager = create_encryption_manager(kms_key_id, region)
    return SecureCredentialHandler(encryption_manager)