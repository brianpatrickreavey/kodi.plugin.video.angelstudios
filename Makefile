# Makefile for common development tasks

lint:
	flake8 plugin.video.angelstudios/ --max-line-length=120
	black plugin.video.angelstudios/ --line-length 120

unittest:
	pytest tests/unit/

unittest-with-coverage:
	.venv/bin/python -m pytest --cov=plugin.video.angelstudios --cov-report=term-missing tests/unit

coverage:
	pytest --cov=plugin.video.angelstudios tests/unit/

zip:
	git archive -o angelstudios-kodi-addon.zip HEAD