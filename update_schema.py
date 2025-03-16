# update_schema.py

import os
import sqlite3
import logging
from db import Base, engine
from config import DATABASE_URL

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_sqlite_path_from_url(url):
    """Extract SQLite file path from database URL."""
    if url.startswith('sqlite:///'):
        return url[10:]
    return None

def backup_database(db_path):
    """Create a backup of the database file."""
    import shutil
    backup_path = f"{db_path}.backup"
    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backup created at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create database backup: {str(e)}")
        return False

def check_column_exists(conn, table, column):
    """Check if a column exists in a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    return column in columns

def add_column_to_table(conn, table, column, column_type):
    """Add a column to a table if it doesn't exist."""
    if not check_column_exists(conn, table, column):
        try:
            cursor = conn.cursor()
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
            logger.info(f"Added column {column} to table {table}")
            return True
        except Exception as e:
            logger.error(f"Failed to add column {column} to {table}: {str(e)}")
            return False
    else:
        logger.info(f"Column {column} already exists in table {table}")
        return True

def update_video_table(conn):
    """Update the videos table schema."""
    add_column_to_table(conn, "videos", "created_at", "TIMESTAMP")
    add_column_to_table(conn, "videos", "duration_seconds", "INTEGER")
    add_column_to_table(conn, "videos", "transcript", "TEXT")
    add_column_to_table(conn, "videos", "is_analyzed", "BOOLEAN DEFAULT 0")
    
    # Check if videos table exists at all
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'")
    if not cursor.fetchone():
        logger.warning("Videos table does not exist! Will be created with init_db.")
        return False
    
    return True

def update_summary_table(conn):
    """Update the video_summaries table schema."""
    add_column_to_table(conn, "video_summaries", "short_summary", "TEXT")
    add_column_to_table(conn, "video_summaries", "detailed_summary", "TEXT")
    add_column_to_table(conn, "video_summaries", "has_transcription", "BOOLEAN DEFAULT 0")
    add_column_to_table(conn, "video_summaries", "last_analyzed", "TIMESTAMP")
    
    # Check if video_summaries table exists at all
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_summaries'")
    if not cursor.fetchone():
        logger.warning("Video_summaries table does not exist! Will be created with init_db.")
        return False
    
    return True

def main():
    """Update the database schema to match current models."""
    logger.info("Starting database schema update")
    
    # Get SQLite database path
    db_path = get_sqlite_path_from_url(DATABASE_URL)
    if not db_path:
        logger.error(f"Could not extract database path from {DATABASE_URL}")
        return False
    
    # Check if database file exists
    if not os.path.exists(db_path):
        logger.warning(f"Database file {db_path} does not exist. Will initialize a new database.")
        # Import all models to ensure they're properly registered
        from models.video import Video
        from models.video_summary import VideoSummary
        
        # Create all tables from scratch
        Base.metadata.create_all(bind=engine)
        logger.info("Created new database with all tables")
        return True
    
    # Backup existing database
    if not backup_database(db_path):
        logger.error("Failed to backup database, aborting schema update")
        return False
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        
        # Update tables
        videos_updated = update_video_table(conn)
        summaries_updated = update_summary_table(conn)
        
        # Commit changes
        conn.commit()
        conn.close()
        
        if not videos_updated or not summaries_updated:
            logger.info("Some tables were missing. Running full initialization.")
            # Import all models
            from models.video import Video
            from models.video_summary import VideoSummary
            
            # Create any missing tables
            Base.metadata.create_all(bind=engine)
        
        logger.info("Database schema update completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("Database schema updated successfully.")
    else:
        print("Database schema update failed. Check logs for details.")