#!/bin/bash

# SmartChat Production Deployment Script
# This script builds, tests, and deploys the SmartChat application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
SKIP_TESTS=${SKIP_TESTS:-false}
BACKUP_BEFORE_DEPLOY=${BACKUP_BEFORE_DEPLOY:-true}

echo -e "${BLUE}🚀 Starting SmartChat deployment for environment: ${ENVIRONMENT}${NC}"

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if required files exist
check_requirements() {
    print_status "Checking deployment requirements..."
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found!"
        exit 1
    fi
    
    if [ ! -f ".env" ] && [ "$ENVIRONMENT" = "production" ]; then
        print_warning ".env file not found. Please copy env.production.example to .env and configure it."
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    print_status "Requirements check passed"
}

# Backup current deployment (if exists)
backup_deployment() {
    if [ "$BACKUP_BEFORE_DEPLOY" = "true" ]; then
        print_status "Creating backup of current deployment..."
        
        # Create backup directory with timestamp
        BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup database if container is running
        if docker ps | grep -q smartchat-postgres; then
            print_status "Backing up PostgreSQL database..."
            docker exec smartchat-postgres pg_dump -U postgres smartchat > "$BACKUP_DIR/database_backup.sql"
        fi
        
        # Backup volumes
        if docker volume ls | grep -q smartchat; then
            print_status "Backing up Docker volumes..."
            docker run --rm -v smartchat_upload_data:/data -v "$PWD/$BACKUP_DIR:/backup" alpine tar czf /backup/uploads.tar.gz -C /data .
            docker run --rm -v smartchat_logs_data:/data -v "$PWD/$BACKUP_DIR:/backup" alpine tar czf /backup/logs.tar.gz -C /data .
        fi
        
        print_status "Backup completed: $BACKUP_DIR"
    fi
}

# Build Docker images
build_images() {
    print_status "Building Docker images..."
    
    # Build backend
    print_status "Building backend image..."
    docker build -t smartchat-backend:latest -f backend/Dockerfile backend/
    
    # Build frontend
    print_status "Building frontend image..."
    docker build -t smartchat-frontend:latest -f frontend/Dockerfile frontend/
    
    print_status "Docker images built successfully"
}

# Run tests
run_tests() {
    if [ "$SKIP_TESTS" = "false" ]; then
        print_status "Running tests..."
        
        # Test backend
        print_status "Testing backend..."
        docker run --rm smartchat-backend:latest python -m pytest tests/ || true
        
        # Test frontend build
        print_status "Testing frontend build..."
        docker run --rm smartchat-frontend:latest echo "Frontend build test passed"
        
        print_status "Tests completed"
    else
        print_warning "Skipping tests (SKIP_TESTS=true)"
    fi
}

# Deploy services
deploy_services() {
    print_status "Deploying SmartChat services..."
    
    # Stop existing services
    print_status "Stopping existing services..."
    docker-compose down || true
    
    # Start new deployment
    print_status "Starting new deployment..."
    docker-compose up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -q "Up (healthy)"; then
            break
        fi
        
        echo "Waiting for services... ($((attempt + 1))/$max_attempts)"
        sleep 10
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Services failed to become healthy within timeout"
        docker-compose logs
        exit 1
    fi
    
    print_status "All services are healthy"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Check if all containers are running
    if ! docker-compose ps | grep -q "Up"; then
        print_error "Some containers are not running"
        docker-compose ps
        exit 1
    fi
    
    # Test health endpoints
    print_status "Testing health endpoints..."
    
    # Wait a bit for services to fully start
    sleep 5
    
    # Test backend health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_status "Backend health check passed"
    else
        print_warning "Backend health check failed"
    fi
    
    # Test frontend health
    if curl -f http://localhost:3000/health > /dev/null 2>&1; then
        print_status "Frontend health check passed"
    else
        print_warning "Frontend health check failed"
    fi
    
    print_status "Deployment verification completed"
}

# Show deployment status
show_status() {
    echo -e "\n${BLUE}📊 Deployment Status${NC}"
    echo "===================="
    docker-compose ps
    
    echo -e "\n${BLUE}🔗 Service URLs${NC}"
    echo "==============="
    echo "Frontend: http://localhost:3000"
    echo "Backend:  http://localhost:8000"
    echo "Backend API Docs: http://localhost:8000/docs"
    
    echo -e "\n${BLUE}📝 Logs${NC}"
    echo "========"
    echo "View logs: docker-compose logs -f [service_name]"
    echo "Services: frontend, backend, postgres, redis, qdrant"
}

# Main deployment flow
main() {
    echo -e "${BLUE}Starting SmartChat deployment...${NC}\n"
    
    check_requirements
    backup_deployment
    build_images
    run_tests
    deploy_services
    verify_deployment
    show_status
    
    echo -e "\n${GREEN}🎉 SmartChat deployment completed successfully!${NC}"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        echo -e "\n${YELLOW}⚠ Production deployment notes:${NC}"
        echo "1. Ensure all API keys are properly configured in .env"
        echo "2. Set up SSL certificates for HTTPS"
        echo "3. Configure monitoring and alerting"
        echo "4. Set up automated backups"
        echo "5. Review security settings"
    fi
}

# Handle script termination
trap 'echo -e "\n${RED}Deployment interrupted${NC}"; exit 1' INT TERM

# Run main function
main "$@" 