# SmartChat Operations Manual

**Version: 1.0**

---

## 1. Introduction

This manual provides a comprehensive guide for developers and system administrators responsible for deploying, managing, and maintaining the SmartChat application.

### 1.1. Application Overview

SmartChat is a powerful, AI-driven document intelligence platform. It allows users to upload documents, ask questions, and receive insightful answers based on the document's content.

### 1.2. Architecture Overview

The application follows a modern, microservices-oriented architecture:

-   **Frontend**: A responsive web interface built with **React** and **TypeScript**.
-   **Backend**: A robust API service powered by **FastAPI** (Python).
-   **Database**: **PostgreSQL** for storing application data (users, documents, conversations).
-   **Vector Store**: **Qdrant** for efficient similarity search on document embeddings.
-   **Caching**: **Redis** for improving performance and caching session data.
-   **AI Services**: Integrates with multiple LLM providers (OpenAI, Anthropic, Google) for conversational AI and a separate service for generating text embeddings.
-   **Containerization**: All services are containerized using **Docker**.

---

## 2. System Prerequisites

Before setting up the application, ensure the following tools are installed on your system:

-   **Git**: For version control.
-   **Docker** and **Docker Compose**: For running the application stack.
-   **Python 3.11+** and **pip**: For backend development.
-   **Node.js 18+** and **npm**: For frontend development.
-   **(Optional) Terraform**: For managing cloud infrastructure.
-   **(Optional) `kubectl`**: For deploying to Kubernetes.

---

## 3. Local Development Setup

A detailed guide for setting up a local development environment is available in the main project `README.md`. This section provides a summary.

### 3.1. Getting Started

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/smartchat.git
    cd smartchat
    ```

2.  **Configure Environment**:
    -   Copy `backend/.env.example` to `backend/.env` and fill in the required API keys.
    -   Copy `frontend/.env.example` to `frontend/.env`.

3.  **Run the Stack**:
    Use the development Docker Compose file to start all services with hot-reloading enabled:
    ```bash
    docker-compose -f docker-compose.dev.yml up --build
    ```

-   **Backend API** will be available at `http://localhost:8000`.
-   **Frontend App** will be available at `http://localhost:3000`.

---

## 4. Production Deployment

This section details the steps to deploy SmartChat to a production environment.

### 4.1. Deployment Script

The primary method for deployment is the `deploy.sh` script in the root directory.

**Prerequisites**:
-   A production server with Docker and Docker Compose installed.
-   SSH access to the server.
-   A `.env.production` file containing all necessary production environment variables.

**Steps**:
1.  Place the `.env.production` file in the root of the project on the server.
2.  Run the deployment script:
    ```bash
    ./deploy.sh production
    ```
This script will pull the latest Docker images, stop any running containers, and start the new ones in detached mode.

### 4.2. Infrastructure as Code (IaC)

For automated cloud deployments, refer to the Terraform and Kubernetes documentation.

---

## 5. Infrastructure Management

SmartChat includes multiple options for infrastructure setup and management.

### 5.1. Terraform (AWS)

-   **Location**: `infrastructure/terraform/aws/`
-   **Purpose**: Automates the provisioning of all required AWS resources, including VPC, RDS, ElastiCache, Auto Scaling Groups, and an ALB.
-   **Usage**: See the `README.md` in that directory for detailed instructions on applying the Terraform configuration.

### 5.2. Kubernetes

-   **Location**: `infrastructure/kubernetes/`
-   **Purpose**: Provides production-ready Kubernetes manifests for deploying SmartChat.
-   **Usage**: The `deploy.sh` script in this directory automates the deployment process to a configured Kubernetes cluster.

### 5.3. Docker Swarm

-   **Location**: `infrastructure/docker-swarm/`
-   **Purpose**: An alternative container orchestration setup using Docker Swarm.
-   **Usage**: The `deploy-swarm.sh` script handles the deployment of the stack.

---

## 6. Security Management

### 6.1. SSL Certificates (Certbot)

-   **Location**: `infrastructure/security/`
-   **Management Script**: `manage-security.sh`
-   **Usage**:
    -   `./manage-security.sh issue-cert`: To obtain a new SSL certificate.
    -   Renewal is handled automatically by the Certbot container.

### 6.2. Secrets Management (Vault)

-   **Location**: `infrastructure/security/`
-   **Management Script**: `manage-security.sh`
-   **Usage**:
    -   `./manage-security.sh vault-init`: To initialize and unseal Vault for the first time.
    -   `./manage-security.sh vault-unseal`: To unseal Vault on subsequent restarts.

Refer to the `README.md` in this directory for detailed instructions.

---

## 7. Monitoring and Health Checks

The application exposes several endpoints for monitoring.

-   **/health/detailed**: A comprehensive health check endpoint on the backend.
-   **Frontend Health UI**: A React component at `/health` that visualizes the output of the detailed health check.

Your load balancer should be configured to use the `/health/readiness` endpoint for readiness probes.

---

## 8. Backup and Recovery

-   **Database**: The `scripts/backup_database.sh` script provides a way to create backups of the PostgreSQL database. It is recommended to run this script as a cron job.
-   **Recovery**: Restore a database backup using standard `pg_restore` commands.

---

## 9. CI/CD Pipeline

-   **Location**: `.github/workflows/cicd.yml`
-   **Documentation**: `.github/workflows/README.md`
-   **Functionality**: Automates linting, testing, Docker image building, and deployment based on pushes and pull requests to the `main` and `develop` branches.

---

## 10. Troubleshooting

-   **Logs**: Use `docker-compose logs -f <service_name>` to view real-time logs for any service.
-   **Common Issues**:
    -   **API Errors**: Check the backend logs for detailed error messages. The `X-Request-ID` header can be used to trace requests between the frontend and backend.
    -   **Container not starting**: Use `docker-compose ps` to check the status of containers and `docker-compose logs` to see why it might have exited.
    -   **Permission errors**: Ensure that the user running the Docker daemon has the correct permissions for the volume mounts. 