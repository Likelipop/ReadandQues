.PHONY: run docker-up docker-down migrate test

# Full startup flow: Docker Compose up -> Runserver
run: docker-up
	@echo "🚀 Launching Django server..."
	cd ReadAndQues && ../.venv/bin/python manage.py runserver 0.0.0.0:8000

docker-up:
	@echo "🐳 Starting Docker services..."
	docker compose up -d

docker-down:
	@echo "🛑 Stopping Docker services..."
	docker compose down

migrate: docker-up
	@echo "🗄️ Running migrations..."
	cd ReadAndQues && ../.venv/bin/python manage.py migrate

test: docker-up
	@echo "🧪 Running tests..."
	cd ReadAndQues && ../.venv/bin/python manage.py test articles
