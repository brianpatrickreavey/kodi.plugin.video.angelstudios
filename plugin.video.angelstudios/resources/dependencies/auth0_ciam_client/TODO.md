# TODO: Publish auth0_ciam_client as Kodi Addon

## Goal
Convert the bundled `auth0_ciam_client` package into a standalone Kodi addon that can be distributed via the official Kodi repository, eliminating the need for bundling in the Angel Studios addon.

## Benefits
- Smaller Angel Studios addon size
- Reusable auth component for other addons
- Official Kodi distribution and updates
- Better separation of concerns

## Required Steps

### 1. Package Structure
- Create new Kodi addon: `script.module.auth0-ciam-client`
- Move auth0_ciam_client code to `resources/lib/`
- Add proper `addon.xml` with metadata
- Add license and documentation

### 2. Dependencies
- Declare public dependencies: `script.module.requests`, `script.module.beautifulsoup4`
- Ensure no circular dependencies with Angel Studios addon

### 3. Versioning & Releases
- Set up semantic versioning
- Create GitHub releases
- Submit to Kodi addon repository

### 4. Testing
- Unit tests for the standalone package
- Integration testing with Angel Studios addon
- Kodi compatibility testing

### 5. Migration
- Update Angel Studios addon to use dependency instead of bundling
- Ensure backward compatibility during transition
- Update documentation

## Timeline
- Phase 1: Package creation and testing (1-2 weeks)
- Phase 2: Kodi repository submission (2-4 weeks for approval)
- Phase 3: Migration in Angel Studios addon (1 week)

## Risks
- Repository approval process
- Potential API changes requiring updates
- Dependency conflicts with other addons

## Contacts
- Kodi addon submission: https://kodi.wiki/view/Add-on_submission