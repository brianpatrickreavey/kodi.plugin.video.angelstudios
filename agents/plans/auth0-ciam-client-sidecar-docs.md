# Auth0 CIAM Client - Sidecar Documentation

## Project Overview
This package extracts authentication logic from the Kodi Angel Studios addon into a reusable Python library for Auth0 Customer Identity and Access Management (CIAM) flows.

## Architecture Overview

### Core Components
- `auth0_ciam/core.py`: Main `AuthenticationCore` class handling auth flows
- `auth0_ciam/session_store.py`: Abstract `SessionStore` interface + implementations
- `auth0_ciam/exceptions.py`: Custom exception hierarchy
- `auth0_ciam/config.py`: Configuration dataclasses
- `auth0_ciam/utils.py`: JWT validation and helper functions

### Key Design Decisions
- **Abstract Storage**: `SessionStore` interface allows different persistence backends
- **Configuration-Driven**: All Auth0-specific settings parameterized via config
- **Error Alignment**: Exceptions align with Auth0 error responses where possible
- **Headless Operation**: Designed for programmatic use without browser interaction

## Current Implementation Status

### What's Working (Angel Studios Compatible)
- Username/password authentication via web scraping
- JWT token extraction from cookies (`angel_jwt_v2`, `angel_jwt`)
- Token validation and expiration checking
- Session persistence via configurable storage backends
- Automatic token refresh using stored credentials
- Kodi addon integration via `KodiSessionStore`

### Known Limitations (v0.1.0)
- No OAuth PKCE support (uses web scraping instead)
- No refresh token support
- Hardcoded to Angel Studios Auth0 flow
- Limited to username/password authentication
- No multi-factor authentication support

## Migration from Kodi Addon

### Files to Extract
- `plugin.video.angelstudios/resources/lib/angel_authentication.py` (entire file)
- Related tests from `tests/unit/test_angel_authentication.py`
- Angel-specific configuration constants

### Integration Points
- `main.py`: Imports `AuthenticationCore` and `KodiSessionStore`
- `angel_interface.py`: Uses `AuthenticationRequiredError` and `SessionExpiredError`
- Settings: JWT token and credentials stored via Kodi addon settings

### Backward Compatibility
- Keep existing `AngelStudioSession` class as deprecated wrapper
- Maintain same public API for `AuthenticationCore`
- Preserve exception types and messages

## Development Guidelines

### Testing
- 100% unit test coverage target
- Mock external HTTP calls for reliable testing
- Test both generic usage and Angel Studios integration
- Include integration tests for end-to-end flows

### Code Style
- Type hints throughout
- Dataclasses for configuration
- Comprehensive error handling
- Clear separation of concerns

### Versioning
- Semantic versioning (MAJOR.MINOR.PATCH)
- Start at 0.1.0 (working but incomplete)
- Major version bumps for breaking API changes

## Future Enhancements (Post v0.1.0)

### High Priority
- OAuth PKCE flow support
- Refresh token implementation
- Multiple authentication methods (social login, MFA)
- Better error handling with Auth0 error codes

### Medium Priority
- Async/await support
- Connection pooling
- Rate limiting
- Telemetry/logging hooks

### Low Priority
- SAML authentication
- Custom Auth0 rule support
- Multi-tenant configuration
- Admin API integration

## Security Considerations

### Current Implementation
- Credentials stored encrypted via Kodi settings
- JWT tokens validated for expiration
- HTTPS-only communication
- No sensitive data in logs

### Future Improvements
- Token encryption at rest
- Secure credential storage options
- Audit logging capabilities
- Security headers validation

## Deployment Checklist

### Pre-Release
- [ ] All tests passing (467+ tests)
- [ ] Documentation complete
- [ ] License appropriate
- [ ] PyPI name available
- [ ] Version number correct

### Release Process
- [ ] Create GitHub repository
- [ ] Set up CI/CD pipeline
- [ ] Publish to PyPI
- [ ] Update Kodi addon dependency
- [ ] Announce release

### Post-Release
- [ ] Monitor for issues
- [ ] Gather user feedback
- [ ] Plan next version features
- [ ] Update documentation

## Troubleshooting

### Common Issues
- **Import Errors**: Check Python path and virtual environment
- **Network Timeouts**: Verify internet connectivity and firewall settings
- **Auth0 Changes**: Monitor for Auth0 flow modifications
- **Cookie Issues**: Check for Auth0 cookie name changes

### Debug Mode
- Enable detailed logging: Set log level to DEBUG
- Check network requests: Use requests debugging
- Validate tokens: Use JWT decoding tools
- Test credentials: Verify against Auth0 directly

## Support and Maintenance

### Issue Tracking
- Use GitHub Issues for bug reports
- Include full error messages and stack traces
- Provide minimal reproduction cases
- Tag issues with appropriate labels

### Contributing
- Fork repository for contributions
- Create feature branches from main
- Write tests for new functionality
- Update documentation for API changes
- Submit pull requests with clear descriptions

---

*This documentation is designed to provide comprehensive context for new developers or AI assistants working on this project.*