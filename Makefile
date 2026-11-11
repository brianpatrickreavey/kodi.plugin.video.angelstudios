# Makefile for Kodi Angel Studios addon development
SHELL := /bin/bash

# Directory and module definitions
ADDON_DIRS := plugin.video.angelstudios/
PACKAGE_DIR := auth0-ciam-client/
TEST_DIRS := tests/
ADDON_MODULES := plugin.video.angelstudios

.PHONY: lint black flake8 format format-and-lint unittest unittest-with-coverage coverage kodi-test kodi-test-look zip
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

kodi-test:
	KODI_CAPTION_TEST="$(KODI_CAPTION_TEST)" pytest $(TEST_DIRS)kodi/test_event_packet.py $(TEST_DIRS)kodi/test_kodi_app.py $(TEST_DIRS)kodi/test_playlist.py $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_captions_live.py -v

# Same checks, and the watched plays stay on screen. Not part of unittest.
kodi-test-look:
	KODI_CAPTION_LOOK=1 KODI_CAPTION_TEST="$(KODI_CAPTION_TEST)" pytest $(TEST_DIRS)kodi/test_event_packet.py $(TEST_DIRS)kodi/test_kodi_app.py $(TEST_DIRS)kodi/test_playlist.py $(TEST_DIRS)kodi/test_notices.py $(TEST_DIRS)kodi/test_captions_live.py -v

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