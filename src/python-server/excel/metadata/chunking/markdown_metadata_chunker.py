import sys
import re
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import logging

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# Import from ai_services
from ai_services.anthropic_service import AnthropicService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('MarkdownMetadataChunker')

class MarkdownMetadataChunker:
    """
    Chunks Excel metadata in markdown format while preserving cell data integrity.
    Uses efficient token estimation to avoid API rate limits.
    """
    
    def __init__(self, max_tokens: int = 18000, anthropic_service: Optional[AnthropicService] = None):
        """
        Initialize the chunker.
        
        Args:
            max_tokens: Maximum tokens per chunk
            anthropic_service: Optional AnthropicService instance
        """
        self.max_tokens = max_tokens
        self.anthropic_service = anthropic_service or AnthropicService()
        # Cache for token estimates to avoid repeated API calls
        self._token_cache = {}
        logger.info(f"Initialized MarkdownMetadataChunker with max_tokens={max_tokens}")
        
    def _estimate_tokens_fast(self, text: str) -> int:
        """
        Fast token estimation using fallback method only.
        Avoids API calls that cause loops.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Approximate token count
        """
        if not text:
            return 0
            
        # Use cache to avoid recalculating
        text_hash = hash(text)
        if text_hash in self._token_cache:
            return self._token_cache[text_hash]
            
        char_count = len(text)
        
        # Check if text appears to be structured metadata
        if self._is_structured_metadata(text):
            # Structured data with repetitive patterns compress better
            estimated_tokens = int(char_count / 2.8)
        else:
            # Regular text
            estimated_tokens = int(char_count / 2.5)
        
        result = max(1, estimated_tokens)
        
        # Cache the result
        self._token_cache[text_hash] = result
        
        logger.debug(f"Fast token estimate: {result} for text length {char_count}")
        return result
    
    def _is_structured_metadata(self, text: str) -> bool:
        """
        Check if text appears to be structured Excel metadata.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text appears to be structured metadata
        """
        try:
            patterns = [
                r'addr=\w+\d+',      # addr=A1, addr=B5, etc.
                r'v=',               # v=something (compressed format)
                r'f==',              # f==formula
                r'deps=\d+→\d+',     # deps=0→1
                r'\| \w+\d+ |'       # Table format with cell addresses
            ]
            
            sample_text = text[:1000]  # Check first 1000 chars for efficiency
            pattern_matches = sum(1 for pattern in patterns if re.search(pattern, sample_text))
            return pattern_matches >= 2
        except Exception as e:
            logger.warning(f"Error checking if structured metadata: {str(e)}")
            return False
    
    async def chunk_metadata(self, markdown_content: str) -> List[str]:
        """
        Split markdown metadata into chunks while preserving cell integrity.
        Uses efficient chunking strategy to avoid token counting loops.
        
        Args:
            markdown_content: Full markdown string
            
        Returns:
            List of markdown chunks
        """
        if not markdown_content or not markdown_content.strip():
            raise ValueError("Markdown content cannot be empty")
        
        logger.info(f"Starting to chunk metadata of length {len(markdown_content)} characters")
        
        try:
            # Use simple line-based chunking with size estimation
            chunks = await self._chunk_by_lines(markdown_content)
            logger.info(f"Created {len(chunks)} chunks")
            
            # Validate chunks with minimal token counting
            await self._validate_chunks_fast(chunks)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking metadata: {str(e)}")
            raise
    
    async def _chunk_by_lines(self, content: str) -> List[str]:
        """
        Chunk content by lines while respecting logical boundaries.
        Uses fast estimation to avoid API rate limits.
        
        Args:
            content: Markdown content to chunk
            
        Returns:
            List of chunks
        """
        lines = content.split('\n')
        chunks = []
        current_chunk_lines = []
        current_chunk_chars = 0
        
        # Estimate target characters per chunk (conservative)
        target_chars_per_chunk = self.max_tokens * 2.5  # Conservative estimate
        
        # Keep header content for each chunk
        header_lines = []
        i = 0
        
        # Extract header content (first few lines until first sheet)
        while i < len(lines) and not lines[i].startswith('## Sheet:'):
            header_lines.append(lines[i])
            i += 1
        
        header_content = '\n'.join(header_lines)
        header_chars = len(header_content)
        
        logger.debug(f"Header content: {len(header_lines)} lines, {header_chars} characters")
        
        # Start first chunk with header
        current_chunk_lines = header_lines[:]
        current_chunk_chars = header_chars
        
        # Process remaining lines
        while i < len(lines):
            line = lines[i]
            line_chars = len(line) + 1  # +1 for newline
            
            # Check if this is a sheet boundary
            if line.startswith('## Sheet:'):
                # If current chunk is getting large, start new chunk
                if current_chunk_chars + line_chars > target_chars_per_chunk and len(current_chunk_lines) > len(header_lines):
                    # Save current chunk
                    chunk_text = '\n'.join(current_chunk_lines)
                    chunks.append(chunk_text)
                    logger.debug(f"Created chunk with {current_chunk_chars} characters")
                    
                    # Start new chunk with header
                    current_chunk_lines = header_lines[:] + [line]
                    current_chunk_chars = header_chars + line_chars
                else:
                    # Add to current chunk
                    current_chunk_lines.append(line)
                    current_chunk_chars += line_chars
            else:
                # Regular line - check if adding it would exceed limit
                if current_chunk_chars + line_chars > target_chars_per_chunk and len(current_chunk_lines) > len(header_lines):
                    # Save current chunk
                    chunk_text = '\n'.join(current_chunk_lines)
                    chunks.append(chunk_text)
                    logger.debug(f"Created chunk with {current_chunk_chars} characters")
                    
                    # Start new chunk with header
                    current_chunk_lines = header_lines[:] + [line]
                    current_chunk_chars = header_chars + line_chars
                else:
                    # Add to current chunk
                    current_chunk_lines.append(line)
                    current_chunk_chars += line_chars
            
            i += 1
        
        # Add final chunk if it has content
        if len(current_chunk_lines) > len(header_lines):
            chunk_text = '\n'.join(current_chunk_lines)
            chunks.append(chunk_text)
            logger.debug(f"Created final chunk with {current_chunk_chars} characters")
        
        logger.info(f"Successfully created {len(chunks)} chunks using line-based approach")
        return chunks
    
    async def _validate_chunks_fast(self, chunks: List[str]) -> None:
        """
        Fast validation that checks only a sample of chunks to avoid loops.
        
        Args:
            chunks: List of chunks to validate
        """
        try:
            if not chunks:
                raise ValueError("No chunks were created")
            
            # Only validate a sample to avoid excessive API calls
            sample_size = min(3, len(chunks))
            sample_indices = [0, len(chunks)//2, len(chunks)-1] if len(chunks) > 2 else list(range(len(chunks)))
            
            for i in sample_indices[:sample_size]:
                chunk = chunks[i]
                if not chunk.strip():
                    logger.warning(f"Chunk {i+1} is empty")
                    continue
                
                # Use fast estimation
                token_count = self._estimate_tokens_fast(chunk)
                if token_count > self.max_tokens * 1.2:  # Allow 20% buffer
                    logger.warning(f"Chunk {i+1} may exceed token limit: {token_count} > {self.max_tokens}")
            
            logger.info(f"Fast validation completed for {len(chunks)} chunks (sampled {sample_size})")
            
        except Exception as e:
            logger.error(f"Error in fast validation: {str(e)}")
            # Don't raise - validation is not critical
    
    async def get_chunk_info(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """
        Get detailed information about each chunk using fast estimation.
        
        Args:
            chunks: List of markdown chunks
            
        Returns:
            List of chunk information dictionaries
        """
        try:
            chunk_info = []
            
            for i, chunk in enumerate(chunks):
                try:
                    lines = chunk.split('\n')
                    # Use fast token estimation
                    token_count = self._estimate_tokens_fast(chunk)
                    
                    # Find sheets in this chunk
                    sheets = []
                    for line in lines:
                        if line.startswith('## Sheet:'):
                            sheet_name = line.replace('## Sheet: ', '').split('(')[0].strip()
                            sheets.append(sheet_name)
                    
                    # Count table rows (cell data rows)
                    table_rows = len([line for line in lines 
                                    if line.startswith('|') and 
                                    not line.startswith('| Row |') and 
                                    not line.startswith('|---')])
                    
                    chunk_info.append({
                        'chunk_index': i + 1,
                        'token_count': token_count,
                        'line_count': len(lines),
                        'character_count': len(chunk),
                        'sheets': sheets,
                        'table_rows': table_rows,
                        'has_dependency_summary': '📊 Dependency Analysis Summary' in chunk,
                        'has_header': chunk.startswith('# '),
                        'token_efficiency': token_count / self.max_tokens if self.max_tokens > 0 else 0
                    })
                    
                except Exception as e:
                    logger.warning(f"Error analyzing chunk {i+1}: {str(e)}")
                    # Add basic info even if analysis fails
                    chunk_info.append({
                        'chunk_index': i + 1,
                        'token_count': self._estimate_tokens_fast(chunk),
                        'line_count': len(chunk.split('\n')),
                        'character_count': len(chunk),
                        'sheets': [],
                        'table_rows': 0,
                        'has_dependency_summary': False,
                        'has_header': False,
                        'token_efficiency': 0,
                        'error': str(e)
                    })
            
            return chunk_info
            
        except Exception as e:
            logger.error(f"Error getting chunk info: {str(e)}")
            raise