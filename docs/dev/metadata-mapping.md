# Kodi Metadata Mapping Documentation

**Last Updated:** January 2026
**Kodi Version:** v21
**Purpose:** Comprehensive mapping of Kodi metadata capabilities to Angel Studios API availability and implementation status.

---

## Overview

This document provides a complete inventory of:
1. **Kodi v21 metadata setters** - All available VideoInfoTag and ListItem methods
2. **Angel API fields** - Current and potential fields available from GraphQL responses
3. **Implementation status** - Which metadata is actively being set in the plugin
4. **Technical constraints** - Blocking issues or dependencies for future enhancements

### Status Key

- **✅ Implemented** - Currently being set in code (see implementation file/method)
- **🟡 Available but Not Implemented** - Present in Angel API but not yet applied to Kodi metadata
- **❌ Not Available** - Not found in Angel API responses (API limitation)
- **❓ Unknown** - Needs API exploration; might be available in extended queries

---

## 1. VideoInfoTag Metadata (InfoTagVideo setters)

### Display & Identification

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setTitle(str)` | string | ✅ | `name` (episode/project) | Set from episode/project name | - |
| `setPlot(str)` | string | ✅ | `description` / `theaterDescription` | Full description text | Prefers `description` over `theaterDescription` |
| `setOriginalTitle(str)` | string | 🟡 | UNKNOWN | Not currently used | May exist in extended metadata |
| `setSortTitle(str)` | string | ✅ | Generated (`f"Season {season_number:03d}"`) | Used for numeric season sorting | Custom format, not from API |
| `setTagLine(str)` | string | 🟡 | UNKNOWN | Not currently used | Possible shorthand/tagline field |

### Numeric Identifiers & Numbering

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setEpisode(int)` | integer | ✅ | `episodeNumber` | Episode sequential number | Numeric only; skips if 0 |
| `setSeason(int)` | integer | ✅ | `seasonNumber` | Season sequential number | Skips if 0 (indicates movie) |
| `setYear(int)` | integer | 🟡 | UNKNOWN | Not currently used | Release/aired year |
| `setIMDBNumber(str)` | string | 🟡 | UNKNOWN | Not currently used | External ID mapping |

### Dates & Time

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setPremiered(str)` | string (YYYY-MM-DD) | 🟡 | UNKNOWN | Not currently used | Episode/project premiere date |
| `setDateAdded(str)` | string (YYYY-MM-DD) | 🟡 | UNKNOWN | Not currently used | When item was added to library |

### Ratings & Content Info

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setRating(float)` | float (0.0-10.0) | 🟡 | UNKNOWN | Not currently used | IMDb/user rating; need API confirmation |
| `setVotes(int)` | integer | 🟡 | UNKNOWN | Not currently used | Number of votes for rating |
| `setMpaa(str)` | string | 🟡 | `metadata.contentRating` | Content rating (when available) | Nested under `metadata` |

### Genres & Classification

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setGenres(list[str])` | list of strings | 🟡 | `metadata.genres` | Available in metadata | Nested structure; needs extraction |

### Media Relationships

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setTvShowTitle(str)` | string | ✅ | `project.name` | Project title for episodes | Only set during playback |
| `setCast(list[xbmc.Actor])` | Actor objects | 🟡 | `cast[].name` | Cast list available | Requires Actor object creation; needs testing |
| `setUniqueIDs(dict)` | dict {id_type: id_value} | 🟡 | UNKNOWN | Not currently used | External provider IDs (tmdb, imdb, etc.) |

### Stream & Content Info

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setDuration(int)` | seconds (integer) | ✅ | `source.duration` / `duration` | Episode length in seconds | Priority: `source.duration` > `duration` |
| `setMediaType(str)` | string | ✅ | N/A (mapped by content type) | "video", "episode", etc. | Set via `kodi_content_mapper` |
| `setPlaycount(int)` | integer | 🟡 | `watchPosition` (available) | Not currently set | Could mark watched episodes |
| `setResumePoint(float)` | float (0.0-1.0) | ✅ | `watchPosition.position` + `duration` | Resume progress bar | Calculated ratio (position/duration) |

### Metadata & Classification

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setTrailer(str)` | string (URL) | 🟡 | UNKNOWN | Not currently used | Trailer URL if available |
| `addSeason(int)` | integer | ✅ | `seasonNumber` | Season metadata tagging | Marks item as season in Kodi |

### Special Note: VideoStreamDetail

Added to episodes during playback to indicate codec and resolution:

| Property | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setCodec(str)` | string | ✅ | Hardcoded ("h264") | Video codec hint | Currently hardcoded; could extract from source |
| `setWidth(int)` | pixels | ✅ | Hardcoded (1920) | Video width | Currently hardcoded; could detect from manifest |
| `setHeight(int)` | pixels | ✅ | Hardcoded (1080) | Video height | Currently hardcoded; could detect from manifest |

---

## 2. ListItem Art Metadata (setArt)

### Artwork Types

| Art Type | Status | Angel API Field | Purpose | Current Use | Constraints |
|---|---|---|---|---|---|
| `poster` | ✅ | `discoveryPosterCloudinaryPath` / `posterCloudinaryPath` | Vertical poster (primary) | Set for all content | Cloudinary paths; URL-built via API |
| `landscape` | ✅ | `discoveryPosterLandscapeCloudinaryPath` / `posterLandscapeCloudinaryPath` | Horizontal fanart | Set for all content | Reused as both landscape and fanart |
| `fanart` | ✅ | Same as landscape | Background/hero image | Set for all content | Duplicate of landscape URL |
| `logo` | ✅ | `logoCloudinaryPath` | Clear logo (text-free) | Set for all content | Reused as logo/clearlogo/icon |
| `clearlogo` | ✅ | `logoCloudinaryPath` | Clean logo variant | Set for all content | Reused from logo URL |
| `icon` | ✅ | `logoCloudinaryPath` | Small icon (default) | Set for all content | Reused from logo URL |
| `thumb` | 🟡 | UNKNOWN | Thumbnail/preview | Not currently used | Could be smaller poster variant |
| `banner` | 🟡 | UNKNOWN | Wide banner | Not currently used | Horizontal banner with text |
| `characterart` | ❌ | UNKNOWN | Character artwork | Not available in API | Not in Angel Studios data model |
| `discart` | ❌ | UNKNOWN | Disc/media art | Not available in API | Not applicable to streaming |

---

## 3. ListItem Properties (setProperty)

### Playability & Stream Type

| Property | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `IsPlayable` | string ("true"/"false") | ✅ | `source.url` / `url` presence | True if stream available | Set based on source existence |

### InputStream Adaptive (ISA) Properties

| Property | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `inputstream` | string | ✅ | N/A (config-based) | Set to "inputstream.adaptive" | Only if ISA enabled & available |
| `inputstream.adaptive.manifest_type` | string | ✅ | N/A (config-based) | Set to "hls" | Assumes HLS manifests |
| `inputstream.adaptive.stream_selection_type` | string | ✅ | N/A (quality settings) | "adaptive" / "fixed-res" / "ask-quality" | Based on quality preference |
| `inputstream.adaptive.chooser_resolution_max` | string | ✅ | N/A (quality settings) | "1080p", "720p", etc. | From addon quality settings |

### Network & Loading

| Property | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `inputstream.adaptive.manifest_type` | string | ✅ | N/A | "hls" for all streams | Set during playback setup |
| `IsFolder` | string ("true"/"false") | ✅ | N/A | "false" for episodes; "true" for menus | Playability indicator |

### Other ListItem Methods

| Method | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setPath(str)` | string (URL) | ✅ | `source.url` / `url` | Manifest URL for playback | HLS manifest from API |
| `setLabel(str)` | string | ✅ | `name` / `subtitle` | Display label in menus | Set on ListItem constructor |
| `setLabel2(str)` | string | 🟡 | UNKNOWN | Not currently used | Secondary label (subtitle line 2) |
| `setContentLookup(bool)` | boolean | ✅ | N/A | Set to False for ISA | Prevents Kodi metadata lookup |
| `setMimeType(str)` | string | ✅ | N/A | "application/vnd.apple.mpegurl" for HLS | Set during playback |

---

## 4. Content Type Mapping

### Media Type Classification

| Angel Content Type | Kodi Setter Arg | Kodi Content Type | Status | Example |
|---|---|---|---|---|
| `movie` | `setMediaType()` | "movies" | ✅ | Standalone films |
| `series` | `setMediaType()` | "tvshows" | ✅ | Multi-episode shows |
| `special` | `setMediaType()` | "videos" | ✅ | Dry Bar Comedy Specials |
| `podcast` | `setMediaType()` | "videos" | ✅ | Podcast content |
| `livestream` | `setMediaType()` | "videos" | ✅ | Live streams |

**Important Note:** Episodes always use `setContent("episodes")` regardless of parent type.

---

## 5. Episode-Specific Metadata

### Episode Availability Status

| Status Indicator | Implementation | Status | Constraint |
|---|---|---|---|
| Available | Normal list item display | ✅ | `source` or `url` present |
| Unavailable | `[I] {title} (Unavailable)[/I]` | ✅ | No `source` and no `url` |
| `IsPlayable` | Set to "false" for unavailable | ✅ | Prevents playback attempt |

### Episode Progress Tracking

| Field | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| Resume Point | float (0.0-1.0) | ✅ | `watchPosition.position` / `duration` | Progress bar calculation | Ratio of position to total duration |
| Watch Position (seconds) | integer | 🟡 | `watchPosition.position` | Available but not visualized beyond bar | Could show "1:23:45 / 2:00:00" |

---

## 6. Season-Specific Metadata

### Season Metadata

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `addSeason(int)` | integer | ✅ | `seasonNumber` | Metadata tagging | Marks item as season in Kodi system |
| `setSortTitle(str)` | string | ✅ | Generated (`f"Season {season_number:03d}"`) | Numeric sorting | Custom format; ensures proper order |
| `setMediaType()` | string | ✅ | `kodi_content_mapper[content_type]` | Applied from project type | Inherits parent project type |

### "[All Episodes]" Special Item

| Property | Value | Status | Purpose |
|---|---|---|---|
| Label | "[All Episodes]" | ✅ | Display text in menu |
| Icon | "DefaultRecentlyAddedEpisodes.png" | ✅ | Visual indicator |
| Sort Title | "Season 999" | ✅ | Forces to end of list |
| Parameter | `season_id=None` | ✅ | Triggers flattened episode view |

---

## 7. Project (Series/Movie) Metadata

### Project-Level Information

| Kodi Setter | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| `setTitle()` | string | ✅ | `project.name` | Series/movie title | Set from project data |
| `setPlot()` | string | ✅ | `project.description` | Full project description | - |
| `setMediaType()` | string | ✅ | `kodi_content_mapper[projectType]` | "tvshows" / "movies" / "videos" | Mapped from Angel projectType |
| `setYear()` | integer | 🟡 | UNKNOWN | Not currently used | Release year if available |
| `setGenres()` | list | 🟡 | `metadata.genres` | Available but not extracted | Nested in metadata object |

### Project Artwork

Handled via `setArt()` with Cloudinary paths (see Section 2 above).

---

## 8. Continue Watching & Resumable Content

### Resume Data Structure

| Field | Data Type | Status | Angel API Field | Current Use | Constraints |
|---|---|---|---|---|---|
| Episode GUID | string | ✅ | `episode.guid` | Unique identifier | Required for cache lookup |
| Project Slug | string | ✅ | `episode.projectSlug` / embedded `project.slug` | Navigation reference | Fallback to embedded if needed |
| Watch Position | float (seconds) | ✅ | `watchPosition.position` | Resume point calculation | Combined with duration |
| Duration | integer (seconds) | ✅ | `episode.duration` | Progress bar denominator | Used to calculate ratio |

### Pagination

| Field | Data Type | Status | Angel API Field | Current Use | Constraint |
|---|---|---|---|---|---|
| Has Next Page | boolean | ✅ | `pageInfo.hasNextPage` | Determines "[Load More...]" display | - |
| End Cursor | string (opaque) | ✅ | `pageInfo.endCursor` | Cursor for next page query | Passed to next request |

---

## 9. Known Limitations & Constraints

### API Response Structure

| Constraint | Impact | Workaround |
|---|---|---|
| Sparse episode data in project cache | Only `guid` + `episodeNumber` available; need full fetch for playback | Batch fetch missing episodes via `get_episodes_for_guids()` |
| Nested metadata objects | Content rating, genres in `metadata` subobject | Explicit extraction in `_process_attributes_to_infotags()` |
| Cloudinary path URLs | Paths need conversion to full URLs | `angel_interface.get_cloudinary_url()` handles conversion |
| No direct rating/votes fields | Rating data not in current responses | Marked as ❌ (not available) unless discovered |

### Kodi Integration Constraints

| Constraint | Impact | Workaround |
|---|---|---|
| ISA (InputStream Adaptive) optional | Quality selection requires ISA or manual fallback | Check `xbmc.getCondVisibility()` and adapt UI |
| VideoStreamDetail hardcoded | Codec/resolution not detected from manifest | Currently static (h264, 1920x1080) |
| No native playlist support | Episodes must be played individually | URL routing prevents inline queuing |
| Content type cannot be "seasons" | Seasons must use "tvshows" content type | Fixed mapping in plugin |

### Performance Constraints

| Constraint | Impact | Mitigation |
|---|---|---|
| Large episode count (100+) | UI rendering bottleneck | Pagination in future; streaming aggregation |
| Metadata processing per item | 50-100+ items slow list creation | Deferred cache writes (non-blocking) |
| Image URL building (Cloudinary) | URL reuse pattern implemented | Cache Cloudinary URLs in API interface |

---

## 10. Discovery & Enhancement Process

This section documents how to add new metadata mappings as the Angel API evolves.

### Step 1: Identify New API Fields

When discovering new fields in Angel API responses:

1. **Review GraphQL responses**: Check `resources/graphql/*.graphql` query definitions
2. **Examine raw responses**: Log full API responses in `angel_interface.py`
3. **Check Angel API documentation**: Confirm field availability and structure
4. **Document findings**: Add findings to the "Unknown" (❓) section below

### Step 2: Map to Kodi Capabilities

1. **Consult Kodi v21 API**: Reference `xbmcgui.InfoTagVideo` and `xbmcgui.ListItem` documentation
2. **Test setter availability**: Verify setter exists and accepts expected data type
3. **Validate data transformation**: Ensure Angel API value matches Kodi setter expectations
4. **Document mapping**: Add row to appropriate section (1-9) above

### Step 3: Implementation

1. **Update helper method**: Modify `_process_attributes_to_infotags()` or `_create_list_item_from_episode()`
2. **Add conditional logic**: Only set if field is non-None and valid
3. **Extract nested fields**: Handle dot-notation access (e.g., `metadata.genres`)
4. **Test with coverage**: Ensure 100% unit test coverage per project requirements
5. **Verify in Kodi**: Test visual display in live Kodi UI

### Step 4: Documentation Update

1. **Change status**: Update table status from 🟡 to ✅
2. **Add current use**: Document where it's being set (e.g., "`_process_attributes_to_infotags()` line X")
3. **Update constraints**: Note any limitations discovered
4. **Add test reference**: Link to test case that verifies implementation

### Example: Adding Genre Metadata

**Current state:**
```
| `setGenres(list[str])` | list | 🟡 | `metadata.genres` | Not currently used | Nested structure |
```

**Steps:**
1. Verify `metadata.genres` exists and is list of strings
2. Find Kodi setter: `InfoTagVideo.setGenres(list)` ✅
3. Implement in `_process_attributes_to_infotags()`:
   ```python
   if info_dict.get("metadata", {}).get("genres"):
       info_tag.setGenres(info_dict["metadata"]["genres"])
   ```
4. Add unit test in `test_kodi_ui_interface.py`
5. Update doc status to ✅

**Updated row:**
```
| `setGenres(list[str])` | list | ✅ | `metadata.genres` | Set in _process_attributes_to_infotags() L1700 | Nested under metadata |
```

---

## 11. Unknown/Unexplored Fields

Fields marked ❓ that warrant future investigation:

### Potential API Fields

| Possible Angel API Field | Possible Kodi Setter | Priority | Notes |
|---|---|---|---|
| `originalTitle` | `setOriginalTitle()` | 🔵 Medium | Might exist in extended metadata |
| `year` / `releaseYear` | `setYear()` | 🔵 Medium | Production/release year |
| `premiere` / `airedDate` | `setPremiered()` | 🔵 Medium | Episode premiere date |
| `imdbId` / `externalIds` | `setIMDBNumber()` / `setUniqueIDs()` | 🔵 Medium | External provider IDs |
| `rating` / `imdbRating` | `setRating()` | 🟢 Low | User/critic ratings |
| `trailer` / `trailerUrl` | `setTrailer()` | 🟢 Low | Trailer URL if available |
| `tags` / `keywords` | N/A (display as plot) | 🟢 Low | Searchable keywords |

### Potential Kodi Capabilities Not Yet Used

| Kodi Setter | Data Type | Priority | Why Not Used | Potential Use |
|---|---|---|---|---|
| `setLabel2()` | string | 🟡 | Not exposed in ListItem setup | Secondary subtitle; episode air date? |
| `setPlaycount()` | integer | 🟡 | Requires watched state tracking | Mark played episodes (0 or 1) |
| `addVideoStream()` | VideoStreamDetail | 🔵 | Hardcoded; no manifest parsing | Detect actual codec/resolution |
| `setCast()` | xbmc.Actor list | 🟡 | Not currently extracted | Actor data if available in API |

---

## 12. Testing & Validation

### Unit Test Coverage

All metadata setters are tested in:
- **File**: `tests/unit/test_kodi_ui_interface.py`
- **Coverage**: 100% required (per `make unittest-with-coverage`)
- **Parametrization**: Multiple test data sets for different content types

### Integration Testing

Manual Kodi testing checklist:
- [ ] Episodes display correct title/plot/duration
- [ ] Artwork loads correctly (poster, fanart, logo)
- [ ] Progress bars show accurate resume points
- [ ] Season numbers sort correctly (numeric, not alphabetic)
- [ ] "[All Episodes]" appears at end of list
- [ ] Playback metadata displays (show title, episode #, etc.)

---

## 13. References

- **Kodi v21 Python API**: https://codedocs.xyz/xbmc/xbmc/
- **xbmcgui.InfoTagVideo**: https://codedocs.xyz/xbmc/xbmc/class_xbmc_g_u_i_1_1_info_tag_video.html
- **xbmcgui.ListItem**: https://codedocs.xyz/xbmc/xbmc/class_xbmc_g_u_i_1_1_list_item.html
- **Cloudinary image URLs**: `angel_interface.get_cloudinary_url(path)` method
- **Angel GraphQL API**: See `resources/graphql/*.graphql` and `angel_interface.py`

---

## 14. Changelog

| Date | Change | Impact |
|---|---|---|
| 2026-01-14 | Initial documentation created | Baseline mapping established |
| - | - | - |

---

**Questions?** See [DEVELOPMENT.md](../DEVELOPMENT.md) or create an issue referencing this doc.
