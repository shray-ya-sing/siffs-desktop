import numpy as np
from typing import List, Dict, Union, Optional, Tuple
from sentence_transformers import SentenceTransformer
import torch
from tqdm import tqdm
import logging

class ChunkEmbedder:
    """
    Converts text chunks into high-dimensional vectors using sentence-transformers.
    Modified to handle chunks with both natural text and markdown formats.
    """
    
    def __init__(
        self, 
        model_name: str = 'all-MiniLM-L6-v2',
        device: Optional[str] = None,
        cache_folder: Optional[str] = None,
        use_auth_token: Optional[Union[bool, str]] = None
    ):
        """Initialize the embedder with a sentence-transformers model."""
        self.logger = logging.getLogger(__name__)
        
        try:
            self.model = SentenceTransformer(
                model_name,
                device=device,
                cache_folder=cache_folder,
                use_auth_token=use_auth_token
            )
            
            self.model_name = model_name
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            self.max_seq_length = self.model.max_seq_length
            
            self.logger.info(f"Initialized {model_name} with {self.embedding_dimension} dimensions")
            self.logger.info(f"Max sequence length: {self.max_seq_length} tokens")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize model {model_name}: {str(e)}")
            raise
    
    def embed_chunks(
        self,
        chunks: List[Dict[str, str]],
        batch_size: int = 32,
        show_progress_bar: bool = True,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = True,
        output_value: str = 'sentence_embedding'
    ) -> Tuple[np.ndarray, List[Dict]]:
        """
        Embed a list of chunks using the sentence transformer.
        Modified to handle chunks with both 'text' and 'markdown' fields.
        
        Args:
            chunks: List of chunk dictionaries with 'text', 'markdown', and 'metadata' keys
            
        Returns:
            Tuple of (embeddings array, enhanced chunks list with both formats)
        """
        if not chunks:
            return np.array([]), []
        
        # Extract only natural text for embedding
        texts = [chunk['text'] for chunk in chunks]
        
        # Prepare enhanced chunk data that includes both formats
        enhanced_chunks = []
        for chunk in chunks:
            enhanced_chunk = {
                'text': chunk['text'],  # Natural language text
                'markdown': chunk.get('markdown', chunk['text']),  # Markdown format
                'metadata': chunk.get('metadata', {})
            }
            enhanced_chunks.append(enhanced_chunk)
        
        try:
            # Embed only the natural language text
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress_bar,
                output_value=output_value,
                convert_to_numpy=convert_to_numpy,
                convert_to_tensor=not convert_to_numpy,
                normalize_embeddings=normalize_embeddings
            )
            
            self.logger.info(f"Successfully embedded {len(chunks)} chunks")
            
            return embeddings, enhanced_chunks
            
        except Exception as e:
            self.logger.error(f"Error embedding chunks: {str(e)}")
            raise
    
    def embed_single_text(
        self,
        text: str,
        normalize_embedding: bool = True,
        convert_to_numpy: bool = True
    ) -> np.ndarray:
        """Embed a single text string."""
        embedding = self.model.encode(
            text,
            normalize_embeddings=normalize_embedding,
            convert_to_numpy=convert_to_numpy,
            convert_to_tensor=not convert_to_numpy
        )
        
        return embedding
    
    def get_model_info(self) -> Dict[str, any]:
        """Get information about the current model."""
        return {
            'model_name': self.model_name,
            'embedding_dimension': self.embedding_dimension,
            'max_seq_length': self.max_seq_length,
            'device': str(self.model.device),
            'similarity_function': self.model.similarity_fn_name
        }