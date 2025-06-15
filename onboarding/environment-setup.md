# Environment Setup Guide 🛠️

Welcome to the environment setup guide! This guide will walk you through setting up your development environment for the Imangor API project. We'll make sure you have everything you need to start contributing to the codebase.

## Prerequisites

Before we begin, ensure you have the following installed on your system:

- Python 3.11 or higher
- Docker and Docker Compose
- Git
- A code editor (VS Code recommended)
- PostgreSQL (optional, as we use Docker)
- Redis (optional, as we use Docker)

## Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/your-org/imangor-api.git
cd imangor-api

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

## Step 2: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # If you have one
```

## Step 3: Environment Configuration

1. Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

2. Configure the following environment variables in your `.env` file:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/imangor
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/imangor_test

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json

# Other settings
ENVIRONMENT=development
DEBUG=True
```

## Step 4: Docker Setup

Our application uses Docker for containerization. Here's how to set it up:

1. Build the Docker images:

```bash
docker-compose build
```

2. Start the services:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database
- Redis server
- Celery worker
- Celery beat
- The main application

## Step 5: Database Setup

1. Run database migrations:

```bash
# Using Alembic
alembic upgrade head
```

2. (Optional) Seed the database with initial data:

```bash
python scripts/seed_database.py
```

## Step 6: Verify Installation

1. Check if all services are running:

```bash
docker-compose ps
```

2. Run the test suite:

```bash
pytest
```

3. Start the development server:

```bash
uvicorn main:app --reload
```

4. Visit http://localhost:8000/docs to see the API documentation

## Common Issues and Solutions

### Database Connection Issues

If you can't connect to the database:
1. Check if PostgreSQL is running: `docker-compose ps`
2. Verify your DATABASE_URL in .env
3. Try restarting the containers: `docker-compose restart`

### Redis Connection Issues

If Redis isn't connecting:
1. Check Redis status: `docker-compose ps`
2. Verify REDIS_URL in .env
3. Try restarting Redis: `docker-compose restart redis`

### Celery Issues

If Celery tasks aren't running:
1. Check Celery worker status: `docker-compose ps`
2. View Celery logs: `docker-compose logs -f celery`
3. Restart Celery: `docker-compose restart celery`

## Development Tools Setup

### VS Code Setup

1. Install recommended extensions:
   - Python
   - Pylance
   - Docker
   - GitLens
   - FastAPI Snippets

2. Configure settings.json:

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true
}
```

### Git Setup

1. Configure Git hooks:

```bash
# Install pre-commit hooks
pre-commit install
```

2. Set up your Git identity:

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

## Next Steps

Now that your environment is set up, you can:

1. Read the [Architecture Guide](architecture.md) to understand the system design
2. Check out the [API Development Guide](api-development.md) to start coding
3. Review the [Testing Guide](testing.md) to understand our testing practices

## Need Help?

If you encounter any issues during setup:
1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Search the project's issue tracker
3. Ask in the team's communication channels
4. Schedule a pair programming session with a team member

Happy coding! 🚀 