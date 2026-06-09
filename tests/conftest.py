"""Test fixtures — patches the key store so all tests use demo mode (no API keys)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# Patch BEFORE any module imports the real get_key_store
import src.models.key_store as _ks


class _VoidKeyStore:
    """Key store that returns None for all keys — forces demo mode everywhere."""
    def get_key(self, name):
        return None
    def set_key(self, name, value):
        pass
    def has_key(self, name):
        return False


_ks.get_key_store = lambda: _VoidKeyStore()
