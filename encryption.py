"""
Smart Notes Vault - Fernet AES-128 Encryption Module
Fernet = AES-128-CBC + HMAC-SHA256 with random IV
"""

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
import base64
import os
import logging

logger = logging.getLogger(__name__)


def get_fernet() -> Fernet:
    """Return a Fernet instance using the app's key."""
    key = current_app.config.get('FERNET_KEY', '')
    if not key:
        raise ValueError(
            "FERNET_KEY not set. Generate one with: "
            "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_note(plaintext: str) -> bytes:
    """Encrypt a note string and return ciphertext bytes."""
    try:
        f = get_fernet()
        return f.encrypt(plaintext.encode('utf-8'))
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise


def decrypt_note(ciphertext: bytes) -> str:
    """Decrypt ciphertext bytes and return plaintext string."""
    try:
        f = get_fernet()
        return f.decrypt(ciphertext).decode('utf-8')
    except InvalidToken:
        logger.error("Decryption failed - invalid token or wrong key")
        raise ValueError("Cannot decrypt note: invalid key or corrupted data.")
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise


def generate_new_key() -> str:
    """Generate a new Fernet key (for initial setup)."""
    return Fernet.generate_key().decode()
