# Kodi Addon Checker Remediation Plan

## Issues to Address

- Resize addon icon from 1024x1024 to 512x512 pixels
- Refactor main.py entry point to reduce from 112 lines to under 15 lines
- Remove or exclude __pycache__ directories from addon package
- Decide on GraphQL files - either remove, embed in Python, or accept warnings
- Remove or convert .webp fanart file to .png/.jpg format
- Ensure all addon files use only whitelisted extensions
- Test addon validation passes with zero warnings/errors
- Update build process to exclude development files
- Add kodi-addon-checker to CI pipeline for automated validation ✅
- Add kodi-addon-checker as pre-commit hook (with __pycache__ warnings accepted)