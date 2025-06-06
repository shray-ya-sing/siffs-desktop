import os
import py_compile
import importlib.util
from pathlib import Path

def compile_py_files():
    """
    Compile Python files in the transformers directory to .pyc files.
    Specifically targets __init__.py and modeling_bert.py files.
    Uses a hardcoded path to the transformers directory.
    """
    # Hardcoded path to the transformers directory
    transformers_path = Path("C:/Users/shrey/projects/cori-apps/cori_app/resources/python/python-server/_internal/transformers")
    
    if not transformers_path.exists() or not transformers_path.is_dir():
        print(f"Error: Transformers directory not found at {transformers_path}")
        return
    
    print(f"Searching for Python files in: {transformers_path}")
    compiled_count = 0
    
    # Files we want to compile
    target_files = ['__init__.py', 'modeling_bert.py']
    
    for root, dirs, files in os.walk(transformers_path):
        for target_file in target_files:
            if target_file in files:
                py_file = Path(root) / target_file
                pyc_file = py_file.with_suffix('.pyc')
                
                try:
                    # Get the Python version-specific cache tag
                    cache_tag = importlib.util.cache_from_source(target_file)
                    # Remove the cache directory part and just keep the filename
                    cache_tag = os.path.basename(cache_tag)
                    
                    # Compile directly to the target .pyc file
                    py_compile.compile(
                        str(py_file),
                        cfile=str(pyc_file),
                        doraise=True
                    )
                    print(f"Compiled: {py_file} -> {pyc_file}")
                    compiled_count += 1
                except Exception as e:
                    print(f"Error compiling {py_file}: {e}")
    
    print(f"\nCompilation complete. Compiled {compiled_count} Python files.")

if __name__ == "__main__":
    compile_py_files()