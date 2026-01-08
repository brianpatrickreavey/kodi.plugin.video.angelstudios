# Tracking features for Angel Studios KODI Plugin

# Angel Studios Features
## Watched Progress Tracking
This seems to be tracked within Angel Studios, so there must be progressive API
calls taht we can make to update our progress on the Angel Studios Servers.
This is then served back to us when loading a project and when we go to play
an actual episode, a dialog pops up asking to resume or not.

# Plugin Configuration Options Features

## Playback

### Test Hygiene
- Consider switching test fixtures to use a fresh `xbmcaddon.Addon` mock per test to avoid state leakage when toggling cache settings.

## Authentication
* Implement remote logout endpoint call when available (currently only clears local session state)

# Code Review
- [addon.xml](plugin.video.angelstudios/addon.xml) — COMPLETE
- [helpers.py](plugin.video.angelstudios/helpers.py) — COMPLETE
- [main.py](plugin.video.angelstudios/main.py) — COMPLETE
- [resources/images/icons/Angel_Studios_Logo.png](plugin.video.angelstudios/resources/images/icons/Angel_Studios_Logo.png) — COMPLETE
- [resources/images/fanart/Angel_Studios_Fanart.webp](plugin.video.angelstudios/resources/images/fanart/Angel_Studios_Fanart.webp) — COMPLETE
- [resources/language/resource.language.en_gb/strings.po](plugin.video.angelstudios/resources/language/resource.language.en_gb/strings.po) — COMPLETE
- [resources/settings.xml](plugin.video.angelstudios/resources/settings.xml) — COMPLETE
- [resources/lib/__init__.py](plugin.video.angelstudios/resources/lib/__init__.py) — COMPLETE
- [resources/lib/angel_authentication.py](plugin.video.angelstudios/resources/lib/angel_authentication.py) — COMPLETE
- [resources/lib/angel_interface.py](plugin.video.angelstudios/resources/lib/angel_interface.py) — COMPLETE
- [resources/lib/inputstream_helper.py](plugin.video.angelstudios/resources/lib/inputstream_helper.py) — COMPLETE (merged into kodi_ui_interface.py)
- [resources/lib/kodi_ui_interface.py](plugin.video.angelstudios/resources/lib/kodi_ui_interface.py) — TODO
- [resources/lib/angel_graphql/query_getProjectsForMenu.graphql](plugin.video.angelstudios/resources/lib/angel_graphql/query_getProjectsForMenu.graphql) — TODO
- [resources/lib/angel_graphql/query_getProject.graphql](plugin.video.angelstudios/resources/lib/angel_graphql/query_getProject.graphql) — TODO
- [resources/lib/angel_graphql/query_getEpisodeAndUserWatchData.graphql](plugin.video.angelstudios/resources/lib/angel_graphql/query_getEpisodeAndUserWatchData.graphql) — TODO
- [resources/lib/angel_graphql/fragment_ProjectMetadata.graphql](plugin.video.angelstudios/resources/lib/angel_graphql/fragment_ProjectMetadata.graphql) — TODO
- [resources/lib/angel_graphql/fragment_ProjectBasic.graphql](plugin.video.angelstudios/resources/lib/angel_graphql/fragment_ProjectBasic.graphql) — TODO
- [resources/lib/angel_graphql/fragment_ContentImage.graphql](plugin.video.angelstudios/resources/lib/angel_graphql/fragment_ContentImage.graphql) — TODO
- [resources/lib/angel_graphql/fragment_DiscoveryImages.graphql](plugin.video.angelstudios/resources/lib/angel_graphql/fragment_DiscoveryImages.graphql) — TODO
