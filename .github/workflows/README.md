# CI/CD Pipeline

This document explains the setup and functionality of the CI/CD pipeline for the SmartChat application, which is managed using GitHub Actions.

## Pipeline Overview

The CI/CD pipeline is defined in `.github/workflows/cicd.yml` and consists of three main jobs:

1.  **`lint-and-test`**: This job runs on every push and pull request to the `main` and `develop` branches. It performs:
    -   Code checkout.
    -   Setup of Python and Node.js environments.
    -   Installation of backend and frontend dependencies.
    -   Linting of both backend (with `isort`, `black`, `flake8`) and frontend code.
    -   Execution of unit and integration tests for both backend (`pytest`) and frontend.

2.  **`build-and-push`**: This job runs only on pushes to the `main` and `develop` branches, and it depends on the successful completion of `lint-and-test`. It is responsible for:
    -   Building the production Docker images for the backend and frontend.
    -   Tagging the images:
        -   Pushes to `main` are tagged as `latest`.
        -   Pushes to `develop` are tagged as `develop`.
    -   Pushing the tagged images to Docker Hub.

3.  **`deploy`**: This job runs only on pushes to the `main` branch and depends on the successful completion of `build-and-push`. It handles the deployment to the production server by:
    -   Connecting to the production server via SSH.
    -   Navigating to the application directory.
    -   Pulling the latest Docker images from the registry.
    -   Restarting the application using `docker-compose`.

## Setup and Configuration

To use this CI/CD pipeline, you need to configure the following secrets in your GitHub repository settings (`Settings -> Secrets and variables -> Actions`):

### Repository Secrets

-   **`DOCKERHUB_USERNAME`**: Your username for Docker Hub.
-   **`DOCKERHUB_TOKEN`**: An access token for Docker Hub with read/write permissions.
-   **`PROD_SERVER_HOST`**: The hostname or IP address of your production server.
-   **`PROD_SERVER_USERNAME`**: The username for SSH access to your production server.
-   **`PROD_SERVER_SSH_KEY`**: The private SSH key for accessing your production server.

### Environments

The `deploy` job uses a GitHub Environment named `production`. You can configure this environment to add protection rules, such as required reviewers for deployments to the `main` branch.

## Workflow Triggers

-   **Push to `main`**: Triggers all three jobs: `lint-and-test`, `build-and-push` (with `latest` tag), and `deploy`.
-   **Push to `develop`**: Triggers `lint-and-test` and `build-and-push` (with `develop` tag).
-   **Pull Request to `main`**: Triggers the `lint-and-test` job to ensure code quality before merging.

## Manual Workflow Dispatch

You can also add a `workflow_dispatch` event to the `on` section in the `cicd.yml` file to allow manual triggering of the pipeline from the GitHub Actions tab.

```yaml
on:
  workflow_dispatch:
  push:
    # ...
```

This provides a robust, automated workflow for maintaining code quality and deploying the SmartChat application. 