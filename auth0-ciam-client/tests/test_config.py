"""Unit tests for Auth0Config validation."""

import pytest

from auth0_ciam_client.config import Auth0Config


class TestAuth0Config:
    """Test Auth0Config validation"""

    def test_config_validation_empty_base_url(self):
        """Test that empty base_url raises ValueError"""
        with pytest.raises(ValueError, match="base_url is required"):
            Auth0Config(base_url="")

    def test_config_validation_invalid_timeout(self):
        """Test that non-positive timeout raises ValueError"""
        with pytest.raises(ValueError, match="request_timeout must be positive"):
            Auth0Config(base_url="https://example.com", request_timeout=0)

    def test_config_validation_negative_timeout(self):
        """Test that negative timeout raises ValueError"""
        with pytest.raises(ValueError, match="request_timeout must be positive"):
            Auth0Config(base_url="https://example.com", request_timeout=-1)

    def test_config_validation_empty_cookie_names(self):
        """Test that empty jwt_cookie_names raises ValueError"""
        with pytest.raises(ValueError, match="jwt_cookie_names must be a non-empty list"):
            Auth0Config(base_url="https://example.com", jwt_cookie_names=[])

    def test_config_validation_invalid_cookie_names_type(self):
        """Test that non-list jwt_cookie_names raises ValueError"""
        with pytest.raises(ValueError, match="jwt_cookie_names must be a non-empty list"):
            Auth0Config(base_url="https://example.com", jwt_cookie_names="not_a_list")

    def test_config_validation_negative_buffer(self):
        """Test that negative expiry_buffer_hours raises ValueError"""
        with pytest.raises(ValueError, match="expiry_buffer_hours must be non-negative"):
            Auth0Config(base_url="https://example.com", expiry_buffer_hours=-1)

    def test_config_validation_valid_config(self):
        """Test that valid config works"""
        config = Auth0Config(
            base_url="https://example.com",
            jwt_cookie_names=["cookie1", "cookie2"],
            request_timeout=30,
            expiry_buffer_hours=2,
            user_agent="Test Agent"
        )
        assert config.base_url == "https://example.com"
        assert config.jwt_cookie_names == ["cookie1", "cookie2"]
        assert config.request_timeout == 30
        assert config.expiry_buffer_hours == 2
        assert config.user_agent == "Test Agent"