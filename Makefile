run:
	docker compose up --build --remove-orphans

enter:
	docker exec -it minicon-dev bash

stop:
	docker compose down -v

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

check-all: format lint test
