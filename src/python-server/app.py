from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
import os
import sys
import asyncio
import json
from pathlib import Path
from functools import wraps


# Add the current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from excel.metadata.excel_metadata_processor import ExcelMetadataProcessor
from excel.metadata.excel_metadata_analyzer import ExcelMetadataAnalyzer

def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
        try:
            # Run the async function and get the async generator
            gen = f(*args, **kwargs)
            
            # Create a sync generator that yields from the async generator
            def sync_gen():
                while True:
                    try:
                        # Get the next value from the async generator
                        chunk = loop.run_until_complete(gen.__anext__())
                        yield chunk
                    except StopAsyncIteration:
                        break
                loop.close()
            
            # Return the streaming response
            return Response(
                stream_with_context(sync_gen()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )
        except Exception as e:
            loop.close()
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    return wrapper  # This should be at the decorator level, not inside wrapper!

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    # Configuration
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    # Simple health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'ok', 'message': 'Python server is running'})
    
    # Example API endpoint
    @app.route('/api/example', methods=['GET'])
    def example_endpoint():
        return jsonify({'message': 'Hello from Python server!'})

    # Excel metadata extraction endpoint
    @app.route('/api/excel/extract-metadata', methods=['POST'])
    def extract_metadata():
        try:
            data = request.get_json()
            file_path = data.get('filePath')
            
            if not file_path:
                return jsonify({
                    'status': 'error',
                    'message': 'No file path provided'
                }), 400
                
            # Initialize the metadata processor
            processor = ExcelMetadataProcessor(workbook_path=file_path)
            
            # Process the workbook
            metadata, markdown = processor.process_workbook()
            
            return jsonify({
                'status': 'success',
                'markdown': markdown,
                'metadata': metadata
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/excel/analyze-metadata', methods=['POST'])
    @async_route
    async def analyze_metadata():
        data = request.get_json()
        metadata = data.get('metadata')
        model = data.get('model', 'claude-sonnet-4-20250514')
        temperature = float(data.get('temperature', 0.3))
        
        if not metadata:
            yield "data: " + json.dumps({'error': 'No metadata provided'}) + "\n\n"
            yield "data: [DONE]\n\n"
            return

        analyzer = ExcelMetadataAnalyzer()
        
        try:
            stream = await analyzer.analyze_metadata(
                model_metadata=metadata,
                model=model,
                temperature=temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    
    # Return the app
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 3001))  # Default to 3001 to avoid conflicts with other services
    app.run(host='127.0.0.1', port=port, debug=True)
