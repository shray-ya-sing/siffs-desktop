/*
 * Siffs - Fast File Search Desktop Application
 * Copyright (C) 2025  Siffs
 * 
 * Contact: github.suggest277@passinbox.com
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
import { FileItem } from '../../folder-view/FileExplorer'
import { FileSpreadsheet } from 'lucide-react'
import { forwardRef } from 'react'

interface MentionDropdownProps {
  files: FileItem[]
  selectedIndex: number
  position: { top: number; left: number }
  onSelect: (file: FileItem) => void
  className?: string
}

const MentionDropdown = forwardRef<HTMLDivElement, MentionDropdownProps>(
  ({ files, selectedIndex, position, onSelect, className = '' }, ref) => {
    if (files.length === 0) return null

    return (
      <div
        ref={ref}
        className={`absolute z-50 w-64 max-h-60 overflow-y-auto bg-gray-800 border border-gray-700 rounded-md shadow-lg ${className}`}
        style={{
          top: `${position.top}px`,
          left: `${position.left}px`,
        }}
      >
        {files.map((file, index) => (
          <div
            key={file.path}
            className={`p-2 hover:bg-gray-700 cursor-pointer ${
              index === selectedIndex ? 'bg-gray-700' : ''
            }`}
            onClick={() => onSelect(file)}
          >
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-green-500 flex-shrink-0" />
              <span className="text-sm truncate">{file.name}</span>
            </div>
            <div className="text-xs text-gray-400 truncate pl-6">{file.path}</div>
          </div>
        ))}
      </div>
    )
  }
)

MentionDropdown.displayName = 'MentionDropdown'

export default MentionDropdown