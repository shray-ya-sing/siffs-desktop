# hook-sentence_transformers.py
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas = []
binaries = []
hiddenimports = []

# Collect everything from sentence_transformers
st_datas, st_binaries, st_hiddenimports = collect_all('sentence_transformers')
datas.extend(st_datas)
binaries.extend(st_binaries)
hiddenimports.extend(st_hiddenimports)

# Add metadata
datas.extend(copy_metadata('sentence_transformers'))

# Ensure cross_encoder is included
hiddenimports.extend([
    'sentence_transformers.cross_encoder',
    'sentence_transformers.cross_encoder.CrossEncoder',
    'sentence_transformers.models',
    'sentence_transformers.util',
])