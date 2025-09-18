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