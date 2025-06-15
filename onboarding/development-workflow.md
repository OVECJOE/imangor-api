# Development Workflow Guide 🔄

Welcome to our development workflow guide! This document explains how we work together as a team, from setting up your development environment to deploying changes to production.

## Table of Contents

1. [Overview](#overview)
2. [Development Process](#development-process)
3. [Code Organization](#code-organization)
4. [Version Control](#version-control)
5. [Code Review](#code-review)
6. [Testing Strategy](#testing-strategy)
7. [Deployment Process](#deployment-process)
8. [Documentation](#documentation)

## Overview

Our development workflow is designed to:
- Ensure code quality and consistency
- Facilitate collaboration
- Maintain system reliability
- Enable rapid iteration
- Support continuous delivery

## Development Process

### 1. Task Management

We use GitHub Issues and Projects to manage our work:

1. **Issue Creation**
   - Create a new issue for each task
   - Use issue templates for consistency
   - Label issues appropriately
   - Assign to team members
   - Link to related issues/PRs

2. **Issue Types**
   - 🐛 Bug: Something isn't working
   - ✨ Feature: New functionality
   - 🔧 Enhancement: Improvement to existing feature
   - 📝 Documentation: Documentation updates
   - 🧪 Test: Adding or improving tests
   - 🔄 Refactor: Code restructuring

3. **Issue Template**
```markdown
## Description
[Detailed description of the issue]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Details
- [ ] Database changes needed
- [ ] API changes needed
- [ ] Frontend changes needed

## Dependencies
- Related issues: #123, #456
- Blocked by: #789

## Additional Context
[Any additional information]
```

### 2. Branch Strategy

We follow a trunk-based development approach:

1. **Main Branches**
   - `main`: Production-ready code
   - `develop`: Integration branch
   - `staging`: Pre-production testing

2. **Feature Branches**
   - Format: `feature/issue-number-short-description`
   - Example: `feature/123-add-user-authentication`

3. **Branch Workflow**
```bash
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/123-add-user-authentication

# Keep feature branch updated
git checkout develop
git pull origin develop
git checkout feature/123-add-user-authentication
git rebase develop

# Complete feature
git checkout develop
git pull origin develop
git merge --no-ff feature/123-add-user-authentication
git push origin develop
```

### 3. Development Cycle

1. **Setup**
   ```bash
   # Clone repository
   git clone git@github.com:organization/imangor-api.git
   cd imangor-api
   
   # Setup environment
   python -m venv venv
   source venv/bin/activate
   poetry install
   
   # Setup pre-commit hooks
   pre-commit install
   
   # Start development services
   docker-compose up -d
   ```

2. **Development**
   - Write code following our style guide
   - Run tests locally
   - Update documentation
   - Create/update migrations
   - Test changes manually

3. **Testing**
   ```bash
   # Run tests
   pytest
   
   # Run specific test
   pytest tests/test_auth.py -k test_login
   
   # Run with coverage
   pytest --cov=app tests/
   
   # Run linting
   flake8
   black .
   isort .
   mypy .
   ```

4. **Code Review**
   - Create pull request
   - Request reviews
   - Address feedback
   - Update PR as needed
   - Merge when approved

## Code Organization

### 1. Project Structure

```
imangor-api/
├── alembic/              # Database migrations
├── app/
│   ├── api/             # API endpoints
│   ├── core/            # Core functionality
│   ├── crud/            # Database operations
│   ├── db/              # Database setup
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic models
│   └── services/        # Business logic
├── tests/               # Test suite
├── .github/             # GitHub workflows
├── docker/              # Docker configuration
├── k8s/                 # Kubernetes manifests
└── scripts/             # Utility scripts
```

### 2. Code Style

We follow these style guides:
- [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)

Example of our code style:
```python
# app/api/v1/endpoints/users.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.crud import user as user_crud

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user)
) -> List[UserResponse]:
    """
    Retrieve users with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Currently authenticated user
        
    Returns:
        List of user objects
    """
    users = user_crud.get_multi(db, skip=skip, limit=limit)
    return users
```

## Version Control

### 1. Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

Example:
```
feat(auth): add JWT authentication

- Implement JWT token generation
- Add token validation middleware
- Update user model for auth

Closes #123
```

### 2. Git Hooks

We use pre-commit hooks to maintain code quality:

```yaml
# .pre-commit-config.yaml
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files

-   repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
    -   id: black

-   repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
    -   id: isort

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8
```

## Code Review

### 1. Pull Request Process

1. **PR Creation**
   - Use PR template
   - Link related issues
   - Add reviewers
   - Add labels
   - Request review

2. **PR Template**
```markdown
## Description
[Description of changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Closes #123

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No merge conflicts
```

3. **Review Guidelines**
   - Code quality
   - Test coverage
   - Documentation
   - Performance
   - Security
   - Maintainability

## Testing Strategy

### 1. Test Types

1. **Unit Tests**
   ```python
   # tests/test_auth.py
   import pytest
   from fastapi.testclient import TestClient
   
   def test_login_success(client: TestClient, test_user):
       response = client.post(
           "/api/v1/auth/login",
           data={
               "username": test_user.email,
               "password": "testpass123"
           }
       )
       assert response.status_code == 200
       data = response.json()
       assert "access_token" in data
       assert data["token_type"] == "bearer"
   ```

2. **Integration Tests**
   ```python
   # tests/integration/test_user_flow.py
   def test_user_registration_and_login(client: TestClient, db: Session):
       # Register user
       response = client.post(
           "/api/v1/users/",
           json={
               "email": "test@example.com",
               "password": "testpass123"
           }
       )
       assert response.status_code == 201
       
       # Login
       response = client.post(
           "/api/v1/auth/login",
           data={
               "username": "test@example.com",
               "password": "testpass123"
           }
       )
       assert response.status_code == 200
   ```

3. **API Tests**
   ```python
   # tests/api/test_users_api.py
   def test_create_user(client: TestClient, admin_token_headers):
       response = client.post(
           "/api/v1/users/",
           headers=admin_token_headers,
           json={
               "email": "new@example.com",
               "password": "newpass123"
           }
       )
       assert response.status_code == 201
       data = response.json()
       assert data["email"] == "new@example.com"
   ```

### 2. Test Coverage

We maintain high test coverage:
- Unit tests: >90%
- Integration tests: >80%
- API tests: >85%

## Deployment Process

### 1. CI/CD Pipeline

1. **GitHub Actions Workflow**
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install poetry
        poetry install
    - name: Run tests
      run: |
        poetry run pytest
    - name: Run linting
      run: |
        poetry run flake8
        poetry run black . --check
        poetry run isort . --check-only
```

2. **Deployment Stages**
   - Development: Automatic on push to `develop`
   - Staging: Manual trigger from `staging`
   - Production: Manual trigger from `main`

### 2. Deployment Checklist

Before deploying to production:
- [ ] All tests pass
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Performance tested
- [ ] Security scan completed
- [ ] Backup verified
- [ ] Rollback plan ready

## Documentation

### 1. Code Documentation

1. **Docstring Format**
```python
def process_user_data(user_id: int, data: dict) -> dict:
    """Process user data and return updated information.
    
    Args:
        user_id: The ID of the user to process
        data: Dictionary containing user data to process
        
    Returns:
        dict: Processed user data
        
    Raises:
        ValueError: If user_id is invalid
        ProcessingError: If data processing fails
    """
    pass
```

2. **Module Documentation**
```python
"""User management module.

This module handles all user-related operations including:
- User creation and updates
- Authentication
- Authorization
- Profile management

Example:
    >>> from app.crud import user
    >>> user.create(db, obj_in=user_data)
    User(id=1, email="user@example.com")
"""
```

### 2. API Documentation

We use FastAPI's automatic documentation:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

Example endpoint documentation:
```python
@router.post("/users/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
) -> UserResponse:
    """Create a new user.
    
    This endpoint creates a new user in the system.
    The user's password will be hashed before storage.
    
    Args:
        user: User creation data
        db: Database session
        
    Returns:
        UserResponse: Created user data
        
    Raises:
        HTTPException: If email already exists
    """
    return crud.user.create(db, obj_in=user)
```

## Need Help?

If you need assistance with our development workflow:
1. Check our documentation
2. Ask in team channels
3. Schedule a pair programming session
4. Review our knowledge base

Remember: Following our workflow helps maintain code quality and team efficiency! 🔄 