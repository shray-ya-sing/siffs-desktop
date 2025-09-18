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
// hooks/useMention.ts
import { useState, useRef, useEffect, useCallback } from 'react'
import { FileItem } from '../folder-view/FileExplorer'

export const useMention = (fileTree: FileItem[]) => {
  const [showMentions, setShowMentions] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0)
  const [mentionPosition, setMentionPosition] = useState({ top: 0, left: 0 })
  const mentionResults = useRef<FileItem[]>([])

  const findExcelFiles = useCallback((query: string): FileItem[] => {
    const results: FileItem[] = []
    
    const searchFiles = (items: FileItem[]) => {
      items.forEach(item => {
        if (item.isDirectory && item.children) {
          searchFiles(item.children)
        } else if (item.name.toLowerCase().endsWith('.xlsx') && 
                  item.name.toLowerCase().includes(query.toLowerCase())) {
          results.push(item)
        }
      })
    }
    
    searchFiles(fileTree)
    return results
  }, [fileTree])

  const handleMentionInput = (
    e: React.ChangeEvent<HTMLTextAreaElement>,
    textarea: HTMLTextAreaElement | null
  ) => {
    const value = e.target.value
    const atIndex = value.lastIndexOf('@')
    
    if (atIndex !== -1 && (atIndex === 0 || value[atIndex - 1] === ' ')) {
      const query = value.substring(atIndex + 1)
      setMentionQuery(query)
      mentionResults.current = findExcelFiles(query)
      
      if (textarea) {
        const cursorPosition = textarea.selectionStart
        const textBeforeCursor = value.substring(0, cursorPosition)
        const lines = textBeforeCursor.split('\n')
        const currentLine = lines[lines.length - 1]
        
        const tempEl = document.createElement('div')
        tempEl.style.position = 'absolute'
        tempEl.style.visibility = 'hidden'
        tempEl.style.whiteSpace = 'pre'
        tempEl.style.font = window.getComputedStyle(textarea).font
        document.body.appendChild(tempEl)
        tempEl.textContent = currentLine.substring(0, atIndex - (textBeforeCursor.length - currentLine.length))
        
        const left = textarea.offsetLeft + tempEl.offsetWidth
        const lineHeight = parseInt(window.getComputedStyle(textarea).lineHeight)
        const top = textarea.offsetTop + (lines.length * lineHeight)
        
        document.body.removeChild(tempEl)
        
        setMentionPosition({ top, left })
        setShowMentions(true)
        setSelectedMentionIndex(0)
      }
    } else {
      setShowMentions(false)
    }
  }

  const handleMentionKeyDown = (
    e: React.KeyboardEvent,
    onSelect: (file: FileItem) => void
  ) => {
    if (!showMentions) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedMentionIndex(prev => 
          Math.min(prev + 1, mentionResults.current.length - 1)
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedMentionIndex(prev => Math.max(prev - 1, 0))
        break
      case 'Enter':
        e.preventDefault()
        if (mentionResults.current[selectedMentionIndex]) {
          onSelect(mentionResults.current[selectedMentionIndex])
          setShowMentions(false)
        }
        break
      case 'Escape':
        setShowMentions(false)
        break
    }
  }

  return {
    showMentions,
    mentionQuery,
    selectedMentionIndex,
    mentionPosition,
    mentionResults: mentionResults.current,
    handleMentionInput,
    handleMentionKeyDown,
    setShowMentions
  }
}