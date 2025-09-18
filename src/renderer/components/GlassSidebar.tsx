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
import React, { useState } from "react"
import { Plus, Folder, ChevronRight, X, Menu, ChevronLeft, Loader } from "lucide-react"
import { slideProcessingService } from '../services/slide-processing.service'

interface GlassSidebarProps {
  className?: string
  children?: React.ReactNode
  collapsed?: boolean
  onToggle?: () => void
}

function cn(...classes: (string | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export function GlassSidebar({ className, children, collapsed = false, onToggle }: GlassSidebarProps) {
  const [folders, setFolders] = useState<{ name: string; id: string; path: string }[]>([])
  const [showInput, setShowInput] = useState(false)
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [indexingStatus, setIndexingStatus] = useState<string>("")
  const [indexingResults, setIndexingResults] = useState<any>(null)
  const [typewriterText, setTypewriterText] = useState("")

  const handleNewFolderClick = () => {
    setShowInput(true)
  }

  const handleSubmitFolder = async () => {
    if (inputValue.trim() && !isLoading) {
      setIsLoading(true)
      setIndexingStatus('')
      setIndexingResults(null)
      
      // Strip quotes from the input path
      const cleanedPath = inputValue.trim().replace(/^["'](.+)["']$/, '$1')

      try {
        console.log('Starting folder indexing for:', cleanedPath)
        
        const result = await slideProcessingService.processFolderIndex(cleanedPath)
        
        console.log('Indexing completed:', result)
        setIndexingResults(result)
        setIndexingStatus(`Successfully indexed ${result.files_processed} files with ${result.slides_processed} slides`)
        
        const newFolder = {
          name: cleanedPath.split(/[\\\\/]/).pop() || cleanedPath,
          id: Date.now().toString(),
          path: cleanedPath
        }
        setFolders((prev) => [...prev, newFolder])
        
        // Save to localStorage
        localStorage.setItem('connectedFolder', cleanedPath)
        localStorage.setItem('connectedFolderName', newFolder.name)
        
        setInputValue("")
        setShowInput(false)
      } catch (error) {
        console.error('Indexing failed:', error)
        setIndexingStatus(`Indexing failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
      } finally {
        setIsLoading(false)
      }
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSubmitFolder()
    }
    if (e.key === "Escape") {
      setShowInput(false)
      setInputValue("")
      setIndexingStatus("")
    }
  }

  const handleRemoveFolder = (folderId: string) => {
    setFolders((prev) => prev.filter((folder) => folder.id !== folderId))
    // Also remove from localStorage if it's the current connected folder
    const removedFolder = folders.find(f => f.id === folderId)
    if (removedFolder) {
      const savedFolder = localStorage.getItem('connectedFolder')
      if (savedFolder === removedFolder.path) {
        localStorage.removeItem('connectedFolder')
        localStorage.removeItem('connectedFolderName')
      }
    }
  }

  // Typewriter effect for processing text
  React.useEffect(() => {
    if (isLoading && !indexingStatus) {
      const text = "Processing Folder..."
      let index = 0
      setTypewriterText("")

      const typewriterInterval = setInterval(() => {
        if (index < text.length) {
          setTypewriterText(text.slice(0, index + 1))
          index++
        } else {
          // Reset and start over for loop effect
          setTimeout(() => {
            index = 0
            setTypewriterText("")
          }, 1000)
        }
      }, 100)

      return () => clearInterval(typewriterInterval)
    } else {
      setTypewriterText("")
    }
  }, [isLoading, indexingStatus])

  // Load saved folder on component mount
  React.useEffect(() => {
    const savedFolder = localStorage.getItem('connectedFolder')
    const savedFolderName = localStorage.getItem('connectedFolderName')
    if (savedFolder && savedFolderName) {
      const existingFolder = {
        name: savedFolderName,
        id: 'saved-' + Date.now(),
        path: savedFolder
      }
      setFolders([existingFolder])
    }
  }, [])

  return (
    <>
      <button
        onClick={onToggle}
        className={cn(
          "fixed top-12 z-50 p-2 hover:bg-white/90 rounded-lg border transition-all duration-300 bg-transparent border-none border-transparent shadow-none",
          collapsed ? "left-4" : "left-72",
        )}
      >
        {collapsed ? <Menu className="w-4 h-4 text-gray-600" /> : <ChevronLeft className="w-4 h-4 text-gray-600" />}
      </button>

      <aside
        className={cn(
          "fixed left-0 top-0 h-screen z-40 transition-all duration-300",
          collapsed ? "w-0 -translate-x-full" : "w-64 translate-x-0",
          "border-r border-sidebar-border/30",
          "flex flex-col overflow-hidden",
          className,
        )}
      >
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-3 mt-12">
            {/* New Folder Button */}
            <button
              onClick={handleNewFolderClick}
              className="flex items-center gap-3 w-full p-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-white/50 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>New Folder</span>
            </button>

            {showInput && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 p-2 rounded-lg border border-gray-200 bg-transparent">
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Enter folder path..."
                    className="flex-1 text-sm bg-transparent border-none outline-none placeholder-gray-400"
                    autoFocus
                  />
                  <button
                    onClick={handleSubmitFolder}
                    className="p-1 text-gray-500 hover:text-gray-700 transition-all duration-200"
                    disabled={isLoading}
                  >
                    {isLoading ? <Loader className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
                  </button>
                </div>
                
                {(typewriterText || indexingStatus) && (
                  <div className={cn(
                    "text-xs px-2 py-1",
                    typewriterText 
                      ? 'text-gray-500 bg-transparent' // Grey text for typewriter effect
                      : indexingStatus.includes('failed') 
                        ? 'text-red-600 bg-red-50 rounded' 
                        : 'text-green-600 bg-green-50 rounded'
                  )}>
                    {typewriterText || indexingStatus}
                  </div>
                )}
                
                {indexingResults && (
                  <div className="text-xs text-gray-500 px-2">
                    Files: {indexingResults.files_processed} | Slides: {indexingResults.slides_processed}
                    {indexingResults.failed_files?.length > 0 && (
                      <div className="text-yellow-600">
                        {indexingResults.failed_files.length} files failed
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {folders.length > 0 && (
              <div className="space-y-1">
                {folders.map((folder) => (
                  <div
                    key={folder.id}
                    className="flex items-center justify-between gap-3 p-2 text-sm text-gray-700 hover:bg-white/50 rounded-lg cursor-pointer transition-colors group"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <Folder className="w-4 h-4 text-gray-400 group-hover:text-gray-500" />
                      <span className="truncate" title={folder.path}>{folder.name}</span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleRemoveFolder(folder.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-all duration-200"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {children}
        </div>
      </aside>
    </>
  )
}
