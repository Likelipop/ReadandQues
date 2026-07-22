cmake_minimum_required(VERSION 3.10)
project(ReadAndQues NONE)

set(PYTHON "${CMAKE_SOURCE_DIR}/.venv/bin/python")
set(CELERY "${CMAKE_SOURCE_DIR}/.venv/bin/celery")
set(DJANGO_DIR "${CMAKE_SOURCE_DIR}/ReadAndQues")

# Custom target: run / dev
add_custom_target(run
    COMMAND docker compose up -d
    COMMAND ${PYTHON} ${DJANGO_DIR}/manage.py runserver 0.0.0.0:8000
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Starting Docker background services and launching Django server..."
)

# Custom target: worker
add_custom_target(worker
    COMMAND docker compose up -d
    COMMAND ${CELERY} -A worker_service.celery_app worker -l info -Q ai_queue
    WORKING_DIRECTORY ${DJANGO_DIR}
    COMMENT "Starting Celery worker process for ai_queue..."
)

# Custom target: docker-up
add_custom_target(docker-up
    COMMAND docker compose up -d
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Starting Docker background services..."
)

# Custom target: docker-down
add_custom_target(docker-down
    COMMAND docker compose down
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Stopping Docker services..."
)

# Custom target: docker-build
add_custom_target(docker-build
    COMMAND docker compose up -d --build
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Building and starting Docker services..."
)

# Custom target: docker-logs
add_custom_target(docker-logs
    COMMAND docker compose logs -f
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Tailing logs from Docker containers..."
)

# Custom target: migrate
add_custom_target(migrate
    COMMAND docker compose up -d
    COMMAND ${PYTHON} ${DJANGO_DIR}/manage.py migrate
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running Django database migrations..."
)

# Custom target: makemigrations
add_custom_target(makemigrations
    COMMAND ${PYTHON} ${DJANGO_DIR}/manage.py makemigrations
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generating Django database migrations..."
)

# Custom target: test
add_custom_target(test
    COMMAND docker compose up -d
    COMMAND ${PYTHON} ${DJANGO_DIR}/manage.py test articles
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running Django automated tests..."
)

# Custom target: shell
add_custom_target(shell
    COMMAND docker compose up -d
    COMMAND ${PYTHON} ${DJANGO_DIR}/manage.py shell
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Opening Django shell..."
)
