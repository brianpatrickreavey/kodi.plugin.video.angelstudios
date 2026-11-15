# Manual tests

These checks need a person. `make unittest` and `dev/script.angelstudios.integration-testing` cannot do them.

Before a push to `main` that touches a row, run that row. Write the date and what you saw in the last column.

The rule for that push is in the process repo `README.md`, under Ship.

## Captions

`make kodi-test` checks the caption track Kodi reports. It does not read the words on the picture. `make kodi-test-look` leaves the picture up. Use that when you fill these rows in.

| Check | What you should see | Last result |
| --- | --- | --- |
| English words | `make kodi-test-look KODI_CAPTION_TEST=captions-english`. Tuttle Twins, season 1, episode 1. The words follow the speech and use Kodi's subtitle font. | not run |
| Captions turned off | `make kodi-test-look KODI_CAPTION_TEST=captions-off`. Same episode. After captions turn off, the picture has no words. | not run |
| No subtitle language | `make kodi-test-look KODI_CAPTION_TEST=captions-none`. Same episode. No words on the picture. | not run |
| Spanish words | `make kodi-test-look KODI_CAPTION_TEST=captions-spanish`. Same episode. The words are Spanish. | not run |
| Forced only | `make kodi-test-look KODI_CAPTION_TEST=captions-forced-only`. Same episode. No words. This episode has no forced track. | not run |
| No caption tracks | `make kodi-test-look KODI_CAPTION_TEST=no-captions`. Kensuke's Kingdom. No words, and no caption choice. | not run |
| Hearing impaired on | `make kodi-test-look KODI_CAPTION_TEST=hearing-impaired-on`. Young Washington. English closed captions, including sound cues, not the regular track. | not run |
| Hearing impaired off | `make kodi-test-look KODI_CAPTION_TEST=hearing-impaired-off`. Young Washington. Regular English words, not the closed-caption track. | not run |

## Guild Voting

`make kodi-test-guild` checks two things after sign-in. The main menu has Guild Voting directly above Settings. The Guild Voting folder starts with Already voted on, then lists torch links and does not open one. Angel can offer a different torch in a category on the next read, so that check does not compare the two lists title by title. It does not vote. It does not play a torch. An empty ballot list still opens, and shows Already voted on.

Do not submit a vote from this list unless you mean to change your Guild ballot. Name the torch first.

| Check | What you should see | Last result |
| --- | --- | --- |
| Questions after the torch | Open one torch from Guild Voting. The picture and audio play. The questions stay hidden. Stop the torch, or let it finish. The two questions appear after that. Choose No on "Submit this vote?". The website ballot for that torch is unchanged. | not run |
| Torch with no stream | Open a torch that has no stream. Kodi says "This torch cannot be played yet." The vote questions do not appear. | not run |
| DRM torch, install cancelled | Open a DRM torch. Kodi asks to install Widevine. Choose Cancel. Kodi says the torch is protected by DRM, and that Widevine can be installed from the addon settings, under Install Widevine. The vote questions do not appear. No vote is sent. | not run |
| DRM torch plays | Open a DRM torch. If Kodi asks to install Widevine, install it and accept the license. The picture and audio play. The questions stay hidden until the torch ends or you stop it. Choose No. The website ballot is unchanged. | not run |
| Install Widevine setting | In the addon settings, next to Use InputStream Adaptive, choose Install Widevine. If it is already installed, Kodi says "Widevine is installed." If you cancel the installer, no second error appears. | not run |
| Empty list | When Angel has no torches, open Guild Voting. The folder shows "Already voted on" and no torch links. | not run |
| Real vote | Only when you name the torch. Submit the two answers. The website shows those answers. A comment, recommended age, or age reason already saved on the website is still there. | not run |
| List after a vote | After a vote you asked to send, leave Guild Voting and open it again. That torch is gone from the ballot list. | not run |
| Already voted on | In Guild Voting, open Already voted on. The torch you voted on is listed. Open it. The picture and audio play. The two questions do not appear. | not run |
| Signed out | Sign out, then open the addon. Guild Voting is absent. Settings is still last. This clears the saved login. Do not use `make kodi-test-guild` for this row. That run signs back in. | not run |
| Not a Guild member | An account that is signed in and is not a Guild member opens Guild Voting and sees "Join the Guild to vote." This needs an account other than the one used for the vote rows. | not run |
