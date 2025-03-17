from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
import json

from models.video import Video
from models.video_summary import VideoSummary

class VideoRepository:
    """Repository for video and summary data operations."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    def create_video(self, 
                     video_id: str, 
                     title: str, 
                     channel_name: str,
                     published_at: datetime,
                     thumbnail_url: str,
                     duration: int,
                     description: str = None,
                     transcript: str = None) -> Video:
        """
        Create a new video record.
        
        Args:
            video_id: YouTube video ID
            title: Video title
            channel_name: Channel name
            published_at: Publication date
            thumbnail_url: Thumbnail URL
            duration: Duration in seconds
            description: Video description (optional)
            transcript: Video transcript (optional)
            
        Returns:
            Created Video object
        """
        video = Video(
            id=video_id,
            title=title,
            description=description,
            channel_title=channel_name,
            published_at=published_at,
            thumbnail_url=thumbnail_url,  # Now correctly using the thumbnail_url field
            duration_seconds=duration,
            transcript=transcript
        )
        
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)
        
        return video
    
    # Add this method to VideoRepository class
    def get_videos(self, limit: int = 10, skip: int = 0) -> List[Video]:
        """
        Get a list of videos with pagination.
        
        Args:
            limit: Maximum number of videos to return
            skip: Number of videos to skip (for pagination)
            
        Returns:
            List of Video objects
        """
        return self.db.query(Video).offset(skip).limit(limit).all()


    def get_video_summary(self, video_id: str) -> Optional[VideoSummary]:
        """
        Get the summary for a specific video.
    
        Args:
            video_id: YouTube video ID
        
        Returns:
            VideoSummary object or None if not found
        """
        return self.db.query(VideoSummary).filter(VideoSummary.video_id == video_id).first()

    def save_video_summary(self, summary: VideoSummary) -> VideoSummary:
        """
        Save a video summary to the database.
        
        Args:
            summary: VideoSummary object
            
        Returns:
            Saved VideoSummary object
        """
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        return summary



    def update_transcript(self, video_id: str, transcript: str) -> Optional[Video]:
        """
        Update the transcript for a video.
        
        Args:
            video_id: YouTube video ID
            transcript: Video transcript
            
        Returns:
            Updated Video object or None if not found
        """
        video = self.get_video_by_id(video_id)
        if not video:
            return None
            
        video.transcript = transcript
        #video.created_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(video)
        
        return video
    
    def create_summary(self,
               video_id: str,
               short_summary: str,
               detailed_summary: str,
               key_points: List[Dict[str, Any]],
               topics: List[str],
               sentiment: str,
               entities: List[Dict[str, Any]] = None,
               key_moments: List[Dict[str, Any]] = None) -> Optional[VideoSummary]:
        """
        Create a new summary for a video.
        
        Args:
            video_id: YouTube video ID
            short_summary: Short summary text
            detailed_summary: Detailed summary text
            key_points: List of key points with timestamps
            topics: List of topics
            sentiment: Overall sentiment
            entities: List of entities mentioned (optional)
            key_moments: List of key moments with timestamps (optional)
            
        Returns:
            Created VideoSummary object or None if video not found
        """
        video = self.get_video_by_id(video_id)
        if not video:
            print(f"Video {video_id} not found when creating summary")
            return None
        
        # Handle different formats of key_points
        processed_key_points = key_points
        if isinstance(key_points, str):
            # If key_points is a string, convert to a list with a single item
            processed_key_points = [{"text": key_points, "timestamp": None}]
        elif isinstance(key_points, list):
            # If key_points is a list of strings, convert each to a dict
            if key_points and isinstance(key_points[0], str):
                processed_key_points = [{"text": kp, "timestamp": None} for kp in key_points]

        # Handle different formats of topics
        processed_topics = topics
        if isinstance(topics, dict):
            # If topics is a dict, extract the name field
            processed_topics = [topics.get("name", "Unknown Topic")]
        elif isinstance(topics, list) and topics and isinstance(topics[0], dict):
            # If topics is a list of dicts, extract the name field from each
            processed_topics = [topic.get("name", "Unknown Topic") for topic in topics]

        try:
            if hasattr(video, 'is_analyzed'):       
                # Mark the video as analyzed
                video.is_analyzed = True
                # Update last_updated timestamp
                video.last_updated = datetime.utcnow()
                self.db.commit()

            # Create summary with new fields
            summary = VideoSummary(
                video_id=video_id,
                short_summary=short_summary,
                detailed_summary=detailed_summary,
                key_points=processed_key_points,
                topics=processed_topics,
                sentiment=sentiment,
                entities=entities or [],
                key_moments=key_moments or [],
                has_transcription=True if video.transcript else False,
                transcription_source="api" if video.transcript else "generated",
                last_analyzed=datetime.utcnow()
            )
            
            print(f"Created summary for video {video_id}")
            
            # Save summary to database
            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)
            
            return summary

        except Exception as e:
            import traceback
            print(f"Error creating summary: {str(e)}")
            print(traceback.format_exc())
            self.db.rollback()
            return None
        
    def get_video_by_id(self, video_id: str) -> Optional[Video]:
        """
        Get a video by its ID.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video object or None if not found
        """
        return self.db.query(Video).filter(Video.id == video_id).first()
    
    def get_recent_videos(self, limit: int = 10) -> List[Video]:
        """
        Get recently analyzed videos.
        
        Args:
            limit: Maximum number of videos to return
            
        Returns:
            List of Video objects
        """
        videos = self.db.query(
            Video.id, 
            Video.title, 
            Video.description, 
            Video.thumbnail_url,
            Video.channel_title,
            Video.published_at
        ).join(VideoSummary)\
            .limit(limit)\
            .all()
        result = []
        for v in videos:
            video = Video(
                id=v.id,
                title=v.title,
                description=v.description,
                thumbnail_url=v.thumbnail_url,
                channel_title=v.channel_title,
                published_at=v.published_at
            )
            result.append(video)
        
        return result
    
    def search_videos(self, 
                      query: str, 
                      limit: int = 10, 
                      offset: int = 0) -> List[Video]:
        """
        Search for videos by query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of matching Video objects
        """
        search_term = f"%{query}%"
        
        return self.db.query(Video)\
            .filter(
                or_(
                    Video.title.ilike(search_term),
                    Video.description.ilike(search_term),
                    Video.channel_title.ilike(search_term)
                )
            )\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    def count_search_results(self, query: str) -> int:
        """
        Count search results for pagination.
        
        Args:
            query: Search query
            
        Returns:
            Total count of matching videos
        """
        search_term = f"%{query}%"
        
        return self.db.query(Video)\
            .filter(
                or_(
                    Video.title.ilike(search_term),
                    Video.description.ilike(search_term),
                    Video.channel_title.ilike(search_term)
                )
            )\
            .count()
            
    def get_related_videos(self, video_id: str, limit: int = 5) -> List[Video]:
        """
        Get videos related to the specified video.
        
        Args:
            video_id: YouTube video ID
            limit: Maximum number of related videos to return
            
        Returns:
            List of related Video objects
        """
        # First check if we have explicit relationships stored
        # This would require a new table like video_relationships
        # For now, we'll use a simple query based on similar topics/content
        
        # Get the current video first to extract its topics
        video = self.get_video_by_id(video_id)
        if not video or not video.summary:
            return []
        
        # Get topics from the video summary
        topics = []
        if hasattr(video.summary, 'topics') and video.summary.topics:
            if isinstance(video.summary.topics, list):
                topics = video.summary.topics
            elif isinstance(video.summary.topics, str):
                # Handle case where topics might be a JSON string
                try:
                    topics = json.loads(video.summary.topics)
                except:
                    topics = [video.summary.topics]
        
        if not topics:
            # Fallback to searching by channel if no topics
            return self.db.query(Video)\
                .filter(Video.channel_title == video.channel_title)\
                .filter(Video.id != video_id)\
                .limit(limit)\
                .all()
        
        # Search for videos that match any of the topics
        # This requires the topics to be stored in a searchable format
        # For now, we'll do a simple search on video titles and descriptions
        search_terms = []
        for topic in topics:
            if isinstance(topic, dict) and 'name' in topic:
                search_terms.append(topic['name'])
            elif isinstance(topic, str):
                search_terms.append(topic)
        
        if not search_terms:
            return []
        
        # Build a query with OR conditions for each term
        from sqlalchemy import or_
        conditions = []
        for term in search_terms:
            term_like = f"%{term}%"
            conditions.append(Video.title.ilike(term_like))
            conditions.append(Video.description.ilike(term_like))
        
        return self.db.query(Video)\
            .filter(or_(*conditions))\
            .filter(Video.id != video_id)\
            .limit(limit)\
            .all()

    def save_video_relationships(self, video_id: str, related_video_ids: List[str], 
                                similarity_scores: Dict[str, float]) -> bool:
        """
        Save relationship data between videos.
        
        Args:
            video_id: Source video ID
            related_video_ids: List of related video IDs
            similarity_scores: Dictionary mapping video IDs to similarity scores
            
        Returns:
            True if successful, False otherwise
        """
        # For proper implementation, you would need a video_relationships table
        # This is a placeholder that shows how it would work
        # You would need to create the table first
        
        # Example SQL that would be needed:
        # CREATE TABLE video_relationships (
        #     source_video_id VARCHAR NOT NULL,
        #     target_video_id VARCHAR NOT NULL,
        #     similarity_score FLOAT,
        #     relationship_type VARCHAR,
        #     PRIMARY KEY (source_video_id, target_video_id),
        #     FOREIGN KEY (source_video_id) REFERENCES videos(id),
        #     FOREIGN KEY (target_video_id) REFERENCES videos(id)
        # )
        
        try:
            # Check if VideoRelationship model exists
            # If you create this model, uncomment and use this code
            """
            # Delete existing relationships for this video
            self.db.query(VideoRelationship)\
                .filter(VideoRelationship.source_video_id == video_id)\
                .delete()
            
            # Create new relationship records
            for related_id in related_video_ids:
                if related_id == video_id:
                    continue  # Skip self-relationship
                    
                score = similarity_scores.get(related_id, 0.0)
                relationship = VideoRelationship(
                    source_video_id=video_id,
                    target_video_id=related_id,
                    similarity_score=score,
                    relationship_type="content_similarity"
                )
                self.db.add(relationship)
            
            self.db.commit()
            """
            
            # For now, just log that we would save relationships
            print(f"Would save {len(related_video_ids)} relationships for video {video_id}")
            for related_id in related_video_ids:
                score = similarity_scores.get(related_id, 0.0)
                print(f"  - Related to {related_id} with score {score:.2f}")
            
            return True
            
        except Exception as e:
            import traceback
            print(f"Error saving video relationships: {str(e)}")
            print(traceback.format_exc())
            self.db.rollback()
            return False

    def get_video_network(self, video_id: str, depth: int = 1, max_videos: int = 20) -> Dict[str, Any]:
        """
        Get a network of videos related to the specified video.
        
        Args:
            video_id: Starting video ID
            depth: How many degrees of separation to include
            max_videos: Maximum number of videos to include
            
        Returns:
            Dictionary with nodes and edges for the network
        """
        # For proper implementation, you would query the video_relationships table
        # This is a placeholder using the get_related_videos method
        
        visited = set()
        nodes = []
        edges = []
        queue = [(video_id, 0)]  # (video_id, depth)
        
        while queue and len(nodes) < max_videos:
            current_id, current_depth = queue.pop(0)
            
            if current_id in visited:
                continue
                
            visited.add(current_id)
            
            # Get video details
            video = self.get_video_by_id(current_id)
            if not video:
                continue
                
            # Add node
            nodes.append({
                "id": video.id,
                "title": video.title,
                "channel": video.channel_title,
                "group": current_depth + 1  # For visualization grouping
            })
            
            # If we've reached max depth, don't get related videos
            if current_depth >= depth:
                continue
                
            # Get related videos
            related = self.get_related_videos(current_id, limit=5)
            
            for rel_video in related:
                # Add edge
                edges.append({
                    "source": video.id,
                    "target": rel_video.id,
                    "value": 1  # Weight (would be similarity score in full implementation)
                })
                
                # Add to queue for next iteration
                if rel_video.id not in visited:
                    queue.append((rel_video.id, current_depth + 1))
                    
        return {
            "nodes": nodes,
            "edges": edges
        }