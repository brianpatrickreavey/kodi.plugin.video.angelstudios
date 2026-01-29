# Auth0 CIAM Client

A Python library for Auth0 Customer Identity and Access Management (CIAM) authentication flows.

## Features

- **Session Management**: Persistent authentication state with configurable storage backends
- **JWT Token Handling**: Automatic token validation, refresh, and expiration management
- **Configurable Auth Flows**: Support for various Auth0 authentication patterns
- **Angel Studios Integration**: Pre-configured settings for Angel Studios authentication
- **Extensible Design**: Abstract interfaces for custom storage and configuration
- **Error Handling**: Comprehensive exception hierarchy for different authentication scenarios
- **Type Safety**: Full type hints and dataclass-based configuration

## Installation

```bash
pip install auth0-ciam-client
```

Or for development:

```bash
git clone <repository-url>
cd auth0-ciam-client
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
from auth0_ciam_client import AuthenticationCore, Auth0Config, InMemorySessionStore

# Configure for your Auth0 tenant
config = Auth0Config(
    base_url="https://your-app.auth0.com",
    jwt_cookie_names=["auth_token", "jwt"],
    request_timeout=30
)

# Create authentication core with in-memory storage
auth = AuthenticationCore(
    session_store=InMemorySessionStore(),
    config=config
)

# Authenticate
result = auth.authenticate("username@example.com", "password")
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
if result.success:
    print("Successfully authenticated with Angel Studios!")
    # Token is automatically stored for future use
else:
    print(f"Authentication failed: {result.error_message}")
```

### Session Management

```python
# Check if session is still valid
if auth.validate_session():
    print("Session is valid")
else:
    print("Session expired or missing")

# Ensure valid session (auto-refresh if needed)
try:
    auth.ensure_valid_session()
    print("Session is ready for use")
except AuthenticationRequiredError:
    print("Re-authentication required")
```

## API Reference

### AuthenticationCore

The main class for handling authentication flows.

#### Methods

- `authenticate(username: str, password: str) -> AuthResult`
  - Performs full authentication flow
  - Returns AuthResult with success status and token/error

- `validate_session() -> bool`
  - Checks if current token is valid and not expired

- `ensure_valid_session() -> None`
  - Ensures session is valid, refreshing automatically if needed
  - Raises AuthenticationRequiredError if refresh fails

- `logout() -> None`
  - Clears authentication state (token only, preserves credentials)

#### Constructor

```python
AuthenticationCore(
    session_store: SessionStore,
    config: Auth0Config,
    error_callback: Optional[Callable[[str, str], None]] = None,
    logger: Optional[logging.Logger] = None
)
```

### Auth0Config

Configuration dataclass for Auth0 settings.

#### Parameters

- `base_url: str` - Base URL for your Auth0 application (required)
- `jwt_cookie_names: List[str]` - Cookie names to check for JWT tokens (default: ["angel_jwt_v2", "angel_jwt"])
- `request_timeout: int` - HTTP request timeout in seconds (default: 30)
- `expiry_buffer_hours: int` - Hours before expiration to attempt refresh (default: 1)
- `user_agent: Optional[str]` - Custom User-Agent string (default: None)

### SessionStore

Abstract base class for session persistence. Implement this for custom storage backends.

#### Required Methods

- `save_token(token: str) -> None`
- `get_token() -> Optional[str]`
- `clear_token() -> None`
- `save_credentials(username: str, password: str) -> None`
- `get_credentials() -> Tuple[Optional[str], Optional[str]]`
- `clear_credentials() -> None`

#### Built-in Implementations

- `InMemorySessionStore` - Simple in-memory storage (not persistent)

### Exceptions

- `AuthenticationError` - Base exception for authentication failures
- `AuthenticationRequiredError` - Session invalid, re-authentication needed
- `InvalidCredentialsError` - Username/password incorrect
- `NetworkError` - Network connectivity issues

## Advanced Usage

### Custom Session Storage

```python
from auth0_ciam_client import AuthenticationCore, SessionStore, Auth0Config
import json
import os

class FileSessionStore(SessionStore):
    def __init__(self, file_path: str = "~/.auth_session.json"):
        self.file_path = os.path.expanduser(file_path)

    def _load_data(self) -> dict:
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_data(self, data: dict) -> None:
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def save_token(self, token: str) -> None:
        data = self._load_data()
        data['token'] = token
        self._save_data(data)

    def get_token(self) -> Optional[str]:
        return self._load_data().get('token')

    def clear_token(self) -> None:
        data = self._load_data()
        data.pop('token', None)
        self._save_data(data)

    def save_credentials(self, username: str, password: str) -> None:
        data = self._load_data()
        data['username'] = username
        data['password'] = password
        self._save_data(data)

    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        data = self._load_data()
        return data.get('username'), data.get('password')

    def clear_credentials(self) -> None:
        data = self._load_data()
        data.pop('username', None)
        data.pop('password', None)
        self._save_data(data)

# Use custom storage
config = Auth0Config(base_url="https://your-app.auth0.com")
auth = AuthenticationCore(
    session_store=FileSessionStore(),
    config=config
)
```

### Error Handling

```python
from auth0_ciam_client import (
    AuthenticationCore, Auth0Config, InMemorySessionStore,
    AuthenticationError, InvalidCredentialsError, NetworkError
)

auth = AuthenticationCore(
    session_store=InMemorySessionStore(),
    config=Auth0Config(base_url="https://your-app.auth0.com")
)

try:
    result = auth.authenticate(username, password)
    if not result.success:
        print(f"Authentication failed: {result.error_message}")
except InvalidCredentialsError:
    print("Invalid username or password")
except NetworkError:
    print("Network connectivity issue - check your connection")
except AuthenticationError as e:
    print(f"Authentication error: {e}")
```

### Logging

```python
import logging
from auth0_ciam_client import AuthenticationCore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("my_app")

# Pass logger to AuthenticationCore
auth = AuthenticationCore(
    session_store=InMemorySessionStore(),
    config=config,
    logger=logger
)
```

## Development

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=auth0_ciam_client --cov-report=html

# Run specific test file
pytest tests/test_core.py
```

### Code Quality

```bash
# Format code
black auth0_ciam_client/ tests/

# Lint code
flake8 auth0_ciam_client/ tests/

# Type checking
mypy auth0_ciam_client/
```

### Building

```bash
# Build distribution
python -m build

# Install locally
pip install -e .
```

## License

GPL-3.0-only

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a Pull Request

## Disclaimer

This package is not officially affiliated with Auth0 Inc. or Angel Studios. It provides client-side utilities for interacting with Auth0 authentication services and is designed for educational and development purposes.