import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging

class JsonTextCompressor:
    """
    Converts Excel metadata JSON into natural language text format optimized
    for embedding models, with explicit relationship descriptions and semantic context.
    """
    
    def __init__(self, max_cells_per_sheet: int = 100000, max_cell_length: int = 200):
        """
        Initialize the text compressor.
        
        Args:
            max_cells_per_sheet: Maximum number of cells to process per sheet
            max_cell_length: Maximum length of cell content to include
        """
        self.max_cells_per_sheet = max_cells_per_sheet
        self.max_cell_length = max_cell_length
        self.logger = logging.getLogger(__name__)
    
    def compress_workbook(self, metadata: Dict[str, Any]) -> str:
        """
        Convert workbook metadata to natural language text optimized for embeddings.
        
        Args:
            metadata: Dictionary containing Excel workbook metadata
            
        Returns:
            str: Natural language representation of the workbook
        """
        try:
            if not metadata:
                return "No metadata available"
                
            lines = []
            
            # Workbook information in natural language
            workbook_name = metadata.get('workbookName', 'Untitled')
            lines.append(f"# Excel Workbook: {workbook_name}")
            lines.append(f"This workbook is located at: {metadata.get('workbookPath', 'Unknown location')}")
            lines.append(f"It contains {len(metadata.get('sheetNames', []))} worksheets: {', '.join(metadata.get('sheetNames', []))}")
            lines.append(f"The currently active sheet is: {metadata.get('activeSheet', 'None')}")
            lines.append("")
            
            # Process each sheet
            for sheet in metadata.get('sheets', []):
                lines.extend(self._process_sheet(sheet))
                
            # Add dependency summary if available
            if 'dependencySummary' in metadata:
                lines.extend(self._process_dependency_summary(metadata['dependencySummary']))
                
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error compressing workbook: {str(e)}")
            return f"Error compressing metadata: {str(e)}"
    
    def _process_sheet(self, sheet: Dict[str, Any]) -> List[str]:
        """Process a single sheet into natural language text."""
        lines = []
        
        try:
            sheet_name = sheet.get('name', 'Untitled')
            # Sheet header in natural language
            lines.append(f"## Worksheet: {sheet_name}")
            
            # Handle error case
            if 'error' in sheet:
                lines.append(f"This worksheet encountered an error during extraction: {sheet['error']}")
                lines.append("")
                return lines
                
            # Sheet metadata in natural language
            row_count = sheet.get('rowCount', 0)
            col_count = sheet.get('columnCount', 0)
            extracted_rows = sheet.get('extractedRowCount', 0)
            extracted_cols = sheet.get('extractedColumnCount', 0)
            
            lines.append(f"This worksheet has {row_count} rows and {col_count} columns of data.")
            lines.append(f"For analysis, we extracted {extracted_rows} rows and {extracted_cols} columns.")
            
            # Process tables if any
            if sheet.get('tables'):
                lines.append("")
                lines.append("### Tables in this worksheet:")
                for table in sheet['tables']:
                    table_name = table.get('name', 'unnamed')
                    table_range = table.get('range', 'unknown range')
                    col_count = len(table.get('columns', []))
                    lines.append(f"- Table '{table_name}' spans the range {table_range} and contains {col_count} columns")
                    if table.get('columns'):
                        col_names = [col.get('name', '') for col in table['columns']]
                        lines.append(f"  The columns are: {', '.join(col_names)}")
            
            # Process cell data
            if 'cellData' in sheet:
                lines.append("")
                lines.append("### Cell Data and Relationships:")
                cell_lines = self._process_cell_data(sheet['cellData'], sheet_name)
                lines.extend(cell_lines)
            
            lines.append("")  # Add spacing between sheets
            return lines
            
        except Exception as e:
            self.logger.error(f"Error processing sheet {sheet.get('name', 'unknown')}: {str(e)}")
            return [f"Error processing sheet: {str(e)}"]
    
    def _process_cell_data(self, cell_data: List[List[Dict[str, Any]]], sheet_name: str) -> List[str]:
        """Process cell data into natural language text."""
        lines = []
        cell_count = 0
        
        # Group cells by row for context
        row_contexts = {}
        
        try:
            # First pass: collect row context
            for row_idx, row in enumerate(cell_data):
                row_labels = []
                row_values = []
                for cell in row:
                    if cell.get('value') is not None:
                        if isinstance(cell['value'], str) and not cell['value'].isdigit():
                            row_labels.append((cell['address'], cell['value']))
                        else:
                            row_values.append((cell['address'], cell['value']))
                
                if row_labels:
                    row_contexts[row_idx + 1] = row_labels[0][1] if row_labels else None
            
            # Second pass: generate natural language descriptions
            for row_idx, row in enumerate(cell_data):
                for col_idx, cell in enumerate(row):
                    if cell_count >= self.max_cells_per_sheet:
                        lines.append(f"\n... (showing first {self.max_cells_per_sheet} cells for embedding)")
                        return lines
                    
                    # Skip empty cells and cells with only formatting
                    if not cell.get('value') and not cell.get('formula'):
                        continue
                        
                    cell_text = self._format_cell_natural_language(
                        cell, sheet_name, row_contexts, row_idx, col_idx, cell_data
                    )
                    if cell_text:
                        lines.append(cell_text)
                        lines.append("")  # Add spacing between cells
                        cell_count += 1
                        
        except Exception as e:
            self.logger.error(f"Error processing cell data: {str(e)}")
            lines.append(f"Error processing cells: {str(e)}")
            
        return lines
    
    def _format_cell_natural_language(
        self, 
        cell: Dict[str, Any], 
        sheet_name: str,
        row_contexts: Dict[int, str],
        row_idx: int,
        col_idx: int,
        all_cells: List[List[Dict[str, Any]]]
    ) -> str:
        """Format a single cell's information in natural language."""
        try:
            if not cell or 'error' in cell:
                return ""
            
            parts = []
            address = cell.get('address', '?')
            
            # Start with cell identification and context
            cell_label = self._get_cell_label(cell, row_contexts.get(row_idx + 1))
            if cell_label:
                parts.append(f"Cell {address} ({cell_label}) in worksheet '{sheet_name}':")
            else:
                parts.append(f"Cell {address} in worksheet '{sheet_name}':")
            
            # Value description
            if 'value' in cell and cell['value'] is not None:
                value = str(cell['value'])
                if len(value) > self.max_cell_length:
                    value = value[:self.max_cell_length] + "..."
                
                # Add semantic description based on value type
                if isinstance(cell['value'], (int, float)):
                    parts.append(f"This cell contains the numeric value {value}")
                elif cell['value'] and str(cell['value']).startswith('='):
                    parts.append(f"This cell contains a formula")
                else:
                    parts.append(f"This cell contains the text '{value}'")
            
            # Formula description
            if cell.get('formula'):
                formula = cell['formula']
                if len(formula) > self.max_cell_length:
                    formula = formula[:self.max_cell_length] + "..."
                
                formula_type = self._identify_formula_type(formula)
                parts.append(f"The cell calculates its value using the {formula_type} formula: {formula}")
            
            # Dependencies - using explicit descriptive language
            if cell.get('directPrecedents'):
                precedents = cell['directPrecedents']
                precedent_count = len(precedents)
                
                if precedent_count == 1:
                    parts.append(f"This cell's formula depends on this precedent cell: {precedents[0]}")
                else:
                    parts.append(f"This cell's formula depends on these {precedent_count} precedent cells: {', '.join(precedents[:10])}")
                    if precedent_count > 10:
                        parts.append(f"  ... and {precedent_count - 10} more precedent cells")
            
            # Dependents - using explicit descriptive language
            if cell.get('directDependents'):
                dependents = cell['directDependents']
                dependent_count = len(dependents)
                
                if dependent_count == 1:
                    parts.append(f"This cell's value influences this dependent cell: {dependents[0]}")
                else:
                    parts.append(f"This cell's value influences these {dependent_count} dependent cells: {', '.join(dependents[:10])}")
                    if dependent_count > 10:
                        parts.append(f"  ... and {dependent_count - 10} more dependent cells")
            
            # Add connection summary
            total_connections = cell.get('totalConnections', 0)
            if total_connections > 0:
                parts.append(f"In total, this cell has {total_connections} formula connections in the workbook")
            
            # Adjacent cell context
            adjacent_context = self._get_adjacent_context(row_idx, col_idx, all_cells)
            if adjacent_context:
                parts.append(f"Adjacent cells: {adjacent_context}")
            
            # Formatting highlights (only significant ones)
            fmt_desc = self._get_formatting_description(cell.get('formatting', {}))
            if fmt_desc:
                parts.append(f"Cell formatting: {fmt_desc}")
            
            # Row context
            if row_contexts.get(row_idx + 1):
                parts.append(f"This cell is in the row for: {row_contexts[row_idx + 1]}")
            
            return "\n".join(parts)
            
        except Exception as e:
            self.logger.error(f"Error formatting cell: {str(e)}")
            return ""
    
    def _get_cell_label(self, cell: Dict[str, Any], row_context: Optional[str]) -> Optional[str]:
        """Determine a semantic label for the cell based on its content and context."""
        value = cell.get('value')
        if not value:
            return None
            
        # If it's a string that's not a number, it might be a label
        if isinstance(value, str) and not value.replace('.', '').replace('-', '').isdigit():
            return value[:50]  # Truncate long labels
            
        # If we have row context and this is a number, combine them
        if row_context and isinstance(value, (int, float)):
            return f"{row_context} value"
            
        return None
    
    def _identify_formula_type(self, formula: str) -> str:
        """Identify the type of formula for better description."""
        formula_upper = formula.upper()
        
        if 'SUM(' in formula_upper:
            return "SUM aggregation"
        elif 'AVERAGE(' in formula_upper or 'AVG(' in formula_upper:
            return "AVERAGE calculation"
        elif 'COUNT(' in formula_upper:
            return "COUNT"
        elif 'IF(' in formula_upper:
            return "conditional IF"
        elif 'VLOOKUP(' in formula_upper or 'HLOOKUP(' in formula_upper:
            return "LOOKUP"
        elif 'INDEX(' in formula_upper and 'MATCH(' in formula_upper:
            return "INDEX-MATCH lookup"
        elif any(op in formula for op in ['+', '-', '*', '/']):
            return "arithmetic"
        else:
            return "custom"
    
    def _get_adjacent_context(self, row_idx: int, col_idx: int, all_cells: List[List[Dict[str, Any]]]) -> str:
        """Get context from adjacent cells."""
        contexts = []
        
        try:
            # Check left cell (usually labels)
            if col_idx > 0 and row_idx < len(all_cells):
                left_cell = all_cells[row_idx][col_idx - 1]
                if left_cell.get('value') and isinstance(left_cell['value'], str):
                    contexts.append(f"left cell {left_cell['address']} contains label '{left_cell['value']}'")
            
            # Check top cell (usually headers)
            if row_idx > 0 and row_idx - 1 < len(all_cells) and col_idx < len(all_cells[row_idx - 1]):
                top_cell = all_cells[row_idx - 1][col_idx]
                if top_cell.get('value'):
                    contexts.append(f"top cell {top_cell['address']} contains '{str(top_cell['value'])}'")
            
            # Check right cell (for comparison)
            if col_idx < len(all_cells[row_idx]) - 1:
                right_cell = all_cells[row_idx][col_idx + 1]
                if right_cell.get('value'):
                    contexts.append(f"right cell {right_cell['address']} contains '{str(right_cell['value'])}'")
                    
        except Exception:
            pass
            
        return "; ".join(contexts) if contexts else ""
    
    def _get_formatting_description(self, formatting: Dict[str, Any]) -> str:
        """Get natural language description of significant formatting."""
        if not formatting:
            return ""
            
        fmt_parts = []
        
        # Font formatting
        font = formatting.get('font', {})
        if font.get('bold'):
            fmt_parts.append("bold text")
        if font.get('italic'):
            fmt_parts.append("italic text")
        if font.get('color') and font['color'] not in ['#000000', None, 'auto']:
            fmt_parts.append(f"colored text ({font['color']})")
            
        # Fill/background
        fill = formatting.get('fill', {})
        if fill.get('startColor') and fill['startColor'] not in ['#FFFFFF', None]:
            fmt_parts.append(f"background color {fill['startColor']}")
            
        # Number format
        num_format = formatting.get('numberFormat')
        if num_format and num_format != 'General':
            if '$' in str(num_format):
                fmt_parts.append("currency format")
            elif '%' in str(num_format):
                fmt_parts.append("percentage format")
            elif '0.00' in str(num_format):
                fmt_parts.append("decimal format")
                
        return ", ".join(fmt_parts) if fmt_parts else ""
    
    def _process_dependency_summary(self, summary: Dict[str, Any]) -> List[str]:
        """Process dependency summary into natural language."""
        lines = []
        
        lines.append("")
        lines.append("## Workbook Dependency Analysis:")
        lines.append(f"This workbook contains {summary.get('totalCells', 0)} cells with data")
        lines.append(f"Of these, {summary.get('formulaCells', 0)} cells contain formulas that depend on other cells")
        lines.append(f"There are {summary.get('valueCells', 0)} cells with direct values (no formulas)")
        lines.append(f"The total number of cell-to-cell dependencies is {summary.get('totalDependencies', 0)}")
        
        # Most connected cells
        if summary.get('mostConnectedCells'):
            lines.append("")
            lines.append("### Most interconnected cells (highest number of connections):")
            for item in summary['mostConnectedCells'][:5]:
                lines.append(f"- Cell {item['cell']} has {item['connections']} total connections to other cells")
        
        # Most complex formulas
        if summary.get('mostComplexFormulas'):
            lines.append("")
            lines.append("### Cells with the most complex formulas (most precedents):")
            for item in summary['mostComplexFormulas'][:5]:
                lines.append(f"- Cell {item['cell']} depends on {item['precedents']} other cells")
        
        # Most referenced cells
        if summary.get('mostReferencedCells'):
            lines.append("")
            lines.append("### Most frequently referenced cells (most dependents):")
            for item in summary['mostReferencedCells'][:5]:
                lines.append(f"- Cell {item['cell']} is used by {item['dependents']} other cells")
        
        return lines
    
    def compress_from_file(self, json_file: str) -> str:
        """
        Load JSON from file and compress to natural language text.
        
        Args:
            json_file: Path to JSON file containing metadata
            
        Returns:
            str: Natural language text representation
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both direct metadata and wrapped format
            metadata = data.get('metadata', data)
            return self.compress_workbook(metadata)
            
        except Exception as e:
            self.logger.error(f"Error processing file {json_file}: {str(e)}")
            return f"Error processing file {json_file}: {str(e)}"
    
    def compress_json_str(self, json_str: str) -> str:
        """
        Compress JSON string to natural language text.
        
        Args:
            json_str: JSON string containing metadata
            
        Returns:
            str: Natural language text representation
        """
        try:
            data = json.loads(json_str)
            # Handle both direct metadata and wrapped format
            metadata = data.get('metadata', data)
            return self.compress_workbook(metadata)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON string: {str(e)}")
            return "Invalid JSON string"
        except Exception as e:
            self.logger.error(f"Error processing JSON: {str(e)}")
            return f"Error processing JSON: {str(e)}"
    
    def compress_chunks(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """
        Convert an array of chunk metadata objects into natural language text strings.
        
        Args:
            chunks: List of chunk metadata dictionaries from extract_workbook_metadata_chunks
            
        Returns:
            List[str]: Array of natural language text representations, one per chunk
        """
        try:
            if not chunks:
                return ["No chunks available"]
                
            compressed_chunks = []
            
            for chunk_idx, chunk in enumerate(chunks):
                try:
                    # Compress individual chunk
                    chunk_text = self._compress_single_chunk(chunk, chunk_idx, len(chunks))
                    compressed_chunks.append(chunk_text)
                    
                except Exception as e:
                    self.logger.error(f"Error compressing chunk {chunk_idx}: {str(e)}")
                    compressed_chunks.append(f"Error compressing chunk {chunk_idx}: {str(e)}")
                    
            return compressed_chunks
            
        except Exception as e:
            self.logger.error(f"Error compressing chunks: {str(e)}")
            return [f"Error compressing chunks: {str(e)}"]

    def _compress_single_chunk(self, chunk: Dict[str, Any], chunk_idx: int, total_chunks: int) -> str:
        """
        Compress a single chunk metadata object into natural language text.
        
        Args:
            chunk: Single chunk metadata dictionary
            chunk_idx: Index of this chunk in the array
            total_chunks: Total number of chunks
            
        Returns:
            str: Natural language representation of the chunk
        """
        lines = []
        
        try:
            # Handle error chunks
            if 'error' in chunk:
                lines.append(f"# Chunk Error")
                lines.append(f"Workbook: {chunk.get('workbookName', 'Unknown')}")
                lines.append(f"Sheet: {chunk.get('sheetName', 'Unknown')}")
                lines.append(f"Error: {chunk['error']}")
                return "\n".join(lines)
            
            # Chunk header with context
            workbook_name = chunk.get('workbookName', 'Unknown')
            sheet_name = chunk.get('sheetName', 'Unknown') 
            start_row = chunk.get('startRow', 0)
            end_row = chunk.get('endRow', 0)
            
            lines.append(f"# Excel Data Chunk {chunk_idx + 1} of {total_chunks}")
            lines.append(f"Workbook: {workbook_name}")
            lines.append(f"Worksheet: {sheet_name}")
            lines.append(f"Row Range: {start_row} to {end_row} ({chunk.get('rowCount', 0)} rows)")
            lines.append("")
            
            # Process tables if any
            if chunk.get('tables'):
                lines.append("## Tables in this chunk:")
                for table in chunk['tables']:
                    table_name = table.get('name', 'unnamed')
                    table_range = table.get('range', 'unknown range')
                    if table.get('intersectsChunk'):
                        lines.append(f"- Table '{table_name}' (range: {table_range}) intersects with this chunk")
                    else:
                        lines.append(f"- Table '{table_name}' spans the range {table_range}")
                        
                    if table.get('columns'):
                        col_names = [col.get('name', '') for col in table['columns']]
                        lines.append(f"  Columns: {', '.join(col_names)}")
                lines.append("")
            
            # Process cell data
            if chunk.get('cellData'):
                lines.append("## Cell Data and Relationships:")
                
                # Build row contexts for this chunk
                row_contexts = self._build_chunk_row_contexts(chunk['cellData'], start_row)
                
                # Process cells
                cell_lines = self._process_chunk_cells(
                    chunk['cellData'], 
                    sheet_name,
                    row_contexts,
                    start_row
                )
                lines.extend(cell_lines)
            
            # Add chunk-level dependency summary if available
            if chunk.get('dependencySummary'):
                lines.extend(self._process_chunk_dependency_summary(chunk['dependencySummary']))
                
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error compressing single chunk: {str(e)}")
            return f"Error compressing chunk: {str(e)}"

    def _build_chunk_row_contexts(self, cell_data: List[List[Dict[str, Any]]], start_row: int) -> Dict[int, str]:
        """Build row contexts for a chunk's cells."""
        row_contexts = {}
        
        try:
            for row_idx, row in enumerate(cell_data):
                actual_row_num = start_row + row_idx
                row_labels = []
                
                for cell in row:
                    if cell.get('value') is not None:
                        if isinstance(cell['value'], str) and not cell['value'].isdigit():
                            row_labels.append((cell['address'], cell['value']))
                
                if row_labels:
                    row_contexts[actual_row_num] = row_labels[0][1] if row_labels else None
                    
        except Exception as e:
            self.logger.error(f"Error building row contexts: {str(e)}")
            
        return row_contexts

    def _process_chunk_cells(
        self, 
        cell_data: List[List[Dict[str, Any]]], 
        sheet_name: str,
        row_contexts: Dict[int, str],
        start_row: int
    ) -> List[str]:
        """Process cells in a chunk into natural language text."""
        lines = []
        cell_count = 0
        
        try:
            for row_idx, row in enumerate(cell_data):
                actual_row_num = start_row + row_idx
                
                for col_idx, cell in enumerate(row):
                    # Skip empty cells
                    if not cell.get('value') and not cell.get('formula'):
                        continue
                    
                    # Reuse existing cell formatting logic with chunk context
                    cell_text = self._format_cell_natural_language(
                        cell, 
                        sheet_name,
                        row_contexts,
                        row_idx,
                        col_idx,
                        cell_data
                    )
                    
                    if cell_text:
                        lines.append(cell_text)
                        lines.append("")  # Add spacing
                        cell_count += 1
                        
                        # Limit cells per chunk if needed
                        if cell_count >= self.max_cells_per_sheet:
                            lines.append(f"... (showing first {self.max_cells_per_sheet} cells in this chunk)")
                            return lines
                            
        except Exception as e:
            self.logger.error(f"Error processing chunk cells: {str(e)}")
            lines.append(f"Error processing cells: {str(e)}")
            
        return lines

    def _process_chunk_dependency_summary(self, summary: Dict[str, Any]) -> List[str]:
        """Process chunk-level dependency summary."""
        lines = []
        
        lines.append("")
        lines.append("### Chunk Dependency Summary:")
        
        if summary.get('totalPrecedents', 0) > 0:
            lines.append(f"Cells in this chunk depend on {summary['totalPrecedents']} external cells")
            
        if summary.get('totalDependents', 0) > 0:
            lines.append(f"Cells in this chunk influence {summary['totalDependents']} external cells")
            
        if summary.get('internalDependencies', 0) > 0:
            lines.append(f"There are {summary['internalDependencies']} dependencies within this chunk")
            
        if summary.get('externalDependencies', 0) > 0:
            lines.append(f"There are {summary['externalDependencies']} dependencies to cells outside this chunk")
            
        # List some external connections
        if summary.get('externalPrecedents'):
            lines.append("")
            lines.append("Key external cells this chunk depends on:")
            for ext_cell in summary['externalPrecedents'][:5]:
                lines.append(f"- {ext_cell}")
                
        if summary.get('externalDependents'):
            lines.append("")
            lines.append("Key external cells that depend on this chunk:")
            for ext_cell in summary['externalDependents'][:5]:
                lines.append(f"- {ext_cell}")
        
        lines.append("")
        return lines

    # Convenience method for compressing chunks from file
    def compress_chunks_from_file(self, json_file: str) -> List[str]:
        """
        Load chunk array from JSON file and compress to text array.
        
        Args:
            json_file: Path to JSON file containing chunk array
            
        Returns:
            List[str]: Array of natural language text representations
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different possible formats
            if isinstance(data, list):
                chunks = data
            elif isinstance(data, dict) and 'chunks' in data:
                chunks = data['chunks']
            else:
                raise ValueError("Invalid JSON format - expected array of chunks")
                
            return self.compress_chunks(chunks)
            
        except Exception as e:
            self.logger.error(f"Error processing file {json_file}: {str(e)}")
            return [f"Error processing file {json_file}: {str(e)}"]