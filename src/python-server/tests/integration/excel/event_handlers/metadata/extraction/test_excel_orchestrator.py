import asyncio
import logging
from pathlib import Path
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent.parent
sys.path.append(str(project_root))

from core.events import event_bus
from excel.orchestration.excel_orchestrator import ExcelOrchestrator
from excel.metadata.extraction.event_handlers.metadata_cache_handler import MetadataCacheHandler
from excel.metadata.extraction.event_handlers.chunk_extractor_handler import ChunkExtractorHandler
from storage.excel_metadata_storage import ExcelMetadataStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestWebSocketManager:
    """Mock WebSocket manager for testing"""
    
    def __init__(self, completion_event: Optional[asyncio.Event] = None):
        self.messages = []
        self.clients = set()
        self.completion_event = completion_event
    
    async def connect(self, websocket, client_id: str = None):
        """Mock connect method"""
        client_id = client_id or f"test_{len(self.clients) + 1}"
        self.clients.add(client_id)
        return client_id
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        """Capture and log messages"""
        self.messages.append({
            "client_id": client_id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"Message to {client_id}: {json.dumps(message, indent=2)}")

        # Set completion event if we get an EXTRACTION_COMPLETE message
        if message.get("type") == "EXTRACTION_COMPLETE" and self.completion_event:
            self.completion_event.set()
    
    def disconnect(self, client_id: str):
        """Mock disconnect method"""
        self.clients.discard(client_id)

class TestProgressTracker:
    """Tracks and logs extraction progress"""
    
    def __init__(self, test_ws_manager: TestWebSocketManager):
        self.start_time = None
        self.chunks_received = 0
        self.completed = asyncio.Event()
        self.completion_event = None
        self.ws_manager = test_ws_manager
        self.client_id = "test_client"
        self.request_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def wait_for_completion(self, timeout: float = 300):
        """Wait for extraction to complete"""
        try:
            await asyncio.wait_for(self.completed.wait(), timeout=timeout)
            logger.info("Test completed successfully!")
            return True
        except asyncio.TimeoutError:
            logger.error("Test timed out waiting for completion")
            return False
    
    def get_messages_by_type(self, message_type: str) -> list:
        """Get all messages of a specific type"""
        return [
            msg for msg in self.ws_manager.messages 
            if msg["message"].get("type") == message_type
        ]
    
    def verify_extraction_complete(self) -> bool:
        """Verify that extraction completed successfully"""
        complete_msgs = self.get_messages_by_type("EXTRACTION_COMPLETE")
        if not complete_msgs:
            return False
        
        # Get the last complete message
        last_complete = complete_msgs[-1]
        total_chunks = last_complete["message"].get("totalChunks", 0)
        
        # Check we got the expected number of chunk messages
        chunk_msgs = self.get_messages_by_type("CHUNK_EXTRACTED")
        
        logger.info(f"Extraction completed with {len(chunk_msgs)} chunks")
        logger.info(f"Reported total chunks: {total_chunks}")
        
        return len(chunk_msgs) > 0 and len(chunk_msgs) == total_chunks

    def get_chunks(self) -> list:
        """Get all extracted chunks with their data"""
        chunk_msgs = self.get_messages_by_type("CHUNK_EXTRACTED")
        # Sort chunks by chunkIndex to maintain order
        return sorted(
            [msg["message"] for msg in chunk_msgs],
            key=lambda x: x.get("chunkIndex", 0)
        )


async def run_extraction_test(file_path: str, force_refresh: bool = False):
    """Run end-to-end extraction test using ExcelOrchestrator"""
    # Create the tracker first with a temporary ws_manager
    temp_ws_manager = TestWebSocketManager()
    tracker = TestProgressTracker(temp_ws_manager)
    
    # Now create the real ws_manager with the tracker's completion event
    test_ws_manager = TestWebSocketManager(completion_event=tracker.completed)
    
    # Update the tracker's ws_manager to use the real one
    tracker.ws_manager = test_ws_manager
    
    # Monkey patch the manager in the ExcelOrchestrator
    import api.websocket_manager
    original_manager = api.websocket_manager.manager
    api.websocket_manager.manager = test_ws_manager
    
    try:
        # Initialize components
        storage = ExcelMetadataStorage()
        
        # Create the ExcelOrchestrator instance (this registers all its handlers)
        orchestrator = ExcelOrchestrator()
        
        # Initialize other handlers
        cache_handler = MetadataCacheHandler(event_bus, storage)
        extractor = ChunkExtractorHandler(event_bus)
        
        # Log test start
        logger.info("\n" + "="*50)
        logger.info(f"STARTING EXTRACTION TEST")
        logger.info(f"File: {file_path}")
        logger.info(f"Force refresh: {force_refresh}")
        logger.info("="*50 + "\n")
        
        # Connect test client
        client_id = await test_ws_manager.connect(None)
        
        # Start the extraction by sending a WebSocket message
        await event_bus.emit("ws_message_received", {
            "client_id": client_id,
            "message": {
                "type": "EXTRACT_METADATA",
                "filePath": str(Path(file_path).absolute()),
                "id": tracker.request_id,
                "forceRefresh": force_refresh
            }
        })
        
        # Wait for completion
        success = await tracker.wait_for_completion()
        
        # Verify results
        if success:
            extraction_ok = tracker.verify_extraction_complete()
            logger.info(f"Extraction verification: {'SUCCESS' if extraction_ok else 'FAILED'}")

            # Print chunk summaries
            logger.info("\n" + "="*50)
            logger.info("EXTRACTED CHUNKS SUMMARY")
            logger.info("="*50)
            for i, chunk in enumerate(chunks):
                logger.info(f"\nChunk {i + 1}:")
                logger.info(f"  Sheet: {chunk.get('sheetName')}")
                logger.info(f"  Rows: {chunk.get('startRow')} - {chunk.get('endRow')}")
                logger.info(f"  Cells: {len(chunk.get('cellData', []))} rows")
                
                # Print a sample of cell data (first 3 rows of first 3 columns)
                sample_cells = chunk.get('cellData', [])[:3]
                if sample_cells:
                    logger.info("  Sample cell data (first 3 rows, first 3 columns):")
                    for row in sample_cells:
                        sample = row[:3] if len(row) > 3 else row
                        logger.info(f"    {[cell.get('value', '') for cell in sample]}")
            
            # Print full chunk data to a file
            output_file = "extracted_chunks.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, indent=2, ensure_ascii=False)
            logger.info(f"\nFull chunk data saved to: {output_file}")
            
            logger.info("\n" + "="*50)
            logger.info(f"Extraction verification: {'SUCCESS' if extraction_ok else 'FAILED'}")
            
            
            # Log summary
            msg_types = {}
            for msg in test_ws_manager.messages:
                msg_type = msg["message"].get("type")
                msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
            
            logger.info("\nMessage Summary:")
            for msg_type, count in msg_types.items():
                logger.info(f"  {msg_type}: {count}")
            
            return extraction_ok
        return False
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False
    finally:
        # Restore original manager
        api.websocket_manager.manager = original_manager

if __name__ == "__main__":
    # Update this path to point to your test Excel file
    test_file = (
        Path(__file__).parent.parent.parent.parent.parent.parent # Go up to tests directory
        / "test_files" 
        / "single_tab_no_error.xlsx"
    )
    
    # Run the test
    test_passed = asyncio.run(run_extraction_test(test_file, force_refresh=True))
    sys.exit(0 if test_passed else 1)