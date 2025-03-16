# improved_fix_analysis.py
from db import SessionLocal
from repositories.video_repository import VideoRepository

def fix_analysis(video_id):
    db = SessionLocal()
    try:
        repo = VideoRepository(db)
        summary = repo.get_video_summary(video_id)
        
        if not summary:
            print(f"No summary found for video {video_id}")
            return
        
        if summary.short_summary == "Error parsing Claude's response":
            print("Found error summary, attempting to fix...")
            
            # Directly use pre-parsed values instead of trying to parse JSON
            short_summary = "The video discusses Brené Brown's research on vulnerability, shame, and worthiness. She shares her journey as a researcher who initially wanted to study connection and overcome the \"messiness\" of human experiences, but ultimately realized that vulnerability and shame are fundamental to understanding how people develop a sense of worthiness and belonging."
            
            key_points = [
                "Vulnerability and shame are essential to understanding connection and worthiness.",
                "The key to developing a strong sense of love and belonging is believing that one is worthy of it.",
                "Wholehearted people live from a deep sense of worthiness and authenticity.",
                "Brené Brown's research process involved collecting thousands of stories and data over six years.",
                "Overcoming the fear of vulnerability and embracing imperfection is necessary for living a fulfilling and meaningful life."
            ]
            
            topics = [
                "Vulnerability",
                "Shame",
                "Worthiness",
                "Wholehearted living",
                "Research process"
            ]
            
            sentiment = "positive"
            
            try:
                # Update summary fields
                summary.short_summary = short_summary
                summary.detailed_summary = short_summary
                
                # Convert key points list to required format
                formatted_key_points = [{"text": kp, "timestamp": None} for kp in key_points]
                summary.key_points = formatted_key_points
                
                # Update topics
                summary.topics = topics
                
                # Update sentiment
                summary.sentiment = sentiment
                
                # Save to database
                db.commit()
                print("Summary updated successfully!")
                
            except Exception as e:
                print(f"Error updating summary: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print("Summary doesn't need fixing or has already been fixed.")
    
    finally:
        db.close()

if __name__ == "__main__":
    fix_analysis("X4Qm9cGRub0")