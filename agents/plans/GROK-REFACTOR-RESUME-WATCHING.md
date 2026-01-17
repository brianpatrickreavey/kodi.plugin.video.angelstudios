# GROK REFACTOR RESUME WATCHING: Fix Continue Watching Regression with Fat Query Pattern

## Overview
The Continue Watching menu currently shows all episodes as unavailable due to a broken legacy/new path logic in `continue_watching_menu` (always falls back to legacy processing, where normalized episodes lack "source"). This phase adopts the "fat query" pattern (like projects) by expanding `query_resumeWatching.graphql` to include full content fields (e.g., source subfields) in one query, eliminating the batch-fetch step. Deferred until after GROK-REFACTOR-PHASE-1.md (Kodi UI refactor) to avoid scope overlap.

## Goals
- Fix regression: Ensure Continue Watching episodes show as available when they have sources.
- Adopt "fat" pattern: Single query for full data, reducing API calls.
- Maintain pagination (by 10s) and backward compatibility.
- Fragment queries for clarity; reuse existing fragments where possible.
- Preserve 100% unit test coverage.

## Current Issues
- **Broken Logic**: `continue_watching_menu` checks `if "episodes" in resume_data` → always triggers legacy path → episodes lack "source" → unavailable.
- **Thin Query**: `query_resumeWatching.graphql` returns minimal content (id, name) → requires separate batch fetch.
- **No Fragments**: No dedicated fragments for specials/movies; fields inlined or need creation.

## Proposed Solution
Modify `query_resumeWatching.graphql` to include full content fields via unions and fragments. Update `continue_watching_menu` to remove faulty legacy check (always use "fat" data). Handle remapping for specials/movies (source subfields at higher level, different naming).

### Key Changes
1. **Expand Query**: Replace minimal content with full unions (e.g., `... on ContentEpisode { ...EpisodeListItem }` for episodes; inline/adapt for specials/movies).
2. **Fragments**: Create new fragments (e.g., `fragment_ContentSpecial.graphql`, `fragment_ContentMovie.graphql`) for specials/movies, reusing fields from existing queries where possible (e.g., overlap with `query_getEpisodeAndUserWatchData.graphql`).
3. **Menu Logic**: Remove `if "episodes" in resume_data` check; always process as "fat" data with source available.
4. **Remapping**: Extend helpers (e.g., `_normalize_resume_episode`) to handle either shape (thin vs. fat).

## Implementation Steps
1. **Analyze Overlaps**: Review `query_getEpisodeAndUserWatchData.graphql` for reusable fields/fragments.
2. **Create Fragments**: Add `fragment_ContentSpecial.graphql` and `fragment_ContentMovie.graphql` with source subfields (higher level, different naming).
3. **Update Query**: Modify `query_resumeWatching.graphql` to use unions and new/existing fragments.
4. **Update Menu**: Remove legacy check in `continue_watching_menu`; ensure processing handles full data.
5. **Test**: Run `make unittest-with-coverage`; verify episodes show available.

## Risks
- API may not support full content in resumeWatching—test query first.
- Response size with pagination—monitor for issues.
- Fragment reuse may require adjustments.

## Progress
- Deferred until Phase 1 complete.
- High-level plan ready; implement after UI refactor.

## Reference Query
```
query ResumeWatching($first: Int, $after: String) {
  resumeWatching(first: $first, after: $after) {
    edges {
      node {
        id
        watchableGuid
        position
        updatedAt
        content {
          __typename
          ... on ContentEpisode {
            id
            project {
              slug
              projectType
              name
              id
              __typename
            }
            name
            episodeSubtitle: subtitle
            slug
            url
            releaseDate
            introStartTime
            introEndTime
            genres
            cast {
              name
              __typename
            }
            duration
            episodeNumber
            posterCloudinaryPath
            posterLandscapeCloudinaryPath
            watchableAvailabilityStatus
            watchableAt
            actionsToWatch {
              __typename
            }
            episodeImage: image(aspect: "16:9", category: STILL_1) {
              cloudinaryPath
              __typename
            }
            episodeDescription: description(version: SHORT)
            season {
              id
              seasonNumber
              __typename
            }
            __typename
          }
          ... on ContentSpecial {
            id
            project {
              slug
              projectType
              name
              id
              __typename
            }
            name
            specialSubtitle: subtitle
            duration
            posterCloudinaryPath
            posterLandscapeCloudinaryPath
            watchableAvailabilityStatus
            watchableAt
            actionsToWatch {
              __typename
            }
            specialImage: image(aspect: "16:9", category: STILL_1) {
              cloudinaryPath
              __typename
            }
            specialDescription: description(version: SHORT)
            __typename
          }
          ... on ContentMovie {
            id
            name
            movieSubtitle: subtitle
            duration
            posterCloudinaryPath
            posterLandscapeCloudinaryPath
            watchableAvailabilityStatus
            watchableAt
            actionsToWatch {
              __typename
            }
            movieImage: image(aspect: "16:9", category: STILL_1) {
              cloudinaryPath
              __typename
            }
            movieDescription: description(version: SHORT)
            project {
              slug
              projectType
              name
              id
              __typename
            }
            __typename
          }
          ... on ContentDisplayable {
            id
            name
            description(version: SHORT)
            landscapeNonTitleImage: image(aspect: "16:9", category: NON_TITLE_ART) {
              cloudinaryPath
              __typename
            }
            landscapeStillImage: image(aspect: "16:9", category: STILL_1) {
              cloudinaryPath
              __typename
            }
            __typename
          }
        }
        __typename
      }
      __typename
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
      __typename
    }
    __typename
  }
}
```
