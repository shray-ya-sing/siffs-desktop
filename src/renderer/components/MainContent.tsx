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
import React, { useState, useRef, useEffect } from "react"
import { Search } from "lucide-react"
import { FileCard } from "./FileCard"

interface MainContentProps {
  className?: string
  children?: React.ReactNode
  sidebarCollapsed?: boolean
}

// Types for search results (same as SearchPage)
interface SlideResult {
  slide_id: string;
  score: number;
  file_path: string;
  file_name: string;
  slide_number: number;
  image_base64: string;
}

interface SearchResponse {
  success: boolean;
  query: string;
  results: SlideResult[];
  total_found: number;
  processing_time_ms: number;
  used_reranker: boolean;
  error?: string;
}

function cn(...classes: (string | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

// Utility functions for search result processing
function deduplicateSlides(results: SlideResult[]): SlideResult[] {
  const seen = new Map<string, SlideResult>()
  
  for (const result of results) {
    // Create unique key based on file path and slide number
    const key = `${result.file_path}:${result.slide_number}`
    
    // Keep the result with higher score if duplicate found
    if (!seen.has(key) || (seen.get(key)!.score < result.score)) {
      seen.set(key, result)
    }
  }
  
  // Return deduplicated results sorted by score
  return Array.from(seen.values()).sort((a, b) => b.score - a.score)
}

// Utility functions for grouping presentations
function extractVersionInfo(filename: string) {
  // Remove .pptx extension
  const nameWithoutExt = filename.replace(/\.pptx$/i, '')
  
  // Look for version pattern like "v1", "v2", "_v1", " v1", etc.
  const versionMatch = nameWithoutExt.match(/([\s_-]?)v(\d+)$/i)
  
  if (versionMatch) {
    const baseName = nameWithoutExt.substring(0, versionMatch.index).trim()
    const version = versionMatch[2]
    return { baseName, version, hasVersion: true }
  }
  
  return { baseName: nameWithoutExt, version: null, hasVersion: false }
}

function shouldGroupTogether(filename1: string, filename2: string): boolean {
  const info1 = extractVersionInfo(filename1)
  const info2 = extractVersionInfo(filename2)
  
  // If both have versions and same base name, group them
  if (info1.hasVersion && info2.hasVersion) {
    // Use Levenshtein distance to check similarity of base names
    return calculateSimilarity(info1.baseName.toLowerCase(), info2.baseName.toLowerCase()) > 0.8
  }
  
  // If one has version and the other doesn't, check if base name matches
  if (info1.hasVersion && !info2.hasVersion) {
    return calculateSimilarity(info1.baseName.toLowerCase(), info2.baseName.toLowerCase()) > 0.9
  }
  
  if (!info1.hasVersion && info2.hasVersion) {
    return calculateSimilarity(info1.baseName.toLowerCase(), info2.baseName.toLowerCase()) > 0.9
  }
  
  // If neither has version, they should be separate unless identical
  return info1.baseName.toLowerCase() === info2.baseName.toLowerCase()
}

function calculateSimilarity(str1: string, str2: string): number {
  const maxLength = Math.max(str1.length, str2.length)
  if (maxLength === 0) return 1
  
  const distance = levenshteinDistance(str1, str2)
  return (maxLength - distance) / maxLength
}

function levenshteinDistance(str1: string, str2: string): number {
  const matrix = []
  
  for (let i = 0; i <= str2.length; i++) {
    matrix[i] = [i]
  }
  
  for (let j = 0; j <= str1.length; j++) {
    matrix[0][j] = j
  }
  
  for (let i = 1; i <= str2.length; i++) {
    for (let j = 1; j <= str1.length; j++) {
      if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1]
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j] + 1
        )
      }
    }
  }
  
  return matrix[str2.length][str1.length]
}

interface GroupedResult {
  presentationName: string
  slides: SlideResult[]
  versions: string[]
}

function groupSearchResults(results: SlideResult[]): GroupedResult[] {
  const groups: { [key: string]: GroupedResult } = {}
  
  for (const result of results) {
    const versionInfo = extractVersionInfo(result.file_name)
    const presentationName = versionInfo.baseName
    const version = versionInfo.hasVersion ? `v${versionInfo.version}` : 'v1'
    
    // Find if this should be grouped with an existing group
    let foundGroup = false
    for (const [groupKey, group] of Object.entries(groups)) {
      if (shouldGroupTogether(result.file_name, group.slides[0].file_name)) {
        group.slides.push(result)
        if (!group.versions.includes(version)) {
          group.versions.push(version)
        }
        foundGroup = true
        break
      }
    }
    
    // If no existing group found, create a new one
    if (!foundGroup) {
      const groupKey = `${presentationName}_${Date.now()}_${Math.random()}`
      groups[groupKey] = {
        presentationName,
        slides: [result],
        versions: [version]
      }
    }
  }
  
  // Sort slides within each group by score (highest first)
  Object.values(groups).forEach(group => {
    group.slides.sort((a, b) => b.score - a.score)
    group.versions.sort() // Sort versions
  })
  
  // Convert to array and sort by highest score in each group
  return Object.values(groups).sort((a, b) => b.slides[0].score - a.slides[0].score)
}

export function MainContent({ className, children, sidebarCollapsed = false }: MainContentProps) {
  const [searchValue, setSearchValue] = useState("")
  const [searchState, setSearchState] = useState<"initial" | "searching" | "results">("initial")
  const [typewriterText, setTypewriterText] = useState("")
  const [searchResults, setSearchResults] = useState<SlideResult[]>([])
  const [groupedResults, setGroupedResults] = useState<GroupedResult[]>([])
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchStats, setSearchStats] = useState<{processing_time: number, total_found: number} | null>(null)
  const [copiedCardId, setCopiedCardId] = useState<string | null>(null)
  const [focusedCardIndex, setFocusedCardIndex] = useState<number>(-1)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const cardRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    if (searchState === "searching") {
      const text = "Searching..."
      let index = 0
      setTypewriterText("")

      const typewriterInterval = setInterval(() => {
        if (index < text.length) {
          setTypewriterText(text.slice(0, index + 1))
          index++
        } else {
          clearInterval(typewriterInterval)
        }
      }, 100)

      return () => clearInterval(typewriterInterval)
    }
  }, [searchState])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [searchValue])

  // Global keyboard shortcuts
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Ctrl+T to focus search
      if (e.ctrlKey && e.key === 't') {
        e.preventDefault()
        if (textareaRef.current) {
          textareaRef.current.focus()
          textareaRef.current.select()
          setFocusedCardIndex(-1) // Reset card focus when focusing search
        }
        return
      }

      // Only handle card navigation if we have search results and search bar is not focused
      if (searchState === 'results' && groupedResults.length > 0 && document.activeElement !== textareaRef.current) {
        switch (e.key) {
          case 'Tab':
            e.preventDefault()
            if (e.shiftKey) {
              // Shift+Tab - go to previous card
              setFocusedCardIndex(prev => {
                const newIndex = prev <= 0 ? groupedResults.length - 1 : prev - 1
                setTimeout(() => cardRefs.current[newIndex]?.focus(), 0)
                return newIndex
              })
            } else {
              // Tab - go to next card
              setFocusedCardIndex(prev => {
                const newIndex = prev >= groupedResults.length - 1 ? 0 : prev + 1
                setTimeout(() => cardRefs.current[newIndex]?.focus(), 0)
                return newIndex
              })
            }
            break

          case 'a':
            if (e.ctrlKey && focusedCardIndex >= 0) {
              e.preventDefault()
              // Trigger expand on focused card
              const expandButton = cardRefs.current[focusedCardIndex]?.querySelector('button[data-expand]') as HTMLButtonElement
              if (expandButton) {
                expandButton.click()
              }
            }
            break

          case 'c':
            if (e.ctrlKey && focusedCardIndex >= 0) {
              e.preventDefault()
              // Trigger copy path on focused card
              const focusedGroup = groupedResults[focusedCardIndex]
              if (focusedGroup && focusedGroup.slides.length > 0) {
                const slide = focusedGroup.slides[0]
                if (slide.file_path && handleCopyFilePath) {
                  handleCopyFilePath(slide.file_path, slide.file_name)
                }
              }
            }
            break
        }
      }
    }

    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [searchState, groupedResults.length, focusedCardIndex])

  // Function to handle copying file path to clipboard (from SearchPage)
  const handleCopyFilePath = async (filePath: string, fileName: string) => {
    try {
      console.log('📋 Copying file path to clipboard:', fileName, 'at path:', filePath)
      
      // Type-safe access to electron API
      const electronAPI = (window as any).electron || (window as any).electronAPI
      
      // Check if Electron API is available and has the fileSystem.copyToClipboard method
      if (electronAPI?.fileSystem?.copyToClipboard) {
        try {
          // Use Electron API if available
          const result = await electronAPI.fileSystem.copyToClipboard(filePath)
          
          if (result?.success) {
            console.log('✅ Successfully copied file path to clipboard:', fileName)
            // Show visual feedback
            setCopiedCardId(filePath)
            setTimeout(() => setCopiedCardId(null), 2000) // Hide after 2 seconds
            return
          } else {
            console.error('❌ Failed to copy via Electron API:', result?.error)
          }
        } catch (electronError) {
          console.error('❌ Electron API error:', electronError)
        }
      }
      
      // Fallback to browser clipboard API
      await navigator.clipboard.writeText(filePath)
      console.log('✅ Copied file path to clipboard using browser API:', fileName)
      
      // Show visual feedback
      setCopiedCardId(filePath)
      setTimeout(() => setCopiedCardId(null), 2000) // Hide after 2 seconds
      
    } catch (error) {
      console.error('❌ Error copying file path to clipboard:', error)
    }
  }

  const handleSearch = async (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && searchValue.trim()) {
      e.preventDefault()
      setSearchState("searching")
      setSearchError(null)
      setSearchResults([])
      setSearchStats(null)

      try {
        console.log('🔍 Searching for:', searchValue)
        
        const isDev = process.env.NODE_ENV === 'development'
        const apiBaseUrl = isDev ? 'http://localhost:3001' : 'http://localhost:5001'
        
        const response = await fetch(`${apiBaseUrl}/api/slides/search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: searchValue,
            top_k: 25, // Updated to match new limit
            use_reranker: true
          }),
        })
        
        if (!response.ok) {
          throw new Error(`Search failed: ${response.status} ${response.statusText}`)
        }
        
        const data: SearchResponse = await response.json()
        
        if (data.success) {
          console.log('✅ Search results:', data)
          
          // First, deduplicate the results to remove same file/slide duplicates
          const deduplicatedResults = deduplicateSlides(data.results)
          console.log(`🔄 Deduplicated: ${data.results.length} → ${deduplicatedResults.length} results`)
          
          // Sort results by score in descending order (highest score first)
          const sortedResults = [...deduplicatedResults].sort((a, b) => b.score - a.score)
          setSearchResults(sortedResults)
          
          // Group results by presentation
          const grouped = groupSearchResults(sortedResults)
          setGroupedResults(grouped)
          console.log('📊 Grouped results:', grouped)
          
          setSearchStats({
            processing_time: data.processing_time_ms,
            total_found: data.total_found
          })
          setSearchState("results")
        } else {
          throw new Error(data.error || 'Search failed')
        }
        
      } catch (error) {
        console.error('❌ Search error:', error)
        setSearchError(error instanceof Error ? error.message : 'Search failed')
        setSearchState("results") // Show error in results state
      }
    }
  }

  // Handle keyboard scrolling
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.target === e.currentTarget) { // Only handle if main content is focused
      const scrollAmount = 100 // pixels to scroll
      const mainElement = e.currentTarget as HTMLElement
      
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          mainElement.scrollTop += scrollAmount
          break
        case 'ArrowUp':
          e.preventDefault()
          mainElement.scrollTop -= scrollAmount
          break
        case 'PageDown':
          e.preventDefault()
          mainElement.scrollTop += mainElement.clientHeight * 0.8
          break
        case 'PageUp':
          e.preventDefault()
          mainElement.scrollTop -= mainElement.clientHeight * 0.8
          break
        case 'Home':
          if (e.ctrlKey) {
            e.preventDefault()
            mainElement.scrollTop = 0
          }
          break
        case 'End':
          if (e.ctrlKey) {
            e.preventDefault()
            mainElement.scrollTop = mainElement.scrollHeight
          }
          break
      }
    }
  }

  // Function to manually check for updates
  const checkForUpdates = () => {
    if (window.electron) {
      window.electron.updater.checkForUpdates()
        .then(result => {
          if (result.success) {
            toast({
              title: 'Checking for updates...',
              description: 'Looking for newer versions of the application.',
            })
          } else {
            toast({
              title: 'Update Check Failed',
              description: result.error || 'Could not check for updates',
              variant: 'destructive'
            })
          }
        })
        .catch(err => {
          toast({
            title: 'Error',
            description: 'Failed to communicate with updater',
            variant: 'destructive'
          })
        })
    }
  }

  return (
    <main
      className={cn(
        "transition-all duration-300",
        sidebarCollapsed ? "ml-0" : "ml-64",
        "flex flex-col overflow-y-auto overflow-x-hidden",
        "focus:outline-none", // Remove focus outline
        className,
      )}
      style={{
        height: 'calc(100vh - 32px)', // Account for 32px titlebar height
        scrollBehavior: 'smooth', // Smooth scrolling
        paddingTop: '8px' // Add small top padding
      }}
      tabIndex={0} // Make focusable for keyboard events
      onKeyDown={handleKeyDown}
    >
      <div className="flex-1 p-8 text-transparent bg-transparent">
        {children || (
          <div className="h-full max-w-6xl mx-auto">
            <div className="rounded-xl p-12 min-h-[calc(100vh-8rem)]">
              <div
                className={cn(
                  "transition-all duration-700 ease-out",
                  searchState === "initial" ? "flex justify-center items-center min-h-[60vh]" : "space-y-8",
                )}
              >
                {/* Search Bar */}
                <div
                  className={cn(
                    "relative w-full transition-all duration-700 ease-out",
                    searchState === "initial" ? "max-w-[75%]" : "max-w-2xl mx-auto",
                  )}
                >
                  {/* Hint text */}
                  <div className="text-center mb-3">
                    <span className="text-xs text-gray-400 font-medium tracking-wide">
                      Hit Ctrl+T to search
                    </span>
                  </div>
                  <textarea
                    ref={textareaRef}
                    value={searchValue}
                    onChange={(e) => setSearchValue(e.target.value)}
                    onKeyDown={handleSearch}
                    placeholder="Search..."
                    rows={1}
                    className={cn(
                      "w-full px-4 py-3 rounded-2xl resize-none border-transparent",
                      "border outline-none",
                      "focus:border-gray-300 focus:ring-2 focus:ring-gray-100",
                      "transition-all duration-200 ease-in-out",
                      "text-gray-700 placeholder-gray-400",
                      "backdrop-blur-sm bg-transparent",
                      "min-h-[48px] leading-relaxed",
                    )}
                    style={{
                      minWidth: "300px",
                      overflow: "hidden",
                    }}
                  />
                </div>

                {searchState === "searching" && (
                  <div className="text-center">
                    <div className="text-gray-500 text-lg font-medium">
                      {typewriterText}
                      <span className="animate-pulse">|</span>
                    </div>
                  </div>
                )}

                {searchState === "results" && (
                  <div className="space-y-6 animate-in fade-in-50 slide-in-from-bottom-4 duration-500">
                    {searchError ? (
                      <div className="text-center text-red-600 bg-red-50 p-4 rounded-lg">
                        <h3 className="font-semibold mb-2">Search Error</h3>
                        <p>{searchError}</p>
                      </div>
                    ) : searchResults.length === 0 ? (
                      <div className="text-center text-gray-500">
                        No slides found for "{searchValue}"
                      </div>
                    ) : (
                      <>  
                        <div className="text-center text-sm text-gray-500">
                          Found {searchStats?.total_found || searchResults.length} slides in {groupedResults.length} presentation{groupedResults.length !== 1 ? 's' : ''}
                          {searchStats && ` in ${searchStats.processing_time.toFixed(1)}ms`}
                        </div>
                        
                        {/* Keyboard navigation instructions */}
                        <div className="text-center mb-6">
                          <div className="text-xs text-gray-400 font-medium tracking-wide space-y-1">
                            <div>Use Tab to navigate between cards • Ctrl+A to expand • Ctrl+C to copy path</div>
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                          {groupedResults.map((group, index) => {
                            // Initialize card refs array
                            if (cardRefs.current.length !== groupedResults.length) {
                              cardRefs.current = new Array(groupedResults.length).fill(null)
                            }
                            
                            return (
                              <div
                                key={`${group.presentationName}-${index}`}
                                ref={el => { cardRefs.current[index] = el }}
                              >
                                <FileCard
                                  fileName={group.presentationName}
                                  slideCount={group.slides.length}
                                  versions={group.versions}
                                  slides={group.slides}
                                  onCopyPath={handleCopyFilePath}
                                  isFocused={focusedCardIndex === index}
                                  onFocus={() => setFocusedCardIndex(index)}
                                />
                              </div>
                            )
                          })}
                        </div>
                      </>
                    )}
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
