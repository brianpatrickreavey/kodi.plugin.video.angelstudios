"""Configuration classes for Auth0 CIAM Client."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Auth0Config:
    """Configuration for Auth0 authentication.

    This class contains all settings needed to configure authentication
    against an Auth0 tenant.
    """
    base_url: str
    jwt_cookie_names: List[str] = field(default_factory=lambda: ["angel_jwt_v2", "angel_jwt"])
    request_timeout: int = 30
    expiry_buffer_hours: int = 1
    user_agent: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.base_url:
            raise ValueError("base_url is required")
        if not isinstance(self.jwt_cookie_names, list) or not self.jwt_cookie_names:
            raise ValueError("jwt_cookie_names must be a non-empty list")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")
        if self.expiry_buffer_hours < 0:
            raise ValueError("expiry_buffer_hours must be non-negative")


def create_angel_studios_config() -> Auth0Config:
    """Create a pre-configured Auth0Config for Angel Studios.

    Returns:
        Auth0Config: Configuration optimized for Angel Studios authentication
    """
    return Auth0Config(
        base_url="https://www.angel.com",
        jwt_cookie_names=["angel_jwt_v2", "angel_jwt"],
        request_timeout=30,
        expiry_buffer_hours=1,
    )