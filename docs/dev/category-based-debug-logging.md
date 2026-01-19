# Category-Based Debug Logging

## Overview

The Kodi addon implements category-based debug logging to enable selective debugging of performance-critical code paths without the 85-90% performance penalty of global debug logging.

## How It Works

Debug messages can be assigned to categories (`art`, `api`) and selectively promoted to INFO level through user settings. When a category toggle is disabled, those debug messages remain at DEBUG level and have zero performance impact. Performance timing uses the dedicated `[PERF]` logging system.

## User Settings

Located in **Settings → Troubleshooting → Troubleshooting settings**:

- **Debug mode**: Controls overall debug logging level (`off`, `debug`, `trace`)
- **Promote artwork debug logs**: Shows artwork processing debug messages at INFO level
- **Promote timing debug logs** (deprecated): Previously controlled performance timing debug messages; now use "Enable performance logging" setting
- **Promote API debug logs**: Shows GraphQL API debug messages at INFO level

## Categories

### `art` Category
Debug logs related to artwork processing and resolution:
- Still image selection (portraitStill1, portraitTitleImage, etc.)
- Cloudinary URL generation and reuse
- Logo injection from projects to episodes
- Artwork dictionary construction

### `timing` Category (Deprecated)
**Note**: Performance timing now uses the dedicated `[PERF]` logging system controlled by the "Enable performance logging" setting. The `timing` category is no longer used in active code.

### `api` Category
GraphQL API communication:
- Query execution and response logging
- Authentication session validation
- Error handling and retries

## Usage in Code

```python
# Promote to INFO when art toggle enabled
self.log.debug("Processing artwork still", category="art")

# Promote to INFO when API toggle enabled
self.log.debug("GraphQL query executed", category="api")

# Regular debug (no category) - only promoted if debug_mode is debug/trace
self.log.debug("General debug message")
```

## Performance Impact

- **Disabled categories**: ~0ms overhead (no string operations, no logging)
- **Enabled categories**: ~0.1-0.2ms per promoted message
- **Unknown categories**: ~0.3ms (warning logged for missing settings)

## Benefits

- Zero performance cost for disabled debug logging
- Granular control over debug output visibility
- Maintains debugging capability in hot paths
- Backwards compatible with existing code
- Automatic detection of unknown categories

## Troubleshooting

If debug messages don't appear as expected:
1. Verify Kodi's log level includes INFO messages
2. Check that the appropriate category toggle is enabled
3. Look for "Unknown debug category" warnings in logs
4. Ensure debug_mode is set to "debug" or "trace" for general debug visibility

## Implementation Details

- Logger class: `KodiLogger` in `kodi_utils.py`
- Settings mapping: `main.py` builds category promotions dict
- Category validation: Unknown categories trigger INFO warnings
- Backwards compatibility: Existing `debug()` calls work unchanged</content>
<parameter name="filePath">/home/bpreavey/Code/kodi.plugin.video.angelstudios/docs/dev/category-based-debug-logging.md