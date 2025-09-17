import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pinecone import Pinecone, ServerlessSpec
import json
import time

logger = logging.getLogger(__name__)

class PineconeVectorDB:
    """Pinecone vector database service for storing and searching slide embeddings"""
    
    def __init__(self, api_key: str = None, environment: str = "us-east-1"):
        """
        Initialize Pinecone client
        
        Args:
            api_key: Pinecone API key (if None, will try to get from environment)
            environment: Pinecone environment
        """
        # Hardcoded API key (temporary fix)
        self.api_key = api_key or "pcsk_QEA8e_RNPvdrhcXJLZQnNCq6U3BSeNbpTS7VMLaE4VEmh9ZSUUwgP5j23yu5psPbWBoo3"
        
        # Comment out environment loading for now
        # self.api_key = api_key or os.getenv('PINECONE_API_KEY')
        
        logger.info(f"Pinecone API key: {'SET' if self.api_key else 'NOT SET'}")
        if self.api_key:
            logger.info(f"Pinecone API key length: {len(self.api_key)}")
            logger.info(f"Pinecone API key starts with: {self.api_key[:10]}...")
        
        if not self.api_key:
            logger.error("Pinecone API key is not available!")
            raise ValueError("Pinecone API key is required.")
        
        self.environment = environment
        self.index_name = "siffs-slides"  # Index name for slide embeddings
        self.index = None
        
        try:
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=self.api_key)
            logger.info("Pinecone client initialized successfully")
            
            # Initialize index
            self._initialize_index()
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            raise
    
    def _initialize_index(self, dimension: int = 1024):
        """Initialize or connect to Pinecone index"""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes.indexes] if existing_indexes.indexes else []
            
            if self.index_name not in index_names:
                # Create new index
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.environment
                    )
                )
                # Wait for index to be ready
                while not self.pc.describe_index(self.index_name).status['ready']:
                    time.sleep(1)
                logger.info(f"Index {self.index_name} created successfully")
            else:
                logger.info(f"Using existing index: {self.index_name}")
            
            # Connect to index
            self.index = self.pc.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone index: {e}")
            raise
    
    def upsert_slide_embeddings(self, embeddings_data: List[Dict]) -> bool:
        """
        Store slide embeddings in Pinecone
        
        Args:
            embeddings_data: List of embedding dictionaries with metadata
            
        Returns:
            True if successful, False otherwise
        """
        if not self.index:
            logger.error("Pinecone index not initialized")
            return False
        
        try:
            vectors = []
            for embedding_data in embeddings_data:
                embedding = embedding_data.get('embedding', [])
                metadata = embedding_data.get('metadata', {})
                
                if not embedding:
                    logger.warning("Skipping empty embedding")
                    continue
                
                # Create unique ID for the slide
                slide_id = metadata.get('slide_id', f"slide_{len(vectors)}")
                
                # Prepare metadata (Pinecone has limitations on metadata size and types)
                pinecone_metadata = {
                    'file_path': metadata.get('file_path', ''),
                    'file_name': metadata.get('file_name', ''),
                    'slide_number': int(metadata.get('slide_number', 0)),
                    'image_path': metadata.get('image_path', '')
                }
                
                vectors.append({
                    'id': slide_id,
                    'values': embedding,
                    'metadata': pinecone_metadata
                })
            
            if not vectors:
                logger.warning("No valid vectors to upsert")
                return False
            
            # Upsert vectors in batches
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
                logger.info(f"Upserted batch {i//batch_size + 1}, {len(batch)} vectors")
            
            logger.info(f"Successfully upserted {len(vectors)} slide embeddings to Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Error upserting embeddings to Pinecone: {e}")
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
        if not self.index:
            logger.error("Pinecone index not initialized")
            return []
        
        try:
            # Prepare filter if specified
            filter_dict = {}
            if file_filter:
                filter_dict['file_name'] = {'$eq': file_filter}
            
            # Perform vector search
            search_results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict if filter_dict else None
            )
            
            # Process results
            results = []
            for match in search_results.matches:
                result = {
                    'slide_id': match.id,
                    'score': float(match.score),
                    'metadata': dict(match.metadata) if match.metadata else {}
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} similar slides")
            return results
            
        except Exception as e:
            logger.error(f"Error searching Pinecone: {e}")
            return []
    
    def delete_slides_by_file(self, file_path: str) -> bool:
        """
        Delete all slides from a specific file
        
        Args:
            file_path: Path of the file whose slides should be deleted
            
        Returns:
            True if successful, False otherwise
        """
        if not self.index:
            logger.error("Pinecone index not initialized")
            return False
        
        try:
            # Query to find all slides from this file
            query_results = self.index.query(
                vector=[0] * 1024,  # Dummy vector for metadata-only query
                top_k=10000,  # Large number to get all matches
                include_metadata=True,
                filter={'file_path': {'$eq': file_path}}
            )
            
            # Extract IDs to delete
            ids_to_delete = [match.id for match in query_results.matches]
            
            if ids_to_delete:
                # Delete vectors
                self.index.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} slides from file {file_path}")
                return True
            else:
                logger.info(f"No slides found for file {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting slides from Pinecone: {e}")
            return False
    
    def get_index_stats(self) -> Dict:
        """Get statistics about the Pinecone index"""
        if not self.index:
            return {}
        
        try:
            stats = self.index.describe_index_stats()
            return {
                'total_vector_count': stats.total_vector_count,
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}
    
    def clear_all_vectors(self) -> bool:
        """Clear all vectors from the index"""
        if not self.index:
            logger.error("Pinecone index not initialized")
            return False
        
        try:
            self.index.delete(delete_all=True)
            logger.info("Cleared all vectors from Pinecone index")
            return True
        except Exception as e:
            logger.error(f"Error clearing Pinecone index: {e}")
            return False

# Global Pinecone service instance
_pinecone_service = None

def get_pinecone_service() -> PineconeVectorDB:
    """Get or create global Pinecone service"""
    global _pinecone_service
    if _pinecone_service is None:
        _pinecone_service = PineconeVectorDB()
    return _pinecone_service
