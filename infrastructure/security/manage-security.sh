#!/bin/bash

# SmartChat Security Services Management Script
# Usage: ./manage-security.sh [action]
# Actions: start, stop, logs, issue-cert, renew-certs, vault-init, vault-unseal

set -e

# Configuration
COMPOSE_FILE="docker-compose.yml"
DOMAIN="smartchat.yourdomain.com"
EMAIL="your-email@yourdomain.com"

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

log() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}" >&2; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
warning() { echo -e "${YELLOW}[WARNING] $1${NC}"; }

# --- Helper Functions ---

check_docker() {
    if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
        error "Docker and Docker Compose are not installed. Please install them to continue."
        exit 1
    fi
    log "Docker and Docker Compose are available."
}

ensure_network() {
    if ! docker network ls | grep -q "smartchat-network"; then
        warning "smartchat-network not found. Creating it now."
        docker network create smartchat-network
        success "smartchat-network created."
    fi
}

# --- Main Actions ---

start_services() {
    log "Starting security services (Certbot, Vault)..."
    check_docker
    ensure_network
    docker-compose -f "$COMPOSE_FILE" up -d
    success "Security services started."
    docker-compose -f "$COMPOSE_FILE" ps
}

stop_services() {
    log "Stopping security services..."
    docker-compose -f "$COMPOSE_FILE" down
    success "Security services stopped."
}

view_logs() {
    log "Tailing logs for security services... (Press Ctrl+C to exit)"
    docker-compose -f "$COMPOSE_FILE" logs -f
}

issue_certificate() {
    log "Issuing new SSL certificate for ${DOMAIN}..."
    
    # Ensure Nginx is running and configured for the challenge
    if ! docker ps | grep -q "nginx"; then
        error "Nginx container is not running. Please start the main application stack first."
        exit 1
    fi
    
    log "Temporarily stopping nginx to issue certificate..."
    docker stop nginx || warning "Nginx was not running."
    
    docker-compose -f "$COMPOSE_FILE" run --rm --entrypoint "\\
      certbot certonly --webroot -w /var/www/certbot \\
      --email ${EMAIL} -d ${DOMAIN} --agree-tos --no-eff-email" certbot

    success "Certificate issued successfully."
    log "Restarting nginx..."
    docker start nginx
}

renew_certificates() {
    log "Attempting to renew SSL certificates..."
    docker-compose -f "$COMPOSE_FILE" run --rm --entrypoint "certbot renew" certbot
    success "Certificate renewal check completed."
}

vault_initialize() {
    log "Initializing and unsealing Vault..."
    if ! docker ps | grep -q "vault"; then
        error "Vault container is not running. Please start services first."
        exit 1
    fi

    # Initialize Vault
    init_output=$(docker exec vault vault operator init -key-shares=1 -key-threshold=1 -format=json)
    
    if [ -z "$init_output" ]; then
        error "Failed to initialize Vault. Is it already initialized?"
        exit 1
    fi
    
    unseal_key=$(echo "$init_output" | jq -r '.unseal_keys_b64[0]')
    root_token=$(echo "$init_output" | jq -r '.root_token')

    if [ -z "$unseal_key" ] || [ "$unseal_key" == "null" ]; then
        error "Failed to extract unseal key."
        exit 1
    fi
    if [ -z "$root_token" ] || [ "$root_token" == "null" ]; then
        error "Failed to extract root token."
        exit 1
    fi

    log "Unsealing Vault..."
    docker exec vault vault operator unseal "$unseal_key"
    
    # Store credentials securely
    mkdir -p .vault
    echo "$init_output" > .vault/keys.json
    echo "VAULT_ROOT_TOKEN=${root_token}" > .vault/.env
    chmod 600 .vault/*
    
    success "Vault initialized and unsealed."
    success "Unseal Key and Root Token saved in ./ .vault/"
    warning "Secure these credentials! This is for development setup."
}

vault_unseal() {
    log "Unsealing Vault using existing keys..."
    if [ ! -f ".vault/keys.json" ]; then
        error "Vault keys not found. Run 'vault-init' first."
        exit 1
    fi
    
    unseal_key=$(jq -r '.unseal_keys_b64[0]' .vault/keys.json)
    
    if [ -z "$unseal_key" ] || [ "$unseal_key" == "null" ]; then
        error "Could not read unseal key from .vault/keys.json"
        exit 1
    fi
    
    docker exec vault vault operator unseal "$unseal_key"
    success "Vault unsealed."
}

# --- Command Line Interface ---

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 {start|stop|logs|issue-cert|renew-certs|vault-init|vault-unseal}"
    exit 1
fi

case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    logs)
        view_logs
        ;;
    issue-cert)
        issue_certificate
        ;;
    renew-certs)
        renew_certificates
        ;;
    vault-init)
        vault_initialize
        ;;
    vault-unseal)
        vault_unseal
        ;;
    *)
        error "Unknown command: $1"
        exit 1
        ;;
esac

exit 0 