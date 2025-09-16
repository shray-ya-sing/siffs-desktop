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
            # Prepare content list for multimodal embedding
            # According to VoyageAI docs, content should be a list containing text strings and/or PIL images
            content_list = []
            
            # Add text first if provided
            if text:
                content_list.append(text)
            
            # Convert base64 to PIL Image and add to content
            if image_base64:
                try:
                    # Decode base64 to bytes
                    import base64
                    from PIL import Image
                    from io import BytesIO
                    
                    image_bytes = base64.b64decode(image_base64)
                    image = Image.open(BytesIO(image_bytes))
                    content_list.append(image)
                    
                except Exception as e:
                    logger.error(f"Error converting base64 to PIL Image: {e}")
                    # If image conversion fails, continue with just text
                    if not content_list:  # If no text was added either
                        return []
            
            # If no content, return empty
            if not content_list:
                logger.warning("No content to create embedding for")
                return []
            
            # Create single input with content list
            inputs = [content_list]  # VoyageAI expects List[List[Union[str, PIL.Image]]]
            
            # Debug logging
            logger.info(f"🔍 VoyageAI input structure:")
            logger.info(f"   Content list length: {len(content_list)}")
            for i, item in enumerate(content_list):
                if isinstance(item, str):
                    logger.info(f"   Item {i}: Text (length: {len(item)})")
                elif isinstance(item, Image.Image):
                    logger.info(f"   Item {i}: PIL Image (size: {item.size})")
                else:
                    logger.info(f"   Item {i}: Unknown type ({type(item)})")
            
            # Create embedding using voyage-multimodal-3 model
            result = self.client.multimodal_embed(
                inputs=inputs,
                model="voyage-multimodal-3",
                input_type="document"  # Since we're indexing documents
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
        Create text-only embedding for search queries using multimodal model for compatibility
        
        Args:
            text: Input text
            
        Returns:
            List of embedding values
        """
        try:
            logger.info(f"🔍 Creating text embedding for query: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Use multimodal model with text-only input for consistency with slide embeddings
            inputs = [[text]]  # Format as List[List[str]] for multimodal API
            
            result = self.client.multimodal_embed(
                inputs=inputs,
                model="voyage-multimodal-3",  # Use same model as slide embeddings for compatibility
                input_type="query"  # Specify this is a query, not a document
            )
            
            # Extract embedding vector  
            if result and result.embeddings and len(result.embeddings) > 0:
                embedding = result.embeddings[0]
                logger.info(f"✅ Created text embedding with {len(embedding)} dimensions")
                return embedding
            else:
                logger.error("❌ No embedding returned from VoyageAI for text query")
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
    
    def rerank_slides(self, query: str, slide_results: List[Dict], top_k: int = None) -> List[Dict]:
        """
        Rerank slide results using VoyageAI's reranker for better relevance
        
        Args:
            query: The search query text
            slide_results: List of slide result dictionaries from vector search
            top_k: Number of top results to return after reranking
            
        Returns:
            Reranked list of slide results
        """
        try:
            if not slide_results:
                return slide_results
                
            logger.info(f"🔄 Reranking {len(slide_results)} slides with query: '{query[:50]}{'...' if len(query) > 50 else ''}'")
            
            # Extract text representations for reranking
            # Since VoyageAI reranker only works with text, we create text representations
            documents = []
            for result in slide_results:
                # Create a text representation of each slide
                file_name = result.get('file_name', 'Unknown')
                slide_num = result.get('slide_number', 0)
                
                # Create a descriptive text for the slide
                slide_text = f"Slide {slide_num} from {file_name}"
                
                # If we had OCR text from the slides, we would add it here:
                # slide_text += f" Content: {result.get('ocr_text', '')}"
                
                documents.append(slide_text)
            
            # Use VoyageAI reranker
            reranking_result = self.client.rerank(
                query=query,
                documents=documents,
                model="rerank-2.5-lite",  # Fast and high quality
                top_k=top_k,
                truncation=True
            )
            
            # Reorder the slide results based on reranking
            reranked_results = []
            for ranking_result in reranking_result.results:
                original_index = ranking_result.index
                slide_result = slide_results[original_index].copy()
                
                # Update the score with the reranker score
                # Combine both vector similarity and reranker scores
                original_score = slide_result.get('score', 0.0)
                rerank_score = ranking_result.relevance_score
                
                # Weighted combination: 60% reranker, 40% original vector score
                combined_score = (0.6 * rerank_score) + (0.4 * original_score)
                slide_result['score'] = combined_score
                slide_result['rerank_score'] = rerank_score
                slide_result['original_score'] = original_score
                
                reranked_results.append(slide_result)
            
            logger.info(f"✅ Reranking completed: {len(reranked_results)} results")
            if reranked_results:
                logger.info(f"   Top result: combined_score={reranked_results[0]['score']:.4f}, rerank_score={reranked_results[0]['rerank_score']:.4f}")
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"❌ Error during reranking: {e}")
            logger.info("🔄 Falling back to original vector search results")
            return slide_results
    
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
