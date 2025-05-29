from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys

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
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 3001))  # Default to 3001 to avoid conflicts with other services
    app.run(host='127.0.0.1', port=port, debug=True)
