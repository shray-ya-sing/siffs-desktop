# This file makes the directory a Python package
import sys
import os

# Set default encoding
if sys.version_info[0] >= 3:
    import builtins
    builtins.__dict__['_'] = lambda s: s
    if sys.stdout.encoding is None or sys.stdout.encoding.upper() != 'UTF-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')