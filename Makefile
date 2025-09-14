.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-30s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development
.PHONY: dev
dev: ## Start development server with hot reload
	cd back && uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

.PHONY: install
install: ## Install dependencies using uv
	cd back && uv pip install -r pyproject.toml --system

.PHONY: install-dev
install-dev: ## Install development dependencies
	cd back && uv pip install -r pyproject.toml --system --dev

.PHONY: format
format: ## Format code with black and isort
	cd back && black . && isort .

.PHONY: lint
lint: ## Run linting with ruff
	cd back && ruff check .

.PHONY: type-check
type-check: ## Run type checking with mypy
	cd back && mypy app

.PHONY: test
test: ## Run tests with pytest
	cd back && pytest tests/ -v --cov=app --cov-report=term-missing

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	cd back && pytest-watch tests/

# Database
.PHONY: db-upgrade
db-upgrade: ## Run database migrations
	cd back && alembic upgrade head

.PHONY: db-downgrade
db-downgrade: ## Downgrade database by one revision
	cd back && alembic downgrade -1

.PHONY: db-migration
db-migration: ## Create new database migration
	cd back && alembic revision --autogenerate -m "$(message)"

.PHONY: db-reset
db-reset: ## Reset database (drop and recreate)
	cd back && alembic downgrade base && alembic upgrade head

# Docker Development
.PHONY: docker-up
docker-up: ## Start all services with docker-compose (development)
	docker-compose -f deploy/dev/docker-compose.yml up -d

.PHONY: docker-down
docker-down: ## Stop all services
	docker-compose -f deploy/dev/docker-compose.yml down

.PHONY: docker-logs
docker-logs: ## Show logs from all services
	docker-compose -f deploy/dev/docker-compose.yml logs -f

.PHONY: docker-build
docker-build: ## Build docker images (development)
	docker-compose -f deploy/dev/docker-compose.yml build

.PHONY: docker-shell
docker-shell: ## Open shell in app container
	docker-compose -f deploy/dev/docker-compose.yml exec app sh

.PHONY: docker-clean
docker-clean: ## Clean up docker resources
	docker-compose -f deploy/dev/docker-compose.yml down -v --remove-orphans

# Docker Staging
.PHONY: staging-up
staging-up: ## Start staging environment
	docker-compose -f deploy/staging/docker-compose.yml up -d

.PHONY: staging-down
staging-down: ## Stop staging environment
	docker-compose -f deploy/staging/docker-compose.yml down

.PHONY: staging-build
staging-build: ## Build staging images
	docker-compose -f deploy/staging/docker-compose.yml build

.PHONY: staging-logs
staging-logs: ## Show staging logs
	docker-compose -f deploy/staging/docker-compose.yml logs -f

# Docker Production
.PHONY: prod-build
prod-build: ## Build production image
	docker build -f back/build/prod/fastapi/Dockerfile -t fastapi-app:prod back/

.PHONY: prod-up
prod-up: ## Start production environment
	docker-compose -f deploy/prod/docker-compose.yml up -d

.PHONY: prod-down
prod-down: ## Stop production environment
	docker-compose -f deploy/prod/docker-compose.yml down

.PHONY: prod-logs
prod-logs: ## Show production logs
	docker-compose -f deploy/prod/docker-compose.yml logs -f

# Kubernetes
.PHONY: k8s-deploy
k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f k8s/

.PHONY: k8s-delete
k8s-delete: ## Delete from Kubernetes
	kubectl delete -f k8s/

.PHONY: k8s-status
k8s-status: ## Show Kubernetes deployment status
	kubectl get pods,svc,deployments

# Utilities
.PHONY: clean
clean: ## Clean up generated files
	find back -type d -name __pycache__ -exec rm -rf {} +
	find back -type f -name "*.pyc" -delete
	find back -type f -name "*.pyo" -delete
	find back -type f -name "*.coverage" -delete
	rm -rf back/.coverage
	rm -rf back/htmlcov
	rm -rf back/.pytest_cache
	rm -rf back/.mypy_cache
	rm -rf back/.ruff_cache

.PHONY: secrets
secrets: ## Generate secret key
	@python -c "import secrets; print(f'SECRET_KEY={secrets.token_hex(32)}')"

.PHONY: shell
shell: ## Open Python shell with app context
	cd back && python -c "import asyncio; from app.core.database import init_db; asyncio.run(init_db())"

.PHONY: celery-worker
celery-worker: ## Start Celery worker
	cd back && celery -A app.tasks.celery_app worker --loglevel=info

.PHONY: celery-beat
celery-beat: ## Start Celery beat scheduler
	cd back && celery -A app.tasks.celery_app beat --loglevel=info

.PHONY: flower
flower: ## Start Flower (Celery monitoring)
	cd back && celery -A app.tasks.celery_app flower

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

.PHONY: pre-commit-install
pre-commit-install: ## Install pre-commit hooks
	pre-commit install

# Documentation
.PHONY: docs
docs: ## Generate API documentation
	cd back && python -m mkdocs serve

.PHONY: docs-build
docs-build: ## Build documentation
	cd back && python -m mkdocs build

# Health checks
.PHONY: health
health: ## Check application health
	curl -f http://localhost:8000/health || exit 1

.PHONY: health-deps
health-deps: ## Check dependency services health
	@echo "Checking PostgreSQL..."
	@pg_isready -h localhost -p 5432 || echo "PostgreSQL is not running"
	@echo "Checking Redis..."
	@redis-cli ping || echo "Redis is not running"
	@echo "Checking RabbitMQ..."
	@curl -s http://localhost:15672 > /dev/null && echo "RabbitMQ is running" || echo "RabbitMQ is not running"
