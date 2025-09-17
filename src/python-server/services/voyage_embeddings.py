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
    
    # Default batch size for processing multiple images at once
    # Optimized: Batch size 75 is the maximum reliable size for VoyageAI
    # - Batch size 75 provides optimal balance of speed and reliability
    # - Larger batches (100+) cause VoyageAI API timeouts and hanging requests
    # - 10 concurrent workers × 75 images = 750 concurrent images processing
    # - 75 images is the proven maximum that VoyageAI can handle reliably
    DEFAULT_BATCH_SIZE = 75   # Proven maximum batch size for reliable processing
    MAX_BATCH_SIZE = 1000      # VoyageAI theoretical maximum (not practical due to payload size)
    
    def __init__(self, api_key: str = None, batch_size: int = None):
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
        
        # Set batch size with validation
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        if self.batch_size > self.MAX_BATCH_SIZE:
            logger.warning(f"Batch size {self.batch_size} exceeds maximum {self.MAX_BATCH_SIZE}, using maximum")
            self.batch_size = self.MAX_BATCH_SIZE
        elif self.batch_size > 200:
            logger.warning(f"Batch size {self.batch_size} is large and may cause timeouts. Recommended: ≤100")
        elif self.batch_size < 1:
            logger.warning(f"Invalid batch size {self.batch_size}, using default {self.DEFAULT_BATCH_SIZE}")
            self.batch_size = self.DEFAULT_BATCH_SIZE
        
        logger.info(f"VoyageAI API key: {'SET' if self.api_key else 'NOT SET'}")
        logger.info(f"Batch size configured: {self.batch_size}")
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
    
    def create_batch_multimodal_embeddings(self, content_batches: List[List]) -> List[List[float]]:
        """
        Create multimodal embeddings for multiple content items in a single API call
        
        Args:
            content_batches: List of content lists, each containing [text, PIL.Image] items
            
        Returns:
            List of embedding vectors
        """
        import time
        start_time = time.time()
        
        try:
            if not content_batches:
                logger.warning("No content provided for batch embedding")
                return []
            
            logger.info(f"🔍 Starting VoyageAI batch embedding for {len(content_batches)} items...")
            
            # Debug logging for batch structure (first 3 items only)
            for i, content_list in enumerate(content_batches[:3]):
                logger.info(f"   📝 Batch item {i+1}: {len(content_list)} content pieces")
                for j, item in enumerate(content_list):
                    if isinstance(item, str):
                        text_preview = item[:50] + ('...' if len(item) > 50 else '')
                        logger.info(f"      - Text: '{text_preview}'")
                    elif hasattr(item, 'size'):  # PIL Image
                        logger.info(f"      - Image: {item.size} ({item.mode})")
                    else:
                        logger.info(f"      - Unknown type: {type(item)}")
            
            # Log API request details
            prep_time = time.time() - start_time
            logger.info(f"⚡ VoyageAI API Request - Preparation time: {prep_time:.2f}s")
            logger.info(f"📡 Sending request to VoyageAI multimodal_embed API...")
            
            api_start = time.time()
            
            # Create embeddings using voyage-multimodal-3 model with batch processing
            # Add retry mechanism with exponential backoff
            max_retries = 3
            retry_delay = 2  # seconds
            result = None
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        wait_time = retry_delay * (2 ** (attempt - 1))
                        logger.info(f"⏳ Retry attempt {attempt + 1}/{max_retries} after {wait_time}s delay...")
                        time.sleep(wait_time)
                    
                    result = self.client.multimodal_embed(
                        inputs=content_batches,  # Send all batches in one API call
                        model="voyage-multimodal-3",
                        input_type="document"  # Since we're indexing documents
                    )
                    break  # Success, exit retry loop
                    
                except Exception as api_error:
                    logger.warning(f"⚠️ VoyageAI API attempt {attempt + 1} failed: {str(api_error)}")
                    if attempt == max_retries - 1:
                        raise  # Re-raise on final attempt
                    continue
            
            api_time = time.time() - api_start
            total_time = time.time() - start_time
            
            logger.info(f"📡 VoyageAI API Response received - API time: {api_time:.2f}s, Total time: {total_time:.2f}s")
            
            # Extract embedding vectors
            if result and result.embeddings:
                embeddings = result.embeddings
                embedding_dims = len(embeddings[0]) if embeddings else 0
                logger.info(f"✅ Successfully created {len(embeddings)} embeddings (dimensions: {embedding_dims})")
                logger.info(f"⚡ Processing rate: {len(embeddings)/total_time:.2f} embeddings/second")
                return embeddings
            else:
                logger.error(f"❌ VoyageAI returned empty result - API time: {api_time:.2f}s")
                logger.error(f"   Result object: {result}")
                return []
                
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"❌ VoyageAI batch embedding failed after {error_time:.2f}s: {str(e)}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Batch size: {len(content_batches)} items")
            raise
    
    def create_batch_slide_embeddings(self, slides_data: List[Dict]) -> List[Dict]:
        """
        Create embeddings for multiple slides using efficient batch processing
        
        Performance: ~25x faster than individual processing with batch size 100
        - Processes ~0.6 images/second (including conversion time)
        - Optimal batch size: 100 (larger batches cause network timeouts)
        - Automatically falls back to individual processing on batch failures
        
        Args:
            slides_data: List of slide data dictionaries
            
        Returns:
            List of embedding dictionaries
        """
        if not slides_data:
            logger.warning("No slide data provided for batch processing")
            return []
        
        import time
        start_time = time.time()
        logger.info(f"🚀 Starting batch embedding processing for {len(slides_data)} slides (batch size: {self.batch_size})")
        logger.info(f"⏱️ Estimated processing time: ~{len(slides_data) * 0.4:.1f}s at 2.5 slides/second")
        
        all_embeddings = []
        total_batches = (len(slides_data) + self.batch_size - 1) // self.batch_size
        
        # Process slides in batches
        for batch_idx in range(0, len(slides_data), self.batch_size):
            batch_end = min(batch_idx + self.batch_size, len(slides_data))
            current_batch = slides_data[batch_idx:batch_end]
            batch_num = (batch_idx // self.batch_size) + 1
            
            batch_start_time = time.time()
            logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(current_batch)} slides) - Started at {time.strftime('%H:%M:%S')}")
            
            try:
                # Prepare content batches for this batch of slides
                prep_start = time.time()
                content_batches = []
                batch_metadata = []
                
                for slide_data in current_batch:
                    # Prepare content list for each slide
                    content_list = []
                    
                    # Extract slide information
                    image_base64 = slide_data.get('image_base64', '')
                    file_name = slide_data.get('file_name', '')
                    slide_number = slide_data.get('slide_number', 0)
                    
                    # Create text context for the slide
                    slide_text = f"Slide {slide_number} from {file_name}"
                    content_list.append(slide_text)
                    
                    # Convert base64 to PIL Image and add to content
                    if image_base64:
                        try:
                            import base64
                            from PIL import Image
                            from io import BytesIO
                            
                            image_bytes = base64.b64decode(image_base64)
                            image = Image.open(BytesIO(image_bytes))
                            content_list.append(image)
                        except Exception as e:
                            logger.error(f"Error converting base64 to PIL Image for {file_name} slide {slide_number}: {e}")
                            # Continue with just text if image conversion fails
                    
                    content_batches.append(content_list)
                    
                    # Store metadata for later use
                    batch_metadata.append({
                        'file_path': slide_data.get('file_path', ''),
                        'file_name': file_name,
                        'slide_number': slide_number,
                        'image_path': slide_data.get('image_path', ''),
                        'slide_id': f"{file_name}_slide_{slide_number}"
                    })
                
                # Log preparation timing
                prep_time = time.time() - prep_start
                logger.info(f"⚙️ Batch {batch_num} preparation completed in {prep_time:.2f}s - calling VoyageAI API...")
                
                # Create embeddings for the entire batch in one API call
                api_call_start = time.time()
                batch_embeddings = self.create_batch_multimodal_embeddings(content_batches)
                api_call_time = time.time() - api_call_start
                
                if len(batch_embeddings) != len(current_batch):
                    logger.error(f"❌ Mismatch: Expected {len(current_batch)} embeddings, got {len(batch_embeddings)}")
                    # Fall back to individual processing for this batch
                    logger.info(f"🔄 Falling back to individual processing for batch {batch_num}")
                    batch_embeddings = self._process_batch_individually(current_batch)
                
                # Combine embeddings with metadata
                for i, embedding in enumerate(batch_embeddings):
                    if i < len(batch_metadata):  # Safety check
                        embedding_data = {
                            'embedding': embedding,
                            'metadata': batch_metadata[i]
                        }
                        all_embeddings.append(embedding_data)
                
                batch_total_time = time.time() - batch_start_time
                logger.info(f"✅ Completed batch {batch_num}/{total_batches}: {len(batch_embeddings)} embeddings")
                logger.info(f"⏱️ Batch {batch_num} timing breakdown:")
                logger.info(f"   - Preparation: {prep_time:.2f}s")
                logger.info(f"   - API call: {api_call_time:.2f}s")
                logger.info(f"   - Total batch: {batch_total_time:.2f}s")
                logger.info(f"   - Rate: {len(batch_embeddings)/batch_total_time:.2f} embeddings/second")
                
            except Exception as e:
                logger.error(f"❌ Error processing batch {batch_num}: {e}")
                # Fall back to individual processing for this batch
                logger.info(f"🔄 Falling back to individual processing for batch {batch_num}")
                individual_embeddings = self._process_batch_individually(current_batch)
                all_embeddings.extend(individual_embeddings)
                continue
        
        success_count = len(all_embeddings)
        total_slides = len(slides_data)
        total_time = time.time() - start_time
        
        logger.info(f"🎉 Batch processing completed: {success_count}/{total_slides} embeddings created successfully")
        logger.info(f"⏱️  Processing time: {total_time:.2f} seconds ({success_count/total_time:.2f} embeddings/second)")
        
        if success_count < total_slides:
            logger.warning(f"⚠️  Some embeddings failed: {total_slides - success_count} slides could not be processed")
        
        return all_embeddings
    
    def _process_batch_individually(self, slides_data: List[Dict]) -> List[Dict]:
        """
        Fallback method to process slides individually when batch processing fails
        
        Args:
            slides_data: List of slide data dictionaries
            
        Returns:
            List of embedding dictionaries
        """
        logger.info(f"🔄 Processing {len(slides_data)} slides individually as fallback")
        embeddings = []
        
        for i, slide_data in enumerate(slides_data):
            try:
                embedding_data = self.create_slide_embedding(slide_data)
                embeddings.append(embedding_data)
                logger.debug(f"   Individual embedding created for slide {i+1}/{len(slides_data)}")
                
            except Exception as e:
                logger.error(f"   Failed to create individual embedding for slide {i+1}: {e}")
                continue
        
        logger.info(f"✅ Individual processing completed: {len(embeddings)}/{len(slides_data)} embeddings")
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

def get_voyage_embeddings_service(batch_size: int = None) -> VoyageEmbeddingsService:
    """Get or create global VoyageAI embeddings service
    
    Args:
        batch_size: Optional batch size for processing multiple images at once.
                   If None, uses the default batch size (100 - optimal for production).
                   Recommended values:
                   - 100: Optimal balance of speed and reliability (default)
                   - 50-200: Safe range for most use cases
                   - >200: May cause network timeouts with large images
                   Only applies when creating a new service instance.
    """
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = VoyageEmbeddingsService(batch_size=batch_size)
    return _embeddings_service

def configure_voyage_batch_size(batch_size: int) -> VoyageEmbeddingsService:
    """Configure or reconfigure the global VoyageAI service with a specific batch size
    
    This will create a new service instance with the specified batch size,
    replacing any existing instance.
    
    Args:
        batch_size: Batch size for processing multiple images at once
                   Recommended: 100 (optimal for production use)
                   Testing shows:
                   - 100: ~25x faster than individual, reliable
                   - 500+: Network timeouts due to large payloads
                   - <50: Reduces API efficiency
        
    Returns:
        Configured VoyageEmbeddingsService instance
    """
    global _embeddings_service
    _embeddings_service = VoyageEmbeddingsService(batch_size=batch_size)
    return _embeddings_service
