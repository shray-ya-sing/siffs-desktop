# Siffs - Fast File Search Desktop Application
# Copyright (C) 2025  Siffs
# 
# Contact: github.suggest277@passinbox.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# LEGACY CODE: NOT IN USE

import os
import sys
import logging

# Add the current directory to path for PyInstaller
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    application_path = os.path.dirname(sys.executable)
    sys.path.insert(0, application_path)
else:
    # Running in development
    application_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, application_path)

from app import create_app
from waitress import serve
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In production, load .env from the same directory as the executable
if getattr(sys, 'frozen', False):
    env_path = os.path.join(os.path.dirname(sys.executable), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '127.0.0.1')
    threads = int(os.environ.get('WAITRESS_THREADS', 4))
    
    logger.info(f"Starting production server on {host}:{port} with {threads} threads")
    logger.info(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
    
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        # Recommended production settings
        channel_timeout=120,  # seconds to wait for client to complete request
        cleanup_interval=30,  # seconds between cleanup runs
        connection_limit=1000,  # max concurrent connections
        asyncore_use_poll=True  # better for high concurrency
    )