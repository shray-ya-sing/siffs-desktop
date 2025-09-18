# Siffs - Fast File Search Desktop Application
# Copyright (C) 2025  Siffs
# 
# Contact: github.suggest277@passinbox.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.models import OptimizersConfig, UpdateResult, PointIdsList
from qdrant_client.http.exceptions import UnexpectedResponse

logger = logging.getLogger(__name__)

class QdrantVectorDB:
    """Qdrant local vector database service for storing and searching slide embeddings"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize Qdrant client with local storage
        
        Args:
            db_path: Path to store the local Qdrant database (if None, uses default app data location)
        """
        # Set up local database path
        if db_path is None:
            # Use platform-appropriate app data directory
            if os.name == 'nt':  # Windows
                app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
                db_path = os.path.join(app_data, 'SIFFS', 'vector_db')
            else:  # Mac/Linux
                app_data = os.path.expanduser('~/.local/share')
                db_path = os.path.join(app_data, 'SIFFS', 'vector_db')
        
        # Create directory if it doesn't exist
        os.makedirs(db_path, exist_ok=True)
        
        self.db_path = db_path
        self.collection_name = "siffs_slides"  # Collection name for slide embeddings
        self.vector_size = 1024  # VoyageAI embedding dimension
        
        try:
            # Initialize Qdrant client with local storage
            self.client = QdrantClient(path=db_path)
            logger.info(f"✅ Qdrant client initialized with local storage: {db_path}")
            
            # Initialize collection
            self._initialize_collection()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant client: {e}")
            raise
    
    def _initialize_collection(self):
        """Initialize or connect to Qdrant collection"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create new collection
                logger.info(f"🔧 Creating new Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE  # Same as Pinecone
                    ),
                    optimizers_config=OptimizersConfig(
                        deleted_threshold=0.2,
                        vacuum_min_vector_number=1000,
                        default_segment_number=2,
                        max_segment_size=None,
                        memmap_threshold=10000,
                        indexing_threshold=20000,
                        flush_interval_sec=5,
                        max_optimization_threads=2
                    )
                )
                logger.info(f"✅ Collection '{self.collection_name}' created successfully")
            else:
                logger.info(f"✅ Using existing collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing Qdrant collection: {e}")
            raise
    
    def upsert_slide_embeddings(self, embeddings_data: List[Dict]) -> bool:
        """
        Store slide embeddings in Qdrant
        
        Args:
            embeddings_data: List of embedding dictionaries with metadata
            
        Returns:
            True if successful, False otherwise
        """
        if not embeddings_data:
            logger.warning("⚠️ No embeddings data provided for upsert")
            return False
        
        try:
            points = []
            for embedding_data in embeddings_data:
                embedding = embedding_data.get('embedding', [])
                metadata = embedding_data.get('metadata', {})
                
                if not embedding or len(embedding) != self.vector_size:
                    logger.warning(f"⚠️ Skipping invalid embedding (expected {self.vector_size} dimensions, got {len(embedding) if embedding else 0})")
                    continue
                
                # Generate UUID for the slide (required by Qdrant)
                original_slide_id = metadata.get('slide_id', f"slide_{len(points)}")
                
                # Convert slide_id to UUID if it's not already
                try:
                    # Try to parse as UUID first
                    slide_uuid = uuid.UUID(original_slide_id)
                    point_id = str(slide_uuid)
                except ValueError:
                    # If not a UUID, generate a new one but keep original in metadata
                    slide_uuid = uuid.uuid4()
                    point_id = str(slide_uuid)
                
                # Prepare payload (metadata) - Qdrant stores all metadata as payload
                payload = {
                    'file_path': metadata.get('file_path', ''),
                    'file_name': metadata.get('file_name', ''),
                    'slide_number': int(metadata.get('slide_number', 0)),
                    'image_path': metadata.get('image_path', ''),
                    'slide_id': original_slide_id,  # Keep original slide ID in metadata
                    'uuid_id': point_id  # Store UUID separately
                }
                
                # Create point for Qdrant
                point = PointStruct(
                    id=point_id,  # Use UUID for point ID
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
            
            if not points:
                logger.warning("⚠️ No valid points to upsert")
                return False
            
            # Upsert points in batches for better performance
            batch_size = 100
            total_upserted = 0
            
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                
                operation_result = self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                
                if isinstance(operation_result, UpdateResult) and operation_result.status == 'completed':
                    total_upserted += len(batch)
                    logger.info(f"📤 Upserted batch {i//batch_size + 1}: {len(batch)} points")
                else:
                    logger.error(f"❌ Failed to upsert batch {i//batch_size + 1}")
                    return False
            
            logger.info(f"✅ Successfully upserted {total_upserted} slide embeddings to Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error upserting embeddings to Qdrant: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            return False
    
    def search_similar_slides(self, query_embedding: List[float], top_k: int = 25, 
                            file_filter: str = None) -> List[Dict]:
        """
        Search for similar slides using vector similarity
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            file_filter: Optional filter by file name
            
        Returns:
            List of similar slides with metadata and scores
        """
        if not query_embedding or len(query_embedding) != self.vector_size:
            logger.error(f"❌ Invalid query embedding (expected {self.vector_size} dimensions)")
            return []
        
        try:
            # Prepare filter if specified
            query_filter = None
            if file_filter:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="file_name",
                            match=MatchValue(value=file_filter)
                        )
                    ]
                )
            
            # Perform vector search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True
            )
            
            # Process results
            results = []
            for hit in search_results:
                payload = dict(hit.payload) if hit.payload else {}
                result = {
                    'slide_id': payload.get('slide_id', str(hit.id)),  # Use original slide_id from metadata
                    'score': float(hit.score),
                    'metadata': payload
                }
                results.append(result)
            
            logger.info(f"🔍 Found {len(results)} similar slides")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching Qdrant: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            return []
    
    def delete_slides_by_file(self, file_path: str) -> bool:
        """
        Delete all slides from a specific file
        
        Args:
            file_path: Path of the file whose slides should be deleted
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete points by filter
            delete_result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_path",
                            match=MatchValue(value=file_path)
                        )
                    ]
                )
            )
            
            if isinstance(delete_result, UpdateResult):
                logger.info(f"🗑️ Deleted slides from file: {file_path}")
                return True
            else:
                logger.warning(f"⚠️ Delete operation returned unexpected result for file: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error deleting slides from Qdrant: {e}")
            return False
    
    def get_collection_info(self) -> Dict:
        """Get information about the Qdrant collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            return {
                'total_vector_count': collection_info.points_count,
                'vector_size': collection_info.config.params.vectors.size,
                'distance_metric': collection_info.config.params.vectors.distance.name,
                'status': collection_info.status,
                'optimizer_status': collection_info.optimizer_status,
                'indexed_vectors': collection_info.indexed_vectors_count
            }
        except Exception as e:
            logger.error(f"❌ Error getting collection info: {e}")
            return {}
    
    def clear_all_vectors(self) -> bool:
        """Clear all vectors from the collection"""
        try:
            # Delete all points in the collection
            delete_result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[]  # Empty filter matches all points
                )
            )
            
            if isinstance(delete_result, UpdateResult):
                logger.info("🗑️ Cleared all vectors from Qdrant collection")
                return True
            else:
                logger.warning("⚠️ Clear operation returned unexpected result")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error clearing Qdrant collection: {e}")
            return False
    
    def delete_vectors_by_folder(self, folder_path: str) -> int:
        """Delete all vectors from a specific folder
        
        Args:
            folder_path: The folder path to delete vectors from
            
        Returns:
            Number of vectors deleted
        """
        try:
            import os
            # Normalize the folder path for consistent matching
            normalized_folder = os.path.normpath(folder_path)
            
            # First, get all points that match the folder path
            # We need to scroll through all points and check their file_path metadata
            matching_ids = []
            
            # Scroll through all points to find matches
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,  # Process in batches
                with_payload=True,
                with_vectors=False  # We don't need vectors, just IDs and metadata
            )
            
            points = scroll_result[0]  # First element is the points list
            next_page_offset = scroll_result[1]  # Second element is the next offset
            
            while points:
                for point in points:
                    if point.payload and 'file_path' in point.payload:
                        point_file_path = point.payload['file_path']
                        # Normalize the point's file path for comparison
                        normalized_point_path = os.path.normpath(point_file_path)
                        
                        # Check if the point's file path starts with the folder path
                        if normalized_point_path.startswith(normalized_folder):
                            # Additional check to ensure it's actually in this folder (not just a substring match)
                            # The path should either be exactly the folder or have a path separator after the folder
                            if (normalized_point_path == normalized_folder or 
                                normalized_point_path.startswith(normalized_folder + os.sep)):
                                matching_ids.append(point.id)
                
                # Get next batch if there is one
                if next_page_offset:
                    scroll_result = self.client.scroll(
                        collection_name=self.collection_name,
                        limit=10000,
                        offset=next_page_offset,
                        with_payload=True,
                        with_vectors=False
                    )
                    points = scroll_result[0]
                    next_page_offset = scroll_result[1]
                else:
                    break
            
            # Delete the matching points if any found
            if matching_ids:
                delete_result = self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=PointIdsList(
                        points=matching_ids
                    )
                )
                
                if isinstance(delete_result, UpdateResult):
                    deleted_count = len(matching_ids)
                    logger.info(f"🗑️ Deleted {deleted_count} vectors from folder: {folder_path}")
                    return deleted_count
                else:
                    logger.warning("⚠️ Delete operation returned unexpected result")
                    return 0
            else:
                logger.info(f"🔍 No vectors found for folder: {folder_path}")
                return 0
                
        except Exception as e:
            logger.error(f"❌ Error deleting vectors by folder: {e}")
            return 0
    
    def get_database_size(self) -> Dict[str, Any]:
        """Get database storage size information"""
        try:
            # Calculate database directory size
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(self.db_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        file_count += 1
                    except OSError:
                        continue
            
            # Get collection info for vector count
            collection_info = self.get_collection_info()
            vector_count = collection_info.get('total_vector_count', 0)
            
            return {
                'database_path': self.db_path,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'vector_count': vector_count,
                'avg_size_per_vector': round(total_size / vector_count, 2) if vector_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating database size: {e}")
            return {'error': str(e)}
    
    def optimize_collection(self) -> bool:
        """Optimize the collection for better performance"""
        try:
            # Trigger collection optimization
            self.client.update_collection(
                collection_name=self.collection_name,
                optimizer_config=OptimizersConfig(
                    deleted_threshold=0.2,
                    vacuum_min_vector_number=1000,
                    default_segment_number=2,
                    max_segment_size=None,  # Let Qdrant decide
                    memmap_threshold=10000,
                    indexing_threshold=20000,
                    flush_interval_sec=5,
                    max_optimization_threads=2
                )
            )
            logger.info("🛠️ Collection optimization triggered")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error optimizing collection: {e}")
            return False

# Global Qdrant service instance
_qdrant_service = None

def get_qdrant_service(db_path: str = None) -> QdrantVectorDB:
    """Get or create global Qdrant service"""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantVectorDB(db_path=db_path)
    return _qdrant_service

def clear_qdrant_service():
    """Clear global Qdrant service (useful for testing)"""
    global _qdrant_service
    _qdrant_service = None
