# Production Environment Setup Guide

This guide provides comprehensive instructions for setting up SmartChat in a production environment with high availability, scalability, and security.

## 🏗️ Infrastructure Overview

### Architecture Components
- **Application Layer**: React frontend + FastAPI backend
- **Database Layer**: PostgreSQL + Redis cache
- **Search Layer**: Qdrant vector database
- **Load Balancer**: Nginx reverse proxy
- **Monitoring**: Prometheus + Grafana stack
- **Container Orchestration**: Docker Compose or Kubernetes

### Recommended Server Specifications

#### Minimum Production Setup (Small-Medium Traffic)
```yaml
Application Server:
  CPU: 4 cores (2.4GHz+)
  RAM: 8GB
  Storage: 100GB SSD
  Network: 1Gbps

Database Server:
  CPU: 4 cores (2.4GHz+)
  RAM: 16GB
  Storage: 200GB SSD (with backup)
  Network: 1Gbps
```

#### Scalable Production Setup (High Traffic)
```yaml
Load Balancer (2x):
  CPU: 2 cores
  RAM: 4GB
  Storage: 50GB SSD

Application Servers (3x):
  CPU: 8 cores (2.4GHz+)
  RAM: 16GB
  Storage: 100GB SSD
  Network: 1Gbps

Database Cluster:
  Primary: 8 cores, 32GB RAM, 500GB SSD
  Replica: 8 cores, 32GB RAM, 500GB SSD
  
Vector Database:
  CPU: 4 cores
  RAM: 8GB
  Storage: 200GB SSD
```

## 🌐 Network Configuration

### Port Allocation
```yaml
External (Public):
  80:  HTTP (redirect to HTTPS)
  443: HTTPS (nginx)

Internal (Private Network):
  3000: Frontend (React dev server)
  8000: Backend API (FastAPI)
  5432: PostgreSQL
  6379: Redis
  6333: Qdrant HTTP API
  6334: Qdrant gRPC API
  9090: Prometheus
  3000: Grafana
```

### DNS Configuration
```bash
# Main domain
smartchat.yourdomain.com -> Load Balancer IP

# API subdomain (optional)
api.smartchat.yourdomain.com -> Load Balancer IP

# Admin/monitoring subdomain
admin.smartchat.yourdomain.com -> Load Balancer IP
```

### Firewall Rules
```bash
# Allow HTTP/HTTPS traffic
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH (restrict to specific IPs in production)
sudo ufw allow 22/tcp

# Block all other external traffic
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

## 📋 Cloud Provider Setup

### AWS Deployment
```yaml
# Infrastructure as Code (Terraform)
Resources:
  - Application Load Balancer (ALB)
  - EC2 instances with Auto Scaling Groups
  - RDS PostgreSQL Multi-AZ
  - ElastiCache Redis cluster
  - EFS for shared storage
  - Route 53 for DNS
  - Certificate Manager for SSL
  - CloudWatch for monitoring
```

### Google Cloud Platform
```yaml
Resources:
  - Google Kubernetes Engine (GKE) cluster
  - Cloud SQL PostgreSQL with read replicas
  - Memorystore Redis
  - Cloud Load Balancing
  - Cloud DNS
  - SSL certificates via Google-managed certificates
  - Cloud Monitoring and Logging
```

### DigitalOcean Setup
```yaml
Resources:
  - Droplets with Docker
  - Managed PostgreSQL cluster
  - Managed Redis cluster
  - Load Balancer
  - Spaces for file storage
  - Let's Encrypt for SSL
```

## 🔧 Load Balancer Configuration

### Nginx Load Balancer (nginx.conf)
```nginx
upstream backend_servers {
    least_conn;
    server backend1:8000 max_fails=3 fail_timeout=30s;
    server backend2:8000 max_fails=3 fail_timeout=30s;
    server backend3:8000 max_fails=3 fail_timeout=30s;
}

upstream frontend_servers {
    least_conn;
    server frontend1:3000 max_fails=3 fail_timeout=30s;
    server frontend2:3000 max_fails=3 fail_timeout=30s;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;

server {
    listen 80;
    server_name smartchat.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name smartchat.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/smartchat.crt;
    ssl_certificate_key /etc/ssl/private/smartchat.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Frontend (React app)
    location / {
        proxy_pass http://frontend_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API endpoints
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # File upload endpoints (higher timeout)
    location /api/documents/upload {
        limit_req zone=upload burst=5 nodelay;
        proxy_pass http://backend_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_connect_timeout 75s;
        client_max_body_size 100M;
    }

    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://backend_servers/health;
    }

    # Static assets (if served by nginx)
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### HAProxy Alternative Configuration
```haproxy
global
    daemon
    log stdout local0
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy

defaults
    mode http
    log global
    option httplog
    option dontlognull
    option http-server-close
    option forwardfor except 127.0.0.0/8
    option redispatch
    retries 3
    timeout http-request 10s
    timeout queue 1m
    timeout connect 10s
    timeout client 1m
    timeout server 1m
    timeout http-keep-alive 10s
    timeout check 10s

frontend smartchat_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/smartchat.pem
    redirect scheme https if !{ ssl_fc }
    
    # ACLs
    acl is_api path_beg /api/
    acl is_upload path_beg /api/documents/upload
    
    # Rate limiting (requires stick-tables)
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    http-request track-sc0 src
    http-request deny if { sc_http_req_rate(0) gt 20 }
    
    use_backend backend_api if is_api
    default_backend frontend_servers

backend frontend_servers
    balance roundrobin
    option httpchk GET /
    server frontend1 frontend1:3000 check
    server frontend2 frontend2:3000 check

backend backend_api
    balance roundrobin
    option httpchk GET /health
    server backend1 backend1:8000 check
    server backend2 backend2:8000 check
    server backend3 backend3:8000 check
```

## 📦 Container Orchestration

### Docker Compose Production
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - NODE_ENV=production
    restart: unless-stopped
    deploy:
      replicas: 2

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - QDRANT_URL=${QDRANT_URL}
    restart: unless-stopped
    deploy:
      replicas: 3
    depends_on:
      - postgres
      - redis
      - qdrant

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    restart: unless-stopped
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

### Kubernetes Deployment
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smartchat-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: smartchat-backend
  template:
    metadata:
      labels:
        app: smartchat-backend
    spec:
      containers:
      - name: backend
        image: smartchat/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: smartchat-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: smartchat-backend-service
spec:
  selector:
    app: smartchat-backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

## 🔐 SSL/TLS Certificate Setup

### Let's Encrypt (Recommended)
```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d smartchat.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Manual Certificate Installation
```bash
# Copy certificates
sudo cp smartchat.crt /etc/ssl/certs/
sudo cp smartchat.key /etc/ssl/private/
sudo chmod 644 /etc/ssl/certs/smartchat.crt
sudo chmod 600 /etc/ssl/private/smartchat.key

# Update nginx configuration
sudo nginx -t
sudo systemctl reload nginx
```

## 🏥 Health Checks and Monitoring

### Application Health Endpoints
```python
# backend/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.core.database import get_db
import redis
import requests

router = APIRouter()

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    try:
        # Database check
        db.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    try:
        # Redis check
        r = redis.Redis.from_url(settings.redis_url)
        r.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    try:
        # Qdrant check
        response = requests.get(f"{settings.qdrant_url}/health", timeout=5)
        if response.status_code == 200:
            health_status["services"]["qdrant"] = "healthy"
        else:
            health_status["services"]["qdrant"] = f"unhealthy: HTTP {response.status_code}"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["qdrant"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"status": "ready"}

@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}
```

## 🚀 Deployment Process

### Automated Deployment Script
```bash
#!/bin/bash
# deploy-production.sh

set -e

echo "🚀 Starting SmartChat production deployment..."

# Configuration
REPO_URL="https://github.com/yourusername/smartchat.git"
DEPLOY_DIR="/opt/smartchat"
BACKUP_DIR="/backups/smartchat"
LOG_FILE="/var/log/smartchat-deploy.log"

# Create backup
echo "📦 Creating backup..."
timestamp=$(date +%Y%m%d_%H%M%S)
sudo -u postgres pg_dump smartchat_db > "$BACKUP_DIR/db_backup_$timestamp.sql"

# Pull latest code
echo "📥 Pulling latest code..."
cd $DEPLOY_DIR
git pull origin main

# Build containers
echo "🏗️ Building containers..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Deploy with zero downtime
echo "🔄 Deploying with zero downtime..."
docker-compose -f docker-compose.prod.yml up -d --remove-orphans

# Wait for health checks
echo "🏥 Waiting for health checks..."
sleep 30

# Verify deployment
echo "✅ Verifying deployment..."
if curl -f -s http://localhost/health > /dev/null; then
    echo "✅ Deployment successful!"
    
    # Cleanup old images
    docker image prune -f
    
    # Send notification (optional)
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"SmartChat production deployment successful"}' \
        $SLACK_WEBHOOK_URL
else
    echo "❌ Deployment failed - rolling back..."
    docker-compose -f docker-compose.prod.yml down
    # Restore from backup if needed
    exit 1
fi

echo "🎉 Production deployment completed successfully!"
```

## 📊 Performance Optimization

### Database Optimization
```sql
-- PostgreSQL performance tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();

-- Create indexes for performance
CREATE INDEX CONCURRENTLY idx_documents_owner_status 
ON documents(owner_id, status);

CREATE INDEX CONCURRENTLY idx_messages_conversation_created 
ON messages(conversation_id, created_at);
```

### Redis Configuration
```conf
# redis.conf optimizations
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

## 🛡️ Security Considerations

### Server Hardening
```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Install fail2ban
sudo apt-get install fail2ban
sudo systemctl enable fail2ban

# Set up automatic security updates
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Application Security
- Implement rate limiting on all API endpoints
- Use HTTPS everywhere with HSTS headers
- Regularly update dependencies and base images
- Implement proper input validation and sanitization
- Use environment variables for all secrets
- Regular security audits and vulnerability scanning

## 📈 Scaling Strategies

### Horizontal Scaling
1. **Application Tier**: Add more backend/frontend containers
2. **Database Tier**: Set up read replicas for PostgreSQL
3. **Cache Tier**: Implement Redis clustering
4. **Load Balancing**: Use multiple load balancer instances

### Vertical Scaling
1. **CPU**: Increase core count for compute-intensive tasks
2. **Memory**: Add RAM for better caching and performance
3. **Storage**: Upgrade to faster SSDs with higher IOPS

### Auto-scaling (Kubernetes)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: smartchat-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: smartchat-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 🔧 Troubleshooting

### Common Issues
1. **High Memory Usage**: Check for memory leaks, optimize queries
2. **Slow Response Times**: Add caching, optimize database queries
3. **Connection Timeouts**: Adjust connection pool settings
4. **SSL Certificate Issues**: Verify certificate chain and renewal

### Log Analysis
```bash
# Application logs
docker-compose logs -f backend
docker-compose logs -f frontend

# System logs
sudo journalctl -u docker
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Database logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

## 📝 Maintenance Checklist

### Daily
- [ ] Check application health status
- [ ] Monitor system resources (CPU, memory, disk)
- [ ] Review error logs

### Weekly
- [ ] Database backup verification
- [ ] Security update installation
- [ ] Performance metrics review

### Monthly
- [ ] SSL certificate renewal check
- [ ] Dependency updates
- [ ] Security audit
- [ ] Disaster recovery testing

---

This production setup guide provides a comprehensive foundation for deploying SmartChat in a scalable, secure, and maintainable production environment. Adjust the configurations based on your specific requirements, traffic patterns, and infrastructure constraints. 