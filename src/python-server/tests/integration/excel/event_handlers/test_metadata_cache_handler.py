# tests/test_metadata_cache_handler.py
import pytest
import asyncio
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock
import tempfile
import json

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from core.events import EventBus
from excel.metadata.extraction.event_handlers.metadata_cache_handler import MetadataCacheHandler


@pytest.fixture
def event_bus():
    """Create a fresh event bus for each test"""
    return EventBus()


@pytest.fixture
def mock_storage():
    """Create a mock storage with configurable behavior"""
    storage = Mock()
    storage.get_latest_version = Mock(return_value=None)
    storage.get_all_chunks = Mock(return_value=[])
    return storage


@pytest.fixture
def cache_handler(event_bus, mock_storage):
    """Create cache handler with dependencies"""
    return MetadataCacheHandler(event_bus, mock_storage)


@pytest.fixture
def sample_chunks():
    """Sample valid chunks data"""
    return [
        {
            "sheetName": "Sheet1",
            "startRow": 1,
            "endRow": 10,
            "cellData": [[{"value": "A1"}, {"value": "B1"}]],
            "chunkId": "chunk_1"
        },
        {
            "sheetName": "Sheet1", 
            "startRow": 11,
            "endRow": 20,
            "cellData": [[{"value": "A11"}, {"value": "B11"}]],
            "chunkId": "chunk_2"
        }
    ]


@pytest.fixture
def sample_version(sample_chunks):
    """Sample cached version data"""
    return {
        "version_id": "v123",
        "file_path": "test.xlsx",
        "created_at": datetime.now().isoformat(),
        "change_description": "Test version",
        "chunks": sample_chunks
    }


@pytest.fixture
async def event_tracker(event_bus):
    """Track events emitted during tests"""
    events = []
    
    async def track_event(event):
        events.append({
            "type": event.type,
            "data": event.data
        })
    
    # Register handlers for all events we care about
    event_bus.on_async("CACHED_METADATA_FOUND", track_event)
    event_bus.on_async("START_FRESH_EXTRACTION", track_event)
    event_bus.on_async("EXTRACTION_ERROR", track_event)
    
    return events


@pytest.fixture
def temp_excel_file():
    """Create a temporary Excel file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp.write(b"Fake Excel content")
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Cleanup
    try:
        os.unlink(tmp_path)
    except:
        pass


class TestMetadataCacheHandler:
    """Integration tests for MetadataCacheHandler"""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, cache_handler, event_bus, mock_storage, 
                            sample_version, sample_chunks, event_tracker, temp_excel_file):
        """Test successful cache hit scenario"""
        # Setup mock to return cached data
        mock_storage.get_latest_version.return_value = sample_version
        mock_storage.get_all_chunks.return_value = sample_chunks
        
        # Emit cache check event
        await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": temp_excel_file,
            "client_id": "test-client",
            "request_id": "test-123"
        })
        
        # Wait for async processing
        await asyncio.sleep(0.1)
        
        # Verify storage was queried
        mock_storage.get_latest_version.assert_called_once()
        mock_storage.get_all_chunks.assert_called_once_with("v123")
        
        # Check that CACHED_METADATA_FOUND was emitted
        assert len(event_tracker) == 1
        assert event_tracker[0]["type"] == "CACHED_METADATA_FOUND"
        
        # Verify event data
        event_data = event_tracker[0]["data"]
        assert event_data["from_cache"] is True
        assert event_data["cache_version_id"] == "v123"
        assert len(event_data["chunks"]) == 2
        assert event_data["client_id"] == "test-client"
        assert event_data["request_id"] == "test-123"
    
    @pytest.mark.asyncio
    async def test_cache_miss_no_version(self, cache_handler, event_bus, 
                                        mock_storage, event_tracker, temp_excel_file):
        """Test cache miss when no cached version exists"""
        # Setup mock to return no cached version
        mock_storage.get_latest_version.return_value = None
        
        # Emit cache check event
        await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": temp_excel_file,
            "client_id": "test-client",
            "request_id": "test-456"
        })
        
        # Wait for async processing
        await asyncio.sleep(0.1)
        
        # Verify storage was queried
        mock_storage.get_latest_version.assert_called_once()
        
        # Check that START_FRESH_EXTRACTION was emitted
        assert len(event_tracker) == 1
        assert event_tracker[0]["type"] == "START_FRESH_EXTRACTION"
        
        # Verify event data
        event_data = event_tracker[0]["data"]
        assert event_data["from_cache"] is False
        assert event_data["client_id"] == "test-client"
        assert os.path.exists(event_data["file_path"])
    
    @pytest.mark.asyncio
    async def test_cache_miss_invalid_chunks(self, cache_handler, event_bus,
                                           mock_storage, sample_version, event_tracker, temp_excel_file):
        """Test cache miss when chunks are invalid"""
        # Setup mock with invalid chunks
        mock_storage.get_latest_version.return_value = sample_version
        mock_storage.get_all_chunks.return_value = [
            {"invalid": "chunk", "missing": "required fields"}
        ]
        
        # Emit cache check event
        await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": temp_excel_file,
            "client_id": "test-client"
        })
        
        await asyncio.sleep(0.1)
        
        # Should emit START_FRESH_EXTRACTION due to invalid chunks
        assert len(event_tracker) == 1
        assert event_tracker[0]["type"] == "START_FRESH_EXTRACTION"
    
    @pytest.mark.asyncio
    async def test_force_refresh(self, cache_handler, event_bus,
                                mock_storage, sample_version, sample_chunks, event_tracker, temp_excel_file):
        """Test force refresh bypasses cache"""
        # Setup mock with valid cache
        mock_storage.get_latest_version.return_value = sample_version
        mock_storage.get_all_chunks.return_value = sample_chunks
        
        # Emit cache check with force_refresh
        await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": temp_excel_file,
            "client_id": "test-client",
            "force_refresh": True
        })
        
        await asyncio.sleep(0.1)
        
        # Storage should not be queried
        mock_storage.get_latest_version.assert_not_called()
        
        # Should emit START_FRESH_EXTRACTION
        assert len(event_tracker) == 1
        assert event_tracker[0]["type"] == "START_FRESH_EXTRACTION"
    
    @pytest.mark.asyncio
    async def test_file_not_found(self, cache_handler, event_bus,
                                 mock_storage, event_tracker):
        """Test error handling for non-existent file"""
        # Use non-existent file
        fake_file = "/path/to/non/existent/file.xlsx"
        
        # Emit cache check event
        await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": fake_file,
            "client_id": "test-client",
            "request_id": "test-789"
        })
        
        await asyncio.sleep(0.1)
        
        # Should emit EXTRACTION_ERROR
        assert len(event_tracker) == 1
        assert event_tracker[0]["type"] == "EXTRACTION_ERROR"
        
        # Verify error details
        error_data = event_tracker[0]["data"]
        assert "File not found" in error_data["error"]
        assert error_data["client_id"] == "test-client"
        assert error_data["request_id"] == "test-789"
    
    @pytest.mark.asyncio
    async def test_storage_exception(self, cache_handler, event_bus,
                                   mock_storage, event_tracker, temp_excel_file):
        """Test error handling when storage throws exception"""
        # Make storage throw exception
        mock_storage.get_latest_version.side_effect = Exception("Storage connection failed")
        
        # Emit cache check event
        await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": temp_excel_file,
            "client_id": "test-client"
        })
        
        await asyncio.sleep(0.1)
        
        # Should emit EXTRACTION_ERROR
        assert len(event_tracker) == 1
        assert event_tracker[0]["type"] == "EXTRACTION_ERROR"
        assert "Cache check failed" in event_tracker[0]["data"]["error"]
    
    @pytest.mark.asyncio
    async def test_empty_chunks(self, cache_handler, event_bus,
                               mock_storage, sample_version, event_tracker, temp_excel_file):
        """Test cache miss when chunks list is empty"""
        # Setup mock with empty chunks
        mock_storage.get_latest_version.return_value = sample_version
        mock_storage.get_all_chunks.return_value = []
        
        await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": temp_excel_file,
            "client_id": "test-client"
        })
        
        await asyncio.sleep(0.1)
        
        # Should emit START_FRESH_EXTRACTION
        assert len(event_tracker) == 1
        assert event_tracker[0]["type"] == "START_FRESH_EXTRACTION"
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_chunks", [
        None,  # None instead of list
        "not a list",  # String instead of list
        [None, None],  # List of None
        [{"sheetName": "Sheet1"}],  # Missing required fields
        [{"startRow": 1, "endRow": 10}],  # Missing sheetName
    ])
    async def test_various_invalid_chunks(self, cache_handler, event_bus,
                                        mock_storage, sample_version, event_tracker, 
                                        temp_excel_file, invalid_chunks):
        """Test cache miss with various invalid chunk formats"""
        mock_storage.get_latest_version.return_value = sample_version
        mock_storage.get_all_chunks.return_value = invalid_chunks
        
        await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": temp_excel_file,
            "client_id": "test-client"
        })
        
        await asyncio.sleep(0.1)
        
        # All invalid formats should trigger fresh extraction
        assert len(event_tracker) == 1
        assert event_tracker[0]["type"] == "START_FRESH_EXTRACTION"


@pytest.mark.asyncio
async def test_concurrent_cache_checks(event_bus, mock_storage, temp_excel_file):
    """Test multiple concurrent cache checks"""
    cache_handler = MetadataCacheHandler(event_bus, mock_storage)
    events = []
    
    async def track_event(event):
        events.append(event.type)
    
    event_bus.on_async("START_FRESH_EXTRACTION", track_event)
    
    # Emit multiple cache checks concurrently
    tasks = []
    for i in range(5):
        task = event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": temp_excel_file,
            "client_id": f"client-{i}"
        })
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    await asyncio.sleep(0.2)
    
    # All should complete without errors
    assert len(events) == 5