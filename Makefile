# Makefile for common development tasks
SHELL := /bin/bash

.PHONY: lint black flake8 format format-and-lint unittest unittest-with-coverage coverage zip

black:
	source .venv/bin/activate && black --line-length=120 plugin.video.angelstudios/ tests/

black-check:
	source .venv/bin/activate && black --check --line-length=120 plugin.video.angelstudios/ tests/

flake8:
	source .venv/bin/activate && flake8 plugin.video.angelstudios/ tests/ --max-line-length=120

pyright:
	source .venv/bin/activate && pyright plugin.video.angelstudios/

lint: black-check flake8
	source .venv/bin/activate && pyright plugin.video.angelstudios/

format: black

format-and-lint: format lint

unittest:
	source .venv/bin/activate && pytest tests/unit/ -v

unittest-with-coverage:
	source .venv/bin/activate && python -m pytest --cov=plugin.video.angelstudios --cov-report=term-missing tests/unit

coverage:
	source .venv/bin/activate && pytest --cov=plugin.video.angelstudios tests/unit/

zip:
	git archive -o angelstudios-kodi-addon.zip HEAD