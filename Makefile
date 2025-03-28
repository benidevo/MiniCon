setup-dev:
	poetry install --with dev
	poetry run pre-commit install

format:
	poetry run black .
	poetry run isort .

lint:
	poetry run flake8
	poetry run mypy src

test:
	poetry run pytest -xvs tests/

test-coverage:
	poetry run pytest --cov=src tests/

check-all: format lint test

.PHONY: setup-dev format lint test test-coverage check-all
