import logging
from typing import List, Dict, Any, Optional, Set, Tuple
import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter, defaultdict
import re
import json

logger = logging.getLogger(__name__)

class ContentNetworkAnalyzer:
    """Service for analyzing networks of related YouTube videos to identify patterns and insights."""
    
    def __init__(self, similarity_threshold=0.3):
        """
        Initialize the content network analyzer.
        
        Args:
            similarity_threshold: Threshold for considering videos as related (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            min_df=2,
            max_df=0.9,
            ngram_range=(1, 2)
        )
        
    def build_content_network(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a network of related video content based on transcript similarity.
        
        Args:
            videos: List of video dictionaries with transcripts and metadata
            
        Returns:
            Dictionary with network analysis results
        """
        if not videos or len(videos) < 2:
            logger.warning("Cannot build network with fewer than 2 videos")
            return {"error": "Insufficient videos for network analysis"}
        
        # Extract transcript texts and create document-term matrix
        transcripts = [self._preprocess_text(v.get('transcript', '')) for v in videos]
        titles = [v.get('title', 'Unknown') for v in videos]
        video_ids = [v.get('id', '') for v in videos]
        
        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(transcripts)
        
        # Create graph representation
        G = self._create_graph(similarity_matrix, video_ids, titles)
        
        # Calculate network metrics
        metrics = self._calculate_network_metrics(G)
        
        # Identify key topics and themes
        topics = self._extract_network_topics(transcripts, video_ids, titles)
        
        # Find central videos
        central_videos = self._identify_central_videos(G, videos)
        
        # Identify content clusters
        clusters = self._identify_content_clusters(G, videos)
        
        # Generate insights
        insights = self._generate_network_insights(G, videos, topics, central_videos, clusters)
        
        # Prepare visualization data
        visualization_data = self._prepare_visualization_data(G, videos)
        
        return {
            "network_metrics": metrics,
            "topics": topics,
            "central_videos": central_videos,
            "clusters": clusters,
            "insights": insights,
            "visualization_data": visualization_data
        }
    
    def analyze_topic_evolution(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze how topics evolve across a set of videos over time.
        
        Args:
            videos: List of video dictionaries with transcripts and publication dates
            
        Returns:
            Dictionary with topic evolution analysis
        """
        if not videos:
            return {"error": "No videos provided for analysis"}
        
        # Sort videos by publication date
        sorted_videos = sorted(videos, key=lambda v: v.get('published_at', ''))
        
        # Extract topics for each video
        video_topics = []
        for video in sorted_videos:
            # Get topics either from existing analysis or extract new ones
            if video.get('summary') and video['summary'].get('topics'):
                topics = video['summary']['topics']
            else:
                text = video.get('transcript', '') or video.get('description', '') or ''
                topics = self._extract_topics_from_text(text)
            
            video_topics.append({
                'id': video.get('id', ''),
                'title': video.get('title', 'Unknown'),
                'published_at': video.get('published_at', ''),
                'topics': topics
            })
        
        # Track topic presence and strength over time
        topic_evolution = self._track_topic_evolution(video_topics)
        
        # Identify emerging, trending, and declining topics
        topic_trends = self._identify_topic_trends(topic_evolution)
        
        # Generate insights about topic evolution
        insights = self._generate_topic_evolution_insights(topic_evolution, topic_trends)
        
        return {
            "topic_evolution": topic_evolution,
            "topic_trends": topic_trends,
            "insights": insights
        }
    
    def generate_comprehensive_summary(self, videos: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive summary across multiple related videos.
        
        Args:
            videos: List of video dictionaries with transcripts and summaries
            
        Returns:
            Comprehensive summary text
        """
        if not videos:
            return "No videos provided for analysis."
        
        # Extract existing summaries
        summaries = []
        for video in videos:
            if video.get('summary') and video['summary'].get('short_summary'):
                summaries.append(video['summary']['short_summary'])
        
        if not summaries:
            return "No summaries available for analysis."
        
        # Combine summaries and extract key points
        combined_summary = " ".join(summaries)
        
        # Extract key sentences using TextRank-like algorithm
        key_sentences = self._extract_key_sentences(combined_summary)
        
        # Build the comprehensive summary
        comprehensive_summary = "# Comprehensive Analysis of Related Content\n\n"
        comprehensive_summary += "## Overview\n\n"
        comprehensive_summary += self._generate_overview_paragraph(videos, key_sentences) + "\n\n"
        
        # Add key themes
        comprehensive_summary += "## Key Themes\n\n"
        themes = self._extract_themes_across_videos(videos)
        for theme in themes[:5]:  # Top 5 themes
            comprehensive_summary += f"- **{theme['name']}**: {theme['description']}\n"
        
        comprehensive_summary += "\n## Main Points\n\n"
        for sentence in key_sentences[:7]:  # Top 7 sentences
            comprehensive_summary += f"- {sentence}\n"
        
        # Add comparative insights
        comprehensive_summary += "\n## Comparative Insights\n\n"
        comprehensive_summary += self._generate_comparative_insights(videos)
        
        return comprehensive_summary
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove special characters and numbers
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _calculate_similarity_matrix(self, texts: List[str]) -> np.ndarray:
        """Calculate similarity matrix between texts using TF-IDF and cosine similarity."""
        if not texts or all(not text for text in texts):
            # Return empty matrix if no valid texts
            return np.zeros((len(texts), len(texts)))
        
        # Filter out empty texts
        valid_indices = [i for i, text in enumerate(texts) if text]
        valid_texts = [texts[i] for i in valid_indices]
        
        if not valid_texts:
            return np.zeros((len(texts), len(texts)))
            
        try:
            # Create TF-IDF matrix
            tfidf_matrix = self.vectorizer.fit_transform(valid_texts)
            
            # Calculate cosine similarity
            valid_similarity = cosine_similarity(tfidf_matrix)
            
            # Create full similarity matrix with zeros for invalid texts
            full_similarity = np.zeros((len(texts), len(texts)))
            for i, vi in enumerate(valid_indices):
                for j, vj in enumerate(valid_indices):
                    full_similarity[vi, vj] = valid_similarity[i, j]
            
            return full_similarity
            
        except Exception as e:
            logger.error(f"Error calculating similarity matrix: {str(e)}")
            return np.zeros((len(texts), len(texts)))
    
    def _create_graph(self, similarity_matrix: np.ndarray, video_ids: List[str], titles: List[str]) -> nx.Graph:
        """Create a graph representation of the video network."""
        G = nx.Graph()
        
        # Add nodes
        for i, video_id in enumerate(video_ids):
            G.add_node(video_id, title=titles[i])
        
        # Add edges based on similarity threshold
        for i in range(len(video_ids)):
            for j in range(i+1, len(video_ids)):
                similarity = similarity_matrix[i, j]
                if similarity >= self.similarity_threshold:
                    G.add_edge(video_ids[i], video_ids[j], weight=similarity)
        
        return G
    
    def _calculate_network_metrics(self, G: nx.Graph) -> Dict[str, Any]:
        """Calculate key metrics for the content network."""
        metrics = {}
        
        # Basic metrics
        metrics["node_count"] = G.number_of_nodes()
        metrics["edge_count"] = G.number_of_edges()
        metrics["density"] = nx.density(G)
        
        # Connectivity metrics
        try:
            metrics["average_clustering"] = nx.average_clustering(G)
        except:
            metrics["average_clustering"] = 0
            
        # Connected components
        components = list(nx.connected_components(G))
        metrics["component_count"] = len(components)
        
        # Centrality metrics
        if G.number_of_nodes() > 0:
            try:
                degree_centrality = nx.degree_centrality(G)
                metrics["max_degree_centrality"] = max(degree_centrality.values()) if degree_centrality else 0
                metrics["avg_degree_centrality"] = sum(degree_centrality.values()) / len(degree_centrality) if degree_centrality else 0
                
                betweenness_centrality = nx.betweenness_centrality(G)
                metrics["max_betweenness_centrality"] = max(betweenness_centrality.values()) if betweenness_centrality else 0
            except Exception as e:
                logger.error(f"Error calculating centrality metrics: {str(e)}")
        
        return metrics
    
    def _extract_network_topics(self, transcripts: List[str], video_ids: List[str], titles: List[str]) -> List[Dict[str, Any]]:
        """Extract common topics across the network."""
        # Combine all transcripts
        combined_text = " ".join([t for t in transcripts if t])
        
        if not combined_text:
            return []
        
        # Extract topics using TF-IDF to find important terms
        try:
            # Use a different vectorizer for topic extraction
            topic_vectorizer = TfidfVectorizer(
                stop_words='english',
                min_df=1,
                max_df=0.9,
                ngram_range=(1, 2)
            )
            
            # Create document-term matrix
            dtm = topic_vectorizer.fit_transform([combined_text])
            
            # Get feature names (terms)
            feature_names = topic_vectorizer.get_feature_names_out()
            
            # Get TF-IDF scores
            tfidf_scores = dtm.toarray()[0]
            
            # Create term-score pairs and sort
            term_scores = [(feature_names[i], tfidf_scores[i]) for i in range(len(feature_names))]
            term_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Extract top terms as topics
            topics = []
            for term, score in term_scores[:10]:  # Top 10 terms
                # Skip single-letter terms
                if len(term) <= 1:
                    continue
                    
                topics.append({
                    "name": term,
                    "score": float(score),
                    "count": sum(1 for t in transcripts if term in t),
                    "videos": [video_ids[i] for i, t in enumerate(transcripts) if term in t]
                })
                
                if len(topics) >= 5:  # Limit to 5 topics
                    break
            
            return topics
            
        except Exception as e:
            logger.error(f"Error extracting network topics: {str(e)}")
            return []
    
    def _identify_central_videos(self, G: nx.Graph, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify central videos in the network based on centrality metrics."""
        if G.number_of_nodes() == 0:
            return []
            
        try:
            # Calculate degree and betweenness centrality
            degree_centrality = nx.degree_centrality(G)
            betweenness_centrality = nx.betweenness_centrality(G)
            
            # Combine metrics and sort nodes
            node_centrality = {}
            for node in G.nodes():
                node_centrality[node] = {
                    "id": node,
                    "degree_centrality": degree_centrality.get(node, 0),
                    "betweenness_centrality": betweenness_centrality.get(node, 0),
                    "combined_score": degree_centrality.get(node, 0) + betweenness_centrality.get(node, 0)
                }
            
            # Sort by combined score
            sorted_nodes = sorted(node_centrality.values(), key=lambda x: x["combined_score"], reverse=True)
            
            # Get top nodes
            top_nodes = sorted_nodes[:min(3, len(sorted_nodes))]
            
            # Find corresponding videos
            central_videos = []
            for node in top_nodes:
                video_id = node["id"]
                video = next((v for v in videos if v.get('id') == video_id), None)
                if video:
                    central_videos.append({
                        "id": video_id,
                        "title": video.get('title', 'Unknown'),
                        "channel_title": video.get('channel_title', 'Unknown'),
                        "degree_centrality": node["degree_centrality"],
                        "betweenness_centrality": node["betweenness_centrality"],
                        "combined_score": node["combined_score"]
                    })
            
            return central_videos
            
        except Exception as e:
            logger.error(f"Error identifying central videos: {str(e)}")
            return []
    
    def _identify_content_clusters(self, G: nx.Graph, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify clusters of related content in the network."""
        if G.number_of_nodes() == 0:
            return []
            
        try:
            # Detect communities using the Louvain method
            try:
                from community import best_partition
                partition = best_partition(G)
            except ImportError:
                # Fallback to connected components if community detection is not available
                components = list(nx.connected_components(G))
                partition = {}
                for i, component in enumerate(components):
                    for node in component:
                        partition[node] = i
            
            # Group videos by cluster
            clusters = defaultdict(list)
            for video_id, cluster_id in partition.items():
                video = next((v for v in videos if v.get('id') == video_id), None)
                if video:
                    clusters[cluster_id].append({
                        "id": video_id,
                        "title": video.get('title', 'Unknown'),
                        "channel_title": video.get('channel_title', 'Unknown')
                    })
            
            # Format clusters for response
            result = []
            for cluster_id, cluster_videos in clusters.items():
                if len(cluster_videos) > 0:
                    result.append({
                        "id": cluster_id,
                        "videos": cluster_videos,
                        "size": len(cluster_videos)
                    })
            
            # Sort clusters by size
            result.sort(key=lambda c: c["size"], reverse=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Error identifying content clusters: {str(e)}")
            return []
    
    def _generate_network_insights(self, G: nx.Graph, videos: List[Dict[str, Any]], 
                                  topics: List[Dict[str, Any]], central_videos: List[Dict[str, Any]], 
                                  clusters: List[Dict[str, Any]]) -> List[str]:
        """Generate insights based on network analysis."""
        insights = []
        
        # Insight on network size and connectivity
        if G.number_of_nodes() > 0:
            insights.append(f"The content network consists of {G.number_of_nodes()} videos with {G.number_of_edges()} connections between them.")
            
            if len(clusters) > 1:
                insights.append(f"The content is organized into {len(clusters)} distinct topic clusters.")
            elif len(clusters) == 1:
                insights.append("All videos form a single coherent content cluster.")
            
            density = nx.density(G)
            if density > 0.7:
                insights.append("The content network is very densely connected, indicating strongly related content.")
            elif density > 0.3:
                insights.append("The content network shows moderate connectivity between videos.")
            else:
                insights.append("The content network is sparsely connected, suggesting diverse or loosely related content.")
        
        # Insight on central videos
        if central_videos:
            most_central = central_videos[0]
            insights.append(f"The video '{most_central['title']}' is central to the content network, connecting multiple topics.")
            
            if len(central_videos) > 1:
                insights.append(f"Other influential videos include '{central_videos[1]['title']}'" + 
                               (f" and '{central_videos[2]['title']}'" if len(central_videos) > 2 else "") + ".")
        
        # Insight on common topics
        if topics:
            top_topics = ", ".join([f"'{t['name']}'" for t in topics[:3]])
            insights.append(f"The most common topics across the content network are {top_topics}.")
            
            if len(topics) > 3:
                insights.append(f"Additional topics include {', '.join([f''{t['name']}'' for t in topics[3:]])}.")
        
        return insights
    
    def _prepare_visualization_data(self, G: nx.Graph, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data for network visualization."""
        nodes = []
        for video_id in G.nodes():
            video = next((v for v in videos if v.get('id') == video_id), None)
            if video:
                # Get node properties from graph if available
                node_attrs = G.nodes[video_id]
                
                node = {
                    "id": video_id,
                    "title": video.get('title', node_attrs.get('title', 'Unknown')),
                    "group": 1  # Default group
                }
                
                # Add channel info if available
                if 'channel_title' in video:
                    node["channel"] = video['channel_title']
                
                nodes.append(node)
        
        edges = []
        for source, target, data in G.edges(data=True):
            edge = {
                "source": source,
                "target": target,
                "value": data.get('weight', 1)
            }
            edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def _extract_key_sentences(self, text: str, num_sentences: int = 10) -> List[str]:
        """Extract key sentences from text using a simplified TextRank-like approach."""
        if not text:
            return []
            
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= num_sentences:
            return sentences
            
        # Create TF-IDF features for each sentence
        vectorizer = TfidfVectorizer(stop_words='english')
        try:
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            # Calculate similarity between sentences
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # Calculate sentence scores
            scores = np.sum(similarity_matrix, axis=1)
            
            # Get top sentences
            top_indices = scores.argsort()[-num_sentences:][::-1]
            
            # Return sentences in original order
            ordered_indices = sorted(top_indices)
            key_sentences = [sentences[i] for i in ordered_indices]
            
            return key_sentences
            
        except Exception as e:
            logger.error(f"Error extracting key sentences: {str(e)}")
            return sentences[:num_sentences]
    
    def _extract_topics_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract topics from text using TF-IDF."""
        if not text:
            return []
            
        try:
            # Use TF-IDF to extract important terms
            vectorizer = TfidfVectorizer(
                stop_words='english',
                min_df=1,
                max_df=0.9,
                ngram_range=(1, 2)
            )
            
            # Create document-term matrix
            dtm = vectorizer.fit_transform([text])
            
            # Get feature names (terms)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get TF-IDF scores
            tfidf_scores = dtm.toarray()[0]
            
            # Create term-score pairs and sort
            term_scores = [(feature_names[i], tfidf_scores[i]) for i in range(len(feature_names))]
            term_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Extract top terms as topics
            topics = []
            for term, score in term_scores[:10]:
                # Skip single-letter terms
                if len(term) <= 1:
                    continue
                    
                topics.append({
                    "name": term,
                    "confidence": int(score * 100)
                })
                
                if len(topics) >= 5:  # Limit to 5 topics
                    break
            
            return topics
            
        except Exception as e:
            logger.error(f"Error extracting topics from text: {str(e)}")
            return []
    
    def _track_topic_evolution(self, video_topics: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Track how topics evolve over time across videos."""
        if not video_topics:
            return {}
            
        # Extract all unique topics
        all_topics = set()
        for video in video_topics:
            topics = video.get('topics', [])
            for topic in topics:
                if isinstance(topic, dict) and 'name' in topic:
                    all_topics.add(topic['name'])
                elif isinstance(topic, str):
                    all_topics.add(topic)
        
        # Track each topic's presence over time
        topic_evolution = {}
        for topic in all_topics:
            topic_evolution[topic] = []
            
            for video in video_topics:
                video_id = video.get('id', '')
                title = video.get('title', 'Unknown')
                published_at = video.get('published_at', '')
                
                # Check if this topic is in the video
                video_topics_list = video.get('topics', [])
                topic_presence = False
                topic_confidence = 0
                
                for vtopic in video_topics_list:
                    if isinstance(vtopic, dict) and vtopic.get('name') == topic:
                        topic_presence = True
                        topic_confidence = vtopic.get('confidence', 50)
                        break
                    elif vtopic == topic:
                        topic_presence = True
                        topic_confidence = 50  # Default confidence
                        break
                
                if topic_presence:
                    topic_evolution[topic].append({
                        "video_id": video_id,
                        "title": title,
                        "published_at": published_at,
                        "confidence": topic_confidence
                    })
        
        return topic_evolution
    
    def _identify_topic_trends(self, topic_evolution: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[str]]:
        """Identify emerging, trending, and declining topics."""
        if not topic_evolution:
            return {}
            
        # Calculate metrics for each topic
        topic_metrics = {}
        for topic, appearances in topic_evolution.items():
            # Skip topics with too few appearances
            if len(appearances) < 2:
                continue
                
            # Sort by published date
            sorted_appearances = sorted(appearances, key=lambda a: a.get('published_at', ''))
            
            # Calculate trend based on confidence changes
            confidences = [a.get('confidence', 50) for a in sorted_appearances]
            if len(confidences) >= 3:
                # Calculate slope of confidence trend
                x = list(range(len(confidences)))
                y = confidences
                
                # Simple linear regression
                n = len(x)
                slope = (n * sum(x[i] * y[i] for i in range(n)) - sum(x) * sum(y)) / (n * sum(x[i]**2 for i in range(n)) - sum(x)**2)
                
                topic_metrics[topic] = {
                    "appearances": len(appearances),
                    "first_appearance": sorted_appearances[0].get('published_at', ''),
                    "last_appearance": sorted_appearances[-1].get('published_at', ''),
                    "trend_slope": slope,
                    "average_confidence": sum(confidences) / len(confidences)
                }
            else:
                # Not enough data for trend calculation
                topic_metrics[topic] = {
                    "appearances": len(appearances),
                    "first_appearance": sorted_appearances[0].get('published_at', ''),
                    "last_appearance": sorted_appearances[-1].get('published_at', ''),
                    "trend_slope": 0,
                    "average_confidence": sum(confidences) / len(confidences)
                }
        
        # Categorize topics by trend
        trending = []
        declining = []
        stable = []
        
        for topic, metrics in topic_metrics.items():
            if metrics["trend_slope"] > 0.5:
                trending.append(topic)
            elif metrics["trend_slope"] < -0.5:
                declining.append(topic)
            else:
                stable.append(topic)
        
        return {
            "trending": trending,
            "declining": declining,
            "stable": stable
        }
    
    def _generate_topic_evolution_insights(self, topic_evolution: Dict[str, List[Dict[str, Any]]], 
                                         topic_trends: Dict[str, List[str]]) -> List[str]:
        """Generate insights about topic evolution."""
        insights = []
        
        # Insight on topic variety
        if topic_evolution:
            insights.append(f"The content covers {len(topic_evolution)} distinct topics over time.")
            
            # Most common topics
            topic_counts = {topic: len(appearances) for topic, appearances in topic_evolution.items()}
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            
            if sorted_topics:
                top_topics = ", ".join([f"'{topic}'" for topic, _ in sorted_topics[:3]])
                insights.append(f"The most frequently discussed topics are {top_topics}.")
        
        # Insight on trending topics
        if topic_trends.get("trending"):
            trending_topics = ", ".join([f"'{t}'" for t in topic_trends["trending"][:3]])
            insights.append(f"Topics gaining traction include {trending_topics}.")
        
        # Insight on declining topics
        if topic_trends.get("declining"):
            declining_topics = ", ".join([f"'{t}'" for t in topic_trends["declining"][:3]])
            insights.append(f"Topics receiving less focus recently include {declining_topics}.")
        
        return insights
    
    def _generate_overview_paragraph(self, videos: List[Dict[str, Any]], key_sentences: List[str]) -> str:
        """Generate an overview paragraph based on key sentences and video metadata."""
        if not videos:
            return "No videos available for analysis."
            
        if not key_sentences:
            return "Insufficient content for generating an overview."
            
        # Get some metadata about the videos
        video_count = len(videos)
        channels = set(v.get('channel_title', 'Unknown') for v in videos)
        channel_count = len(channels)
        
        # Create intro sentence
        overview = f"This analysis covers {video_count} videos from {channel_count} different channels. "
        
        # Add content overview from key sentences
        if len(key_sentences) >= 2:
            # Use first sentence and another informative sentence
            overview += key_sentences[0] + " "
            
            # Find another informative sentence (not too similar to the first)
            for sentence in key_sentences[1:]:
                # Simple check - if the sentence is different enough from the first one
                if len(set(sentence.split()) - set(key_sentences[0].split())) > 5:
                    overview += sentence
                    break
        elif key_sentences:
            overview += key_sentences[0]
        
        return overview
    
    def _extract_themes_across_videos(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract common themes across multiple videos."""
        # Collect all topics from video summaries
        all_topics = []
        for video in videos:
            if video.get('summary') and video['summary'].get('topics'):
                topics = video['summary']['topics']
                
                for topic in topics:
                    if isinstance(topic, dict) and 'name' in topic:
                        all_topics.append(topic['name'])
                    elif isinstance(topic, str):
                        all_topics.append(topic)
        
        # Count topic frequencies
        topic_counts = Counter(all_topics)
        
        # Sort by frequency and extract top themes
        themes = []
        for topic, count in topic_counts.most_common(10):
            themes.append({
                "name": topic,
                "count": count,
                "description": f"Appears in {count} out of {len(videos)} videos.",
                "prevalence": (count / len(videos)) * 100
            })
        
        return themes
    
    def _generate_comparative_insights(self, videos: List[Dict[str, Any]]) -> str:
        """Generate comparative insights across videos."""
        if len(videos) < 2:
            return "Insufficient videos for comparative analysis."
            
        # Extract key aspects for comparison
        insights = ""
        
        # Compare video lengths if duration is available
        durations = [v.get('duration_seconds', 0) for v in videos if v.get('duration_seconds', 0) > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            insights += f"Video lengths range from {self._format_duration(min_duration)} to {self._format_duration(max_duration)}, "
            insights += f"with an average length of {self._format_duration(avg_duration)}.\n\n"
        
        # Compare sentiment if available
        sentiments = []
        for video in videos:
            if video.get('summary') and video['summary'].get('sentiment'):
                sentiments.append(video['summary']['sentiment'])
        
        if sentiments:
            sentiment_counts = Counter(sentiments)
            most_common = sentiment_counts.most_common(1)[0][0]
            
            insights += f"The most common sentiment across videos is '{most_common}'. "
            
            if len(sentiment_counts) > 1:
                insights += "The videos show a mix of emotional tones, reflecting diverse perspectives on the topics.\n\n"
            else:
                insights += "The videos maintain a consistent emotional tone throughout the collection.\n\n"
        
        # Compare topics if available
        all_topics = []
        for video in videos:
            if video.get('summary') and video['summary'].get('topics'):
                topics = video['summary']['topics']
                for topic in topics:
                    if isinstance(topic, dict) and 'name' in topic:
                        all_topics.append(topic['name'])
                    elif isinstance(topic, str):
                        all_topics.append(topic)
        
        if all_topics:
            topic_counts = Counter(all_topics)
            common_topics = [topic for topic, count in topic_counts.items() if count > 1]
            
            if common_topics:
                insights += f"Common topics that appear across multiple videos include {', '.join(common_topics[:5])}."
                if len(common_topics) > 5:
                    insights += f" and {len(common_topics) - 5} others"
                insights += ".\n\n"
            else:
                insights += "Each video covers distinct topics with minimal overlap, suggesting a broad coverage of the subject area.\n\n"
        
        if not insights:
            return "Insufficient data for comparative analysis."
            
        return insights
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to a readable string."""
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"