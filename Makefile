.PHONY: help run dev docker-up docker-down docker-build docker-logs migrate makemigrations test shell clean

PYTHON := .venv/bin/python

help:
	@echo "========================================================================"
	@echo "                      ReadAndQues Project Commands                      "
	@echo "========================================================================"
	@echo "  make run           : Start Docker services & launch local Django server"
	@echo "  make docker-up     : Start all services via Docker Compose"
	@echo "  make docker-down   : Stop all Docker Compose services"
	@echo "  make docker-build  : Build and start all Docker Compose services"
	@echo "  make docker-logs   : Tail logs from Docker Compose containers"
	@echo "  make migrate       : Apply Django database migrations"
	@echo "  make makemigrations: Generate new Django database migrations"
	@echo "  make test          : Run Django automated tests"
	@echo "  make shell         : Open Django interactive shell"
	@echo "  make clean         : Remove Python byte code & cache files"
	@echo "  make init-db       : Initialize database (Mongo indexes, migrations, BM25)"
	@echo "  make seed-db       : Initialize database and seed sample articles"
	@echo "========================================================================"

run: dev

dev: docker-up
	@echo "🚀 Launching Django server on 0.0.0.0:8000..."
	cd ReadAndQues && ../$(PYTHON) manage.py runserver 0.0.0.0:8000

docker-up:
	@echo "🐳 Starting Docker background services (Postgres, Mongo, ChromaDB)..."
	docker compose up -d

docker-down:
	@echo "🛑 Stopping Docker services..."
	docker compose down

docker-build:
	@echo "🏗️ Building and starting Docker services..."
	docker compose up -d --build

docker-logs:
	@echo "📜 Tailing Docker container logs..."
	docker compose logs -f

migrate: docker-up
	@echo "🗄️ Applying Django migrations..."
	cd ReadAndQues && ../$(PYTHON) manage.py migrate

makemigrations:
	@echo "📝 Generating Django migrations..."
	cd ReadAndQues && ../$(PYTHON) manage.py makemigrations

init-db: docker-up
	@echo "🛠️ Initializing database (Migrations, Superuser, Indexes)..."
	cd ReadAndQues && ../$(PYTHON) manage.py init_db

seed-db: docker-up
	@echo "🌱 Initializing database and seeding sample articles..."
	cd ReadAndQues && ../$(PYTHON) manage.py init_db --seed

test: docker-up
	@echo "🧪 Running Django test suite..."
	cd ReadAndQues && ../$(PYTHON) manage.py test articles

shell: docker-up
	@echo "💻 Opening Django shell..."
	cd ReadAndQues && ../$(PYTHON) manage.py shell

clean:
	@echo "🧹 Cleaning up bytecode and cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache
