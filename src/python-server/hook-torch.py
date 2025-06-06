# hook-torch.py
from PyInstaller.utils.hooks import collect_all, copy_metadata
import os

datas = []
binaries = []
hiddenimports = []

# Collect torch
torch_datas, torch_binaries, torch_hiddenimports = collect_all('torch')
datas.extend(torch_datas)
binaries.extend(torch_binaries)
hiddenimports.extend(torch_hiddenimports)

# Add metadata
datas.extend(copy_metadata('torch'))

# Ensure _C module is included
hiddenimports.extend([
    'torch._C',
    'torch._C._dynamo',
    'torch._dynamo',
])