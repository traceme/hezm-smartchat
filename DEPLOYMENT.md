# SmartChat Deployment Guide

This guide covers deployment options for the SmartChat application using Docker containers.

## 🚀 Quick Start

### Production Deployment

1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd hezm-smartchat
   cp env.production.example .env
   # Edit .env with your production values
   ```

2. **Deploy with the deployment script:**
   ```bash
   ./deploy.sh production
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Development Setup

1. **Start development environment:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Access development services:**
   - Frontend: http://localhost:3001
   - Backend API: http://localhost:8006

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM available
- 10GB+ disk space

## 🏗️ Architecture Overview

### Services

| Service | Production Port | Dev Port | Description |
|---------|----------------|----------|-------------|
| Frontend | 3000 | 3001 | React app with nginx |
| Backend | 8000 | 8006 | FastAPI application |
| PostgreSQL | 5432 | 5432 | Primary database |
| Redis | 6379 | 6379 | Caching and sessions |
| Qdrant | 6333, 6334 | 6333, 6334 | Vector database |

### Volumes

- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis persistence
- `qdrant_data`: Vector database storage
- `upload_data`: Uploaded documents
- `logs_data`: Application logs

## 🔧 Configuration

### Environment Variables

Copy `env.production.example` to `.env` and configure:

#### Required Settings
```bash
# API Keys (Required for AI functionality)
OPENAI_API_KEY=sk-your_openai_key_here
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here
GOOGLE_API_KEY=your_google_ai_key_here

# Security
SECRET_KEY=your_secure_secret_key_at_least_32_characters
POSTGRES_PASSWORD=your_secure_database_password
```

#### Optional Settings
```bash
# Ports (defaults shown)
FRONTEND_PORT=3000
BACKEND_PORT=8000
POSTGRES_PORT=5432

# Performance
WORKERS=4
MAX_CONNECTIONS=100

# Security
CORS_ORIGINS=https://yourdomain.com
```

### Database Migration

The application will automatically create tables on first run. To migrate from SQLite:

```bash
# Export from SQLite (if you have existing data)
sqlite3 backend/smartchat_debug.db .dump > backup.sql

# Start containers
docker-compose up -d

# Import to PostgreSQL (if needed)
docker exec -i smartchat-postgres psql -U postgres -d smartchat < backup.sql
```

## 🛠️ Development

### Hot Reloading

The development setup includes hot reloading for both frontend and backend:

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

### Testing

```bash
# Run backend tests
docker-compose exec backend python -m pytest

# Run linting
docker-compose exec backend black .
docker-compose exec backend flake8 .

# Frontend tests
docker-compose exec frontend npm test
```

### Development Tools

```bash
# Access backend shell
docker-compose exec backend bash

# Access database
docker-compose exec postgres psql -U postgres -d smartchat

# View Redis data
docker-compose exec redis redis-cli
```

## 🚀 Production Deployment

### Using the Deployment Script

The included `deploy.sh` script provides a complete deployment workflow:

```bash
# Full production deployment
./deploy.sh production

# Skip tests (faster deployment)
SKIP_TESTS=true ./deploy.sh production

# Skip backup
BACKUP_BEFORE_DEPLOY=false ./deploy.sh production
```

### Manual Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs

# Scale backend (if needed)
docker-compose up -d --scale backend=3
```

### Health Checks

All services include health checks:

```bash
# Check service health
docker-compose ps

# Test health endpoints
curl http://localhost:8000/health  # Backend
curl http://localhost:3000/health  # Frontend
```

## 🔒 Security

### Production Security Checklist

- [ ] Change default passwords in `.env`
- [ ] Use strong `SECRET_KEY` (32+ characters)
- [ ] Configure `CORS_ORIGINS` for your domain
- [ ] Set up SSL/TLS certificates
- [ ] Enable firewall rules
- [ ] Regular security updates
- [ ] Monitor access logs

### SSL/TLS Setup

For HTTPS, use a reverse proxy like nginx or Traefik:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 Monitoring

### Basic Monitoring

```bash
# View resource usage
docker stats

# Check container logs
docker-compose logs -f [service_name]

# Monitor disk usage
docker system df
```

### Log Management

Logs are stored in the `logs_data` volume:

```bash
# View application logs
docker-compose exec backend tail -f logs/app.log

# View access logs (nginx)
docker-compose exec frontend tail -f /var/log/nginx/access.log
```

## 🔄 Backup and Recovery

### Automated Backups

The deployment script creates backups before deployment:

```bash
# Manual backup
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh backups/20240611_120000
```

### Database Backup

```bash
# Backup database
docker exec smartchat-postgres pg_dump -U postgres smartchat > backup.sql

# Restore database
docker exec -i smartchat-postgres psql -U postgres -d smartchat < backup.sql
```

### Volume Backup

```bash
# Backup uploads
docker run --rm -v smartchat_upload_data:/data -v $(pwd):/backup alpine tar czf /backup/uploads.tar.gz -C /data .

# Restore uploads
docker run --rm -v smartchat_upload_data:/data -v $(pwd):/backup alpine tar xzf /backup/uploads.tar.gz -C /data
```

## 🚨 Troubleshooting

### Common Issues

#### Container fails to start
```bash
# Check logs
docker-compose logs [service_name]

# Check system resources
docker system df
free -h
```

#### Database connection issues
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# Reset database
docker-compose down
docker volume rm smartchat_postgres_data
docker-compose up -d
```

#### Frontend not accessible
```bash
# Check nginx configuration
docker-compose exec frontend nginx -t

# Check proxy settings
curl -I http://localhost:3000
```

### Performance Issues

#### High memory usage
```bash
# Check container stats
docker stats

# Reduce workers
# Edit docker-compose.yml: WORKERS=2
docker-compose up -d
```

#### Slow queries
```bash
# Check database performance
docker-compose exec postgres psql -U postgres -d smartchat -c "SELECT * FROM pg_stat_activity;"
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Set in .env
DEBUG=true
LOG_LEVEL=debug

# Restart services
docker-compose restart
```

## 📚 Additional Resources

- [Docker Compose Reference](https://docs.docker.com/compose/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [React Production Build](https://create-react-app.dev/docs/production-build/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Redis Docker](https://hub.docker.com/_/redis)

## 🆘 Support

For deployment issues:

1. Check the troubleshooting section above
2. Review container logs: `docker-compose logs`
3. Verify configuration in `.env`
4. Ensure all required API keys are set
5. Check system resources and Docker status

---

**Note**: This deployment setup is designed for production use with proper security, monitoring, and backup procedures. Always test in a staging environment before production deployment. 