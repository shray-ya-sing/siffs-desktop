import re
from typing import List, Dict, Tuple, Optional
import logging

class SpreadsheetTextChunker:
    """
    Chunks the natural language text output from JsonTextCompressor into 
    manageable pieces, preserving workbook and worksheet context.
    """
    
    def __init__(self, cells_per_chunk: int = 10, include_summary_chunks: bool = True):
        """
        Initialize the chunker.
        
        Args:
            cells_per_chunk: Number of cell descriptions per chunk (default 10)
            include_summary_chunks: Whether to include dependency summary as separate chunks
        """
        self.cells_per_chunk = cells_per_chunk
        self.include_summary_chunks = include_summary_chunks
        self.logger = logging.getLogger(__name__)
    
    def chunk_workbook_text(self, text: str) -> List[Dict[str, str]]:
        """
        Break workbook text into chunks with context headers.
        
        Args:
            text: Natural language text from JsonTextCompressor
            
        Returns:
            List of dictionaries with 'text' and 'metadata' for each chunk
        """
        chunks = []
        
        try:
            # Parse the workbook structure
            workbook_name, worksheets = self._parse_workbook_structure(text)
            
            # Process each worksheet
            for worksheet_name, worksheet_content in worksheets:
                worksheet_chunks = self._chunk_worksheet(
                    workbook_name, 
                    worksheet_name, 
                    worksheet_content
                )
                chunks.extend(worksheet_chunks)
            
            # Add dependency summary chunks if present and requested
            if self.include_summary_chunks:
                summary_chunks = self._extract_summary_chunks(text, workbook_name)
                chunks.extend(summary_chunks)
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error chunking workbook text: {str(e)}")
            return [{
                'text': f"Error chunking text: {str(e)}",
                'metadata': {'error': True}
            }]
    
    def _parse_workbook_structure(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Parse the text to extract workbook name and worksheet sections.
        
        Returns:
            Tuple of (workbook_name, [(worksheet_name, worksheet_content), ...])
        """
        lines = text.split('\n')
        workbook_name = "Unknown Workbook"
        worksheets = []
        current_worksheet = None
        current_content = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Extract workbook name
            if line.startswith('# Excel Workbook:'):
                workbook_name = line.replace('# Excel Workbook:', '').strip()
            
            # Detect new worksheet
            elif line.startswith('## Worksheet:'):
                # Save previous worksheet if exists
                if current_worksheet:
                    worksheets.append((current_worksheet, '\n'.join(current_content)))
                
                # Start new worksheet
                current_worksheet = line.replace('## Worksheet:', '').strip()
                current_content = []
            
            # Detect end of worksheets section (dependency summary starts)
            elif line.startswith('## Workbook Dependency Analysis:'):
                # Save current worksheet and stop processing worksheets
                if current_worksheet:
                    worksheets.append((current_worksheet, '\n'.join(current_content)))
                break
            
            # Collect worksheet content
            elif current_worksheet:
                current_content.append(lines[i])  # Keep original line with spacing
            
            i += 1
        
        # Don't forget the last worksheet if we reached end of text
        if current_worksheet and current_content:
            worksheets.append((current_worksheet, '\n'.join(current_content)))
        
        return workbook_name, worksheets
    
    def _chunk_worksheet(
        self, 
        workbook_name: str, 
        worksheet_name: str, 
        content: str
    ) -> List[Dict[str, str]]:
        """
        Chunk a single worksheet's content into manageable pieces.
        """
        chunks = []
        
        # Extract cell descriptions from the content
        cell_blocks = self._extract_cell_blocks(content)
        
        # Group cells into chunks
        for i in range(0, len(cell_blocks), self.cells_per_chunk):
            chunk_cells = cell_blocks[i:i + self.cells_per_chunk]
            
            # Create chunk header
            header = self._create_chunk_header(
                workbook_name, 
                worksheet_name, 
                i // self.cells_per_chunk + 1,
                len(cell_blocks)
            )
            
            # Combine header with cell descriptions
            chunk_text = header + '\n\n' + '\n\n'.join(chunk_cells)
            
            # Extract cell addresses for metadata
            cell_addresses = self._extract_cell_addresses(chunk_cells)
            
            chunks.append({
                'text': chunk_text,
                'metadata': {
                    'workbook': workbook_name,
                    'worksheet': worksheet_name,
                    'chunk_type': 'cell_data',
                    'chunk_index': i // self.cells_per_chunk + 1,
                    'cell_count': len(chunk_cells),
                    'cell_addresses': cell_addresses,
                    'start_position': i,
                    'end_position': min(i + self.cells_per_chunk, len(cell_blocks))
                }
            })
        
        # If no cell blocks found but we have content, create a single chunk
        if not cell_blocks and content.strip():
            chunks.append({
                'text': self._create_chunk_header(workbook_name, worksheet_name, 1, 0) + '\n\n' + content,
                'metadata': {
                    'workbook': workbook_name,
                    'worksheet': worksheet_name,
                    'chunk_type': 'worksheet_info',
                    'chunk_index': 1
                }
            })
        
        return chunks
    
    def _extract_cell_blocks(self, content: str) -> List[str]:
        """
        Extract individual cell description blocks from worksheet content.
        Cell blocks are separated by double newlines in the compressed format.
        """
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Skip until we find "### Cell Data and Relationships:" or similar
        cell_section_start = content.find("### Cell Data and Relationships:")
        if cell_section_start == -1:
            # Try alternative markers
            cell_section_start = content.find("Cell ")
            if cell_section_start == -1:
                return []
        
        # Get content after the cell data header
        if "### Cell Data and Relationships:" in content:
            cell_content = content[cell_section_start + len("### Cell Data and Relationships:"):].strip()
        else:
            cell_content = content[cell_section_start:]
        
        # Split by double newlines to get cell blocks
        # Each cell description is separated by a blank line
        blocks = cell_content.split('\n\n')
        
        # Filter out empty blocks and clean up
        cell_blocks = []
        current_block = []
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
                
            # Check if this is a cell description start
            if re.match(r'^Cell [A-Z]+\d+', block):
                # Save previous block if exists
                if current_block:
                    cell_blocks.append('\n'.join(current_block))
                current_block = [block]
            elif current_block:
                # Continue building current cell block
                current_block.append(block)
            
        # Don't forget the last block
        if current_block:
            cell_blocks.append('\n'.join(current_block))
        
        return cell_blocks
    
    def _create_chunk_header(
        self, 
        workbook_name: str, 
        worksheet_name: str, 
        chunk_number: int,
        total_cells: int
    ) -> str:
        """
        Create a descriptive header for each chunk.
        """
        header = f"""=== CHUNK {chunk_number} ===
Workbook: {workbook_name}
Worksheet: {worksheet_name}
Content: Cell descriptions and relationships (chunk {chunk_number})"""
        
        if total_cells > 0:
            header += f"\nTotal cells in worksheet: {total_cells}"
        
        header += "\n" + "=" * 50
        
        return header
    
    def _extract_cell_addresses(self, cell_blocks: List[str]) -> List[str]:
        """
        Extract cell addresses from cell description blocks.
        """
        addresses = []
        
        for block in cell_blocks:
            # Look for pattern "Cell A1" or "Cell A1 (label)"
            match = re.search(r'Cell ([A-Z]+\d+)', block)
            if match:
                addresses.append(match.group(1))
        
        return addresses
    
    def _extract_summary_chunks(self, text: str, workbook_name: str) -> List[Dict[str, str]]:
        """
        Extract dependency summary as separate chunks if present.
        """
        chunks = []
        
        # Find dependency analysis section
        summary_start = text.find("## Workbook Dependency Analysis:")
        if summary_start == -1:
            return chunks
        
        summary_content = text[summary_start:]
        
        # Split summary into logical sections
        sections = []
        current_section = []
        
        for line in summary_content.split('\n'):
            if line.startswith('###'):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        # Add last section
        if current_section:
            sections.append('\n'.join(current_section))
        
        # Create chunks for each summary section
        for i, section in enumerate(sections):
            if not section.strip():
                continue
                
            header = f"""=== DEPENDENCY ANALYSIS CHUNK {i + 1} ===
Workbook: {workbook_name}
Content: Workbook dependency analysis
{"=" * 50}"""
            
            chunks.append({
                'text': header + '\n\n' + section,
                'metadata': {
                    'workbook': workbook_name,
                    'worksheet': 'All Worksheets',
                    'chunk_type': 'dependency_summary',
                    'chunk_index': i + 1,
                    'summary_section': self._identify_summary_section(section)
                }
            })
        
        return chunks
    
    def _identify_summary_section(self, section: str) -> str:
        """
        Identify what type of summary section this is.
        """
        if "Most interconnected cells" in section:
            return "most_connected_cells"
        elif "most complex formulas" in section:
            return "complex_formulas"
        elif "Most frequently referenced" in section:
            return "most_referenced_cells"
        elif "Workbook Dependency Analysis" in section:
            return "overview"
        else:
            return "other"
    
    def chunk_text_string(self, text: str, chunk_size: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Convenience method to chunk a text string.
        
        Args:
            text: The text to chunk
            chunk_size: Optional override for cells per chunk
            
        Returns:
            List of chunk dictionaries
        """
        if chunk_size:
            original_size = self.cells_per_chunk
            self.cells_per_chunk = chunk_size
            chunks = self.chunk_workbook_text(text)
            self.cells_per_chunk = original_size
            return chunks
        else:
            return self.chunk_workbook_text(text)


# Example usage function
def create_chunks_from_compressed_text(compressed_text: str) -> List[Dict[str, str]]:
    """
    Helper function to create chunks from compressed text.
    
    Args:
        compressed_text: Output from JsonTextCompressor
        
    Returns:
        List of chunks ready for embedding
    """
    chunker = SpreadsheetTextChunker(cells_per_chunk=10)
    chunks = chunker.chunk_workbook_text(compressed_text)
    
    # Print summary
    print(f"Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        meta = chunk['metadata']
        print(f"  Chunk {i+1}: {meta['workbook']} / {meta['worksheet']} - {meta['chunk_type']}")
        if 'cell_addresses' in meta:
            print(f"    Cells: {', '.join(meta['cell_addresses'][:5])}")
            if len(meta['cell_addresses']) > 5:
                print(f"    ... and {len(meta['cell_addresses']) - 5} more")
    
    return chunks