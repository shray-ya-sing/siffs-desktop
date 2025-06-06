# Hook for transformers and related packages to ensure they are included in the PyInstaller bundle 

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

def hook(hook_api):
    # Core packages to include
    packages = [
        'transformers',
        'sentence_transformers',
        'tokenizers',
        'torch',
        'numpy',
        'tqdm',
        'requests',
        'packaging',
        'filelock',
        'huggingface_hub'
    ]
    
    # Initialize collections
    datas = []
    hiddenimports = []
    binaries = []
    
    # Special handling for transformers to get all submodules
    try:
        # Get all submodules
        transformers_submodules = collect_submodules('transformers', recursive=True)
        hiddenimports.extend(transformers_submodules)
        
        # Collect data files for transformers
        transformers_data = collect_data_files('transformers')
        datas.extend(transformers_data)
        
        # Special handling for tokenizers
        tokenizers_data = collect_data_files('tokenizers')
        datas.extend(tokenizers_data)
        
        # Collect for other packages
        for package in packages:
            if package not in ['transformers', 'tokenizers']:  # Already handled
                try:
                    pkg_data, pkg_binaries, pkg_hidden = collect_all(package)
                    datas.extend(pkg_data)
                    binaries.extend(pkg_binaries)
                    hiddenimports.extend(pkg_hidden)
                except Exception as e:
                    print(f"Warning: Failed to collect {package}: {e}")
                    
        # Add any additional specific modules that might be missed
        additional_modules = [
            'torch._dynamo',
            'torch._C',
            'transformers.modeling_utils',
            'transformers.configuration_utils',
            'transformers.tokenization_utils',
        ]
        hiddenimports.extend(additional_modules)
        
    except Exception as e:
        print(f"Error in transformers hook: {e}")
    
    return {
        'datas': datas,
        'binaries': binaries,
        'hiddenimports': hiddenimports,
    }