import xlwings as xw
import json
import logging
import traceback
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import os
import sys
from pathlib import Path
# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
# Then import the logging config
from logging_config import setup_logging
setup_logging()
# Get logger for this module
logger = logging.getLogger(__name__)
# Add the current directory to path for imports
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))



class ExcelMetadataProcessor:
    """
    Python class for extracting comprehensive cell-based metadata from Excel workbooks 
    and compressing it to LLM readable format with chunking support.
    """
    
    def __init__(self, workbook_path: Optional[str] = None):
        """
        Initialize the Excel metadata processor.
        
        Args:
            workbook_path: Optional path to the Excel file
        """
        self.workbook_path = workbook_path
        self.extractor = None
        self.compressor = None
        self.metadata = None
        self.display_values = None
        self.chunker = None
        self.max_tokens_per_chunk = 18000
        self.text_compressor = None
        
        # Try to import required modules
        try:
            from extraction.excel_metadata_extractor import ExcelMetadataExtractor
            from compression.markdown_compressor import SpreadsheetMarkdownCompressor
            from compression.text_compressor import JsonTextCompressor
            from chunking.markdown_metadata_chunker import MarkdownMetadataChunker
            self.extractor = ExcelMetadataExtractor(workbook_path)
            self.compressor = SpreadsheetMarkdownCompressor(workbook_path)
            self.chunker = MarkdownMetadataChunker(max_tokens=self.max_tokens_per_chunk)
            self.text_compressor = JsonTextCompressor()
            logger.info("Successfully initialized ExcelMetadataProcessor")
        except ImportError as e:
            logger.error(f"Failed to initialize required modules: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {str(e)}")
            raise

    async def process_workbook(
        self,
        workbook_path: Optional[str] = None,
        output_dir: Optional[str] = None,
        max_rows_per_sheet: int = 100,
        max_cols_per_sheet: int = 50,
        include_display_values: bool = False
    ) -> Tuple[Dict[str, Any], str, List[str], List[Dict[str, Any]]]:
        """
        Process the Excel workbook: extract metadata, compress to markdown, and chunk.
        
        Args:
            workbook_path: Path to the Excel file (if not provided during initialization)
            output_dir: Directory to save output files (optional)
            max_rows_per_sheet: Maximum number of rows to process per sheet
            max_cols_per_sheet: Maximum number of columns to process per sheet
            include_display_values: Whether to include display values (requires xlwings)
            
        Returns:
            Tuple of (metadata_dict, markdown_string, chunks_list, chunk_info_list)
        """
        try:
            # Update workbook path if provided
            if workbook_path:
                self.workbook_path = workbook_path
                
            if not self.workbook_path:
                raise ValueError("No workbook path provided")
                
            logger.info(f"Starting to process workbook: {self.workbook_path}")
            
            # Step 1: Extract metadata
            self.metadata, self.display_values = self._extract_metadata(
                max_rows_per_sheet,
                max_cols_per_sheet,
                include_display_values
            )
            
            # Step 2: Compress to markdown
            markdown = self._compress_to_markdown()
            
            # Step 3: Chunk markdown
            chunks, chunk_info = await self._chunk_markdown(markdown)
            
            # Step 4: Save outputs if output directory is provided
            if output_dir:
                self._save_outputs(output_dir, markdown)
                
            logger.info("Successfully processed workbook")
            return self.metadata, markdown, chunks, chunk_info
            
        except Exception as e:
            logger.error(f"Failed to process workbook: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def _extract_metadata(
        self,
        max_rows_per_sheet: int,
        max_cols_per_sheet: int,
        include_display_values: bool
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Extract metadata from the workbook."""
        try:
            logger.info("Extracting metadata from workbook...")
            
            # Extract metadata using the extractor
            self.metadata, self.display_values = self.extractor.extract_workbook_metadata(
                workbook_path=self.workbook_path,
                max_rows_per_sheet=max_rows_per_sheet,
                max_cols_per_sheet=max_cols_per_sheet,
                include_display_values=include_display_values
            )
            
            logger.info(f"Extracted metadata for {len(self.metadata.get('sheets', []))} sheets")
            return self.metadata, self.display_values
            
        except Exception as e:
            logger.error(f"Error during metadata extraction: {str(e)}")
            raise


    def _extract_metadata_chunks(
        self,
        rows_per_chunk: int = 10,
        max_cols_per_sheet: int = 50,
        include_dependencies: bool = True,
        include_empty_chunks: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Extract metadata from the workbook as an array of chunk objects.
        
        Args:
            rows_per_chunk: Number of rows per chunk (default 10)
            max_cols_per_sheet: Maximum columns to extract per sheet
            include_dependencies: Whether to include dependency analysis
            include_empty_chunks: Whether to include chunks with no data
            
        Returns:
            List of metadata dictionaries, one per chunk
        """
        try:
            logger.info(f"Extracting metadata chunks from workbook (rows per chunk: {rows_per_chunk})...")
            
            # Extract metadata chunks using the extractor
            self.metadata_chunks = self.extractor.extract_workbook_metadata_chunks(
                workbook_path=self.workbook_path,
                rows_per_chunk=rows_per_chunk,
                max_cols_per_sheet=max_cols_per_sheet,
                include_dependencies=include_dependencies,
                include_empty_chunks=include_empty_chunks
            )
            
            # Log extraction summary
            total_chunks = len(self.metadata_chunks)
            sheets_processed = len(set(chunk['sheetName'] for chunk in self.metadata_chunks if 'sheetName' in chunk))
            total_rows = sum(chunk.get('rowCount', 0) for chunk in self.metadata_chunks)
            
            logger.info(f"Extracted {total_chunks} chunks from {sheets_processed} sheets ({total_rows} total rows)")
            
            # Add chunk statistics
            for i, chunk in enumerate(self.metadata_chunks):
                if 'error' not in chunk:
                    cell_count = sum(
                        1 for row in chunk.get('cellData', [])
                        for cell in row
                        if cell.get('value') is not None or cell.get('formula')
                    )
                    chunk['cellCount'] = cell_count
                    chunk['chunkNumber'] = i + 1
                    chunk['totalChunks'] = total_chunks
            
            return self.metadata_chunks
            
        except Exception as e:
            logger.error(f"Error during metadata chunk extraction: {str(e)}")
            raise

    def _compress_to_markdown(self) -> str:
        """Compress the extracted metadata to markdown format."""
        try:
            logger.info("Compressing metadata to markdown...")
            
            if not self.metadata:
                raise ValueError("No metadata available to compress")
                
            # Compress to markdown
            markdown = self.compressor.compress_to_markdown(
                (self.metadata, self.display_values)
            )
            
            logger.info("Successfully compressed metadata to markdown")
            return markdown
            
        except Exception as e:
            logger.error(f"Error during markdown compression: {str(e)}")
            raise


    def _compress_chunks_to_text(self) -> List[str]:
        """
        Compress the extracted metadata chunks to natural language text format.
        
        Returns:
            List[str]: Array of compressed text strings, one per chunk
        """
        try:
            logger.info("Compressing metadata chunks to text...")
            
            if not hasattr(self, 'metadata_chunks') or not self.metadata_chunks:
                raise ValueError("No metadata chunks available to compress")
            
            # Compress chunks to text array
            compressed_texts = self.text_compressor.compress_chunks(self.metadata_chunks)
            
            logger.info(f"Successfully compressed {len(compressed_texts)} chunks to text")
            
            # Log summary statistics
            total_chars = sum(len(text) for text in compressed_texts)
            avg_chars = total_chars / len(compressed_texts) if compressed_texts else 0
            logger.info(f"Total characters: {total_chars}, Average per chunk: {avg_chars:.0f}")
            
            return compressed_texts
            
        except Exception as e:
            logger.error(f"Error during chunk compression: {str(e)}")
            raise

    async def _chunk_markdown(self, markdown: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Chunk the markdown content into strings not exceeding 18K LLM tokens each."""
        try:
            logger.info("Chunking markdown content...")
            
            if not markdown:
                raise ValueError("No markdown content to chunk")
                
            # Chunk the markdown content using the chunker instance
            chunks = await self.chunker.chunk_metadata(markdown)
            chunk_info = await self.chunker.get_chunk_info(chunks)
            
            logger.info(f"Successfully chunked markdown content into {len(chunks)} chunks")
            return chunks, chunk_info
            
        except Exception as e:
            logger.error(f"Error during markdown chunking: {str(e)}")
            raise
    
    def _save_outputs(self, output_dir: str, markdown: str) -> None:
        """Save the extracted metadata and markdown to files."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(self.workbook_path))[0]
            
            # Save metadata as JSON
            metadata_path = os.path.join(output_dir, f"{base_name}_metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": self.metadata,
                    "displayValues": self.display_values
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved metadata to: {metadata_path}")
            
            # Save markdown
            markdown_path = os.path.join(output_dir, f"{base_name}.md")
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
            logger.info(f"Saved markdown to: {markdown_path}")
            
        except Exception as e:
            logger.error(f"Error saving outputs: {str(e)}")
            raise

    @staticmethod
    async def process_file(
        file_path: str,
        output_dir: Optional[str] = None,
        max_rows: int = 100,
        max_cols: int = 50
    ) -> Tuple[Dict[str, Any], str, List[str], List[Dict[str, Any]]]:
        """
        Static method to process a single file.
        
        Args:
            file_path: Path to the Excel file
            output_dir: Directory to save output files (optional)
            max_rows: Maximum rows per sheet to process
            max_cols: Maximum columns per sheet to process
            
        Returns:
            Tuple of (metadata_dict, markdown_string, chunks_list, chunk_info_list)
        """
        try:
            processor = ExcelMetadataProcessor(file_path)
            return await processor.process_workbook(
                output_dir=output_dir,
                max_rows_per_sheet=max_rows,
                max_cols_per_sheet=max_cols
            )
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise

async def main():
    """Command-line interface for the Excel metadata processor."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract and compress Excel workbook metadata to markdown with chunking'
    )
    parser.add_argument('file_path', help='Path to the Excel file')
    parser.add_argument('-o', '--output-dir', help='Output directory for results')
    parser.add_argument('--max-rows', type=int, default=100, 
                       help='Maximum rows per sheet to process')
    parser.add_argument('--max-cols', type=int, default=50,
                       help='Maximum columns per sheet to process')
    
    args = parser.parse_args()
    
    try:
        processor = ExcelMetadataProcessor(args.file_path)
        metadata, markdown, chunks, chunk_info = await processor.process_workbook(
            output_dir=args.output_dir,
            max_rows_per_sheet=args.max_rows,
            max_cols_per_sheet=args.max_cols
        )
        print(f"Successfully processed {args.file_path}")
        print(f"Extracted {len(metadata.get('sheets', []))} sheets")
        print(f"Created {len(chunks)} chunks")
        
    except Exception as e:
        logger.error(f"Failed to process file: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())