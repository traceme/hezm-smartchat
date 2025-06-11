#!/bin/bash
# SmartChat Production Server Setup Script
# This script configures a Ubuntu/Debian server for SmartChat production deployment

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
SMARTCHAT_USER="smartchat"
SMARTCHAT_DIR="/opt/smartchat"
LOG_FILE="/var/log/smartchat-setup.log"
DOMAIN_NAME=""
EMAIL=""

# Functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a $LOG_FILE
    exit 1
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a $LOG_FILE
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a $LOG_FILE
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root. Use: sudo $0"
    fi
}

# Get user input
get_configuration() {
    echo -e "${BLUE}SmartChat Production Server Setup${NC}"
    echo "=================================="
    echo
    
    if [[ -z "$DOMAIN_NAME" ]]; then
        read -p "Enter your domain name (e.g., smartchat.yourdomain.com): " DOMAIN_NAME
        if [[ -z "$DOMAIN_NAME" ]]; then
            error "Domain name is required"
        fi
    fi
    
    if [[ -z "$EMAIL" ]]; then
        read -p "Enter your email for SSL certificates: " EMAIL
        if [[ -z "$EMAIL" ]]; then
            error "Email is required for SSL certificates"
        fi
    fi
    
    echo
    log "Configuration:"
    log "Domain: $DOMAIN_NAME"
    log "Email: $EMAIL"
    log "SmartChat Directory: $SMARTCHAT_DIR"
    echo
    
    read -p "Continue with setup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
}

# Update system
update_system() {
    log "Updating system packages..."
    apt-get update -y
    apt-get upgrade -y
    apt-get install -y curl wget gnupg2 software-properties-common apt-transport-https ca-certificates
}

# Install Docker
install_docker() {
    log "Installing Docker..."
    
    # Remove old versions
    apt-get remove -y docker docker-engine docker.io containerd runc || true
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Enable and start Docker
    systemctl enable docker
    systemctl start docker
    
    # Add smartchat user to docker group
    usermod -aG docker $SMARTCHAT_USER || true
    
    log "Docker installed successfully"
}

# Install Docker Compose
install_docker_compose() {
    log "Installing Docker Compose..."
    
    # Get latest version
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f 4)
    
    # Download and install
    curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    log "Docker Compose $DOCKER_COMPOSE_VERSION installed successfully"
}

# Install Nginx
install_nginx() {
    log "Installing Nginx..."
    apt-get install -y nginx
    systemctl enable nginx
    systemctl start nginx
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    log "Nginx installed successfully"
}

# Setup firewall
setup_firewall() {
    log "Configuring firewall..."
    
    # Install UFW
    apt-get install -y ufw
    
    # Configure UFW
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (be careful!)
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow http
    ufw allow https
    
    # Enable firewall
    ufw --force enable
    
    log "Firewall configured successfully"
}

# Create smartchat user
create_user() {
    log "Creating smartchat user..."
    
    if ! id "$SMARTCHAT_USER" &>/dev/null; then
        useradd -m -s /bin/bash $SMARTCHAT_USER
        usermod -aG sudo $SMARTCHAT_USER
        log "User $SMARTCHAT_USER created successfully"
    else
        log "User $SMARTCHAT_USER already exists"
    fi
}

# Setup SSL certificates with Let's Encrypt
setup_ssl() {
    log "Setting up SSL certificates..."
    
    # Install Certbot
    apt-get install -y certbot python3-certbot-nginx
    
    # Create basic nginx config for domain verification
    cat > /etc/nginx/sites-available/smartchat << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}
EOF
    
    ln -sf /etc/nginx/sites-available/smartchat /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
    
    # Obtain SSL certificate
    certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email $EMAIL
    
    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    log "SSL certificates configured successfully"
}

# Create application directory structure
create_directories() {
    log "Creating application directories..."
    
    mkdir -p $SMARTCHAT_DIR/{data,logs,backups,ssl}
    mkdir -p /var/log/smartchat
    
    # Set ownership
    chown -R $SMARTCHAT_USER:$SMARTCHAT_USER $SMARTCHAT_DIR
    chown -R $SMARTCHAT_USER:$SMARTCHAT_USER /var/log/smartchat
    
    log "Directories created successfully"
}

# Setup monitoring tools
setup_monitoring() {
    log "Setting up monitoring tools..."
    
    # Install system monitoring tools
    apt-get install -y htop iotop nethogs ncdu tree
    
    # Install fail2ban for security
    apt-get install -y fail2ban
    
    # Configure fail2ban
    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF
    
    systemctl enable fail2ban
    systemctl start fail2ban
    
    log "Monitoring tools configured successfully"
}

# Setup log rotation
setup_logrotate() {
    log "Configuring log rotation..."
    
    cat > /etc/logrotate.d/smartchat << EOF
/var/log/smartchat/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 $SMARTCHAT_USER $SMARTCHAT_USER
}

/opt/smartchat/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 $SMARTCHAT_USER $SMARTCHAT_USER
}
EOF
    
    log "Log rotation configured successfully"
}

# Create production nginx configuration
create_nginx_config() {
    log "Creating production Nginx configuration..."
    
    cat > /etc/nginx/sites-available/smartchat << EOF
# Rate limiting
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=upload:10m rate=2r/s;
limit_req_zone \$binary_remote_addr zone=general:10m rate=20r/s;

# Upstream servers
upstream frontend_servers {
    least_conn;
    server 127.0.0.1:3000 max_fails=3 fail_timeout=30s;
}

upstream backend_servers {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name $DOMAIN_NAME;
    return 301 https://\$server_name\$request_uri;
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    server_name $DOMAIN_NAME;

    # SSL Configuration (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/smartchat_access.log;
    error_log /var/log/nginx/smartchat_error.log;

    # General rate limiting
    limit_req zone=general burst=50 nodelay;

    # Health check endpoint (no rate limiting)
    location = /health {
        access_log off;
        proxy_pass http://backend_servers/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # API endpoints
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend_servers;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;
    }

    # File upload endpoints (higher timeout and size limit)
    location /api/documents/upload {
        limit_req zone=upload burst=5 nodelay;
        proxy_pass http://backend_servers;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 600s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 600s;
        client_max_body_size 100M;
    }

    # WebSocket support (if needed)
    location /ws/ {
        proxy_pass http://backend_servers;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Frontend application
    location / {
        proxy_pass http://frontend_servers;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Static files (if serving directly)
    location /static/ {
        alias $SMARTCHAT_DIR/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Favicon
    location = /favicon.ico {
        alias $SMARTCHAT_DIR/static/favicon.ico;
        expires 1y;
        access_log off;
    }

    # Robots.txt
    location = /robots.txt {
        alias $SMARTCHAT_DIR/static/robots.txt;
        access_log off;
    }
}
EOF
    
    # Test nginx configuration
    nginx -t
    
    log "Nginx configuration created successfully"
}

# Create deployment script
create_deployment_script() {
    log "Creating deployment script..."
    
    cat > $SMARTCHAT_DIR/deploy.sh << 'EOF'
#!/bin/bash
# SmartChat Deployment Script

set -e

# Configuration
SMARTCHAT_DIR="/opt/smartchat"
BACKUP_DIR="$SMARTCHAT_DIR/backups"
LOG_FILE="/var/log/smartchat/deploy.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a $LOG_FILE
    exit 1
}

cd $SMARTCHAT_DIR

log "🚀 Starting SmartChat deployment..."

# Create backup
timestamp=$(date +%Y%m%d_%H%M%S)
log "📦 Creating backup..."
docker-compose exec -T postgres pg_dump -U postgres smartchat > "$BACKUP_DIR/db_backup_$timestamp.sql" || true

# Pull latest changes
log "📥 Pulling latest code..."
git pull origin main

# Build new images
log "🏗️ Building Docker images..."
docker-compose build --no-cache

# Run database migrations
log "🗄️ Running database migrations..."
docker-compose run --rm backend alembic upgrade head

# Deploy with rolling update
log "🔄 Deploying application..."
docker-compose up -d --remove-orphans

# Wait for services to be ready
log "⏳ Waiting for services to start..."
sleep 30

# Health check
log "🏥 Performing health check..."
for i in {1..30}; do
    if curl -f -s http://localhost/health > /dev/null; then
        log "✅ Health check passed!"
        break
    fi
    if [ $i -eq 30 ]; then
        error "❌ Health check failed after 30 attempts"
    fi
    sleep 2
done

# Cleanup old images
log "🧹 Cleaning up old Docker images..."
docker image prune -f

log "🎉 Deployment completed successfully!"
EOF
    
    chmod +x $SMARTCHAT_DIR/deploy.sh
    chown $SMARTCHAT_USER:$SMARTCHAT_USER $SMARTCHAT_DIR/deploy.sh
    
    log "Deployment script created successfully"
}

# Create systemd service for auto-startup
create_systemd_service() {
    log "Creating systemd service..."
    
    cat > /etc/systemd/system/smartchat.service << EOF
[Unit]
Description=SmartChat Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$SMARTCHAT_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0
User=$SMARTCHAT_USER

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable smartchat.service
    
    log "Systemd service created successfully"
}

# Setup backup script
setup_backup() {
    log "Setting up backup system..."
    
    cat > $SMARTCHAT_DIR/backup.sh << 'EOF'
#!/bin/bash
# SmartChat Backup Script

set -e

BACKUP_DIR="/opt/smartchat/backups"
RETENTION_DAYS=30
LOG_FILE="/var/log/smartchat/backup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

cd /opt/smartchat

timestamp=$(date +%Y%m%d_%H%M%S)

log "Starting backup process..."

# Database backup
log "Backing up database..."
docker-compose exec -T postgres pg_dump -U postgres smartchat | gzip > "$BACKUP_DIR/db_backup_$timestamp.sql.gz"

# Application files backup
log "Backing up application files..."
tar -czf "$BACKUP_DIR/app_backup_$timestamp.tar.gz" --exclude='backups' --exclude='.git' .

# Cleanup old backups
log "Cleaning up old backups..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

log "Backup completed successfully"
EOF
    
    chmod +x $SMARTCHAT_DIR/backup.sh
    chown $SMARTCHAT_USER:$SMARTCHAT_USER $SMARTCHAT_DIR/backup.sh
    
    # Add to crontab for smartchat user
    (sudo -u $SMARTCHAT_USER crontab -l 2>/dev/null; echo "0 2 * * * $SMARTCHAT_DIR/backup.sh") | sudo -u $SMARTCHAT_USER crontab -
    
    log "Backup system configured successfully"
}

# System optimization
optimize_system() {
    log "Optimizing system performance..."
    
    # Optimize kernel parameters
    cat >> /etc/sysctl.conf << EOF

# SmartChat optimizations
net.core.somaxconn = 65536
net.ipv4.tcp_max_syn_backlog = 65536
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 120
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.tcp_keepalive_intvl = 15
vm.swappiness = 10
fs.file-max = 65536
EOF
    
    # Apply sysctl settings
    sysctl -p
    
    # Optimize limits
    cat >> /etc/security/limits.conf << EOF
$SMARTCHAT_USER soft nofile 65536
$SMARTCHAT_USER hard nofile 65536
$SMARTCHAT_USER soft nproc 32768
$SMARTCHAT_USER hard nproc 32768
EOF
    
    log "System optimization completed"
}

# Main installation function
main() {
    log "Starting SmartChat production server setup..."
    
    check_root
    get_configuration
    
    update_system
    create_user
    install_docker
    install_docker_compose
    install_nginx
    setup_firewall
    create_directories
    setup_ssl
    create_nginx_config
    setup_monitoring
    setup_logrotate
    create_deployment_script
    create_systemd_service
    setup_backup
    optimize_system
    
    # Reload nginx with new configuration
    systemctl reload nginx
    
    log "✅ SmartChat production server setup completed successfully!"
    echo
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  SmartChat Production Server Setup Complete  ${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Clone your SmartChat repository to $SMARTCHAT_DIR"
    echo "2. Create .env file with production configuration"
    echo "3. Run deployment: sudo -u $SMARTCHAT_USER $SMARTCHAT_DIR/deploy.sh"
    echo "4. Access your application at: https://$DOMAIN_NAME"
    echo
    echo -e "${BLUE}Useful commands:${NC}"
    echo "- View logs: journalctl -u smartchat.service -f"
    echo "- Start service: systemctl start smartchat"
    echo "- Stop service: systemctl stop smartchat"
    echo "- Deploy updates: sudo -u $SMARTCHAT_USER $SMARTCHAT_DIR/deploy.sh"
    echo "- Run backups: sudo -u $SMARTCHAT_USER $SMARTCHAT_DIR/backup.sh"
    echo
    echo -e "${YELLOW}Important:${NC} Remember to:"
    echo "- Update DNS records to point $DOMAIN_NAME to this server"
    echo "- Configure your environment variables in .env"
    echo "- Test SSL certificate renewal: certbot renew --dry-run"
    echo "- Set up monitoring and alerting"
    echo
}

# Run main function
main "$@" 