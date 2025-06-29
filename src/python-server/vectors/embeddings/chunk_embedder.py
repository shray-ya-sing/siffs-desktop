import numpy as np
from typing import List, Dict, Union, Optional, Tuple
import logging
import os

from pathlib import Path
import sys
import json

class ChunkEmbedder:
    """
    Converts text chunks into high-dimensional vectors using sentence-transformers.
    Modified to handle chunks with both natural text and markdown formats.
    """
    
    def __init__(
        self, 
        model_name: Optional[str] = 'all-MiniLM-L6-v2',
        device: Optional[str] = None,
        cache_folder: Optional[str] = None,
        use_auth_token: Optional[Union[bool, str]] = None,
        voyageai_api_key: Optional[str] = None
    ):
        """Initialize the embedder with a sentence-transformers model."""
        from sentence_transformers import SentenceTransformer
        import torch
        from tqdm import tqdm
        import voyageai
        
        self.logger = logging.getLogger(__name__)
        self.voyageai_initialized = False
        self.voyageai_client = None
        
        try:
            self.model = SentenceTransformer(
                model_name,
                device=device,
                cache_folder=cache_folder,
                use_auth_token=use_auth_token
            )            
            self.model_name = model_name
            
            # Initialize VoyageAI client if API key is provided
            if voyageai_api_key or os.getenv("VOYAGEAI_API_KEY"):
                self._init_voyageai(voyageai_api_key or os.getenv("VOYAGEAI_API_KEY"))
        
        except Exception as e:
            self.logger.error(f"Failed to initialize model {model_name}: {str(e)}")
    
    def _init_voyageai(self, api_key: str):
        """Initialize the VoyageAI client."""
        if not api_key:
            self.logger.error("VoyageAI API key not provided. Set VOYAGEAI_API_KEY environment variable or pass voyageai_api_key parameter.")
            return
            
        try:
            self.voyageai_client = voyageai.Client(api_key=api_key)
            self.voyageai_initialized = True
            self.logger.info("VoyageAI client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize VoyageAI client: {str(e)}")
            self.voyageai_initialized = False
            
    
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
                'text': chunk.get('text', ''),  # Default to empty string if not present
                'markdown': chunk.get('markdown', chunk.get('text', '')),  # Fallback to text if markdown not available
                'metadata': chunk.get('metadata', {})  # Default to empty dict
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
            
    
    def embed_single_text(
        self,
        text: str,
        use_voyageai: bool = False,
        normalize_embedding: bool = True,
        convert_to_numpy: bool = True,
        model_name: str = "voyage-3",
        output_dimension: Optional[int] = 1024
    ) -> np.ndarray:
        """Embed a single text string.
        
        Args:
            text: The text to embed
            use_voyageai: Whether to use VoyageAI for embedding
            normalize_embedding: Whether to normalize the embedding
            convert_to_numpy: Whether to convert the result to numpy array
            model_name: The name of the VoyageAI model to use
            output_dimension: The dimension of the output embedding
            
        Returns:
            The embedding as a numpy array
        """
        if use_voyageai:
            if not self.voyageai_initialized:
                self._init_voyageai(os.getenv("VOYAGEAI_API_KEY"))
                if not self.voyageai_initialized:
                    self.logger.error("VoyageAI client not initialized. Please provide a valid API key.")
            
            try:
                result = self.voyageai_client.embed(
                    texts=[text],
                    model=model_name,
                    input_type="document",
                    output_dimension=output_dimension or 1024
                )
                return np.array(result.embeddings[0], dtype=np.float32)
            except Exception as e:
                self.logger.error(f"Error embedding text with VoyageAI: {str(e)}")
                
        else:
            try:
                embedding = self.model.encode(
                    text,
                    normalize_embeddings=normalize_embedding,
                    convert_to_numpy=convert_to_numpy,
                    convert_to_tensor=not convert_to_numpy
                )
                return embedding
            except Exception as e:
                self.logger.error(f"Error embedding text with local model: {str(e)}")
                
    
    def get_model_info(self) -> Dict[str, any]:
        """Get information about the current model."""
        return {
            'model_name': self.model_name,
            'embedding_dimension': self.model.get_sentence_embedding_dimension(),
            'max_seq_length': self.model.max_seq_length,
            'device': str(self.model.device),
            'similarity_function': self.model.similarity_fn_name
        }