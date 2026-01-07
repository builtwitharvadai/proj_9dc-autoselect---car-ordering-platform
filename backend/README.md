# AutoSelect Backend - FastAPI Microservices

Backend services for the AutoSelect car ordering platform, built with FastAPI and Python 3.11+.

## Architecture

The backend follows a microservices architecture with the following services:

### Core Services

- **Catalog Service** - Vehicle inventory, models, specifications, and pricing
- **Orders Service** - Order management, cart operations, and order lifecycle
- **Users Service** - Authentication, authorization, and user profile management
- **Payments Service** - Payment processing, transaction management, and billing

### Service Communication

- RESTful APIs for client-facing endpoints
- Internal service-to-service communication via HTTP/gRPC
- Event-driven architecture for asynchronous operations
- Shared database per service pattern with proper isolation

## Technology Stack

- **Framework**: FastAPI 0.104+
- **Python**: 3.11+
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0+
- **Migration**: Alembic
- **Authentication**: JWT with OAuth2
- **API Documentation**: OpenAPI/Swagger (auto-generated)
- **Testing**: pytest, pytest-asyncio
- **Validation**: Pydantic v2

## Project Structure