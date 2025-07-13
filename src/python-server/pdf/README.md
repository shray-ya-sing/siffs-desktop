# PDF Content Extraction System

## Overview

The PDF Content Extraction System provides comprehensive extraction and analysis of PDF documents, following the same event-driven architecture patterns as the existing PowerPoint and Excel extraction systems.

## Architecture

### Components

```
pdf/
├── __init__.py                           # PDF module initialization
├── orchestration/
│   ├── __init__.py
│   └── pdf_orchestrator.py               # WebSocket message routing & coordination
└── content/
    ├── __init__.py
    └── extraction/
        ├── __init__.py
        ├── pdf_content_extractor.py       # Core extraction logic
        └── event_handlers/
            ├── __init__.py
            ├── pdf_cache_handler.py       # Cache management
            └── pdf_content_handler.py     # Content processing
```

### Event Flow

1. **Client Request** → WebSocket message (`EXTRACT_PDF_CONTENT`)
2. **Orchestrator** → Routes to extraction handler
3. **Cache Check** → Verify existing content (`CHECK_PDF_CACHE`)
4. **Fresh Extraction** → Multi-stage content extraction (`START_PDF_FRESH_EXTRACTION`)
5. **Progressive Updates** → Real-time progress via WebSocket
6. **Storage & Caching** → Persist results for future use

## Features

### Content Extraction

- **Text Content**: Character-level extraction with positioning, formatting, and structure
- **Images**: Embedded image extraction with metadata and optional OCR
- **Tables**: Advanced table detection and structure analysis using multiple libraries
- **Forms**: Interactive form field extraction with types and values
- **Document Structure**: Metadata, bookmarks, page layout, and properties

### LLM-Optimized Output

- **Structured Text**: Organized sections, headers, and paragraphs
- **Searchable Content**: Full-text search capabilities
- **Table Conversion**: Tables converted to text format for LLM consumption
- **Image Descriptions**: OCR-extracted text and image metadata
- **Content Summary**: Document overview and statistics

## Libraries Used

### Core PDF Processing
- **PyMuPDF (fitz)**: Fast, comprehensive PDF processing
- **pdfplumber**: Text and table extraction
- **PyPDF2**: Basic PDF operations

### Optional Enhancements
- **pytesseract**: OCR for scanned content
- **camelot-py**: Advanced table extraction
- **opencv-python**: Image analysis

## API Integration

### AI Agent Tools

Located in `ai_services/agents/*/read_write_tools/pdf_info_tools.py`:

- `get_pdf_content_from_cache(workspace_path)` - Complete PDF content
- `get_pdf_text_content(workspace_path, pages=None)` - Text extraction
- `get_pdf_tables(workspace_path, table_ids=None, pages=None)` - Table data
- `get_pdf_images(workspace_path, image_ids=None, pages=None)` - Image metadata
- `get_pdf_forms(workspace_path, pages=None)` - Form field data
- `get_pdf_document_summary(workspace_path)` - Document overview
- `search_pdf_content(workspace_path, search_terms, content_types=None)` - Content search

## WebSocket Events

### Client → Server
- `EXTRACT_PDF_CONTENT` - Initiate PDF extraction

### Server → Client
- `PDF_EXTRACTION_PROGRESS` - Progress updates
- `PDF_PAGE_EXTRACTED` - Page completion
- `PDF_EXTRACTION_COMPLETE` - Extraction finished
- `PDF_EXTRACTION_ERROR` - Error handling

## Caching Strategy

### Multi-Level Caching
1. **JSON Hotcache**: Fast access to essential content (`pdf_content_hotcache.json`)
2. **File Mappings**: Workspace to temporary file mapping
3. **File Hash Validation**: Ensure content freshness

### Cache Structure
```json
{
  "workspace_path": {
    "document_info": {...},
    "pages": [...],
    "document_summary": {...},
    "content_for_llm": {...},
    "cached_at": "2024-01-01T00:00:00Z",
    "file_mtime": 1704067200.0
  }
}
```

## Output Format

### Complete Content Structure
```json
{
  "document_info": {
    "file_path": "path/to/document.pdf",
    "page_count": 10,
    "title": "Document Title",
    "author": "Author Name",
    "has_text": true,
    "has_images": true,
    "has_forms": false,
    "extraction_settings": {...}
  },
  "pages": [
    {
      "page_number": 1,
      "page_content": {
        "text_blocks": [...],
        "images": [...],
        "tables": [...],
        "forms": [...]
      },
      "page_summary": {
        "content_type": "text|mixed|image_heavy|form"
      }
    }
  ],
  "document_summary": {
    "all_text": "Complete extracted text...",
    "extracted_data": {
      "total_tables": 5,
      "total_images": 10,
      "total_forms": 0
    }
  },
  "content_for_llm": {
    "structured_text": {...},
    "searchable_content": "...",
    "metadata_summary": "..."
  }
}
```

## Usage Examples

### Client-Side (WebSocket)
```javascript
// Extract PDF content
ws.send(JSON.stringify({
  type: "EXTRACT_PDF_CONTENT",
  data: {
    filePath: "documents/report.pdf",
    fileContent: "base64_encoded_pdf_data",
    requestId: "unique-request-id",
    include_images: true,
    include_tables: true,
    include_forms: true,
    ocr_images: false
  }
}));

// Listen for progress
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "PDF_EXTRACTION_PROGRESS") {
    console.log(`Progress: ${data.progress}% - ${data.message}`);
  }
};
```

### Server-Side (AI Agent)
```python
# Get complete PDF content
content = get_pdf_content_from_cache("documents/report.pdf")

# Extract specific text pages
text_content = get_pdf_text_content("documents/report.pdf", pages=[1, 2, 3])

# Get all tables
tables = get_pdf_tables("documents/report.pdf")

# Search for terms
search_results = search_pdf_content(
    "documents/report.pdf", 
    ["revenue", "profit"], 
    content_types=["text", "tables"]
)
```

## Error Handling

### PDF Types Supported
- Standard text PDFs
- Scanned PDFs (with OCR)
- Password-protected PDFs (with authentication)
- Form PDFs (interactive and fillable)
- Image-heavy PDFs
- Multi-column layouts

### Fallback Strategies
- Multiple library fallbacks for text extraction
- Graceful degradation for problematic content
- Memory management for large files
- Progressive processing for complex documents

## Performance Optimization

### Memory Management
- Stream processing for large PDFs
- Resource cleanup and proper object disposal
- Caching to avoid re-processing

### Processing Speed
- Page-level parallelism where possible
- Content-type specific extraction
- Optimized library selection based on content

## Integration Notes

The PDF extraction system is fully integrated with the existing event-driven architecture:

1. **Event Bus**: Uses the same event system as Excel and PowerPoint
2. **WebSocket Manager**: Shares the same client communication system
3. **Cache Structure**: Follows the same patterns as other document types
4. **API Tools**: Consistent interface with Excel and PowerPoint tools
5. **Error Handling**: Unified error propagation and client notification

## Testing

The system has been designed with comprehensive error handling and fallback mechanisms. All imports have been tested and the event handlers are properly initialized during application startup.

## Future Enhancements

- **Advanced OCR**: GPU-accelerated OCR for better performance
- **ML-based Extraction**: Intelligent content analysis and classification
- **Enhanced Table Detection**: More sophisticated table recognition
- **Content Analysis**: Automatic summarization and entity extraction
- **Multi-language Support**: OCR and text processing for various languages
