# Data Structure & Caching Architecture

## Overview
This document provides an overview of the two-level caching architecture that optimizes data fetching and enables cross-path cache reuse between navigation flows (continue watching, series browsing, playback). For detailed sections, see the linked sub-documents below.

## Decision
Implemented a two-level cache system: project index cache for navigation and episode detail cache for playback/display.

## Rationale
- Episode data fetched once and reused everywhere (e.g., continue watching episodes available when browsing series)
- Project cache serves as navigation index with sparse episode metadata
- Episode cache contains complete playback data
- Watch positions always fresh from fat resumeWatching query

## Core Principles
1. **Episode data should be fetched once and reused everywhere** - An episode cached from continue watching should be available when browsing that series, and vice versa
2. **Project cache serves as navigation index** - Projects contain sparse episode metadata needed for menu rendering
3. **Episode cache contains complete playback data** - Full metadata including source URLs, artwork, watch position
4. **Watch positions are always fresh** - Fat resumeWatching returns complete fresh data and blindly overwrites cache

## Cache Structure

### Two-Level Cache System

```
┌─────────────────────────────────────────────────────────────┐
│                     SimpleCache (Kodi)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Project Index Cache (Navigation)                           │
│  ├─ project_{slug}                                          │
│  │  ├─ name, slug, projectType (full metadata)             │
│  │  └─ seasons[]                                            │
│  │     ├─ id, name, seasonNumber                           │
│  │     └─ episodes[] (SPARSE - navigation only)            │
│  │        ├─ id, guid, episodeNumber, __typename           │
│  │        └─ (5 fields for ordering/batch fetch)           │
│  │                                                          │
│  Episode Detail Cache (Playback & Display)                  │
│  └─ episode_{guid}                                          │
│     ├─ All fields from EpisodeListItem fragment            │
│     ├─ source {url, duration, credits}                     │
│     ├─ watchPosition {position} (merged from API)          │
│     ├─ artwork, metadata, availability                     │
│     └─ projectSlug (for reverse lookup)                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Cache Key Patterns
| Key | Content | Purpose | Size | TTL |
|-----|---------|---------|------|-----|
| `project_{slug}` | Full project + sparse episodes | Navigation | ~5-10KB | 8h default |
| `episode_{guid}` | Complete episode data | Display/playback | ~5KB | 72h default |

## Sub-Documents
- [Cache Strategy](data-structure-cache-strategy.md): Detailed cache write strategies, coherence, and staleness handling.
- [Data Flows](data-structure-data-flows.md): The three main data flows with optimization impacts.
- [Episode Formats](data-structure-episode-formats.md): Sparse vs. full episode data and normalization.
- [Implementation](data-structure-implementation.md): SimpleCache characteristics, GraphQL requirements, and design rationale.

For episode artwork details (STILL images, ContentSeries integration), see [data-structure-artwork-mapping.md](data-structure-artwork-mapping.md).

## For Agents/AI
Two-level cache with project index and episode details; use fat queries for fresh data; normalize API responses; cache at episode level for reuse.