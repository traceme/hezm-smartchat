#!/usr/bin/env python3
"""
Development runner script for SmartChat backend.

This script helps start all necessary services for development.
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

def start_redis():
    """Start Redis using Docker."""
    print("Starting Redis...")
    try:
        result = subprocess.run([
            "docker", "run", "-d", "--name", "smartchat-redis", 
            "-p", "6379:6379", "redis:alpine"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Redis started successfully")
            return True
        else:
            # Check if container already exists
            if "already in use" in result.stderr:
                print("✅ Redis container already running")
                return True
            else:
                print(f"❌ Failed to start Redis: {result.stderr}")
                return False
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker or start Redis manually.")
        return False

def start_postgres():
    """Start PostgreSQL using Docker."""
    print("Starting PostgreSQL...")
    try:
        result = subprocess.run([
            "docker", "run", "-d", "--name", "smartchat-postgres",
            "-e", "POSTGRES_DB=smartchat",
            "-e", "POSTGRES_USER=postgres", 
            "-e", "POSTGRES_PASSWORD=password",
            "-p", "5432:5432", "postgres:15"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ PostgreSQL started successfully")
            print("⏳ Waiting for PostgreSQL to be ready...")
            time.sleep(5)
            return True
        else:
            if "already in use" in result.stderr:
                print("✅ PostgreSQL container already running")
                return True
            else:
                print(f"❌ Failed to start PostgreSQL: {result.stderr}")
                return False
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker or start PostgreSQL manually.")
        return False

def start_qdrant():
    """Start Qdrant using Docker."""
    print("Starting Qdrant...")
    try:
        result = subprocess.run([
            "docker", "run", "-d", "--name", "smartchat-qdrant",
            "-p", "6333:6333", "qdrant/qdrant"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Qdrant started successfully")
            return True
        else:
            if "already in use" in result.stderr:
                print("✅ Qdrant container already running")
                return True
            else:
                print(f"❌ Failed to start Qdrant: {result.stderr}")
                return False
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker or start Qdrant manually.")
        return False

def init_database():
    """Initialize database tables."""
    print("Initializing database...")
    try:
        result = subprocess.run([sys.executable, "init_db.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Database initialized successfully")
            return True
        else:
            print(f"❌ Database initialization failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

def start_celery_worker():
    """Start Celery worker in background."""
    print("Starting Celery worker...")
    try:
        process = subprocess.Popen([
            sys.executable, "start_celery.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("✅ Celery worker started")
        return process
    except Exception as e:
        print(f"❌ Failed to start Celery worker: {e}")
        return None

def start_fastapi():
    """Start FastAPI development server."""
    print("Starting FastAPI server...")
    try:
        subprocess.run([
            "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n🛑 FastAPI server stopped")
    except Exception as e:
        print(f"❌ Failed to start FastAPI: {e}")

def stop_containers():
    """Stop Docker containers."""
    print("Stopping Docker containers...")
    containers = ["smartchat-redis", "smartchat-postgres", "smartchat-qdrant"]
    
    for container in containers:
        try:
            subprocess.run(["docker", "stop", container], capture_output=True)
            subprocess.run(["docker", "rm", container], capture_output=True)
        except:
            pass

def main():
    """Main development runner."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "stop":
            stop_containers()
            return
        elif command == "test":
            print("Running tests...")
            subprocess.run([sys.executable, "test_document_processing.py"])
            return
        elif command == "worker":
            # Start only Celery worker
            start_celery_worker()
            return
    
    print("SmartChat Development Environment")
    print("=" * 40)
    
    # Start services
    if not start_redis():
        return
    
    if not start_postgres():
        return
    
    if not start_qdrant():
        return
    
    if not init_database():
        return
    
    # Start Celery worker
    celery_process = start_celery_worker()
    
    try:
        # Start FastAPI server (this will block)
        start_fastapi()
    finally:
        # Clean up
        if celery_process:
            celery_process.terminate()
        print("\n🛑 Development environment stopped")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        stop_containers() 