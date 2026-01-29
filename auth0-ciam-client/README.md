# Auth0 CIAM Client

A Python library for Auth0 Customer Identity and Access Management (CIAM) authentication flows.

## Features

- **Session Management**: Persistent authentication state with configurable storage backends
- **JWT Token Handling**: Automatic token validation, refresh, and expiration management
- **Configurable Auth Flows**: Support for various Auth0 authentication patterns
- **Angel Studios Integration**: Pre-configured settings for Angel Studios authentication
- **Extensible Design**: Abstract interfaces for custom storage and configuration

## Installation

```bash
pip install auth0-ciam-client
```

## Quick Start

### Basic Usage

```python
from auth0_ciam_client import AuthenticationCore, Auth0Config, InMemorySessionStore

# Configure for your Auth0 tenant
config = Auth0Config(
    base_url="https://your-app.auth0.com"
)

# Create authentication core with in-memory storage
auth = AuthenticationCore(
    session_store=InMemorySessionStore(),
    config=config
)

# Authenticate
result = auth.authenticate("username", "password")
if result.success:
    print(f"Authenticated! Token: {result.token[:20]}...")
else:
    print(f"Authentication failed: {result.error_message}")
```

### Angel Studios Integration

```python
from auth0_ciam_client import AuthenticationCore, create_angel_studios_config, InMemorySessionStore

# Use pre-configured Angel Studios settings
config = create_angel_studios_config()
auth = AuthenticationCore(
    session_store=InMemorySessionStore(),
    config=config
)

# Authenticate with Angel Studios
result = auth.authenticate("your@email.com", "password")
```

### Custom Session Storage

```python
from auth0_ciam_client import AuthenticationCore, SessionStore, Auth0Config

class CustomSessionStore(SessionStore):
    def save_token(self, token: str) -> None:
        # Your custom storage logic
        pass

    def get_token(self) -> str | None:
        # Your custom retrieval logic
        pass

    # Implement other required methods...

config = Auth0Config(base_url="https://your-app.auth0.com")
auth = AuthenticationCore(
    session_store=CustomSessionStore(),
    config=config
)
```

## Configuration

The `Auth0Config` dataclass supports the following options:

- `base_url`: Base URL for your Auth0 application (required)
- `jwt_cookie_names`: List of cookie names to check for JWT tokens
- `request_timeout`: HTTP request timeout in seconds
- `expiry_buffer_hours`: Hours before token expiration to attempt refresh
- `user_agent`: Custom User-Agent string for requests

## Development

### Setup

```bash
git clone https://github.com/yourusername/auth0-ciam-client
cd auth0-ciam-client
pip install -e ".[dev]"
```

### Testing

```bash
pytest
```

### Code Quality

```bash
black auth0_ciam_client/
flake8 auth0_ciam_client/
mypy auth0_ciam_client/
```

## License

GPL-3.0-only

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This package is not officially affiliated with Auth0 Inc. It provides client-side utilities for interacting with Auth0 authentication services.