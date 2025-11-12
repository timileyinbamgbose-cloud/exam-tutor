"""
Data Encryption Utilities
Epic 3.4: Kubernetes Deployment & Security
NDPR Compliance - Data Encryption at Rest and in Transit
"""

import hashlib
import secrets
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64

from src.core.config import settings
from src.core.logger import logger


class DataEncryption:
    """
    Handles encryption and decryption of sensitive data.
    Uses Fernet (symmetric encryption) with AES-256.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with provided key or from settings.

        Args:
            encryption_key: Base64-encoded encryption key. If None, uses settings.
        """
        if encryption_key:
            self.key = encryption_key.encode()
        elif hasattr(settings, 'data_encryption_key') and settings.data_encryption_key:
            self.key = settings.data_encryption_key.encode()
        else:
            # Generate a key if none provided (for development only)
            logger.warning("No encryption key provided. Generating temporary key.")
            self.key = Fernet.generate_key()

        try:
            self.cipher = Fernet(self.key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded encryption key
        """
        key = Fernet.generate_key()
        return key.decode('utf-8')

    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """
        Derive an encryption key from a password using PBKDF2.

        Args:
            password: User password
            salt: Salt for key derivation. If None, generates new salt.

        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(16)

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt

    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data using Fernet.

        Args:
            data: Data to encrypt (string or bytes)

        Returns:
            Base64-encoded encrypted data
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')

            encrypted_data = self.cipher.encrypt(data)
            return encrypted_data.decode('utf-8')

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data using Fernet.

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted data as string
        """
        try:
            encrypted_bytes = encrypted_data.encode('utf-8')
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_dict(self, data: dict, keys_to_encrypt: list[str]) -> dict:
        """
        Encrypt specific keys in a dictionary.

        Args:
            data: Dictionary containing data
            keys_to_encrypt: List of keys to encrypt

        Returns:
            Dictionary with specified keys encrypted
        """
        encrypted_data = data.copy()
        for key in keys_to_encrypt:
            if key in encrypted_data and encrypted_data[key] is not None:
                encrypted_data[key] = self.encrypt(str(encrypted_data[key]))
        return encrypted_data

    def decrypt_dict(self, data: dict, keys_to_decrypt: list[str]) -> dict:
        """
        Decrypt specific keys in a dictionary.

        Args:
            data: Dictionary containing encrypted data
            keys_to_decrypt: List of keys to decrypt

        Returns:
            Dictionary with specified keys decrypted
        """
        decrypted_data = data.copy()
        for key in keys_to_decrypt:
            if key in decrypted_data and decrypted_data[key] is not None:
                try:
                    decrypted_data[key] = self.decrypt(decrypted_data[key])
                except Exception as e:
                    logger.warning(f"Failed to decrypt key '{key}': {e}")
                    # Keep original value if decryption fails
        return decrypted_data


class PIIMasking:
    """
    Utilities for masking Personally Identifiable Information (PII).
    NDPR Compliance - Data Minimization and Privacy by Design.
    """

    @staticmethod
    def mask_email(email: str) -> str:
        """
        Mask email address, keeping first and last characters visible.

        Args:
            email: Email address to mask

        Returns:
            Masked email (e.g., j***@e***.ng)
        """
        if not email or '@' not in email:
            return "***"

        local, domain = email.split('@')
        if len(local) <= 2:
            masked_local = local[0] + '*'
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]

        domain_parts = domain.split('.')
        if len(domain_parts) > 1:
            masked_domain = domain_parts[0][0] + '*' * (len(domain_parts[0]) - 1)
            masked_domain += '.' + '.'.join(domain_parts[1:])
        else:
            masked_domain = domain

        return f"{masked_local}@{masked_domain}"

    @staticmethod
    def mask_phone(phone: str) -> str:
        """
        Mask phone number, keeping last 4 digits visible.

        Args:
            phone: Phone number to mask

        Returns:
            Masked phone (e.g., ***1234)
        """
        if not phone:
            return "***"

        # Remove non-numeric characters
        digits = ''.join(c for c in phone if c.isdigit())

        if len(digits) <= 4:
            return '*' * len(digits)

        return '*' * (len(digits) - 4) + digits[-4:]

    @staticmethod
    def mask_name(name: str) -> str:
        """
        Mask name, keeping first letter visible.

        Args:
            name: Name to mask

        Returns:
            Masked name (e.g., J*** D***)
        """
        if not name:
            return "***"

        parts = name.split()
        masked_parts = []
        for part in parts:
            if len(part) == 1:
                masked_parts.append(part)
            else:
                masked_parts.append(part[0] + '*' * (len(part) - 1))

        return ' '.join(masked_parts)

    @staticmethod
    def mask_dict(data: dict, pii_fields: list[str]) -> dict:
        """
        Mask PII fields in a dictionary.

        Args:
            data: Dictionary containing data
            pii_fields: List of field names containing PII

        Returns:
            Dictionary with PII fields masked
        """
        masked_data = data.copy()
        masker = PIIMasking()

        for field in pii_fields:
            if field in masked_data and masked_data[field]:
                value = str(masked_data[field])

                # Determine masking method based on field name
                if 'email' in field.lower():
                    masked_data[field] = masker.mask_email(value)
                elif 'phone' in field.lower() or 'mobile' in field.lower():
                    masked_data[field] = masker.mask_phone(value)
                elif 'name' in field.lower():
                    masked_data[field] = masker.mask_name(value)
                else:
                    # Generic masking
                    if len(value) <= 2:
                        masked_data[field] = '*' * len(value)
                    else:
                        masked_data[field] = value[0] + '*' * (len(value) - 2) + value[-1]

        return masked_data


class SecureHash:
    """
    Secure hashing utilities for one-way data protection.
    """

    @staticmethod
    def hash_data(data: str, algorithm: str = 'sha256') -> str:
        """
        Create a secure hash of data.

        Args:
            data: Data to hash
            algorithm: Hashing algorithm (sha256, sha512)

        Returns:
            Hexadecimal hash string
        """
        if algorithm == 'sha256':
            return hashlib.sha256(data.encode()).hexdigest()
        elif algorithm == 'sha512':
            return hashlib.sha512(data.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    @staticmethod
    def verify_hash(data: str, hash_value: str, algorithm: str = 'sha256') -> bool:
        """
        Verify data against a hash.

        Args:
            data: Original data
            hash_value: Hash to verify against
            algorithm: Hashing algorithm used

        Returns:
            True if hash matches, False otherwise
        """
        computed_hash = SecureHash.hash_data(data, algorithm)
        return secrets.compare_digest(computed_hash, hash_value)


# Global instances
encryption = DataEncryption()
pii_masker = PIIMasking()
secure_hasher = SecureHash()


if __name__ == "__main__":
    # Example usage
    print("Encryption Example:")
    encrypted = encryption.encrypt("Sensitive student data")
    print(f"Encrypted: {encrypted}")
    decrypted = encryption.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")

    print("\nPII Masking Example:")
    print(f"Email: {pii_masker.mask_email('john.doe@examstutor.ng')}")
    print(f"Phone: {pii_masker.mask_phone('+234 801 234 5678')}")
    print(f"Name: {pii_masker.mask_name('John Doe')}")

    print("\nHashing Example:")
    data = "student123@examstutor.ng"
    hash_value = secure_hasher.hash_data(data)
    print(f"Hash: {hash_value}")
    print(f"Verification: {secure_hasher.verify_hash(data, hash_value)}")
