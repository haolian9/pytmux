.PHONY: install tests

freeze_as_requirements:
	@ poetry export --format requirements.txt --without-hashes > requirements.txt

install: freeze_as_requirements
	@ python3 -m venv venv
	@ venv/bin/pip install -U -r requirements.txt

lint:
	@ poetry run mypy --show-column-numbers --ignore-missing-imports pytmux
	@ poetry run pylint pytmux

test:
	@ poetry run pytest --color=yes --show-capture=all

shell:
	@ PYTHONPATH=${PWD} poetry shell
