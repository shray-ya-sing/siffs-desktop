import os
import logging
from typing import List, Dict, Any, Optional
import voyageai
import base64
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

class VoyageEmbeddingsService:
    """Service for creating multimodal embeddings using VoyageAI"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize VoyageAI client
        
        Args:
            api_key: VoyageAI API key (if None, will try to get from environment)
        """
        # Hardcoded API key (temporary fix)
        self.api_key = api_key or "pa-lkitG0Pwd7QpXkb7EUyATIlTGHY2aJ6oYHMvOydjfk7"
        
        # Comment out environment loading for now
        # self.api_key = api_key or os.getenv('VOYAGE_API_KEY')
        
        if not self.api_key:
            raise ValueError("VoyageAI API key is required.")
        
        logger.info(f"VoyageAI API key: {'SET' if self.api_key else 'NOT SET'}")
        if self.api_key:
            logger.info(f"VoyageAI API key length: {len(self.api_key)}")
            logger.info(f"VoyageAI API key starts with: {self.api_key[:10]}...")
        
        try:
            self.client = voyageai.Client(api_key=self.api_key)
            logger.info("VoyageAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VoyageAI client: {e}")
            raise
    
    def create_multimodal_embedding(self, image_base64: str, text: str = "") -> List[float]:
        """
        Create multimodal embedding for slide image with optional text
        
        Args:
            image_base64: Base64 encoded image data
            text: Optional text to include in embedding
            
        Returns:
            List of embedding values
        """
        try:
            # Prepare input for multimodal embedding
            inputs = []
            
            # Add image input
            if image_base64:
                inputs.append({
                    "type": "image",
                    "content": image_base64
                })
            
            # Add text input if provided
            if text:
                inputs.append({
                    "type": "text", 
                    "content": text
                })
            
            # Create embedding using voyage-multimodal-3 model
            result = self.client.multimodal_embed(
                inputs=inputs,
                model="voyage-multimodal-3"
            )
            
            # Extract embedding vector
            if result and result.embeddings and len(result.embeddings) > 0:
                embedding = result.embeddings[0]
                logger.debug(f"Created embedding with {len(embedding)} dimensions")
                return embedding
            else:
                logger.error("No embedding returned from VoyageAI")
                return []
                
        except Exception as e:
            logger.error(f"Error creating multimodal embedding: {e}")
            raise
    
    def create_text_embedding(self, text: str) -> List[float]:
        """
        Create text-only embedding for search queries
        
        Args:
            text: Input text
            
        Returns:
            List of embedding values
        """
        try:
            result = self.client.embed(
                texts=[text],
                model="voyage-3"  # Use text model for queries
            )
            
            if result and result.embeddings and len(result.embeddings) > 0:
                embedding = result.embeddings[0]
                logger.debug(f"Created text embedding with {len(embedding)} dimensions")
                return embedding
            else:
                logger.error("No embedding returned from VoyageAI for text")
                return []
                
        except Exception as e:
            logger.error(f"Error creating text embedding: {e}")
            raise
    
    def create_slide_embedding(self, slide_data: Dict) -> Dict:
        """
        Create embedding for a single slide with metadata
        
        Args:
            slide_data: Dictionary containing slide information
            
        Returns:
            Dictionary with embedding and metadata
        """
        try:
            # Extract slide information
            image_base64 = slide_data.get('image_base64', '')
            file_name = slide_data.get('file_name', '')
            slide_number = slide_data.get('slide_number', 0)
            
            # Create text context for the slide
            slide_text = f"Slide {slide_number} from {file_name}"
            
            # Create multimodal embedding
            embedding = self.create_multimodal_embedding(image_base64, slide_text)
            
            if not embedding:
                raise ValueError("Failed to create embedding for slide")
            
            # Return embedding with metadata
            return {
                'embedding': embedding,
                'metadata': {
                    'file_path': slide_data.get('file_path', ''),
                    'file_name': file_name,
                    'slide_number': slide_number,
                    'image_path': slide_data.get('image_path', ''),
                    'slide_id': f"{file_name}_slide_{slide_number}"
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating slide embedding: {e}")
            raise
    
    def create_batch_slide_embeddings(self, slides_data: List[Dict]) -> List[Dict]:
        """
        Create embeddings for multiple slides
        
        Args:
            slides_data: List of slide data dictionaries
            
        Returns:
            List of embedding dictionaries
        """
        embeddings = []
        
        for i, slide_data in enumerate(slides_data):
            try:
                embedding_data = self.create_slide_embedding(slide_data)
                embeddings.append(embedding_data)
                logger.info(f"Created embedding for slide {i+1}/{len(slides_data)}")
                
            except Exception as e:
                logger.error(f"Failed to create embedding for slide {i+1}: {e}")
                continue
        
        logger.info(f"Successfully created {len(embeddings)} embeddings from {len(slides_data)} slides")
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings from VoyageAI"""
        try:
            # Create a test embedding to get dimensions
            test_result = self.client.embed(
                texts=["test"],
                model="voyage-3"
            )
            if test_result and test_result.embeddings:
                return len(test_result.embeddings[0])
            return 1024  # Default dimension for voyage-3
        except:
            return 1024  # Fallback

# Global embeddings service instance
_embeddings_service = None

def get_voyage_embeddings_service() -> VoyageEmbeddingsService:
    """Get or create global VoyageAI embeddings service"""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = VoyageEmbeddingsService()
    return _embeddings_service
