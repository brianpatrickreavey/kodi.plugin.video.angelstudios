# Performance Instrumentation

## Overview
This document describes the configurable performance logging system implemented to measure bottlenecks in menu loading times without cluttering the codebase.

## Decision
Implemented a hybrid approach using decorators for function-level timing and context managers for sub-block timing, controlled by an addon setting.

## Rationale
- Provides data to assess optimizations like deferred cache writes
- Clean implementation that doesn't impact production performance
- Configurable to avoid log spam

## Setting
- **ID**: `enable_performance_logging`
- **Type**: Boolean
- **Default**: `false`
- **Location**: Advanced settings in addon configuration

## Usage

### Function-Level Timing
Apply the `@timed` decorator to methods for total execution time:

```python
from kodi_utils import timed

@timed
def projects_menu(self, content_type=""):
    # Entire method timed
```

### Block-Level Timing
Use `TimedBlock` context manager for sub-sections:

```python
from kodi_utils import TimedBlock

with TimedBlock('api_fetch'):
    data = api_call()
with TimedBlock('ui_render'):
    render_items(data)
```

## Output
- **Format**: `[PERF] block_name: 123.45ms`
- **Level**: `LOGINFO`
- **Requirements**: Kodi log level set to `INFO` or `DEBUG` to see logs
- **Location**: Kodi log viewer

## Examples
- `[PERF] projects_menu: 450.23ms`
- `[PERF] projects_api_fetch: 320.12ms`
- `[PERF] continue_watching_api_fetch: 280.45ms`

## Analysis Tips
- Compare API fetch vs. UI render times
- Identify cache hits/misses impact
- Measure impact of deferred writes if implemented
- Average across multiple runs for consistency

## Files
- `kodi_utils.py`: `timed` decorator and `TimedBlock` class
- `kodi_menu_handler.py`: Applied to `projects_menu`, `seasons_menu`, `episodes_menu`, `continue_watching_menu`
- `resources/settings.xml`: `enable_performance_logging` setting

## For Agents/AI
Enable performance logging to gather timing data; logs appear at INFO level; use for bottleneck analysis.