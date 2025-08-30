# FastAPI with PostgreSQL and Redis

A modern FastAPI application with PostgreSQL database and Redis caching, containerized with Docker.

## Features

- **FastAPI** - Modern, fast web framework for building APIs
- **PostgreSQL** - Robust relational database
- **Redis** - In-memory caching for improved performance
- **Docker** - Containerized for easy deployment
- **SQLAlchemy** - Python ORM for database operations
- **Pydantic** - Data validation using Python type annotations
- **Celery** - Distributed task queue for background processing
- **NewsAPI Integration** - Fetch and process news articles
- **pgAdmin** - Web-based PostgreSQL administration

## Project Structure

```
fastapi-app/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── users.py          # User API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py         # Application configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py       # Database connection
│   │   └── redis_client.py   # Redis connection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py          # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   ├── __init__.py
│   └── main.py              # FastAPI application
├── .env                     # Environment variables
├── .dockerignore
├── docker-compose.yml       # Docker services configuration
├── Dockerfile
├── README.md
└── requirements.txt         # Python dependencies
```

## Quick Start

1. **Clone and navigate to the project:**
   ```bash
   cd fastapi-app
   ```

2. **Start the services:**
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**
   - API: http://localhost:8000
   - Interactive API docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc
   - pgAdmin: http://localhost:5050 (admin@admin.com / admin)

## API Endpoints

### General
- `GET /` - Welcome message
- `GET /health` - Health check

### Users
- `POST /api/v1/users/` - Create a new user
- `GET /api/v1/users/` - Get all users
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user

### News Articles
- `POST /api/v1/news/fetch` - Fetch articles from NewsAPI
- `GET /api/v1/articles` - Get articles (with filtering)
- `GET /api/v1/articles/{article_id}` - Get specific article
- `PUT /api/v1/articles/{article_id}` - Update article status/category
- `POST /api/v1/articles/{article_id}/reprocess` - Reprocess article
- `GET /api/v1/tasks/{task_id}` - Get Celery task status
- `GET /api/v1/articles/stats/summary` - Get article statistics

## Environment Variables

You can modify the `.env` file to change database credentials, Redis settings, and other configuration options.

## Development

To run in development mode:

```bash
# Install dependencies locally (optional)
pip install -r requirements.txt

# Start services
docker-compose up --build

# The application will reload automatically when you make changes to the code
```

## Services

- **FastAPI App**: Runs on port 8000
- **PostgreSQL**: Runs on port 5432
- **Redis**: Runs on port 6379
- **pgAdmin**: Runs on port 5050 (Database administration interface)
- **Celery Worker**: Background task processing
- **Flower**: Runs on port 5555 (Celery monitoring interface)

## Example Usage

Create a new user:
```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "username": "testuser",
       "full_name": "Test User"
     }'
```

Get all users:
```bash
curl "http://localhost:8000/api/v1/users/"
```

### News API Examples

Fetch news articles about technology:
```bash
curl -X POST "http://localhost:8000/api/v1/news/fetch" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "technology",
       "language": "en",
       "page_size": 10
     }'
```

Get all articles:
```bash
curl "http://localhost:8000/api/v1/articles"
```

Get approved articles only:
```bash
curl "http://localhost:8000/api/v1/articles?status=approved"
```

Get technology articles:
```bash
curl "http://localhost:8000/api/v1/articles?category=technology"
```

Check task status:
```bash
curl "http://localhost:8000/api/v1/tasks/{task_id}"
```

Get article statistics:
```bash
curl "http://localhost:8000/api/v1/articles/stats/summary"
```

## pgAdmin Setup

After starting the services, you can access pgAdmin at http://localhost:5050

**Login credentials:**
- Email: `admin@admin.com`
- Password: `admin`

**To connect to the PostgreSQL database:**
1. Click "Add New Server"
2. In the "General" tab:
   - Name: `FastAPI DB` (or any name you prefer)
3. In the "Connection" tab:
   - Host name/address: `db`
   - Port: `5432`
   - Maintenance database: `fastapi_db`
   - Username: `postgres`
   - Password: `password`
4. Click "Save"

Now you can browse your database tables, run queries, and manage your PostgreSQL database through the pgAdmin web interface.
