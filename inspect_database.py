# inspect_database.py

import sqlite3
import sys
import os
from config import DATABASE_URL

def get_sqlite_path_from_url(url):
    """Extract SQLite file path from database URL."""
    if url.startswith('sqlite:///'):
        return url[10:]
    return None

def inspect_database():
    """Inspect the SQLite database and print schema information."""
    db_path = get_sqlite_path_from_url(DATABASE_URL)
    
    if not db_path:
        print(f"Could not extract database path from {DATABASE_URL}")
        return False
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist.")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"Database contains {len(tables)} tables:")
    
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"Columns ({len(columns)}):")
        print("ID  | Name                  | Type       | NotNull | DefaultValue | PK")
        print("-" * 80)
        
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, is_pk = col
            print(f"{col_id:<4}| {col_name:<22}| {col_type:<11}| {not_null:<8}| {default_val or 'None':<12}| {is_pk}")
        
        # If it's one of our main tables, show a sample row
        if table_name in ('videos', 'video_summaries'):
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                sample = cursor.fetchone()
                if sample:
                    print(f"\nSample row from {table_name}:")
                    for i, col in enumerate(columns):
                        col_name = col[1]
                        value = sample[i]
                        print(f"  {col_name}: {value}")
            except Exception as e:
                print(f"Error getting sample: {e}")
    
    conn.close()
    return True

def generate_models():
    """Generate Python model files based on the actual database schema."""
    db_path = get_sqlite_path_from_url(DATABASE_URL)
    
    if not db_path:
        print(f"Could not extract database path from {DATABASE_URL}")
        return False
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist.")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get video_summaries table info
    cursor.execute("PRAGMA table_info(video_summaries)")
    columns = cursor.fetchall()
    
    if not columns:
        print("Could not find video_summaries table in the database.")
        return False
    
    # Generate VideoSummary model
    model_code = """# models/video_summary.py - GENERATED FROM DATABASE SCHEMA

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db import Base

class VideoSummary(Base):
    \"\"\"Model for storing video analysis results.\"\"\"
    
    __tablename__ = "video_summaries"
    
"""
    
    # Add columns based on actual database schema
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, is_pk = col
        
        # Map SQLite types to SQLAlchemy types
        if col_type.upper() == "INTEGER" and is_pk:
            sa_type = "Integer, primary_key=True, index=True"
        elif col_type.upper() == "INTEGER":
            sa_type = "Integer"
        elif col_type.upper() == "TEXT":
            sa_type = "Text"
        elif col_type.upper() == "VARCHAR":
            sa_type = "String"
        elif col_type.upper() == "FLOAT":
            sa_type = "Float"
        elif col_type.upper() == "BOOLEAN":
            sa_type = "Boolean"
        elif col_type.upper() == "TIMESTAMP":
            sa_type = "DateTime"
        elif col_type.upper() == "JSON":
            sa_type = "JSON"
        else:
            sa_type = f"String  # Original type: {col_type}"
        
        # Handle foreign keys separately
        if col_name == "video_id":
            sa_type = 'String, ForeignKey("videos.id"), nullable=False, unique=True'
        
        # Add nullable constraint
        elif not_null:
            sa_type += ", nullable=False"
        else:
            sa_type += ", nullable=True"
        
        # Add default values
        if default_val and "CURRENT_TIMESTAMP" in default_val:
            if col_name == "created_at":
                sa_type += ", server_default=func.now()"
            elif col_name == "updated_at":
                sa_type += ", onupdate=func.now()"
        elif default_val:
            sa_type += f", default={default_val}"
        
        # Add column to model
        model_code += f"    {col_name} = Column({sa_type})\n"
    
    # Add relationships
    model_code += """    
    # Relationship to Video model
    video = relationship("Video", back_populates="summary")
    
    def to_dict(self):
        \"\"\"Convert model to dictionary.\"\"\"
        return {
"""
    
    # Add to_dict method properties
    for col in columns:
        col_name = col[1]
        if col_name in ("created_at", "updated_at", "last_analyzed"):
            model_code += f'            "{col_name}": self.{col_name}.isoformat() if self.{col_name} else None,\n'
        else:
            model_code += f'            "{col_name}": self.{col_name},\n'
    
    # Add backward compatibility for summary if needed
    if "summary" not in [col[1] for col in columns] and "short_summary" in [col[1] for col in columns]:
        model_code += '            "summary": self.short_summary,  # For backward compatibility\n'
    
    # Close the to_dict method
    model_code += "        }\n"
    
    # Write the model to a file
    with open("models/video_summary_generated.py", "w") as f:
        f.write(model_code)
    
    print("Generated models/video_summary_generated.py from the actual database schema.")
    print("Please review this file and rename it to models/video_summary.py if it looks correct.")
    
    conn.close()
    return True

if __name__ == "__main__":
    print("=== SQLite Database Schema Inspector ===\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        generate_models()
    else:
        inspect_database()
        print("\nRun with --generate flag to create model files based on the actual schema:")
        print("python inspect_database.py --generate")