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
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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
          // Sort results by score in descending order (highest score first)
          const sortedResults = [...data.results].sort((a, b) => b.score - a.score)
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

  return (
    <main
      className={cn(
        "min-h-screen transition-all duration-300",
        sidebarCollapsed ? "ml-0" : "ml-64",
        "flex flex-col",
        className,
      )}
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
                  <Search className="absolute left-4 top-4 text-gray-400 w-5 h-5" />
                  <textarea
                    ref={textareaRef}
                    value={searchValue}
                    onChange={(e) => setSearchValue(e.target.value)}
                    onKeyDown={handleSearch}
                    placeholder="Search..."
                    rows={1}
                    className={cn(
                      "w-full pl-12 pr-4 py-3 rounded-2xl resize-none border-transparent",
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
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                          {groupedResults.map((group, index) => (
                            <FileCard
                              key={`${group.presentationName}-${index}`}
                              fileName={group.presentationName}
                              slideCount={group.slides.length}
                              versions={group.versions}
                              slides={group.slides} // Pass all slides for gallery
                              onCopyPath={handleCopyFilePath}
                            />
                          ))}
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
