"""Test shared API dependencies."""
from src.api.dependencies import resolve_provider_model, has_api_key


def test_resolve_provider_model_returns_strings():
    """Without args, should return a (provider, model) tuple of strings."""
    provider, model = resolve_provider_model()
    assert isinstance(provider, str)
    assert isinstance(model, str)


def test_has_api_key_unknown():
    """Unknown provider should not have a key (returns False)."""
    result = has_api_key("__nonexistent_provider_test__")
    # Should return False without raising errors
    assert result is False