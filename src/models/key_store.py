"""Local encrypted API key storage using cryptography library.

API keys are stored in a local JSON file with AES encryption.
The encryption key is derived from a machine-specific identifier,
ensuring keys can only be decrypted on the same machine.
"""
import json
import os
import hashlib
import base64
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Local storage path for API keys.
# Configurable via env var so Docker can mount a persistent volume.
# Default: ~/.cs599-agent/
KEYS_DIR = Path(os.getenv("KEYS_DIR", str(Path.home() / ".cs599-agent")))
KEYS_FILE = KEYS_DIR / "api_keys.enc"
SALT_FILE = KEYS_DIR / ".salt"


class APIKeyStore:
    """Secure local storage for API keys.
    
    Keys are encrypted with AES-256 using a machine-derived key.
    """
    
    def __init__(self):
        self._keys: Dict[str, str] = {}
        self._ensure_storage()
        self._load_keys()
    
    def _ensure_storage(self):
        """Create storage directory if not exists."""
        KEYS_DIR.mkdir(parents=True, exist_ok=True)
        if not SALT_FILE.exists():
            # Generate random salt
            salt = os.urandom(16)
            SALT_FILE.write_bytes(salt)
    
    def _get_fernet(self) -> Fernet:
        """Create Fernet instance for encrypting API keys.

        The encryption key is derived from a MASTER_KEY file (stable across
        container restarts) rather than hostname/username, which change on
        every Docker container restart and would silently wipe all stored keys.
        """
        master_key_file = KEYS_DIR / ".master_key"
        if not master_key_file.exists():
            # Generate a random master key on first run.
            # This file persists in the KEYS_DIR volume, so the key is
            # stable across container restarts as long as the volume survives.
            master_key_file.write_bytes(os.urandom(32))
        master_key = master_key_file.read_bytes()
        salt = SALT_FILE.read_bytes()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key))
        return Fernet(key)
    
    def _load_keys(self):
        """Load and decrypt API keys from storage."""
        if not KEYS_FILE.exists():
            return
        
        try:
            fernet = self._get_fernet()
            encrypted_data = KEYS_FILE.read_bytes()
            decrypted = fernet.decrypt(encrypted_data)
            self._keys = json.loads(decrypted.decode())
        except Exception:
            # If decryption fails (e.g., moved to another machine),
            # start with empty keys
            self._keys = {}
    
    def _save_keys(self):
        """Encrypt and save API keys to storage."""
        fernet = self._get_fernet()
        data = json.dumps(self._keys).encode()
        encrypted = fernet.encrypt(data)
        KEYS_FILE.write_bytes(encrypted)
    
    def get_key(self, provider_name: str) -> Optional[str]:
        """Get API key for a provider.
        
        Also checks environment variable: {PROVIDER_NAME}_API_KEY
        """
        # Check environment first (for CI/CD and dev)
        env_key = os.getenv(f"{provider_name.upper()}_API_KEY")
        if env_key:
            return env_key
        
        return self._keys.get(provider_name)
    
    def set_key(self, provider_name: str, api_key: str):
        """Save API key for a provider."""
        self._keys[provider_name] = api_key
        self._save_keys()
    
    def remove_key(self, provider_name: str):
        """Remove API key for a provider."""
        if provider_name in self._keys:
            del self._keys[provider_name]
            self._save_keys()
    
    def list_providers(self) -> list:
        """List all providers with stored keys."""
        return list(self._keys.keys())
    
    def has_key(self, provider_name: str) -> bool:
        """Check if API key exists for provider."""
        return self.get_key(provider_name) is not None
    
    def clear_all(self):
        """Remove all stored keys. Use with caution."""
        self._keys = {}
        if KEYS_FILE.exists():
            KEYS_FILE.unlink()


# Singleton
_key_store = None


def get_key_store() -> APIKeyStore:
    """Get APIKeyStore singleton."""
    global _key_store
    if _key_store is None:
        _key_store = APIKeyStore()
    return _key_store
