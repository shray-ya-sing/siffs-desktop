"""
PDF content extractor using PyMuPDF and other libraries.
Extracts comprehensive content including text, images, tables, forms, and structure.
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path
import logging
import hashlib

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    print("PyMuPDF imported successfully")
except ImportError as e:
    PYMUPDF_AVAILABLE = False
    print(f"PyMuPDF import failed: {e}")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
    print("pdfplumber imported successfully")
except ImportError as e:
    PDFPLUMBER_AVAILABLE = False
    print(f"pdfplumber import failed: {e}")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
    print("PyPDF2 imported successfully")
except ImportError as e:
    PYPDF2_AVAILABLE = False
    print(f"PyPDF2 import failed: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFContentExtractor:
    """
    Comprehensive PDF content extractor following the PowerPoint pattern.
    Extracts all content types and structures them for LLM consumption.
    """
    
    def __init__(self, pdf_path: Optional[str] = None):
        """
        Initialize the PDF content extractor.
        
        Args:
            pdf_path: Path to the PDF file (optional, can be set later)
        """
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF is required but not installed. Please install with: pip install PyMuPDF")
            
        self.pdf_path = pdf_path
        self.document = None
        self.pdfplumber_pdf = None
        
    def open_document(self, pdf_path: Optional[str] = None) -> None:
        """
        Open the PDF document.
        
        Args:
            pdf_path: Path to the PDF file
        """
        if pdf_path:
            self.pdf_path = pdf_path
            
        if not self.pdf_path:
            raise ValueError("No PDF path specified")
            
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
            
        try:
            self.document = fitz.open(self.pdf_path)
            
            # Also open with pdfplumber if available for better table extraction
            if PDFPLUMBER_AVAILABLE:
                self.pdfplumber_pdf = pdfplumber.open(self.pdf_path)
                
        except Exception as e:
            raise Exception(f"Failed to open PDF: {str(e)}")
    
    def close(self) -> None:
        """Close the document and clean up resources."""
        try:
            if self.document:
                self.document.close()
        except Exception as e:
            logger.warning(f"Warning: Error closing PyMuPDF document: {str(e)}")
        finally:
            self.document = None
            
        try:
            if self.pdfplumber_pdf:
                self.pdfplumber_pdf.close()
        except Exception as e:
            logger.warning(f"Warning: Error closing pdfplumber document: {str(e)}")
        finally:
            self.pdfplumber_pdf = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()
        
    def extract_complete_content(
        self, 
        pdf_path: Optional[str] = None,
        include_images: bool = True,
        include_tables: bool = True,
        include_forms: bool = True,
        ocr_images: bool = False,
        extract_text_blocks: bool = True
    ) -> Dict[str, Any]:
        """
        Extract comprehensive content from the PDF in LLM-friendly format.
        
        Args:
            pdf_path: Path to the PDF file
            include_images: Whether to extract images
            include_tables: Whether to extract tables
            include_forms: Whether to extract form fields
            ocr_images: Whether to run OCR on images
            extract_text_blocks: Whether to extract structured text blocks
            
        Returns:
            Dictionary containing complete PDF content
        """
        if pdf_path or not self.document:
            self.open_document(pdf_path)
            
        try:
            # Get basic document info
            content = {
                "document_info": self._extract_document_metadata(),
                "pages": [],
                "document_summary": {
                    "all_text": "",
                    "key_sections": [],
                    "extracted_data": {
                        "total_tables": 0,
                        "total_images": 0,
                        "total_forms": 0,
                        "total_text_blocks": 0
                    }
                },
                "content_for_llm": {
                    "structured_text": {
                        "title": "",
                        "sections": [],
                        "tables_as_text": [],
                        "image_descriptions": []
                    },
                    "searchable_content": "",
                    "metadata_summary": ""
                }
            }
            
            # Update document info with extraction settings
            content["document_info"]["extraction_settings"] = {
                "include_images": include_images,
                "include_tables": include_tables,
                "include_forms": include_forms,
                "ocr_enabled": ocr_images,
                "extract_text_blocks": extract_text_blocks
            }
            
            all_text_parts = []
            total_tables = 0
            total_images = 0
            total_forms = 0
            total_text_blocks = 0
            
            # Extract content from each page
            for page_num in range(len(self.document)):
                page = self.document[page_num]
                page_content = {
                    "page_number": page_num + 1,
                    "page_content": {},
                    "page_summary": {
                        "main_topics": [],
                        "key_entities": [],
                        "content_type": "text"
                    }
                }
                
                # Extract text blocks
                if extract_text_blocks:
                    text_blocks = self._extract_text_blocks(page)
                    page_content["page_content"]["text_blocks"] = text_blocks
                    total_text_blocks += len(text_blocks)
                    
                    # Collect text for full document text
                    page_text = " ".join([block.get("text", "") for block in text_blocks])
                    all_text_parts.append(page_text)
                
                # Extract images
                if include_images:
                    images = self._extract_images(page, page_num + 1, ocr_images)
                    page_content["page_content"]["images"] = images
                    total_images += len(images)
                
                # Extract tables
                if include_tables:
                    tables = self._extract_tables(page, page_num)
                    page_content["page_content"]["tables"] = tables
                    total_tables += len(tables)
                
                # Extract forms
                if include_forms:
                    forms = self._extract_forms(page, page_num + 1)
                    page_content["page_content"]["forms"] = forms
                    total_forms += len(forms)
                
                # Determine content type
                page_content["page_summary"]["content_type"] = self._classify_page_content(page_content["page_content"])
                
                content["pages"].append(page_content)
            
            # Update summary statistics
            content["document_summary"]["extracted_data"].update({
                "total_tables": total_tables,
                "total_images": total_images,
                "total_forms": total_forms,
                "total_text_blocks": total_text_blocks
            })
            
            # Create complete document text
            content["document_summary"]["all_text"] = "\n".join(all_text_parts)
            content["content_for_llm"]["searchable_content"] = content["document_summary"]["all_text"]
            
            # Create structured content for LLMs
            self._create_llm_optimized_content(content)
            
            return content
            
        except Exception as e:
            raise Exception(f"Failed to extract PDF content: {str(e)}")
    
    def _extract_document_metadata(self) -> Dict[str, Any]:
        """Extract document metadata and properties."""
        try:
            metadata = self.document.metadata
            
            return {
                "file_path": self.pdf_path,
                "extracted_at": datetime.now().isoformat(),
                "page_count": len(self.document),
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
                "encryption": self.document.needs_pass,
                "page_layout": "single_page",  # Default, could be enhanced
                "has_text": self._document_has_text(),
                "has_images": self._document_has_images(),
                "has_forms": self._document_has_forms()
            }
        except Exception as e:
            logger.warning(f"Error extracting document metadata: {str(e)}")
            return {
                "file_path": self.pdf_path,
                "extracted_at": datetime.now().isoformat(),
                "page_count": len(self.document) if self.document else 0,
                "error": str(e)
            }
    
    def _extract_text_blocks(self, page) -> List[Dict[str, Any]]:
        """Extract structured text blocks from a page."""
        try:
            text_blocks = []
            blocks = page.get_text("dict")["blocks"]
            
            block_id = 0
            for block in blocks:
                if "lines" in block:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["text"].strip():  # Only non-empty text
                                text_block = {
                                    "id": f"block_{block_id}",
                                    "page": page.number + 1,
                                    "bbox": span["bbox"],
                                    "text": span["text"],
                                    "font": span["font"],
                                    "font_size": span["size"],
                                    "color": self._color_to_hex(span["color"]),
                                    "style": self._extract_text_style(span),
                                    "reading_order": block_id,
                                    "block_type": self._classify_text_block(span["text"])
                                }
                                text_blocks.append(text_block)
                                block_id += 1
            
            return text_blocks
            
        except Exception as e:
            logger.warning(f"Error extracting text blocks: {str(e)}")
            return []
    
    def _extract_images(self, page, page_num: int, ocr_images: bool = False) -> List[Dict[str, Any]]:
        """Extract images from a page."""
        try:
            images = []
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(self.document, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        image_data = {
                            "id": f"img_{page_num}_{img_index}",
                            "page": page_num,
                            "bbox": page.get_image_bbox(img),
                            "format": pix.ext,
                            "size": [pix.width, pix.height],
                            "file_size": len(pix.tobytes()),
                            "image_type": "embedded",
                            "ocr_text": ""
                        }
                        
                        # Add OCR if requested
                        if ocr_images:
                            image_data["ocr_text"] = self._extract_text_from_image(pix)
                        
                        # Store image data as base64 if needed
                        # image_data["extracted_data"] = base64.b64encode(pix.tobytes()).decode()
                        
                        images.append(image_data)
                    
                    pix = None  # Free memory
                    
                except Exception as e:
                    logger.warning(f"Error processing image {img_index}: {str(e)}")
                    continue
            
            return images
            
        except Exception as e:
            logger.warning(f"Error extracting images: {str(e)}")
            return []
    
    def _extract_tables(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extract tables from a page using pdfplumber if available."""
        try:
            tables = []
            
            if PDFPLUMBER_AVAILABLE and self.pdfplumber_pdf:
                try:
                    plumber_page = self.pdfplumber_pdf.pages[page_num]
                    detected_tables = plumber_page.find_tables()
                    
                    for table_index, table in enumerate(detected_tables):
                        try:
                            table_data = table.extract()
                            if table_data:
                                table_info = {
                                    "id": f"table_{page_num + 1}_{table_index}",
                                    "page": page_num + 1,
                                    "bbox": table.bbox,
                                    "rows": len(table_data),
                                    "columns": len(table_data[0]) if table_data else 0,
                                    "has_header": True,  # Assume first row is header
                                    "cells": self._format_table_cells(table_data)
                                }
                                tables.append(table_info)
                        except Exception as e:
                            logger.warning(f"Error processing table {table_index}: {str(e)}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Error with pdfplumber table extraction: {str(e)}")
            
            # Fallback: try to detect tables from text layout
            if not tables:
                tables = self._extract_tables_from_text_layout(page, page_num + 1)
            
            return tables
            
        except Exception as e:
            logger.warning(f"Error extracting tables: {str(e)}")
            return []
    
    def _extract_forms(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extract form fields from a page."""
        try:
            forms = []
            
            # Get form fields from the page
            if hasattr(page, 'widgets'):
                widgets = page.widgets()
                
                if widgets:
                    form_fields = []
                    for widget in widgets:
                        try:
                            field_info = {
                                "name": widget.field_name or f"field_{len(form_fields)}",
                                "type": self._get_field_type(widget),
                                "value": widget.field_value or "",
                                "bbox": widget.rect,
                                "required": False,  # Would need to check field properties
                                "max_length": None
                            }
                            form_fields.append(field_info)
                        except Exception as e:
                            logger.warning(f"Error processing form field: {str(e)}")
                            continue
                    
                    if form_fields:
                        forms.append({
                            "id": f"form_{page_num}",
                            "page": page_num,
                            "fields": form_fields
                        })
            
            return forms
            
        except Exception as e:
            logger.warning(f"Error extracting forms: {str(e)}")
            return []
    
    def _document_has_text(self) -> bool:
        """Check if document has extractable text."""
        try:
            for page_num in range(min(3, len(self.document))):  # Check first 3 pages
                page = self.document[page_num]
                text = page.get_text().strip()
                if text:
                    return True
            return False
        except:
            return False
    
    def _document_has_images(self) -> bool:
        """Check if document has images."""
        try:
            for page_num in range(min(3, len(self.document))):  # Check first 3 pages
                page = self.document[page_num]
                if page.get_images():
                    return True
            return False
        except:
            return False
    
    def _document_has_forms(self) -> bool:
        """Check if document has form fields."""
        try:
            for page_num in range(min(3, len(self.document))):  # Check first 3 pages
                page = self.document[page_num]
                if hasattr(page, 'widgets') and page.widgets():
                    return True
            return False
        except:
            return False
    
    def _color_to_hex(self, color_int: int) -> str:
        """Convert color integer to hex string."""
        try:
            return f"#{color_int:06x}"
        except:
            return "#000000"
    
    def _extract_text_style(self, span: Dict) -> List[str]:
        """Extract text style information from span."""
        styles = []
        try:
            flags = span.get("flags", 0)
            if flags & 2**4:  # Bold
                styles.append("bold")
            if flags & 2**1:  # Italic
                styles.append("italic")
            if flags & 2**2:  # Underline
                styles.append("underline")
        except:
            pass
        return styles
    
    def _classify_text_block(self, text: str) -> str:
        """Classify text block type based on content."""
        text = text.strip()
        if not text:
            return "empty"
        
        # Simple heuristics for classification
        if len(text) > 100:
            return "paragraph"
        elif text.isupper() or (len(text) < 50 and not text.endswith('.')):
            return "header"
        elif text.startswith(('•', '-', '*', '1.', '2.', '3.')):
            return "list"
        else:
            return "paragraph"
    
    def _classify_page_content(self, page_content: Dict) -> str:
        """Classify the type of content on a page."""
        has_text = bool(page_content.get("text_blocks"))
        has_images = bool(page_content.get("images"))
        has_tables = bool(page_content.get("tables"))
        has_forms = bool(page_content.get("forms"))
        
        if has_forms:
            return "form"
        elif has_images and not has_text:
            return "image_heavy"
        elif has_tables and has_text:
            return "mixed"
        elif has_text:
            return "text"
        else:
            return "unknown"
    
    def _format_table_cells(self, table_data: List[List]) -> List[Dict[str, Any]]:
        """Format table data into cell structure."""
        cells = []
        for row_idx, row in enumerate(table_data):
            for col_idx, cell_text in enumerate(row):
                if cell_text:  # Only include non-empty cells
                    cells.append({
                        "row": row_idx,
                        "col": col_idx,
                        "text": str(cell_text).strip(),
                        "is_header": row_idx == 0,
                        "rowspan": 1,
                        "colspan": 1
                    })
        return cells
    
    def _extract_tables_from_text_layout(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Fallback method to detect tables from text layout."""
        # This is a simplified implementation
        # Could be enhanced with more sophisticated table detection
        return []
    
    def _get_field_type(self, widget) -> str:
        """Determine form field type."""
        try:
            field_type = widget.field_type
            if field_type == 1:
                return "text"
            elif field_type == 2:
                return "checkbox"
            elif field_type == 3:
                return "radio"
            elif field_type == 4:
                return "dropdown"
            elif field_type == 5:
                return "signature"
            else:
                return "unknown"
        except:
            return "unknown"
    
    def _extract_text_from_image(self, pix) -> str:
        """Extract text from image using OCR (placeholder)."""
        # Placeholder for OCR implementation
        # Would require pytesseract or similar
        return ""
    
    def _create_llm_optimized_content(self, content: Dict[str, Any]) -> None:
        """Create LLM-optimized content structure."""
        try:
            # Extract document title
            title = content["document_info"].get("title", "")
            if not title:
                # Try to find title from first page header
                for page in content["pages"]:
                    text_blocks = page.get("page_content", {}).get("text_blocks", [])
                    for block in text_blocks:
                        if block.get("block_type") == "header":
                            title = block.get("text", "")
                            break
                    if title:
                        break
            
            content["content_for_llm"]["structured_text"]["title"] = title
            
            # Create sections from pages
            sections = []
            for page in content["pages"]:
                page_num = page["page_number"]
                text_blocks = page.get("page_content", {}).get("text_blocks", [])
                
                if text_blocks:
                    page_text = " ".join([block.get("text", "") for block in text_blocks])
                    sections.append({
                        "heading": f"Page {page_num}",
                        "content": page_text,
                        "page": page_num
                    })
            
            content["content_for_llm"]["structured_text"]["sections"] = sections
            
            # Convert tables to text format
            tables_as_text = []
            for page in content["pages"]:
                tables = page.get("page_content", {}).get("tables", [])
                for table in tables:
                    table_text = self._table_to_text(table)
                    if table_text:
                        tables_as_text.append(f"Table from Page {page['page_number']}:\n{table_text}")
            
            content["content_for_llm"]["structured_text"]["tables_as_text"] = tables_as_text
            
            # Create image descriptions
            image_descriptions = []
            for page in content["pages"]:
                images = page.get("page_content", {}).get("images", [])
                for img in images:
                    desc = f"Image on Page {page['page_number']}: {img.get('image_type', 'embedded image')}"
                    if img.get("ocr_text"):
                        desc += f" (OCR text: {img['ocr_text']})"
                    image_descriptions.append(desc)
            
            content["content_for_llm"]["structured_text"]["image_descriptions"] = image_descriptions
            
            # Create metadata summary
            doc_info = content["document_info"]
            extracted_data = content["document_summary"]["extracted_data"]
            
            summary_parts = [
                f"PDF document with {doc_info.get('page_count', 0)} pages"
            ]
            
            if extracted_data.get("total_text_blocks", 0) > 0:
                summary_parts.append(f"{extracted_data['total_text_blocks']} text blocks")
            if extracted_data.get("total_tables", 0) > 0:
                summary_parts.append(f"{extracted_data['total_tables']} tables")
            if extracted_data.get("total_images", 0) > 0:
                summary_parts.append(f"{extracted_data['total_images']} images")
            if extracted_data.get("total_forms", 0) > 0:
                summary_parts.append(f"{extracted_data['total_forms']} forms")
            
            content["content_for_llm"]["metadata_summary"] = ", ".join(summary_parts)
            
        except Exception as e:
            logger.warning(f"Error creating LLM-optimized content: {str(e)}")
    
    def _table_to_text(self, table: Dict[str, Any]) -> str:
        """Convert table structure to text format."""
        try:
            cells = table.get("cells", [])
            if not cells:
                return ""
            
            # Group cells by row
            rows = {}
            max_col = 0
            for cell in cells:
                row_idx = cell["row"]
                col_idx = cell["col"]
                max_col = max(max_col, col_idx)
                
                if row_idx not in rows:
                    rows[row_idx] = {}
                rows[row_idx][col_idx] = cell["text"]
            
            # Create text representation
            text_lines = []
            for row_idx in sorted(rows.keys()):
                row_cells = []
                for col_idx in range(max_col + 1):
                    cell_text = rows[row_idx].get(col_idx, "")
                    row_cells.append(cell_text)
                text_lines.append(" | ".join(row_cells))
            
            return "\n".join(text_lines)
            
        except Exception as e:
            logger.warning(f"Error converting table to text: {str(e)}")
            return ""
    
    def extract_content(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract content for cache handler compatibility.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing PDF content
        """
        return self.extract_complete_content(pdf_path)
    
    def extract_to_json(
        self,
        pdf_path: Optional[str] = None,
        output_path: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Extract content and return as JSON string.
        
        Args:
            pdf_path: Path to the PDF file
            output_path: Optional path to save JSON file
            **kwargs: Additional arguments for extract_complete_content
            
        Returns:
            JSON string containing the content
        """
        content = self.extract_complete_content(pdf_path, **kwargs)
        json_str = json.dumps(content, indent=2, ensure_ascii=False, default=str)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"Content saved to: {output_path}")
            
        return json_str


def main():
    """Example usage of the PDF content extractor."""
    # This is for testing/demonstration purposes
    extractor = PDFContentExtractor()
    
    # Example of what can be extracted
    print("PDF Content Extractor")
    print("====================")
    print("This extractor can extract the following from PDF documents:")
    print("- Document metadata (title, author, creation date, etc.)")
    print("- Text content with formatting and positioning")
    print("- Images with metadata and optional OCR")
    print("- Tables with structure and cell data")
    print("- Form fields and their values")
    print("- Document structure and layout")
    print("- LLM-optimized content representation")


if __name__ == "__main__":
    main()
