import faiss
import numpy as np
from typing import List, Dict, Optional, Tuple, Union
import os
import pickle
import logging
from datetime import datetime
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from vectors
from store.embedding_storage import EmbeddingStorage
from embeddings.chunk_embedder import ChunkEmbedder

class FAISSChunkRetriever:
    """
    FAISS-based retriever for Excel chunk embeddings.
    Integrates with EmbeddingStorage for SQLite backend.
    """
    
    def __init__(
        self,
        storage: 'EmbeddingStorage',
        embedder: 'ChunkEmbedder',
        index_path: str = "./faiss_indices"
    ):
        """
        Initialize the FAISS retriever.
        
        Args:
            storage: EmbeddingStorage instance for SQLite access
            embedder: ChunkEmbedder instance for query embedding
            index_path: Directory to store FAISS indices
        """
        self.storage = storage
        self.embedder = embedder
        self.index_path = index_path
        self.logger = logging.getLogger(__name__)
        
        # Create index directory
        os.makedirs(index_path, exist_ok=True)
        
        # Index cache: {workbook_path: {'index': faiss_index, 'chunk_ids': [...]}}
        self.indices = {}
        
        # Load existing indices
        self._load_existing_indices()
    
    def _load_existing_indices(self):
        """Load any existing FAISS indices from disk."""
        try:
            index_meta_path = os.path.join(self.index_path, "index_metadata.pkl")
            if os.path.exists(index_meta_path):
                with open(index_meta_path, 'rb') as f:
                    metadata = pickle.load(f)
                    
                for workbook_path, info in metadata.items():
                    index_file = os.path.join(self.index_path, info['index_file'])
                    if os.path.exists(index_file):
                        index = faiss.read_index(index_file)
                        self.indices[workbook_path] = {
                            'index': index,
                            'chunk_ids': info['chunk_ids'],
                            'embedding_dim': info['embedding_dim']
                        }
                        self.logger.info(f"Loaded index for {os.path.basename(workbook_path)}")
        except Exception as e:
            self.logger.warning(f"Could not load existing indices: {e}")
    
    def build_index_for_workbook(
        self,
        workbook_path: str,
        force_rebuild: bool = False
    ) -> faiss.Index:
        """
        Build or retrieve FAISS index for a specific workbook.
        
        Args:
            workbook_path: Path to the workbook
            force_rebuild: Force rebuilding even if index exists
            
        Returns:
            FAISS index for the workbook
        """
        # Check cache
        if not force_rebuild and workbook_path in self.indices:
            return self.indices[workbook_path]['index']
        
        # Get embeddings from storage
        embeddings, chunks, workbook_info = self.storage.get_workbook_embeddings(workbook_path)
        
        if len(embeddings) == 0:
            raise ValueError(f"No embeddings found for workbook: {workbook_path}")
        
        # Extract chunk IDs for mapping
        chunk_ids = [chunk['chunk_index'] for chunk in chunks]
        
        # Build FAISS index
        dimension = embeddings.shape[1]
        
        # Choose index type based on dataset size
        n_vectors = len(embeddings)
        
        if n_vectors < 1000:
            # For small datasets, use exact search
            index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            self.logger.info(f"Using exact search (IndexFlatIP) for {n_vectors} vectors")
        else:
            # For larger datasets, use IVF index for faster search
            nlist = min(100, n_vectors // 10)  # Number of clusters
            quantizer = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            
            # Train the index
            index.train(embeddings.astype('float32'))
            self.logger.info(f"Using IVF index with {nlist} clusters for {n_vectors} vectors")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings.astype('float32'))
        
        # Add embeddings to index
        index.add(embeddings.astype('float32'))
        
        # Cache the index
        self.indices[workbook_path] = {
            'index': index,
            'chunk_ids': chunk_ids,
            'embedding_dim': dimension
        }
        
        # Save index to disk
        self._save_index(workbook_path)
        
        self.logger.info(f"Built index for {os.path.basename(workbook_path)} with {n_vectors} vectors")
        return index
    
    def build_global_index(self, force_rebuild: bool = False) -> faiss.Index:
        """
        Build a global index across all workbooks.
        
        Args:
            force_rebuild: Force rebuilding even if index exists
            
        Returns:
            Global FAISS index
        """
        global_key = "__GLOBAL__"
        
        # Check cache
        if not force_rebuild and global_key in self.indices:
            return self.indices[global_key]['index']
        
        # Get all embeddings from storage
        all_embeddings, all_chunk_ids = self.storage.get_all_embeddings_for_faiss()
        
        if len(all_embeddings) == 0:
            raise ValueError("No embeddings found in database")
        
        dimension = all_embeddings.shape[1]
        n_vectors = len(all_embeddings)
        
        # Build appropriate index
        if n_vectors < 5000:
            index = faiss.IndexFlatIP(dimension)
        else:
            # Use more sophisticated index for large datasets
            nlist = int(np.sqrt(n_vectors))
            quantizer = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            index.train(all_embeddings.astype('float32'))
        
        # Normalize and add
        faiss.normalize_L2(all_embeddings.astype('float32'))
        index.add(all_embeddings.astype('float32'))
        
        # Cache
        self.indices[global_key] = {
            'index': index,
            'chunk_ids': all_chunk_ids,
            'embedding_dim': dimension
        }
        
        self.logger.info(f"Built global index with {n_vectors} vectors")
        return index
    
    def search(
        self,
        query: str,
        workbook_path: Optional[str] = None,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        return_format: str = 'both'  # 'text', 'markdown', or 'both'
    ) -> List[Dict[str, any]]:
        """
        Search for relevant chunks based on text query.
        Modified to return both text formats.
        
        Args:
            query: Text query string
            workbook_path: Limit search to specific workbook (None = search all)
            top_k: Number of results to return
            score_threshold: Minimum similarity score (0-1)
            return_format: Which text format to return in results
            
        Returns:
            List of result dictionaries with chunk info and scores
        """
        # Embed the query
        query_embedding = self.embedder.embed_single_text(
            query,
            normalize_embedding=True,
            convert_to_numpy=True
        )
        
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Get appropriate index
        if workbook_path:
            if workbook_path not in self.indices:
                self.build_index_for_workbook(workbook_path)
            
            index_info = self.indices[workbook_path]
            index = index_info['index']
            chunk_ids = index_info['chunk_ids']
        else:
            if "__GLOBAL__" not in self.indices:
                self.build_global_index()
            
            index_info = self.indices["__GLOBAL__"]
            index = index_info['index']
            chunk_ids = index_info['chunk_ids']
        
        # Normalize query for cosine similarity
        faiss.normalize_L2(query_embedding.astype('float32'))
        
        # Search
        if hasattr(index, 'nprobe'):
            index.nprobe = min(10, index.nlist)
        
        scores, indices = index.search(query_embedding.astype('float32'), top_k)
        
        # Process results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
                
            if score_threshold and score < score_threshold:
                continue
            
            # Get chunk information from storage
            if workbook_path:
                chunk_index = chunk_ids[idx]
                _, chunks, _ = self.storage.get_workbook_embeddings(workbook_path, return_format=return_format)
                chunk_info = chunks[chunk_index]
                
                result = {
                    'score': float(score),
                    'workbook_path': workbook_path,
                    'workbook_name': os.path.basename(workbook_path),
                    'chunk_index': chunk_index,
                    'metadata': chunk_info['metadata']
                }
                
                # Add requested text format(s)
                if return_format == 'text':
                    result['text'] = chunk_info['text']
                elif return_format == 'markdown':
                    result['markdown'] = chunk_info['markdown']
                else:  # 'both'
                    result['text'] = chunk_info.get('text', '')
                    result['markdown'] = chunk_info.get('markdown', '')
            else:
                chunk_id = chunk_ids[idx]
                chunks = self.storage.get_chunks_by_ids([chunk_id], return_format=return_format)
                
                if chunks:
                    chunk = chunks[0]
                    result = {
                        'score': float(score),
                        'workbook_path': chunk['workbook_path'],
                        'workbook_name': chunk['workbook_name'],
                        'chunk_index': chunk['chunk_index'],
                        'metadata': chunk['metadata']
                    }
                    
                    # Add requested text format(s)
                    if return_format == 'text':
                        result['text'] = chunk['text']
                    elif return_format == 'markdown':
                        result['markdown'] = chunk['markdown']
                    else:  # 'both'
                        result['text'] = chunk.get('text', '')
                        result['markdown'] = chunk.get('markdown', '')
                else:
                    continue
            
            results.append(result)
        
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
        
    
    def search_with_filters(
        self,
        query: str,
        filters: Dict[str, any],
        top_k: int = 5
    ) -> List[Dict[str, any]]:
        """
        Search with metadata filters.
        
        Args:
            query: Text query
            filters: Metadata filters (e.g., {'worksheet': 'Sheet1'})
            top_k: Number of results
            
        Returns:
            Filtered search results
        """
        # Get more results than needed for filtering
        results = self.search(query, top_k=top_k * 3)
        
        # Apply filters
        filtered_results = []
        for result in results:
            metadata = result.get('metadata', {})
            
            # Check all filters
            match = True
            for key, value in filters.items():
                if metadata.get(key) != value:
                    match = False
                    break
            
            if match:
                filtered_results.append(result)
                
            if len(filtered_results) >= top_k:
                break
        
        return filtered_results
    
    def _save_index(self, workbook_path: str):
        """Save FAISS index to disk."""
        try:
            # Save the FAISS index
            index_info = self.indices[workbook_path]
            index_filename = f"index_{os.path.basename(workbook_path)}.faiss"
            index_file = os.path.join(self.index_path, index_filename)
            
            faiss.write_index(index_info['index'], index_file)
            
            # Update metadata
            metadata_file = os.path.join(self.index_path, "index_metadata.pkl")
            
            # Load existing metadata
            metadata = {}
            if os.path.exists(metadata_file):
                with open(metadata_file, 'rb') as f:
                    metadata = pickle.load(f)
            
            # Update with new index info
            metadata[workbook_path] = {
                'index_file': index_filename,
                'chunk_ids': index_info['chunk_ids'],
                'embedding_dim': index_info['embedding_dim'],
                'updated_at': datetime.now().isoformat()
            }
            
            # Save metadata
            with open(metadata_file, 'wb') as f:
                pickle.dump(metadata, f)
                
        except Exception as e:
            self.logger.warning(f"Could not save index for {workbook_path}: {e}")
    
    def update_workbook_index(self, workbook_path: str):
        """Update index when workbook embeddings change."""
        self.build_index_for_workbook(workbook_path, force_rebuild=True)
        
        # Also rebuild global index if it exists
        if "__GLOBAL__" in self.indices:
            self.build_global_index(force_rebuild=True)


# Example usage
def search_excel_chunks(query: str, storage: EmbeddingStorage, embedder: ChunkEmbedder):
    """
    Helper function to search Excel chunks.
    
    Args:
        query: Search query text
        storage: EmbeddingStorage instance
        embedder: ChunkEmbedder instance
    """
    # Initialize retriever
    retriever = FAISSRetriever(storage, embedder)
    
    # Search across all workbooks
    print(f"\nSearching for: '{query}'")
    results = retriever.search(query, top_k=5)
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.3f}")
        print(f"   Workbook: {result['workbook_name']}")
        print(f"   Chunk: {result['metadata']}")
        print(f"   Text preview: {result['text'][:200]}...")
    
    return results