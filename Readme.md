# 🔍 InvestiGator Backend

Autonomous Investigative Intelligence Agent powered by Gemini AI - Backend API built with Django.

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Gemini API Key

### Setup

1. **Clone and configure**

```bash
git clone https://github.com/Hamza-malikx/investigator-backend
cd investigator_backend
cp .env.example .env
```

2. **Update `.env` file**

```env
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=your-secret-key-here
```

3. **Build and run**

```bash
# Development
docker-compose up --build

# Production
docker-compose -f docker-compose.prod.yml up --build -d
```

4. **Initialize database**

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

5. **Access**

- API: `http://localhost:8000/api/`
- Admin: `http://localhost:8000/admin/`

## 🏗️ Architecture

```
investigator_backend/
├── accounts/          # User management & authentication
├── investigations/    # Core investigation logic
├── entities/         # Entity & relationship management
├── evidence/         # Evidence tracking & linking
├── board/            # Investigation board visualization
├── voice/            # Gemini Live API integration
├── reports/          # Report generation
├── core/             # Shared utilities & Gemini client
└── investigator/     # Django project settings
```

## 📡 Key Features

- **Autonomous Research Agent**: Multi-hour investigations with self-correction
- **Entity Relationship Mapping**: Automatic entity extraction and relationship discovery
- **Real-time Updates**: WebSocket support for live investigation board
- **Voice Collaboration**: Gemini Live API for natural voice interactions
- **Evidence Management**: Document analysis and source tracking
- **Interactive Board**: Force-directed graph visualization
- **Report Generation**: Auto-generated intelligence reports

## 🔧 Tech Stack

- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery + Celery Beat
- **WebSockets**: Django Channels
- **AI**: Google Gemini 3 API
- **Deployment**: Docker + Nginx + Gunicorn

## 📚 API Endpoints

### Authentication

```
POST   /api/auth/register/
POST   /api/auth/login/
POST   /api/auth/refresh-token/
```

### Investigations

```
POST   /api/investigations/              # Create investigation
GET    /api/investigations/              # List investigations
GET    /api/investigations/{id}/         # Investigation details
PATCH  /api/investigations/{id}/         # Pause/Resume/Cancel
GET    /api/investigations/{id}/status/  # Real-time status
```

### Entities & Board

```
GET    /api/investigations/{id}/entities/
GET    /api/investigations/{id}/relationships/
GET    /api/investigations/{id}/board/
WS     /ws/investigations/{id}/          # WebSocket for updates
```

### Reports

```
POST   /api/investigations/{id}/reports/generate/
GET    /api/investigations/{id}/reports/
GET    /api/investigations/{id}/reports/{id}/download/
```

## 🔐 Environment Variables

```env
# Django
DEBUG=0
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com

# Database
DB_NAME=investigator_prod
DB_USER=postgres
DB_PASSWORD=strong-password
DB_HOST=db
DB_PORT=5432

# Gemini API
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL_DEFAULT=gemini-1.5-pro

# Redis
REDIS_URL=redis://redis:6379
CELERY_BROKER_URL=redis://redis:6379/0

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

## 🧪 Development

### Run locally without Docker

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate

# Run development server
python manage.py runserver
```

### Run Celery worker (separate terminal)

```bash
celery -A investigator worker --loglevel=info
```

### Run Celery beat (separate terminal)

```bash
celery -A investigator beat --loglevel=info
```

## 📝 Common Commands

```bash
# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Access Django shell
docker-compose exec web python manage.py shell

# Run tests
docker-compose exec web python manage.py test

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Backup database
docker-compose exec db pg_dump -U postgres investigator_prod > backup.sql
```

## 🚢 Production Deployment

1. **Update production environment**

```bash
cp .env.prod.example .env.prod
# Edit .env.prod with production values
```

2. **Deploy with SSL**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. **Setup SSL certificates (using Certbot)**

```bash
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d yourdomain.com
```

## 📊 Monitoring

- **Celery Tasks**: Flower at `http://localhost:5555` (if enabled)
- **Health Check**: `http://localhost:8000/health/`
- **Logs**: `docker-compose logs -f`

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Links

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)

---

**Note**: This is a hackathon project. For production use, implement proper security audits, rate limiting, and monitoring.
