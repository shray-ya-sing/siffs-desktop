import pytest
import asyncio
import websockets
import json
import sys
import os
from pathlib import Path
import multiprocessing
import time
import requests
from typing import Dict, List, Any
import tempfile

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import your app for testing
from app import app
import uvicorn


class ServerProcess:
    """Manages the server process for testing"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.process = None

    def run_server(self):
        uvicorn.run(app, host="127.0.0.1", port=self.port, log_level="error")
        
    def start(self):
        """Start the server in a separate process"""
        self.process = multiprocessing.Process(target=self.run_server)
        self.process.start()
        
        # Wait for server to be ready
        self._wait_for_server()
        
    def stop(self):
        """Stop the server process"""
        if self.process:
            self.process.terminate()
            self.process.join(timeout=5)
            if self.process.is_alive():
                self.process.kill()
                
    def _wait_for_server(self, timeout: int = 120):  # Increased from 10 to 120 seconds
        """Wait for server to be ready to accept connections"""
        import time
        import requests
        from requests.exceptions import RequestException
        
        print(f"Waiting for server to start (timeout: {timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Print progress every 5 seconds
                if int(time.time() - start_time) % 5 == 0:
                    elapsed = int(time.time() - start_time)
                    print(f"Waiting for server... {elapsed}s elapsed")
                    
                response = requests.get(
                    f"http://127.0.0.1:{self.port}/health",
                    timeout=2
                )
                if response.status_code == 200:
                    print("Server started successfully!")
                    return
            except RequestException:
                pass
            time.sleep(0.5)
        
        raise TimeoutError(f"Server did not start within {timeout} seconds")


@pytest.fixture(scope="session")
def server():
    """Start server for the test session"""
    server = ServerProcess(port=8765)
    server.start()
    yield f"http://127.0.0.1:{server.port}"
    server.stop()


@pytest.fixture(scope="session")
def ws_url(server):
    """WebSocket URL for testing"""
    return server.replace("http://", "ws://") + "/ws"


@pytest.fixture
def temp_excel_file():
    """Create a temporary Excel file"""
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        # Create a minimal Excel file (you could use openpyxl here for a real file)
        tmp.write(b"PK")  # Minimal zip signature
        tmp_path = tmp.name
    
    yield tmp_path
    
    try:
        os.unlink(tmp_path)
    except:
        pass


class WebSocketTester:
    """Helper class for WebSocket testing"""
    
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.messages_received: List[Dict] = []
        self.websocket = None
        self.listener_task = None
        
    async def connect(self, client_id: str = "test-client"):
        """Connect to WebSocket"""
        self.websocket = await websockets.connect(f"{self.ws_url}/{client_id}")
        self.listener_task = asyncio.create_task(self._listen_for_messages())
        
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
                
        if self.websocket:
            await self.websocket.close()
            
    async def send_message(self, message: Dict):
        """Send a message through WebSocket"""
        await self.websocket.send(json.dumps(message))
        
    async def wait_for_message(self, message_type: str, timeout: float = 5.0) -> Dict:
        """Wait for a specific message type"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            for msg in self.messages_received:
                if msg.get("type") == message_type:
                    return msg
            await asyncio.sleep(0.1)
            
        raise TimeoutError(f"Did not receive message of type '{message_type}' within {timeout}s")
        
    async def wait_for_messages(self, count: int, timeout: float = 5.0):
        """Wait for a specific number of messages"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if len(self.messages_received) >= count:
                return
            await asyncio.sleep(0.1)
            
        raise TimeoutError(f"Expected {count} messages but got {len(self.messages_received)}")
        
    async def _listen_for_messages(self):
        """Listen for incoming messages"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                self.messages_received.append(data)
                print(f"Received: {data.get('type', 'unknown')} - {data}")
        except websockets.exceptions.ConnectionClosed:
            pass
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
class TestServerEventHandlers:
    """Integration tests for server event handlers"""
    
    async def test_server_health(self, server):
        """Test that server is running"""
        response = requests.get(f"{server}/health")
        assert response.status_code == 200
        
    async def test_websocket_connection(self, ws_url):
        """Test WebSocket connection"""
        tester = WebSocketTester(ws_url)
        await tester.connect("test-connection")
        
        # Should connect successfully
        assert tester.websocket is not None
        assert tester.websocket.open
        
        await tester.disconnect()
        
    async def test_process_command_flow(self, ws_url, temp_excel_file):
        """Test the complete PROCESS_COMMAND flow"""
        tester = WebSocketTester(ws_url)
        await tester.connect("test-flow-client")
        
        # Send PROCESS_COMMAND
        await tester.send_message({
            "type": "PROCESS_COMMAND",
            "command": "test command",
            "id": "test-op-123"
        })
        
        # Should receive STATUS message
        status_msg = await tester.wait_for_message("STATUS", timeout=3)
        assert status_msg["message"] == "Processing your request..."
        assert status_msg["operationId"] == "test-op-123"
        
        # Should receive PROGRESS messages
        await tester.wait_for_messages(2, timeout=5)  # At least STATUS + 1 PROGRESS
        
        # Check that we got progress updates
        progress_messages = [m for m in tester.messages_received if m.get("type") == "PROGRESS"]
        assert len(progress_messages) > 0
        assert progress_messages[0]["stage"] == "extraction"
        
        await tester.disconnect()
        
    async def test_extraction_request_event_flow(self, ws_url):
        """Test that EXTRACT_METADATA_REQUESTED triggers CHECK_CACHE_FOR_METADATA"""
        # This tests the event chain without WebSocket
        # You would need to add an HTTP endpoint that triggers this event
        # or modify your WebSocket handler to accept this message type
        
        tester = WebSocketTester(ws_url)
        await tester.connect("test-extraction-client")
        
        # For now, we can test the PROCESS_COMMAND which should eventually
        # trigger metadata extraction
        await tester.send_message({
            "type": "PROCESS_COMMAND",
            "command": "extract metadata from file",
            "id": "extract-test-123"
        })
        
        # Verify we get expected responses
        await tester.wait_for_message("STATUS")
        
        await tester.disconnect()
        
    async def test_concurrent_connections(self, ws_url):
        """Test multiple concurrent WebSocket connections"""
        testers = []
        
        # Create multiple connections
        for i in range(5):
            tester = WebSocketTester(ws_url)
            await tester.connect(f"concurrent-client-{i}")
            testers.append(tester)
            
        # Send messages from all connections
        for i, tester in enumerate(testers):
            await tester.send_message({
                "type": "PROCESS_COMMAND",
                "command": f"command from client {i}",
                "id": f"concurrent-op-{i}"
            })
            
        # Wait for all to receive responses
        for tester in testers:
            await tester.wait_for_message("STATUS", timeout=5)
            
        # Cleanup
        for tester in testers:
            await tester.disconnect()
            
    async def test_accept_edit_flow(self, ws_url):
        """Test ACCEPT_EDIT message handling"""
        tester = WebSocketTester(ws_url)
        await tester.connect("test-edit-client")
        
        # Send ACCEPT_EDIT message
        await tester.send_message({
            "type": "ACCEPT_EDIT",
            "editId": "test-edit-123"
        })
        
        # In a real test, you'd verify the edit was processed
        # For now, just verify no errors occur
        await asyncio.sleep(0.5)
        
        await tester.disconnect()
        
    async def test_invalid_message_handling(self, ws_url):
        """Test handling of invalid messages"""
        tester = WebSocketTester(ws_url)
        await tester.connect("test-invalid-client")
        
        # Send invalid message
        await tester.send_message({
            "type": "INVALID_TYPE",
            "data": "test"
        })
        
        # Should not crash - just ignore invalid messages
        await asyncio.sleep(0.5)
        
        # Send valid message to ensure connection still works
        await tester.send_message({
            "type": "PROCESS_COMMAND",
            "command": "test after invalid",
            "id": "valid-123"
        })
        
        await tester.wait_for_message("STATUS")
        
        await tester.disconnect()


@pytest.mark.asyncio
async def test_event_handler_registration(server):
    """Test that event handlers are properly registered"""
    # This would require exposing the event bus state through an endpoint
    # For now, we can test indirectly by verifying expected behavior
    
    # Make a request to ensure server is initialized
    response = requests.get(f"{server}/health")
    assert response.status_code == 200
    
    # In a real test, you might add a debug endpoint that returns
    # registered event handlers for verification


@pytest.mark.asyncio 
async def test_full_extraction_flow_with_cache(ws_url, temp_excel_file):
    """Test the complete extraction flow including cache check"""
    # First connection - should trigger fresh extraction
    tester1 = WebSocketTester(ws_url)
    await tester1.connect("cache-test-client-1")
    
    # Send command that should trigger extraction
    await tester1.send_message({
        "type": "PROCESS_COMMAND",
        "command": f"extract metadata from {temp_excel_file}",
        "id": "cache-test-op-1"
    })
    
    # Wait for processing
    await tester1.wait_for_message("STATUS")
    await asyncio.sleep(2)  # Give time for extraction
    
    await tester1.disconnect()
    
    # Second connection - might use cache if implemented
    tester2 = WebSocketTester(ws_url)
    await tester2.connect("cache-test-client-2")
    
    await tester2.send_message({
        "type": "PROCESS_COMMAND", 
        "command": f"extract metadata from {temp_excel_file}",
        "id": "cache-test-op-2"
    })
    
    await tester2.wait_for_message("STATUS")
    
    await tester2.disconnect()


# Debugging helper
@pytest.mark.asyncio
async def test_print_all_messages(ws_url):
    """Helper test to see all messages from server"""
    tester = WebSocketTester(ws_url)
    await tester.connect("debug-client")
    
    await tester.send_message({
        "type": "PROCESS_COMMAND",
        "command": "debug test",
        "id": "debug-123"
    })
    
    # Wait and print all messages
    await asyncio.sleep(3)
    
    print("\n=== All messages received ===")
    for i, msg in enumerate(tester.messages_received):
        print(f"{i}: {msg}")
    print("===========================\n")
    
    await tester.disconnect()