def setup_logging():
    """Configure root logger with file and console handlers."""
    import sys
    import logging
    from logging.handlers import RotatingFileHandler
    import os
    import io
    import codecs
    
    # Suppress PDFMiner debug logs
    logging.getLogger('pdfminer').setLevel(logging.WARNING)

    # Custom UTF-8 safe console handler
    class UTF8ConsoleHandler(logging.StreamHandler):
        def __init__(self, stream=None):
            super().__init__(stream)
            # Ensure UTF-8 encoding for Windows
            if sys.platform == 'win32':
                try:
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    kernel32.SetConsoleCP(65001)
                    kernel32.SetConsoleOutputCP(65001)
                except:
                    pass
        
        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                
                # Handle different stream types
                if hasattr(stream, 'buffer'):
                    # Stream has a buffer, write bytes directly
                    stream.buffer.write(msg.encode('utf-8', errors='replace'))
                    stream.buffer.write(b'\n')
                    stream.buffer.flush()
                elif hasattr(stream, 'write'):
                    # Fallback for streams without buffer
                    try:
                        stream.write(msg + '\n')
                        stream.flush()
                    except UnicodeEncodeError:
                        # If encoding fails, replace problematic characters
                        safe_msg = msg.encode('utf-8', errors='replace').decode('utf-8')
                        stream.write(safe_msg + '\n')
                        stream.flush()
                else:
                    # Last resort: print
                    print(msg.encode('utf-8', errors='replace').decode('utf-8'))
                    
            except Exception as e:
                # Ensure we don't lose log messages due to encoding issues
                try:
                    fallback_msg = f"[ENCODING ERROR] {str(record.msg)}"
                    print(fallback_msg.encode('ascii', errors='replace').decode('ascii'))
                except:
                    self.handleError(record)

    # Create logs directory in a cross-platform way
    if sys.platform == 'win32':
        log_dir = os.path.join(os.environ.get('APPDATA', ''), 'Volute', 'logs')
    else:
        log_dir = os.path.join(os.path.expanduser('~'), '.volute', 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'python.log')

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []

    # Prevent adding handlers multiple times
    if root_logger.handlers:
        return log_file

    # Configure root logger
    root_logger.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation (already has UTF-8 encoding)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler with UTF-8 encoding support
    # Try to get a UTF-8 wrapped stdout if possible
    console_stream = sys.stdout
    if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
        try:
            # Wrap stdout buffer with UTF-8 writer
            console_stream = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        except:
            pass
    
    console_handler = UTF8ConsoleHandler(console_stream)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set encoding for the logging module itself
    if hasattr(logging, 'basicConfig'):
        logging.basicConfig(encoding='utf-8', force=True)
    
    return log_file