#!/usr/bin/env python3
"""
Database initialization script.

This script creates all database tables and can be used to set up the database
for the first time or reset it during development.
"""

import sys
import asyncio
from sqlalchemy.exc import OperationalError
from database import create_tables, drop_tables, engine
from models import *  # Import all models to ensure they're registered
from config import settings

def init_database():
    """Initialize the database by creating all tables."""
    try:
        print("Creating database tables...")
        create_tables()
        print("✅ Database tables created successfully!")
        return True
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print("Make sure PostgreSQL is running and the connection string is correct.")
        return False
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def reset_database():
    """Reset the database by dropping and recreating all tables."""
    try:
        print("⚠️  Dropping all database tables...")
        drop_tables()
        print("Creating database tables...")
        create_tables()
        print("✅ Database reset successfully!")
        return True
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        return False

def check_connection():
    """Check if database connection is working."""
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("SmartChat Database Initialization")
    print(f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    print("-" * 50)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "reset":
            print("⚠️  WARNING: This will delete all data in the database!")
            confirm = input("Are you sure you want to reset the database? (yes/no): ")
            if confirm.lower() == "yes":
                reset_database()
            else:
                print("Database reset cancelled.")
        elif command == "check":
            check_connection()
        else:
            print("Unknown command. Available commands:")
            print("  python init_db.py        - Create tables (default)")
            print("  python init_db.py reset  - Drop and recreate all tables")
            print("  python init_db.py check  - Check database connection")
    else:
        # Default: create tables
        init_database() 