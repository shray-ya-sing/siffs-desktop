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
// ProviderDropdown.tsx
import { ChevronDown } from "lucide-react"

export interface ModelOption {
  id: string
  name: string
  provider: string
}

interface ProviderDropdownProps {
  value: string
  options: ModelOption[]
  onChange: (modelId: string) => void
  className?: string
  isOpen: boolean
  onToggle: (isOpen: boolean) => void
}

export function ProviderDropdown({ 
  value,
  options,
  onChange,
  className = "",
  isOpen,
  onToggle
}: ProviderDropdownProps) {
  const selectedOption = options.find(opt => opt.id === value) || options[0]

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => onToggle(!isOpen)}
        className={`
          flex items-center justify-between w-full px-3 py-2 rounded-3xl text-xs
          transition-all duration-200 border border-gray-700 
          hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-gray-600
          ${isOpen ? 'bg-gray-800/80' : 'bg-gray-900/80 hover:bg-gray-800/80'}
        `}
        style={{
          background: 'linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%)',
          minHeight: '40px',
        }}
      >
        <div className="flex items-center space-x-2">
          <span className="text-gray-300 text-xs">{selectedOption?.name}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-800/80 text-gray-400">
            {selectedOption?.provider}
          </span>
        </div>
        <ChevronDown 
          className={`w-3 h-3 text-gray-400 transition-transform ${isOpen ? 'transform rotate-180' : ''}`} 
        />
      </button>

      {isOpen && (
        <div 
          className={`
            absolute bottom-full mb-2 left-0 right-0 w-full rounded-xl shadow-lg
            bg-gray-900 border border-gray-700 py-1
            animate-fade-in max-h-60 overflow-y-auto z-50
          `}
          style={{
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)'
          }}
        >
          <div className="py-1">
            {options.map((model) => (
              <button
                key={model.id}
                onClick={() => {
                  onChange(model.id)
                  onToggle(false)
                }}
                className={`
                  w-full text-left px-4 py-2 text-sm flex items-center justify-between
                  hover:bg-gray-800/50 transition-colors duration-150
                  ${value === model.id ? 'text-blue-400' : 'text-gray-300'}
                `}
              >
                <span className="text-xs">{model.name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-800/80 text-gray-400">
                  {model.provider}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}