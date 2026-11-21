# Test inventory

Every main-menu item and every addon setting is listed here. Each one points at its unit checks, its Kodi check, and its manual rows. Where a layer does not apply, this file says why.

Unit checks run with `make unittest` from this repo. GitHub Actions runs that suite. It does not start Kodi.

Kodi checks live in `dev/script.angelstudios.integration-testing`. That program addon is not in the release zip. `make kodi-test` is still only the caption checks. Every other bundle has its own `make` target. None of those targets sends a Guild vote, plays a torch through to the questions, or installs Widevine.

Manual rows live in `docs/dev/manual-tests.md`.

## Main menu

| Item | Unit | Kodi | Manual |
| --- | --- | --- | --- |
| Movies | `tests/unit/test_kodi_menu_handler.py` builds the row. `tests/unit/test_kodi_playback_handler.py` plays a movie and seeks when Resume was chosen. | `make kodi-test-catalog` opens the folder and the first title. `make kodi-test-playback` plays Kensuke's Kingdom from the start and stops. It fails if a dialog opens. | Picture and audio: Playback section. |
| Series | Same menu tests. `test_resume_choice_seeks_saved_position` covers series. Episode caption playback is the caption bundle. | `make kodi-test-catalog` opens the folder and the first title. A series episode is played by `make kodi-test` (Tuttle Twins). | Caption words are the Captions section. The picture uses the same player as the movie row. |
| Dry Bar Comedy Specials | Same menu tests. `test_resume_choice_seeks_saved_position` covers specials. | `make kodi-test-catalog` opens the folder and the first title. | No separate picture row. The play path is the same `play_episode` path as movies. |
| Podcasts | `test_main_menu_non_bool_setting_falls_back_to_default` and the folder toggle tests. The setting default in `settings.xml` is off. | `make kodi-test-folders` shows the row, hides it, and puts the setting back. The folder is not opened. | A person does not have to open Podcasts. The check is the menu row. |
| Livestreams | Same as Podcasts. The default is off. | `make kodi-test-folders` shows the row, hides it, and puts the setting back. The folder is not opened. | A person does not have to open Livestreams. The check is the menu row. |
| Continue Watching | `tests/unit/test_kodi_ui_interface_coverage.py` builds the rows. `test_continue_watching_does_not_seek` says the menu link does not seek. The link leaves `content_type` empty. | `make kodi-test-continue` compares the folder with Angel, then resumes one in-progress title through the catalog link and stops. | The clock is the Kodi result. A person does not have to read a resume dialog. |
| Watchlist | `tests/unit/test_watchlist.py`. | `make kodi-test-watchlist`. One check saves a title and removes it. Nothing is played. | Watchlist section. The picture is the Playback row. |
| Top Picks For You | `test_top_picks_menu_placeholder` expects "Top Picks is not available yet." | `make kodi-test-folders` shows and hides the row. It does not open the folder. Opening it is an OK dialog the script cannot press. | Top Picks section. Not opened this pass. |
| Guild Voting | `tests/unit/test_guild_voting.py`. Questions, the unplayable torch, replay, and Widevine are covered there. | `make kodi-test-guild` reads the menu and the torch list. It does not open a torch or send a vote. | Guild Voting section. This pass plays one torch and chooses No. It does not send a vote, install Widevine, or empty the ballot. |
| Settings | `test_settings_and_logout_do_not_refresh`. Opening settings does not sign in. | No Kodi check. `openSettings` is a dialog the script cannot close. | The session row is the part a person has to read. The settings screen itself is not a separate row. |

## Playback and progress

| Behavior | Unit | Kodi | Manual |
| --- | --- | --- | --- |
| A movie, episode, or special plays from its stream | `tests/unit/test_kodi_playback_handler.py` | Movie: `make kodi-test-playback`. Episode: the caption bundle. Special: the catalog folder opens. The special uses the same play path. | Playback section for the movie picture and audio. |
| Resume offers the saved position | `test_resume_choice_seeks_saved_position`, `test_play_from_beginning_does_not_seek`, `test_continue_watching_does_not_seek` | `resume-saved` in `make kodi-test-continue`. On 2026-11-18 it failed: Wingfeather Saga, "Snickbuzzards and Snow Boggans," started at 38 seconds instead of the saved 18:19. | The Kodi check records the clock. The failure is in the Playback section. The seek is issue #34. |
| Preferred video quality | `test_play_video_quality_exact_match_no_isa` and the quality helpers in `tests/unit/test_kodi_playback_handler.py` | No Kodi check. The player does not report which rung it chose. | A person cannot see the rung on the picture. |
| Stopping sends the watch position | `tests/unit/test_watch_progress.py` | No separate Kodi check. The 2026-11-18 resume play stopped at 38 seconds and that position replaced the saved 18:19. A check that proved a brand-new position would move that title on purpose. | Not a manual row. |
| These plays do not ask for Widevine | Movie and episode playback does not attach a Widevine license. Guild DRM is separate. | `playback-movie` fails if a yes/no, OK, or select dialog opens. | Playback section. |
| Closed captions | `tests/unit/test_captions.py` | `make kodi-test` for Tuttle Twins, Kensuke's Kingdom, and Young Washington. `make kodi-test-look` leaves the picture up. | Captions section. The 2026-11-20 look filled the word rows. Young Washington with hearing-impaired captions on showed no words while the closed-caption track was selected. |

## Addon settings

| Setting | What it does | Unit | Kodi | Manual |
| --- | --- | --- | --- | --- |
| Preferred video quality (`video_quality`) | Picks a rung for a normal stream. | `test_play_video_quality_exact_match_no_isa` | No Kodi check. The player does not report the rung. | A person cannot see the rung. |
| Use preferred quality for torches (`torch_viewer_quality`) | Off until the viewer turns it on. Off plays the highest torch row this device can decrypt. On uses Preferred video quality. | `test_software_ladder_picks_the_highest_software_row` and `test_viewer_quality_setting_keeps_1080` in `tests/unit/test_guild_voting.py`. The default in `settings.xml` is off. | No Kodi check. Proving the rung means playing a torch, and these targets do not play a torch. | Not run. This pass does not compare torch rungs. |
| Request timeout (`request_timeout`) | How long one Angel request may take. | No unit check names this setting. It does not change a menu. | No Kodi check. A live check would have to stall the network. | Not a manual row. |
| Username (`username`) | Saved login name. | `tests/unit/test_angel_authentication.py` stores it. `tests/unit/test_main.py` uses it to refresh. | `make kodi-test-auth` and `make kodi-test-signed-out` use it. The checks do not print it. | The session dialog shows the email. That dialog is not opened this pass. |
| Password (`password`) | Saved password. | The same store tests. | The same two targets. The password is not written into the result. Sign-out keeps a recovery file at `/tmp/plugin.video.angelstudios.login-recovery.json` until sign-in works again, then deletes it. | Not a manual row. |
| JWT Token (`jwt_token`) | Hidden setting. Level 4. | The session store tests. | `make kodi-test-auth` clears it and expects a new token before Movies opens. | Not a viewer control. |
| Token refresh buffer (`expiry_buffer_hours`) | How early a token counts as expired. | `tests/unit/test_angel_authentication.py` | No Kodi check. Proving it means waiting until the buffer. | Not a manual row. |
| Show Angel Studios Session details (`show_auth_details`) | Opens the session text viewer. Does not sign in. | `test_router_show_information` and `test_session_details_do_not_refresh` | No Kodi check. The text viewer blocks the script. | Session section. Not opened this pass. |
| Movies (`show_movies`) | Shows or hides Movies. Default on. | `test_main_menu_respects_setting_toggle_off` | `make kodi-test-folders` | The menu row is the check. |
| Series (`show_series`) | Shows or hides Series. Default on. | Same menu tests. | `make kodi-test-folders` | The menu row is the check. |
| Dry Bar Comedy Specials (`show_specials`) | Shows or hides that folder. Default on. | Same menu tests. | `make kodi-test-folders` | The menu row is the check. |
| Podcasts (`show_podcasts`) | Default off. | Same menu tests. | `make kodi-test-folders` | The menu row is the check. |
| Livestreams (`show_livestreams`) | Default off. | Same menu tests. | `make kodi-test-folders` | The menu row is the check. |
| Continue Watching (`show_continue_watching`) | Shows or hides the folder. | Same menu tests. | `make kodi-test-folders` | The menu row is the check. The list itself is `make kodi-test-continue`. |
| Top Picks For You (`show_top_picks`) | Default off. | `test_top_picks_menu_placeholder` | `make kodi-test-folders` shows and hides the row. | Top Picks section. |
| Other Content (`show_other_content`) | Default off. The setting does not add a main-menu row. | No unit check asserts the missing row. The menu builder has no entry for this setting. | `make kodi-test-folders` turns it on and checks that no Other Content row appears, then puts it back. | Not a manual row. There is nothing to see. |
| Watchlist (`show_watchlist`) | Default off. | `tests/unit/test_watchlist.py` | `make kodi-test-watchlist` and `make kodi-test-folders` | Watchlist section. |
| Use InputStream Adaptive (`use_isa`) | Default on. Streams use it. | The playback handler tests. | `make kodi-test-playback` starts a stream. The check does not turn this off. | Not a separate row. Turning it off would stop playback. |
| Install Widevine (`install_widevine`) | Runs the Widevine installer. | `tests/unit/test_kodi_playback_handler.py` covers the ready and install paths. | No Kodi check. These targets must not install Widevine. | Guild Voting section. Not run this pass. |
| Disable cache (`disable_cache`) | Hidden at level 3. Default off. | `tests/unit/test_kodi_cache_manager.py` | No Kodi check. Turning it off is not something a menu row can show. | Not a manual row. |
| Projects cache expiration (`projects_cache_hours`) | Level 3. | `test_cache_ttl_uses_setting_int` | No Kodi check. | Not a manual row. |
| Project cache expiration (`project_cache_hours`) | Level 3. | The cache manager tests. | No Kodi check. | Not a manual row. |
| Episodes cache expiration (`episodes_cache_hours`) | Level 3. | The cache manager tests. | No Kodi check. | Not a manual row. |
| Enable performance logging (`enable_performance_logging`) | Level 3. Default off. | No unit check names this setting. It only adds log lines. | No Kodi check. | Not a manual row. |
| Enable prefetch (`enable_prefetch`) | Level 3. Default off. | The prefetch tests in the menu and cache suites. | No Kodi check. | Not a manual row. |
| Prefetch project count (`prefetch_project_count`) | Level 3. | The same prefetch tests. | No Kodi check. | Not a manual row. |
| Debug mode (`debug_mode`) | Default off. | `test_get_debug_mode`, `test_is_debug`, and `test_is_trace` in `tests/unit/test_kodi_ui_helpers.py` | No Kodi check. Debug and trace can put secrets in the log. | Not a manual row. |
| Promote artwork debug logs (`debug_art_promotion`) | Level 2. Default off. | No unit check names this setting. It only promotes log lines. | No Kodi check. | Not a manual row. |
| Promote timing debug logs (`debug_timing_promotion`) | Level 2. Default off. | No unit check names this setting. It only promotes log lines. | No Kodi check. | Not a manual row. |
| Promote API debug logs (`debug_api_promotion`) | Level 2. Default off. | No unit check names this setting. It only promotes log lines. | No Kodi check. | Not a manual row. |
| Promote cache debug logs (`debug_cache_promotion`) | Level 2. Default off. | No unit check names this setting. It only promotes log lines. | No Kodi check. | Not a manual row. |
| Promote miscategorized debug logs (`debug_miscategorized_promotion`) | Level 2. Default off. | No unit check names this setting. It only promotes log lines. | No Kodi check. | Not a manual row. |
| Promote uncategorized debug logs (`debug_uncategorized_promotion`) | Level 2. Default off. | No unit check names this setting. It only promotes log lines. | No Kodi check. | Not a manual row. |
| Promote all debug logs (`debug_promote_all`) | Level 2. Default off. | No unit check names this setting. It only promotes log lines. | No Kodi check. | Not a manual row. |
| Log authentication steps (`log_auth_steps`) | Default off. When on, the log can include the email and the start of the token. | No unit check names this setting. | No Kodi check. This pass does not turn it on. | Not a manual row. |
| Log authentication steps warned (`log_auth_steps_warned`) | Hidden. Level 4. Not a viewer control. | No unit check names this setting. | No Kodi check. | Not a manual row. |
| Clear cache now (`clear_cache`) | Clears the addon cache and reports success or failure. Does not sign in. | `test_clear_cache_with_notification_success` and the failure test. | `make kodi-test-maintenance` reads the log line `Cache cleared successfully via settings`. | The notification is the same outcome the log records. A person does not have to read it. |
| Force logout (`force_logout`) | Revokes the Angel session and clears the token, username, and password. Does not sign in on the way out. | `test_force_logout_success` and `test_settings_and_logout_do_not_refresh` | `make kodi-test-signed-out`. Press OK on the logout dialog. On 2026-11-20 the check cleared the saved login and did not sign back in. | Guild Voting section, Signed out row. The check is issue #33. |
| Clear debug data (`clear_debug_data`) | Removes trace files and reports success or failure. Does not sign in. | `test_clear_debug_data_with_notification` | `make kodi-test-maintenance` reads the log line `Debug data cleared via settings`. | The notification is the same outcome the log records. A person does not have to read it. |

## Rows this pass does not run

- Torch with no stream. No current torch is known to return no stream. The unit check is `test_unplayable_torch_does_not_ask_the_questions`.
- DRM torch, install cancelled. DRM torch plays. Install Widevine. These targets must not install Widevine, and this pass does not open the installer.
- Empty Guild list. The row can run only when Angel has no torches. This pass does not empty the ballot. `make kodi-test-guild` already allows an empty list and checks that Already voted on is the first row.
- Real vote, and the list after that vote. No torch was named. This pass does not send a vote.
- Already voted on playback. `make kodi-test-guild` checks that the row is first and does not open it.
- Not a Guild member. This pass has no second account.
- Top Picks dialog and the session text viewer. Both block the script. The unit checks name the words and the session lines.
- Torch quality on the picture. Proving the rung means playing a torch far enough to compare it. This pass stops one torch only to see the questions, and it does not compare rungs.
