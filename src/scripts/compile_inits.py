import os
import py_compile
import importlib.util
from pathlib import Path

def compile_init_py_files(root_dir):
    """
    Recursively find all __init__.py files in the directory tree starting at root_dir
    and compile them to __init__.pyc files in the same directory.
    """
    root_path = Path(root_dir).resolve()
    
    if not root_path.exists() or not root_path.is_dir():
        print(f"Error: {root_path} is not a valid directory")
        return
    
    print(f"Searching for __init__.py files in: {root_path}")
    compiled_count = 0
    
    for root, dirs, files in os.walk(root_path):
        if '__init__.py' in files:
            init_py = Path(root) / '__init__.py'
            init_pyc = init_py.parent / '__init__.pyc'
            
            try:
                # Get the Python version-specific cache tag
                cache_tag = importlib.util.cache_from_source('__init__.py')
                # Remove the cache directory part and just keep the filename
                cache_tag = os.path.basename(cache_tag)
                
                # Compile directly to the target .pyc file
                py_compile.compile(
                    str(init_py),
                    cfile=str(init_pyc),
                    doraise=True
                )
                print(f"Compiled: {init_py} -> {init_pyc}")
                compiled_count += 1
            except Exception as e:
                print(f"Error compiling {init_py}: {e}")
    
    print(f"\nCompilation complete. Compiled {compiled_count} __init__.py files.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = os.getcwd()
    
    compile_init_py_files(target_dir)