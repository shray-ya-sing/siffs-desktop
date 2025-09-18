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