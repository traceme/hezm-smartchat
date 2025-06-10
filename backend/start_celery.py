#!/usr/bin/env python3
"""
Celery worker startup script.

This script starts Celery workers for document processing tasks.
"""

import os
import sys
from celery_app import celery_app

def start_worker():
    """Start Celery worker."""
    print("Starting Celery worker for SmartChat document processing...")
    
    # Set worker options
    worker_options = [
        'worker',
        '--loglevel=info',
        '--concurrency=2',  # Number of worker processes
        '--queues=document_processing,celery',  # Listen to specific queues
        '--hostname=smartchat-worker@%h',
    ]
    
    # Start the worker
    celery_app.worker_main(worker_options)

def start_beat():
    """Start Celery beat scheduler."""
    print("Starting Celery beat scheduler...")
    
    beat_options = [
        'beat',
        '--loglevel=info',
        '--schedule-filename=/tmp/celerybeat-schedule',
        '--pidfile=/tmp/celerybeat.pid'
    ]
    
    celery_app.start(beat_options)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "beat":
        start_beat()
    else:
        start_worker() 