#!/usr/bin/env python3
"""
Database Migration Script: SQLite to PostgreSQL

This script migrates data from SQLite to PostgreSQL for SmartChat application.
It handles schema creation, data export, and import with data validation.
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Add backend to path for imports
script_dir = Path(__file__).parent
backend_dir = script_dir.parent / "backend"
sys.path.insert(0, str(backend_dir))

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handles migration from SQLite to PostgreSQL"""
    
    def __init__(self, sqlite_path: str, postgres_url: str):
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.exported_data = {}
        self.migration_stats = {
            'exported': {},
            'imported': {},
            'errors': []
        }
    
    def connect_sqlite(self) -> sqlite3.Connection:
        """Connect to SQLite database"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            logger.info(f"Connected to SQLite database: {self.sqlite_path}")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise
    
    def connect_postgres(self) -> psycopg2.extensions.connection:
        """Connect to PostgreSQL database"""
        try:
            # Parse PostgreSQL URL components
            import urllib.parse as urlparse
            parsed = urlparse.urlparse(self.postgres_url)
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],  # Remove leading slash
                user=parsed.username,
                password=parsed.password
            )
            logger.info(f"Connected to PostgreSQL database: {parsed.hostname}:{parsed.port}/{parsed.path[1:]}")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def export_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """Export data from SQLite table"""
        try:
            sqlite_conn = self.connect_sqlite()
            cursor = sqlite_conn.cursor()
            
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Export data
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Handle datetime conversion
                    if col.endswith('_at') and value:
                        try:
                            # Try to parse as datetime string
                            if isinstance(value, str):
                                # SQLite might store as ISO string
                                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            pass  # Keep original value
                    row_dict[col] = value
                data.append(row_dict)
            
            sqlite_conn.close()
            logger.info(f"Exported {len(data)} rows from {table_name}")
            self.migration_stats['exported'][table_name] = len(data)
            return data
            
        except Exception as e:
            logger.error(f"Failed to export data from {table_name}: {e}")
            self.migration_stats['errors'].append(f"Export {table_name}: {e}")
            return []
    
    def import_table_data(self, table_name: str, data: List[Dict[str, Any]]) -> bool:
        """Import data into PostgreSQL table"""
        if not data:
            logger.info(f"No data to import for {table_name}")
            return True
        
        try:
            pg_conn = self.connect_postgres()
            cursor = pg_conn.cursor()
            
            # Prepare column names and placeholders
            columns = list(data[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            
            # Build INSERT query
            query = f"""
                INSERT INTO {table_name} ({column_names})
                VALUES ({placeholders})
            """
            
            # Prepare data for insertion
            values = []
            for row in data:
                row_values = []
                for col in columns:
                    value = row[col]
                    # Handle JSON fields
                    if col == 'source_chunks' and value:
                        if isinstance(value, str):
                            try:
                                value = json.loads(value)
                            except json.JSONDecodeError:
                                value = None
                    row_values.append(value)
                values.append(tuple(row_values))
            
            # Execute batch insert
            cursor.executemany(query, values)
            
            # Update sequence for ID columns
            if 'id' in columns:
                cursor.execute(f"""
                    SELECT setval('{table_name}_id_seq', 
                           COALESCE((SELECT MAX(id) FROM {table_name}), 1), 
                           MAX(id) IS NOT NULL) 
                    FROM {table_name}
                """)
            
            pg_conn.commit()
            pg_conn.close()
            
            logger.info(f"Successfully imported {len(data)} rows into {table_name}")
            self.migration_stats['imported'][table_name] = len(data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to import data into {table_name}: {e}")
            self.migration_stats['errors'].append(f"Import {table_name}: {e}")
            return False
    
    def run_alembic_migration(self) -> bool:
        """Run Alembic migration to create PostgreSQL schema"""
        try:
            import subprocess
            
            logger.info("Running Alembic migration to create PostgreSQL schema...")
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd=str(backend_dir),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Alembic migration completed successfully")
                return True
            else:
                logger.error(f"Alembic migration failed: {result.stderr}")
                self.migration_stats['errors'].append(f"Alembic migration: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run Alembic migration: {e}")
            self.migration_stats['errors'].append(f"Alembic migration: {e}")
            return False
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful"""
        try:
            sqlite_conn = self.connect_sqlite()
            pg_conn = self.connect_postgres()
            
            # Tables to validate
            tables = ['users', 'documents', 'document_chunks', 'conversations', 'messages']
            
            validation_results = {}
            
            for table in tables:
                # Count rows in SQLite
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                # Count rows in PostgreSQL
                pg_cursor = pg_conn.cursor()
                pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                pg_count = pg_cursor.fetchone()[0]
                
                validation_results[table] = {
                    'sqlite_count': sqlite_count,
                    'postgres_count': pg_count,
                    'match': sqlite_count == pg_count
                }
                
                logger.info(f"Validation {table}: SQLite={sqlite_count}, PostgreSQL={pg_count}, Match={sqlite_count == pg_count}")
            
            sqlite_conn.close()
            pg_conn.close()
            
            # Check if all tables match
            all_match = all(result['match'] for result in validation_results.values())
            
            if all_match:
                logger.info("✅ Migration validation successful - all row counts match")
            else:
                logger.warning("⚠️  Migration validation found mismatches")
            
            return all_match
            
        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return False
    
    def migrate(self) -> bool:
        """Run complete migration process"""
        logger.info("🚀 Starting database migration from SQLite to PostgreSQL")
        
        # Check if SQLite database exists
        if not os.path.exists(self.sqlite_path):
            logger.error(f"SQLite database not found: {self.sqlite_path}")
            return False
        
        try:
            # 1. Run Alembic migration to create schema
            if not self.run_alembic_migration():
                return False
            
            # 2. Export data from SQLite
            tables = ['users', 'documents', 'document_chunks', 'conversations', 'messages']
            
            for table in tables:
                logger.info(f"Exporting data from {table}...")
                self.exported_data[table] = self.export_table_data(table)
            
            # 3. Import data into PostgreSQL (in dependency order)
            import_order = ['users', 'documents', 'document_chunks', 'conversations', 'messages']
            
            for table in import_order:
                if table in self.exported_data:
                    logger.info(f"Importing data into {table}...")
                    if not self.import_table_data(table, self.exported_data[table]):
                        logger.error(f"Failed to import {table}")
                        return False
            
            # 4. Validate migration
            logger.info("Validating migration...")
            validation_success = self.validate_migration()
            
            # 5. Print migration summary
            self.print_migration_summary()
            
            if validation_success and not self.migration_stats['errors']:
                logger.info("🎉 Database migration completed successfully!")
                return True
            else:
                logger.error("❌ Database migration completed with errors")
                return False
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def print_migration_summary(self):
        """Print migration statistics"""
        logger.info("\n" + "="*50)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*50)
        
        logger.info("Exported tables:")
        for table, count in self.migration_stats['exported'].items():
            logger.info(f"  {table}: {count} rows")
        
        logger.info("\nImported tables:")
        for table, count in self.migration_stats['imported'].items():
            logger.info(f"  {table}: {count} rows")
        
        if self.migration_stats['errors']:
            logger.info("\nErrors encountered:")
            for error in self.migration_stats['errors']:
                logger.error(f"  {error}")
        else:
            logger.info("\n✅ No errors encountered")


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Migrate SmartChat database from SQLite to PostgreSQL')
    parser.add_argument('--sqlite-path', 
                       help='Path to SQLite database file',
                       default='backend/smartchat_debug.db')
    parser.add_argument('--postgres-url',
                       help='PostgreSQL connection URL',
                       default=None)
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='Export data but do not import (validation only)')
    
    args = parser.parse_args()
    
    # Get PostgreSQL URL from environment or argument
    postgres_url = args.postgres_url
    if not postgres_url:
        settings = get_settings()
        postgres_url = settings.database_url
        
        # Ensure we're using PostgreSQL URL
        if not postgres_url.startswith('postgresql'):
            logger.error("PostgreSQL URL must be provided via --postgres-url or DATABASE_URL environment variable")
            return False
    
    # Initialize migrator
    migrator = DatabaseMigrator(args.sqlite_path, postgres_url)
    
    if args.dry_run:
        logger.info("Running in dry-run mode (export only)")
        # Just export and validate data structure
        tables = ['users', 'documents', 'document_chunks', 'conversations', 'messages']
        for table in tables:
            data = migrator.export_table_data(table)
            logger.info(f"Would migrate {len(data)} rows from {table}")
        return True
    else:
        # Run full migration
        return migrator.migrate()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 