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