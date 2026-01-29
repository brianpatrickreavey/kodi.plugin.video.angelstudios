# Makefile for Kodi Angel Studios addon development
SHELL := /bin/bash

# Directory and module definitions
ADDON_DIRS := plugin.video.angelstudios/
PACKAGE_DIR := auth0-ciam-client/
TEST_DIRS := tests/
ADDON_MODULES := plugin.video.angelstudios

.PHONY: lint black flake8 format format-and-lint unittest unittest-with-coverage coverage zip
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
	@echo "  zip               - Create addon zip"
	@echo "  clean-all         - Clean all build artifacts"
	@echo "  help              - Show this help"

# === FORMATTING (Addon only) ===
black:
	source .venv/bin/activate && black --line-length=120 $(ADDON_DIRS) $(TEST_DIRS)

black-check:
	source .venv/bin/activate && black --check --line-length=120 $(ADDON_DIRS) $(TEST_DIRS)

format: black

# === LINTING ===
flake8:
	source .venv/bin/activate && flake8 $(ADDON_DIRS) $(TEST_DIRS) --max-line-length=120

pyright:
	source .venv/bin/activate && pyright $(ADDON_DIRS)

lint: black-check flake8
	source .venv/bin/activate && pyright $(ADDON_DIRS)

format-and-lint: format lint

# === TESTING (Addon only) ===
unittest:
	source .venv/bin/activate && pytest $(TEST_DIRS)unit/ -v

unittest-with-coverage:
	source .venv/bin/activate && python -m pytest --cov=$(ADDON_MODULES) --cov-report=term-missing $(TEST_DIRS)unit

coverage:
	source .venv/bin/activate && pytest --cov=$(ADDON_MODULES) $(TEST_DIRS)unit/

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