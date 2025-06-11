# Security Infrastructure Management

This directory contains the necessary configurations and scripts to manage essential security services for the SmartChat application, including SSL certificate management with Certbot and secrets management with HashiCorp Vault.

## Services

1.  **Certbot**: Automates the process of obtaining, renewing, and managing SSL/TLS certificates from Let's Encrypt.
2.  **Vault**: Provides centralized secrets management, including API keys, database credentials, and other sensitive data.

## Prerequisites

- Docker and Docker-Compose must be installed on your system.
- Your server must be accessible from the public internet on ports 80 and 443 for Let's Encrypt certificate issuance.
- A registered domain name pointing to your server's public IP address.

## Directory Structure

```
infrastructure/security/
├── config/
│   ├── certbot/
│   │   ├── conf/      # Let's Encrypt configuration and certificates
│   │   └── www/       # Webroot for ACME challenge
│   └── vault/
│       ├── config/    # Vault server configuration
│       │   └── vault.json
│       ├── file/      # Vault data storage (for file backend)
│       └── logs/      # Vault audit logs
├── .vault/            # (Generated) Secure storage for Vault keys
├── docker-compose.yml # Docker Compose for security services
└── manage-security.sh # Script to manage services
```

## Setup and Usage

All interactions with these services are managed through the `manage-security.sh` script.

### 1. Initial Setup

Before starting, open `manage-security.sh` and configure the following variables:

-   `DOMAIN`: Your application's domain name (e.g., `smartchat.yourdomain.com`).
-   `EMAIL`: The email address for Let's Encrypt registration and recovery.

### 2. Starting and Stopping Services

-   **Start services**:
    ```bash
    ./manage-security.sh start
    ```
    This command will start the Certbot and Vault containers in detached mode. It will also create the `smartchat-network` if it doesn't exist.

-   **Stop services**:
    ```bash
    ./manage-security.sh stop
    ```
    This stops and removes the containers defined in `docker-compose.yml`.

-   **View logs**:
    ```bash
    ./manage-security.sh logs
    ```
    This will tail the logs from both services. Press `Ctrl+C` to exit.

### 3. Managing SSL Certificates (Certbot)

**Important**: Ensure your main application's Nginx or other web server container is running and accessible before issuing a certificate, as Certbot needs to perform an HTTP-01 challenge.

-   **Issue a new certificate**:
    ```bash
    ./manage-security.sh issue-cert
    ```
    This command will temporarily stop your main Nginx container, run Certbot to obtain a certificate for your domain, and then restart Nginx. The certificates will be stored in `config/certbot/conf`.

-   **Renew certificates**:
    Let's Encrypt certificates are valid for 90 days. The Certbot container is configured to automatically check for renewal every 12 hours. You can also trigger a manual renewal check:
    ```bash
    ./manage-security.sh renew-certs
    ```

### 4. Managing Secrets (Vault)

-   **Initialize Vault**:
    On the first run, you must initialize Vault. This process generates the master keys and the initial root token.
    ```bash
    ./manage-security.sh vault-init
    ```
    This command will:
    1.  Initialize Vault.
    2.  Create a `.vault/` directory.
    3.  Save the unseal keys and root token to `.vault/keys.json`.
    4.  Save the root token to `.vault/.env` for easy access.
    5.  Automatically unseal Vault with the newly generated key.

    **⚠️ SECURITY WARNING**: The `.vault/` directory contains highly sensitive information. It is created with restricted permissions (`600`), but you must secure these files. In a production environment, you would use a more robust backend (like Consul or an integrated storage) and manage unsealing through a KMS or a secure operational procedure.

-   **Unsealing Vault on Restart**:
    If you stop and restart the Vault container, it will start in a sealed state. You need to unseal it using the key generated during initialization.
    ```bash
    ./manage-security.sh vault-unseal
    ```
    This reads the unseal key from `.vault/keys.json` and applies it.

-   **Accessing Vault UI**:
    Once unsealed, you can access the Vault UI at `http://<your-server-ip>:8200`. Use the root token from `.vault/keys.json` to log in.

## Integrating with the Application

To use Vault secrets in your application, you will need to:
1.  Use a Vault client library (like `hvac` for Python).
2.  Authenticate your application to Vault (e.g., using AppRole, JWT, or another auth method).
3.  Read secrets from the appropriate path in Vault.
4.  Update your application's configuration to pull secrets from Vault instead of environment variables.

This setup provides a foundational layer for production-grade security. 