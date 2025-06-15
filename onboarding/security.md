# Security Guide 🔒

Welcome to the security guide! This document will help you understand our security practices, measures, and how to maintain a secure codebase. Whether you're implementing new features, reviewing code, or handling sensitive data, this guide will be your companion.

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication](#authentication)
3. [Authorization](#authorization)
4. [Data Security](#data-security)
5. [API Security](#api-security)
6. [Infrastructure Security](#infrastructure-security)
7. [Security Best Practices](#security-best-practices)
8. [Incident Response](#incident-response)

## Security Overview

Our security approach is comprehensive and covers multiple layers:

- Application security
- Infrastructure security
- Data security
- Network security
- Operational security

### Security Principles

1. **Defense in Depth**
   - Multiple layers of security
   - No single point of failure
   - Redundant security measures

2. **Least Privilege**
   - Minimal required permissions
   - Role-based access control
   - Regular permission reviews

3. **Zero Trust**
   - Verify everything
   - Trust nothing
   - Assume breach

## Authentication

### 1. JWT Authentication

```python
# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

### 2. OAuth2 Integration

```python
# app/core/oauth.py
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = crud.user.get(db, id=user_id)
    if user is None:
        raise credentials_exception
    return user
```

## Authorization

### 1. Role-Based Access Control (RBAC)

```python
# app/core/security.py
from enum import Enum
from typing import List

class Role(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"

def check_permissions(
    required_roles: List[Role],
    current_user: User
) -> bool:
    return current_user.role in required_roles

# Usage in endpoints
@router.get("/admin/")
async def admin_endpoint(
    current_user: User = Depends(get_current_user)
):
    if not check_permissions([Role.ADMIN], current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return {"message": "Admin access granted"}
```

### 2. Resource-Based Authorization

```python
# app/core/security.py
def check_resource_access(
    resource: Resource,
    user: User,
    action: str
) -> bool:
    if user.role == Role.ADMIN:
        return True
    
    if action == "read":
        return resource.is_public or resource.owner_id == user.id
    
    if action == "write":
        return resource.owner_id == user.id
    
    return False

# Usage in endpoints
@router.put("/resources/{resource_id}")
async def update_resource(
    resource_id: int,
    update_data: ResourceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resource = crud.resource.get(db, id=resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    if not check_resource_access(resource, current_user, "write"):
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    
    return crud.resource.update(db, db_obj=resource, obj_in=update_data)
```

## Data Security

### 1. Data Encryption

```python
# app/core/encryption.py
from cryptography.fernet import Fernet
from app.core.config import settings

def encrypt_data(data: str) -> str:
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.decrypt(encrypted_data.encode()).decode()

# Usage in models
class SensitiveData(Base):
    __tablename__ = "sensitive_data"
    
    id = Column(Integer, primary_key=True)
    encrypted_value = Column(String)
    
    def set_value(self, value: str):
        self.encrypted_value = encrypt_data(value)
    
    def get_value(self) -> str:
        return decrypt_data(self.encrypted_value)
```

### 2. Secure Password Storage

```python
# app/core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

## API Security

### 1. Rate Limiting

```python
# app/core/rate_limit.py
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/api/endpoint")
@limiter.limit("5/minute")
async def rate_limited_endpoint(request: Request):
    return {"message": "Rate limited endpoint"}
```

### 2. Input Validation

```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr, constr

class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=100)
    full_name: constr(min_length=1, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123",
                "full_name": "John Doe"
            }
        }
```

### 3. CORS Configuration

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Infrastructure Security

### 1. Network Security

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
  namespace: imangor-api
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    ports:
    - protocol: TCP
      port: 8000
```

### 2. Secrets Management

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: imangor-api
type: Opaque
data:
  database-url: <base64-encoded-url>
  jwt-secret: <base64-encoded-secret>
  api-key: <base64-encoded-key>
```

## Security Best Practices

### 1. Code Security

- Use parameterized queries
- Validate all input
- Sanitize output
- Use secure headers
- Implement proper error handling
- Follow secure coding guidelines

### 2. Dependency Security

- Regular dependency updates
- Security scanning
- Vulnerability monitoring
- License compliance
- Dependency auditing

### 3. Configuration Security

- Secure environment variables
- Proper secrets management
- Configuration validation
- Secure defaults
- Regular rotation

### 4. Operational Security

- Regular security audits
- Access reviews
- Security training
- Incident response drills
- Security documentation

## Incident Response

### 1. Incident Classification

```python
# app/core/security.py
from enum import Enum

class SecurityIncidentLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityIncident:
    def __init__(
        self,
        level: SecurityIncidentLevel,
        description: str,
        affected_systems: List[str]
    ):
        self.level = level
        self.description = description
        self.affected_systems = affected_systems
        self.timestamp = datetime.utcnow()
```

### 2. Incident Response Plan

1. **Detection**
   - Monitor security events
   - Log analysis
   - Alert investigation
   - User reports

2. **Containment**
   - Isolate affected systems
   - Block malicious traffic
   - Revoke compromised credentials
   - Implement temporary fixes

3. **Investigation**
   - Gather evidence
   - Analyze logs
   - Identify root cause
   - Document findings

4. **Remediation**
   - Apply security patches
   - Update security measures
   - Restore systems
   - Verify fixes

5. **Recovery**
   - Restore services
   - Monitor for recurrence
   - Update documentation
   - Learn from incident

### 3. Security Monitoring

```python
# app/core/monitoring.py
from prometheus_client import Counter, Histogram
import time

security_incidents = Counter(
    'security_incidents_total',
    'Total number of security incidents',
    ['level', 'type']
)

auth_attempts = Counter(
    'auth_attempts_total',
    'Total number of authentication attempts',
    ['status']
)

request_duration = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['endpoint']
)

def track_security_incident(level: str, type: str):
    security_incidents.labels(level=level, type=type).inc()

def track_auth_attempt(status: str):
    auth_attempts.labels(status=status).inc()

def track_request_duration(endpoint: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            request_duration.labels(endpoint=endpoint).observe(duration)
            return result
        return wrapper
    return decorator
```

## Need Help?

If you need assistance with security:
1. Check the security documentation
2. Review security guidelines
3. Ask in the security channel
4. Report security incidents
5. Schedule a security review

Remember: Security is everyone's responsibility! 🔒 