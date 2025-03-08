run:
	docker compose up --build --remove-orphans

enter:
	docker exec -it minicon-dev bash

stop:
	docker compose down -v