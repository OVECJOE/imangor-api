# Testing Guide 🧪

Welcome to the testing guide! This document will help you understand our testing practices and how to write effective tests for our codebase. Whether you're writing unit tests, integration tests, or end-to-end tests, this guide will be your companion.

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Test Structure](#test-structure)
3. [Writing Tests](#writing-tests)
4. [Test Fixtures](#test-fixtures)
5. [Mocking](#mocking)
6. [Database Testing](#database-testing)
7. [API Testing](#api-testing)
8. [Best Practices](#best-practices)

## Testing Overview

We follow a comprehensive testing strategy that includes:

- Unit tests for business logic
- Integration tests for API endpoints
- End-to-end tests for critical flows
- Performance tests for key operations
- Security tests for vulnerabilities

### Testing Tools

- **pytest**: Main testing framework
- **pytest-asyncio**: For testing async code
- **pytest-cov**: For code coverage
- **pytest-mock**: For mocking
- **httpx**: For API testing
- **faker**: For generating test data

## Test Structure

Our tests are organized in a clear, maintainable structure:

```
tests/
├── conftest.py              # Global test fixtures
├── unit/                    # Unit tests
│   ├── test_models.py
│   ├── test_crud.py
│   └── test_services.py
├── integration/             # Integration tests
│   ├── test_api.py
│   └── test_auth.py
├── e2e/                     # End-to-end tests
│   └── test_workflows.py
└── utils/                   # Test utilities
    ├── factories.py
    └── helpers.py
```

## Writing Tests

### 1. Unit Tests

Example of a unit test for a service:

```python
# tests/unit/test_user_service.py
import pytest
from app.services.user import UserService
from app.core.exceptions import NotFoundException

def test_get_user_by_email(user_service, db_session):
    # Arrange
    email = "test@example.com"
    user = user_service.create_user(
        db_session,
        email=email,
        password="testpass",
        full_name="Test User"
    )

    # Act
    result = user_service.get_user_by_email(db_session, email)

    # Assert
    assert result is not None
    assert result.email == email
    assert result.full_name == "Test User"

def test_get_user_by_email_not_found(user_service, db_session):
    # Arrange
    email = "nonexistent@example.com"

    # Act & Assert
    with pytest.raises(NotFoundException):
        user_service.get_user_by_email(db_session, email)
```

### 2. Integration Tests

Example of an API integration test:

```python
# tests/integration/test_auth.py
def test_login_success(client, db_session, test_user):
    # Arrange
    login_data = {
        "username": test_user.email,
        "password": "testpass"
    }

    # Act
    response = client.post("/api/v1/auth/login", data=login_data)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client, db_session):
    # Arrange
    login_data = {
        "username": "wrong@example.com",
        "password": "wrongpass"
    }

    # Act
    response = client.post("/api/v1/auth/login", data=login_data)

    # Assert
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
```

### 3. End-to-End Tests

Example of an end-to-end test:

```python
# tests/e2e/test_user_workflow.py
def test_user_registration_and_login_workflow(client, db_session):
    # Register new user
    register_data = {
        "email": "newuser@example.com",
        "password": "testpass",
        "full_name": "New User"
    }
    response = client.post("/api/v1/users/", json=register_data)
    assert response.status_code == 201

    # Login with new user
    login_data = {
        "username": register_data["email"],
        "password": register_data["password"]
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Get user profile
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == register_data["email"]
```

## Test Fixtures

### 1. Global Fixtures

```python
# tests/conftest.py
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import SessionLocal
from app.core.config import settings

@pytest.fixture(scope="session")
def db() -> Generator:
    yield SessionLocal()

@pytest.fixture(scope="module")
def client() -> Generator:
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db_session(db: Session) -> Generator:
    transaction = db.begin_nested()
    yield db
    transaction.rollback()
```

### 2. Model Fixtures

```python
# tests/utils/factories.py
import factory
from app.models.user import User
from app.core.security import get_password_hash

class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Faker("email")
    hashed_password = factory.LazyFunction(lambda: get_password_hash("testpass"))
    full_name = factory.Faker("name")
    is_active = True

# tests/conftest.py
@pytest.fixture
def test_user(db_session: Session) -> User:
    user = UserFactory()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
```

## Mocking

### 1. Mocking External Services

```python
# tests/unit/test_file_service.py
def test_upload_file(mocker, file_service):
    # Arrange
    mock_storage = mocker.patch("app.services.storage.upload_file")
    mock_storage.return_value = "https://storage.example.com/file.jpg"
    
    # Act
    result = file_service.upload_file("test.jpg", b"test content")
    
    # Assert
    assert result == "https://storage.example.com/file.jpg"
    mock_storage.assert_called_once_with("test.jpg", b"test content")
```

### 2. Mocking Database

```python
# tests/unit/test_user_service.py
def test_get_user(mocker, user_service):
    # Arrange
    mock_user = UserFactory.build()
    mock_db = mocker.Mock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user
    
    # Act
    result = user_service.get_user(mock_db, 1)
    
    # Assert
    assert result == mock_user
    mock_db.query.assert_called_once()
```

## Database Testing

### 1. Test Database Setup

```python
# tests/conftest.py
@pytest.fixture(scope="session")
def test_db():
    # Create test database
    engine = create_engine(settings.TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    
    # Run tests
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
```

### 2. Database Transactions

```python
# tests/conftest.py
@pytest.fixture(autouse=True)
def db_transaction(db_session):
    # Start transaction
    transaction = db_session.begin_nested()
    
    yield
    
    # Rollback transaction
    transaction.rollback()
```

## API Testing

### 1. API Client Fixture

```python
# tests/conftest.py
@pytest.fixture
def api_client(client: TestClient, test_user: User) -> Generator:
    # Get auth token
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "testpass"
        }
    )
    token = response.json()["access_token"]
    
    # Add auth header
    client.headers = {"Authorization": f"Bearer {token}"}
    yield client
```

### 2. API Test Examples

```python
# tests/integration/test_items.py
def test_create_item(api_client, db_session):
    # Arrange
    item_data = {
        "title": "Test Item",
        "description": "Test Description"
    }
    
    # Act
    response = api_client.post("/api/v1/items/", json=item_data)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == item_data["title"]
    assert "id" in data

def test_get_items_pagination(api_client, db_session):
    # Arrange
    for i in range(15):
        ItemFactory()
    
    # Act
    response = api_client.get("/api/v1/items/?skip=0&limit=10")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 15
```

## Best Practices

### 1. Test Organization

- Follow the Arrange-Act-Assert pattern
- Keep tests focused and single-responsibility
- Use meaningful test names
- Group related tests in classes
- Use appropriate test scopes

### 2. Test Data

- Use factories for test data
- Keep test data minimal
- Use faker for realistic data
- Clean up test data
- Use appropriate test databases

### 3. Test Coverage

- Aim for high coverage of critical paths
- Focus on business logic coverage
- Don't test implementation details
- Use coverage reports effectively
- Maintain test quality

### 4. Performance

- Keep tests fast
- Use appropriate fixtures
- Mock external services
- Use database transactions
- Parallelize when possible

## Common Patterns

### 1. Parameterized Tests

```python
@pytest.mark.parametrize(
    "email,password,expected_status",
    [
        ("test@example.com", "testpass", 200),
        ("wrong@example.com", "testpass", 401),
        ("test@example.com", "wrongpass", 401),
    ]
)
def test_login_combinations(client, email, password, expected_status):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    assert response.status_code == expected_status
```

### 2. Async Tests

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_operation()
    assert result is not None
```

### 3. Test Categories

```python
@pytest.mark.slow
def test_slow_operation():
    # Slow test implementation
    pass

@pytest.mark.integration
def test_integration():
    # Integration test implementation
    pass

@pytest.mark.e2e
def test_e2e():
    # End-to-end test implementation
    pass
```

## Running Tests

### 1. Basic Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_user_service.py

# Run specific test
pytest tests/unit/test_user_service.py::test_get_user

# Run with coverage
pytest --cov=app

# Run specific category
pytest -m "not slow"
```

### 2. Test Configuration

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=app --cov-report=term-missing
markers =
    slow: marks tests as slow
    integration: marks tests as integration
    e2e: marks tests as end-to-end
```

## Need Help?

If you need assistance with testing:
1. Check the pytest documentation
2. Review our test examples
3. Ask in the team's communication channels
4. Schedule a pair programming session

Happy testing! 🧪 