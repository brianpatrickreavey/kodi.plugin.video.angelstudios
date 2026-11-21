# Makefile for Kodi Angel Studios addon development
SHELL := /bin/bash

# Directory and module definitions
ADDON_DIRS := plugin.video.angelstudios/
PACKAGE_DIR := auth0-ciam-client/
TEST_DIRS := tests/
ADDON_MODULES := plugin.video.angelstudios

.PHONY: lint black flake8 format format-and-lint unittest unittest-with-coverage coverage kodi-test kodi-test-look kodi-test-watchlist kodi-test-guild kodi-test-catalog kodi-test-folders kodi-test-continue kodi-test-playback kodi-test-playback-look kodi-test-tags kodi-test-maintenance kodi-test-auth kodi-test-signed-out zip
.PHONY: lint-all test-all clean-all help

# === HELP ===
help:
	@echo "Kodi Angel Studios Addon Development Targets:"
	@echo "  lint              - Lint addon code only"
	@echo "  test              - Test addon only"
	@echo "  lint-all          - Lint addon and package"
	@echo "  test-all          - Test addon and package"
	@echo "  format            - Format addon code"
	@echo "  format-and-lint   - Format and lint addon"
	@echo "  unittest-with-coverage - Test with coverage (addon only)"
	@echo "  kodi-test         - Start Kodi if it is closed, run KODI_CAPTION_TEST (default all), then quit it"
	@echo "  kodi-test-look    - Same, and leave each play on screen for a person to watch"
	@echo "  kodi-test-watchlist - Read the signed-in watchlist in Kodi. One check adds a title and removes it"
	@echo "  kodi-test-guild   - Read Guild Voting in Kodi. Does not open a torch or send a vote"
	@echo "  kodi-test-catalog - Open Movies, Series, and Dry Bar. Does not play"
	@echo "  kodi-test-folders - Show and hide each folder setting, then put the settings back"
	@echo "  kodi-test-continue - Read Continue Watching, then resume one in-progress title"
	@echo "  kodi-test-playback - Play Kensuke's Kingdom from the start, then stop"
	@echo "  kodi-test-playback-look - Same, and leave the picture up for a person"
	@echo "  kodi-test-tags    - Read watch-page tags on a movie, a series, and a special"
	@echo "  kodi-test-maintenance - Clear the cache and the debug data"
	@echo "  kodi-test-auth    - Clear the saved token, open Movies, and sign in again"
	@echo "  kodi-test-signed-out - Sign out, check Guild Voting is gone, then sign back in"
	@echo "  zip               - Create addon zip"
	@echo "  clean-all         - Clean all build artifacts"
	@echo "  help              - Show this help"

# === FORMATTING (Addon only) ===
black:
	black --line-length=120 $(ADDON_DIRS) $(TEST_DIRS)

black-check:
	black --check --line-length=120 $(ADDON_DIRS) $(TEST_DIRS)

format: black

# === LINTING ===
flake8:
	flake8 $(ADDON_DIRS) $(TEST_DIRS) --max-line-length=120

pyright:
	pyright $(ADDON_DIRS)

lint: black-check flake8
	pyright $(ADDON_DIRS)

format-and-lint: format lint

# === TESTING (Addon only) ===
unittest:
	pytest $(TEST_DIRS)unit/ -v

# Starts Kodi when it is closed, asks it to run the program addon, then reads
# the result file. Quits Kodi only when this run started it. Not part of unittest.
# Angel has to be signed in, and the program addon has to be enabled.
KODI_CAPTION_TEST ?= all
KODI_WATCHLIST_TEST ?= watchlist
KODI_GUILD_TEST ?= guild
KODI_CATALOG_TEST ?= catalog
KODI_FOLDERS_TEST ?= folders
KODI_CONTINUE_TEST ?= continue
KODI_PLAYBACK_TEST ?= playback
KODI_TAGS_TEST ?= title-tags
KODI_MAINTENANCE_TEST ?= maintenance
KODI_AUTH_TEST ?= auth
KODI_SIGNED_OUT_TEST ?= signed-out

kodi-test:
	KODI_CAPTION_TEST="$(KODI_CAPTION_TEST)" pytest $(TEST_DIRS)kodi/test_event_packet.py $(TEST_DIRS)kodi/test_kodi_app.py $(TEST_DIRS)kodi/test_playlist.py $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_captions_live.py -v

# Same checks, and the watched plays stay on screen. Not part of unittest.
kodi-test-look:
	KODI_CAPTION_LOOK=1 KODI_CAPTION_TEST="$(KODI_CAPTION_TEST)" pytest $(TEST_DIRS)kodi/test_event_packet.py $(TEST_DIRS)kodi/test_kodi_app.py $(TEST_DIRS)kodi/test_playlist.py $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_captions_live.py -v

# Reads the signed-in watchlist. Does not play video. watchlist-add-remove saves
# one title that is not already saved, then removes it. Not part of unittest.
kodi-test-watchlist:
	KODI_WATCHLIST_TEST="$(KODI_WATCHLIST_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_watchlist_expect.py $(TEST_DIRS)kodi/test_watchlist_live.py -v

# Reads Guild Voting after sign-in. Does not open a torch and does not send a vote.
# An empty ballot list still opens and shows Already voted on. Not part of unittest.
kodi-test-guild:
	KODI_GUILD_TEST="$(KODI_GUILD_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_guild_expect.py $(TEST_DIRS)kodi/test_guild_live.py -v

# Opens Movies, Series, and Dry Bar Comedy Specials, then the first title in each.
# Does not play. Not part of unittest.
kodi-test-catalog:
	KODI_CATALOG_TEST="$(KODI_CATALOG_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_catalog_live.py -v

# Shows and hides each folder setting, then puts every setting back. Not part of unittest.
kodi-test-folders:
	KODI_FOLDERS_TEST="$(KODI_FOLDERS_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_folders_live.py -v

# Reads Continue Watching, then resumes one in-progress title and stops. Not part of unittest.
kodi-test-continue:
	KODI_CONTINUE_TEST="$(KODI_CONTINUE_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_continue_live.py -v

# Plays Kensuke's Kingdom from the start and stops. Does not install Widevine.
kodi-test-playback:
	KODI_PLAYBACK_TEST="$(KODI_PLAYBACK_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_playback_live.py -v

# Same play, and the picture stays up. Not part of unittest.
kodi-test-playback-look:
	KODI_PLAYBACK_LOOK=1 KODI_PLAYBACK_TEST="$(KODI_PLAYBACK_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_playback_live.py -v

# Reads watch-page tags from the three catalog folders. Does not play.
kodi-test-tags:
	KODI_TAGS_TEST="$(KODI_TAGS_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_tags_live.py -v

# Clears the addon cache and the debug trace files. Does not sign out.
kodi-test-maintenance:
	KODI_MAINTENANCE_TEST="$(KODI_MAINTENANCE_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_maintenance_live.py -v

# Clears the saved token, opens Movies, and leaves the new token in place.
kodi-test-auth:
	KODI_AUTH_TEST="$(KODI_AUTH_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_auth_live.py -v

# Signs out and signs back in. Press OK on Force Logout. Not part of unittest.
kodi-test-signed-out:
	KODI_SIGNED_OUT_TEST="$(KODI_SIGNED_OUT_TEST)" pytest $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_signed_out_live.py -v

unittest-with-coverage:
	python -m pytest --cov=$(ADDON_MODULES) --cov-report=term-missing --cov-fail-under=90 $(TEST_DIRS)unit

coverage:
	pytest --cov=$(ADDON_MODULES) $(TEST_DIRS)unit/

# === COORDINATION TARGETS (Addon + Package) ===
lint-all: lint
	@echo "Linting auth0-ciam-client package..."
	cd $(PACKAGE_DIR) && make lint

test-all: unittest-with-coverage
	@echo "Testing auth0-ciam-client package..."
	cd $(PACKAGE_DIR) && make test

# === UTILITY ===
zip:
	git archive -o angelstudios-kodi-addon.zip HEAD

clean-all: clean-addon clean-package

clean-addon:
	find $(ADDON_DIRS) $(TEST_DIRS) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(ADDON_DIRS) $(TEST_DIRS) -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/

clean-package:
	cd $(PACKAGE_DIR) && make clean