# Manual tests

These checks need a person. `make unittest` and `dev/script.angelstudios.integration-testing` cannot do them.

The map of every main-menu item and every addon setting is `docs/dev/test-inventory.md`. That file says which layer covers each one.

Before a push to `main` that touches a row, run that row. Write the date and what you saw in the last column.

The rule for that push is in the process repo `README.md`, under Ship.

## Captions

`make kodi-test` checks the caption track Kodi reports. It does not read the words on the picture. `make kodi-test-look` leaves the picture up. Use that when you fill these rows in.

| Check | What you should see | Last result |
| --- | --- | --- |
| English words | `make kodi-test-look KODI_CAPTION_TEST=captions-english`. Tuttle Twins, season 1, episode 1. The words follow the speech and use Kodi's subtitle font. | 2026-11-18. Tuttle Twins, season 1, episode 1. The captions followed the speech. |
| Captions turned off | `make kodi-test-look KODI_CAPTION_TEST=captions-off`. Same episode. After captions turn off, the picture has no words. | 2026-11-20. After captions turned off, the picture had no words. The video kept playing. |
| No subtitle language | `make kodi-test-look KODI_CAPTION_TEST=captions-none`. Same episode. No words on the picture. | 2026-11-20. No words on the picture. |
| Spanish words | `make kodi-test-look KODI_CAPTION_TEST=captions-spanish`. Same episode. The words are Spanish. | 2026-11-20. The words were Spanish. |
| Forced only | `make kodi-test-look KODI_CAPTION_TEST=captions-forced-only`. Same episode. No words. This episode has no forced track. | 2026-11-20. No words. |
| No caption tracks | `make kodi-test-look KODI_CAPTION_TEST=no-captions`. Kensuke's Kingdom. No words, and no caption choice. | 2026-11-20. Kensuke's Kingdom had no words and no caption choice. |
| Hearing impaired on | `make kodi-test-look KODI_CAPTION_TEST=hearing-impaired-on`. Young Washington. English closed captions, including sound cues, not the regular track. | 2026-11-20. No words on the screen. The check reported that English closed captions were on. |
| Hearing impaired off | `make kodi-test-look KODI_CAPTION_TEST=hearing-impaired-off`. Young Washington. Regular English words, not the closed-caption track. | 2026-11-20. Regular English words were on the screen. |

## Guild Voting

`make kodi-test-guild` checks two things after sign-in. The main menu has Guild Voting directly above Settings. The Guild Voting folder starts with Already voted on, then lists torch links and does not open one. Angel can offer a different torch in a category on the next read, so that check does not compare the two lists title by title. It does not vote. It does not play a torch. An empty ballot list still opens, and shows Already voted on.

Do not submit a vote from this list unless you mean to change your Guild ballot. Name the torch first.

| Check | What you should see | Last result |
| --- | --- | --- |
| Questions after the torch | Open one torch from Guild Voting. The picture and audio play. The questions stay hidden. Stop the torch, or let it finish. The two questions appear after that. Choose No on "Submit this vote?". The website ballot for that torch is unchanged. | 2026-11-20. Opened Quitters episode 2, stopped it, and canceled the vote. That torch was still unvoted on the website. |
| Torch with no stream | Open a torch that has no stream. Kodi says "This torch cannot be played yet." The vote questions do not appear. | Not run. No current torch is known to have no stream. See the inventory. |
| DRM torch, install cancelled | Open a DRM torch. Kodi asks to install Widevine. Choose Cancel. Kodi says the torch is protected by DRM, and that Widevine can be installed from the addon settings, under Install Widevine. The vote questions do not appear. No vote is sent. | Not run. This pass does not install Widevine or cancel that installer. See the inventory. |
| DRM torch plays | Open a DRM torch. If Kodi asks to install Widevine, install it and accept the license. The picture and audio play. The questions stay hidden until the torch ends or you stop it. Choose No. The website ballot is unchanged. | Not run. This pass does not install Widevine. See the inventory. |
| Install Widevine setting | In the addon settings, next to Use InputStream Adaptive, choose Install Widevine. If it is already installed, Kodi says "Widevine is installed." If you cancel the installer, no second error appears. | Not run. This pass does not open the Widevine installer. See the inventory. |
| Empty list | When Angel has no torches, open Guild Voting. The folder shows "Already voted on" and no torch links. | Not run. This pass does not empty the ballot. The row can run only when Angel has no torches. See the inventory. |
| Real vote | Only when you name the torch. Submit the two answers. The website shows those answers. A comment, recommended age, or age reason already saved on the website is still there. | Not run. No torch was named, and this pass does not send a vote. See the inventory. |
| List after a vote | After a vote you asked to send, leave Guild Voting and open it again. That torch is gone from the ballot list. | Not run. It waits on a real vote. See the inventory. |
| Already voted on | In Guild Voting, open Already voted on. The torch you voted on is listed. Open it. The picture and audio play. The two questions do not appear. | Not run. `make kodi-test-guild` checks that the row is first and does not open it. This pass does not play a finished torch. See the inventory. |
| Signed out | Sign out, then open the addon. Guild Voting is absent. Settings is still last. This clears the saved login. Do not use `make kodi-test-guild` for this row. That run signs back in. Use `make kodi-test-signed-out`. Press OK on Force Logout. The check signs back in. | 2026-11-20. While logged out, Guild Voting was gone. After signing in again, Guild Voting was back. The check cleared the saved login and did not sign back in. Settings was not checked. The check is issue #33. |
| Not a Guild member | An account that is signed in and is not a Guild member opens Guild Voting and sees "Join the Guild to vote." This needs an account other than the one used for the vote rows. | Not run. This pass has no second account. See the inventory. |

## Playback

`make kodi-test-playback` plays Kensuke's Kingdom from the start for a few seconds and stops. It fails if Kodi opens a dialog. `make kodi-test-playback-look` leaves the picture up. Use that when you fill the picture row in.

`make kodi-test-continue` reads Continue Watching, then resumes one in-progress movie, episode, or special and stops. The clock is the Kodi result. A person does not have to read the resume dialog for that row.

| Check | What you should see | Last result |
| --- | --- | --- |
| Picture and audio | `make kodi-test-playback-look`. Kensuke's Kingdom. The picture and the audio play. Kodi does not ask to install Widevine. | 2026-11-18. Kensuke's Kingdom had picture and audio. The check did not see a Widevine dialog. |
| Resume clock | `make kodi-test-continue`. One in-progress title starts near the saved position, then stops. | 2026-11-18. Failed. Wingfeather Saga, "Snickbuzzards and Snow Boggans," had 18:19 saved. The player was at 38 seconds. Stopping saved those 38 seconds over the old position. The seek is issue #34. |

## Watchlist

`make kodi-test-watchlist` hides the folder, shows it, compares it with the website, opens the first title's page, and saves then removes one title that was not already saved. It does not play video. The picture for a played title is the Playback row above.

| Check | What you should see | Last result |
| --- | --- | --- |
| Folder and list | `make kodi-test-watchlist`. The folder follows its setting. The titles match the website. One title is saved and then removed. | 2026-11-20. The folder listed 3 titles in Angel's order. The check opened The Spy Next Door without playing it. It added Kensuke's Kingdom and then removed it. |
| Play a saved title | Open one watchlist title and play it. The picture and audio play. This is the same kind of play as the Playback row. | Not run. This pass uses the Kensuke playback row for the picture. See the inventory. |

## Top Picks

The Kodi folder check shows and hides Top Picks For You. It does not open the folder. Opening it shows an OK dialog, and the script cannot press OK.

| Check | What you should see | Last result |
| --- | --- | --- |
| Not available yet | Turn on Top Picks For You. Open it. Kodi says "Top Picks is not available yet." Press OK. Turn the setting off again. | Not run. The dialog blocks the script, and this pass does not open it. The unit check is `test_top_picks_menu_placeholder`. |

## Session

The session action opens a text viewer. The script cannot close it. Settings, this dialog, Install Widevine, clear cache, clear debug data, and Force Logout do not sign in again. The unit checks are `test_session_details_do_not_refresh` and `test_settings_and_logout_do_not_refresh`.

| Check | What you should see | Last result |
| --- | --- | --- |
| Saved session | In the addon settings, under Authentication, choose Show Angel Studios Session details. The login email and the session times are shown. Close the viewer. | Not run. The text viewer blocks the script, and this pass does not open it. |
