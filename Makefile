# Makefile for common development tasks

lint:
	flake8 plugin.video.angelstudios/ --max-line-length=120 --extend-ignore=E501,W503

test:
	pytest tests/

zip:
	git archive -o angelstudios-kodi-addon.zip HEAD