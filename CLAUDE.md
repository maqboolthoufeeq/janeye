# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack production-ready application with:
- **Backend**: FastAPI with async SQLAlchemy, Redis caching, Celery workers, JWT authentication
- **Frontend**: Next.js 15 with TypeScript, Tailwind CSS, cookie-based auth
- **Infrastructure**: Docker Compose for development, Kubernetes-ready for production
- **Package Management**: Backend uses `uv`, Frontend uses `npm`

## Critical Commands

### Backend Development (from root directory)
```bash
# Core development
make dev                    # Start FastAPI dev server with hot reload
make docker-up             # Start all backend services (PostgreSQL, Redis, RabbitMQ, MinIO, Mailpit)
make docker-down           # Stop all services
make docker-logs           # View logs from all services

# Database operations
make db-upgrade            # Run Alembic migrations
make db-migration message="description"  # Create new migration
make db-reset              # Reset database (destructive)

# Code quality
make lint                  # Run ruff linter
make format                # Format with black and isort
make type-check           # Run mypy type checking
make test                 # Run pytest with coverage
make pre-commit           # Run all pre-commit hooks
```

### Frontend Development (from web/ directory)
```bash
npm run dev               # Start Next.js dev server
npm run build            # Build production bundle
npm run lint:fix         # Fix linting issues
npm run format           # Format with prettier
npm run type-check       # TypeScript type checking
npm run pre-commit       # Run all checks before commit (preferred over build)
```

### Docker Environments
```bash
# Development
make docker-build         # Build dev images
make docker-up           # Start dev environment
make docker-shell        # Shell into app container

# Staging
make staging-build       # Build staging images
make staging-up          # Start staging environment

# Production
make prod-build          # Build production image
make prod-up            # Start production environment
```

## Architecture & Code Organization

### Backend Structure (`/back`)
The backend follows a layered architecture with clear separation of concerns:

- **`app/api/`**: API endpoints organized by version and access level
  - `internal/routes/v1/`: Internal API routes (auth, test endpoints)
  - `external/`: External-facing API routes

- **`app/core/`**: Core infrastructure components
  - `db/`: Database connection management (async SQLAlchemy)
  - `caching/`: Redis caching layer
  - `celery/`: Background task configuration
  - `monitoring/`: Logging and Sentry integration

- **`app/models/`**: SQLAlchemy ORM models
  - Uses UUID primary keys
  - Includes mixins for common fields (timestamps, UUID)

- **`app/schemas/`**: Pydantic schemas for validation
  - Separate schemas for request/response
  - Organized by feature domain

- **`app/services/`**: Business logic layer
  - Authentication services (JWT, sessions, OTP)
  - Each service handles a specific domain

- **`app/tasks/`**: Celery background tasks

- **`app/settings/`**: Environment-specific configuration
  - Base settings with Pydantic Settings
  - Environment overrides (dev, staging, production)

### Frontend Structure (`/web`)
Next.js 15 app with App Router:

- **`src/app/`**: App Router pages and layouts
  - `authentication/`: Auth-related pages
  - `profile/`, `user-roles/`: Feature pages

- **`src/components/`**: React components
  - `auth/`: Authentication components (forms, multi-step)
  - `ui/`: Reusable UI components
  - `sidebar/`: Navigation components

- **`src/api/`**: API client layer
  - Feature-based API modules
  - Axios instance with interceptors
  - Type definitions for API responses

- **`src/hooks/`**: Custom React hooks
  - API request wrappers
  - Form validation hooks
  - Auth state management

- **`src/contexts/`**: React contexts
  - Theme management
  - Navigation guards

### Key Design Patterns

1. **Authentication Flow**:
   - Backend: JWT tokens with refresh mechanism
   - Frontend: HTTP-only cookies for secure storage
   - Middleware-based route protection

2. **API Communication**:
   - Backend serves at `/api/v1/`
   - Frontend uses typed API client with axios
   - Automatic token refresh on 401

3. **State Management**:
   - Frontend uses Zustand for global state
   - Hooks pattern for API data caching

4. **Development Workflow**:
   - Docker Compose for service orchestration
   - Hot reload in both backend and frontend
   - Pre-commit hooks for code quality

## Service URLs (Development)

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/v1/docs
- **Frontend**: http://localhost:3000
- **Mailpit UI**: http://localhost:8025
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Flower (Celery)**: http://localhost:5555
- **RabbitMQ Management**: http://localhost:15672 (devuser/devpass)

## Testing Approach

### Backend Testing
- Test files in `back/app/tests/`
- Run with `make test` for full suite
- Uses pytest with async support
- Coverage reports included

### Frontend Testing
- Components should be tested with React Testing Library
- API mocks for isolated testing
- Run `npm test` from web directory

## Important Notes

1. **Database Migrations**: Always create migrations after model changes using `make db-migration message="description"`

2. **Environment Variables**:
   - Backend: Copy `deploy/dev/.env.example` to `.env`
   - Frontend: Copy `web/.env.example` to `.env.local`

3. **Code Style**:
   - Backend: Black formatting, Ruff linting, MyPy type checking
   - Frontend: Prettier formatting, ESLint, TypeScript strict mode
   - Frontend prefers small files (<300 lines), refactor large components

4. **Pre-commit**: Run `make pre-commit` (backend) or `npm run pre-commit` (frontend) before committing

5. **Docker Development**: Use `make docker-up` to start all services. The backend will auto-reload on code changes.

6. **API Testing**: Use `/api/v1/test/*` endpoints to verify service connectivity

7. **Frontend Patterns**:
   - Use Tailwind CSS for styling
   - Create hooks for API requests with Zustand caching
   - Avoid duplicate API calls from re-renders
