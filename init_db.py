# init_db.py

from db import Base, engine

def main():
    """Create database tables."""
    print("Creating database tables...")
    # Import models to ensure they're registered with Base
    import models.video
    import models.video_summary
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    main()