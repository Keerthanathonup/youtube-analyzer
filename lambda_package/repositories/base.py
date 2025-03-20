from sqlalchemy.orm import Session


class BaseRepository:
    """Base repository for database operations."""
    
    def __init__(self, session: Session):
        """
        Initialize with database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    def add(self, obj):
        """
        Add an object to the database.
        
        Args:
            obj: SQLAlchemy model object
            
        Returns:
            Added object
        """
        self.session.add(obj)
        self.session.commit()
        return obj
    
    def update(self, obj):
        """
        Update an object in the database.
        
        Args:
            obj: SQLAlchemy model object to update
            
        Returns:
            Updated object
        """
        self.session.commit()
        return obj
    
    def delete(self, obj):
        """
        Delete an object from the database.
        
        Args:
            obj: SQLAlchemy model object to delete
        """
        self.session.delete(obj)
        self.session.commit()
    
    def rollback(self):
        """Rollback the current transaction."""
        self.session.rollback()