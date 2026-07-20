cmake_minimum_required(VERSION 3.10)
project(ReadAndQues NONE)

# Custom target: run
# Executes: docker compose up -> activates virtual environment -> runs Django dev server
add_custom_target(run
    COMMAND docker compose up -d
    COMMAND ${CMAKE_SOURCE_DIR}/.venv/bin/python ${CMAKE_SOURCE_DIR}/ReadAndQues/manage.py runserver 0.0.0.0:8000
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Starting Docker containers and launching Django server..."
)

add_custom_target(docker-up
    COMMAND docker compose up -d
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Starting Docker services (MongoDB & PostgreSQL)..."
)

add_custom_target(docker-down
    COMMAND docker compose down
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Stopping Docker services..."
)

add_custom_target(migrate
    COMMAND docker compose up -d
    COMMAND ${CMAKE_SOURCE_DIR}/.venv/bin/python ${CMAKE_SOURCE_DIR}/ReadAndQues/manage.py migrate
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running Django database migrations..."
)
