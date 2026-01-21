.PHONY: help build up down logs clean test

# Default target
help:
	@echo "Available commands:"
	@echo "  build     - Build all Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - View logs from all services"
	@echo "  clean     - Remove all containers, images, and volumes"
	@echo "  test      - Run tests for all services"
	@echo "  db-init   - Initialize database with schema"

# Build all Docker images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Clean up everything
clean:
	docker-compose down -v --rmi all --remove-orphans
	docker system prune -f

# Run tests
test:
	docker-compose exec ats-service pytest
	docker-compose exec api-gateway npm test
	docker-compose exec testing-service npm test

# Initialize database
db-init:
	docker-compose exec postgres psql -U postgres -d recruitment_db -f /docker-entrypoint-initdb.d/init.sql

# Check service health
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | jq '.'
	@curl -s http://localhost:8001/health | jq '.'
	@curl -s http://localhost:8002/health | jq '.'
	@curl -s http://localhost:8003/health | jq '.'
	@curl -s http://localhost:8004/health | jq '.'
	@curl -s http://localhost:8005/health | jq '.'

# Development setup
dev-setup:
	cp .env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make build && make up"