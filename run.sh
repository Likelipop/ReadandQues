#!/usr/bin/env bash
set -e

# Determine project directory
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

echo "🐳 [1/3] Khởi chạy Docker Compose (MongoDB & Postgres)..."
docker compose up -d

echo "🐍 [2/3] Kích hoạt môi trường ảo Python (.venv)..."
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "⚠️ Không tìm thấy thư mục .venv!"
    exit 1
fi

echo "📂 [3/3] Di chuyển vào ReadAndQues và khởi chạy Python runserver..."
cd ReadAndQues
python manage.py runserver 0.0.0.0:8000
