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
"use client"

import React, { useRef, useState, useCallback, useEffect } from "react"
import { Button } from "../ui/button"
import { Textarea } from "../ui/textarea"
import {
  TechArrowUpIcon,
  TechAttachmentIcon,
  TechImageIcon,
  TechFileIcon,
  TechXIcon, // Using our new X icon for close
} from "../tech-icons/TechIcons"

interface MessageInputProps {
  input: string;
  setInput: (value: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  handleSendClick: () => void;
  handleAttachment: (type: "general" | "image" | "file") => void;
  isTyping: boolean;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  className?: string;
  attachedFiles?: {
    images: File[];
    documents: File[];
  };
  onRemoveFile?: (type: "image" | "document", index: number) => void;
  disabled?: boolean;
  onFileUpload?: (files: File[]) => void;
  uploadProgress?: { [key: string]: number };
}

export function MessageInput({
  input,
  setInput,
  handleKeyDown,
  handleSendClick,
  handleAttachment,
  isTyping,
  textareaRef,
  className,
  attachedFiles = { images: [], documents: [] },
  onRemoveFile,
  disabled = false,
  onFileUpload,
  uploadProgress,
}: MessageInputProps) {
  // Auto-resize textarea as content grows
  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to auto to get the correct scrollHeight
      textareaRef.current.style.height = "40px"
      // Set the height to scrollHeight to expand the textarea
      const scrollHeight = textareaRef.current.scrollHeight
      textareaRef.current.style.height = `${Math.min(scrollHeight, 120)}px`
    }
  }, [input, textareaRef])

// Count total attached files
const totalAttachedFiles = attachedFiles.images.length + attachedFiles.documents.length;

// State to manage drag-and-drop
const dragCounter = useRef(0);
const [isDragging, setIsDragging] = useState(false);

// Handle file drop
const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
  e.preventDefault();
  e.stopPropagation();

  const files = Array.from(e.dataTransfer.files);
  if (onFileUpload) onFileUpload(files);
  setIsDragging(false);
}, [onFileUpload]);

// Handle drag over
const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
  e.preventDefault();
  e.stopPropagation();
};

// Handle drag enter
const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
  e.preventDefault();
  e.stopPropagation();
  dragCounter.current++;
  setIsDragging(true);
};

// Handle drag leave
const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
  dragCounter.current--;
  if (dragCounter.current === 0) {
    setIsDragging(false);
  }
};

return (
  <div className={className}
    onDrop={handleDrop}
    onDragOver={handleDragOver}
    onDragEnter={handleDragEnter}
    onDragLeave={handleDragLeave}
  >
    {/* Dragging Overlay */}
    {isDragging && (
      <div className="absolute inset-0 bg-blue-800 bg-opacity-50 flex justify-center items-center pointer-events-none">
        <span className="text-xl text-blue-200">Drop files here</span>
      </div>
    )}

    {/* Attached Files Display */}
    {totalAttachedFiles > 0 && (
      <div className="mb-2 flex flex-wrap gap-2">
        {attachedFiles.images.map((file, index) => (
          <div 
            key={`img-${index}`} 
            className="flex items-center px-2 py-1 bg-blue-600/20 rounded-md text-xs text-blue-300 border border-blue-600/30 relative"
          >
            <img src={URL.createObjectURL(file)} alt="preview" className="mr-1.5 w-12 h-12 object-cover" />
            <span className="truncate max-w-[80px]">{file.name}</span>
            {onRemoveFile && (
              <button 
                onClick={() => onRemoveFile("image", index)}
                className="ml-1.5 text-blue-300/70 hover:text-blue-300"
              >
                <TechXIcon className="h-3 w-3" />
              </button>
            )}
            {uploadProgress && uploadProgress[file.name] !== undefined && (
              <div className="absolute bottom-0 left-0 right-0 bg-blue-500 h-0.5" style={{ width: `${uploadProgress[file.name]}%` }} />
            )}
          </div>
        ))}
        {attachedFiles.documents.map((file, index) => (
          <div 
            key={`doc-${index}`} 
            className="flex items-center px-2 py-1 bg-purple-600/20 rounded-md text-xs text-purple-300 border border-purple-600/30 relative"
          >
            <TechFileIcon className="mr-1.5 h-3 w-3" />
            <span className="truncate max-w-[80px]">{file.name}</span>
            {onRemoveFile && (
              <button 
                onClick={() => onRemoveFile("document", index)}
                className="ml-1.5 text-purple-300/70 hover:text-purple-300"
              >
                <TechXIcon className="h-3 w-3" />
              </button>
            )}
            {uploadProgress && uploadProgress[file.name] !== undefined && (
              <div className="absolute bottom-0 left-0 right-0 bg-purple-500 h-0.5" style={{ width: `${uploadProgress[file.name]}%` }} />
            )}
          </div>
        ))}
      </div>
    )}

    <div className="relative">
      <Textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Send a message..."
        className="bg-[#1a2035]/30 border-[#ffffff0f] pr-10 text-sm backdrop-blur-md shadow-[inset_0_0_20px_rgba(0,0,0,0.1)] placeholder:text-gray-500 min-h-[40px] max-h-[120px] resize-none py-2 px-3 transition-all duration-300 focus:shadow-[0_0_15px_rgba(59,130,246,0.2)] gradient-border"
        style={{ overflow: "hidden" }}
      />
      <Button
        onClick={handleSendClick}
        className="absolute right-1 top-1 h-7 w-7 p-0 bg-blue-600/80 hover:bg-blue-700/80 text-white rounded-md backdrop-blur-sm shadow-[0_0_10px_rgba(59,130,246,0.3)] transition-all duration-300 hover:shadow-[0_0_15px_rgba(59,130,246,0.5)] disabled:opacity-50 disabled:hover:bg-blue-600/80 disabled:hover:shadow-[0_0_10px_rgba(59,130,246,0.3)]"
        disabled={!input.trim() && totalAttachedFiles === 0 || disabled}
      >
        <TechArrowUpIcon />
      </Button>
    </div>
    
    {/* File Attachment Buttons */}
    <div className="flex items-center mt-2 space-x-2">
      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-xs bg-[#1a2035]/20 hover:bg-[#1a2035]/40 text-gray-300 rounded-md backdrop-blur-sm border border-[#ffffff0f] transition-all duration-300"
        onClick={() => handleAttachment("file")}
        disabled={isTyping || disabled}
      >
        <TechAttachmentIcon className="mr-1.5" />
        <span>Attach</span>
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-xs bg-[#1a2035]/20 hover:bg-[#1a2035]/40 text-gray-300 rounded-md backdrop-blur-sm border border-[#ffffff0f] transition-all duration-300"
        onClick={() => handleAttachment("image")}
        disabled={isTyping || disabled}
      >
        <TechImageIcon className="mr-1.5" />
        <span>Image</span>
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-xs bg-[#1a2035]/20 hover:bg-[#1a2035]/40 text-gray-300 rounded-md backdrop-blur-sm border border-[#ffffff0f] transition-all duration-300"
        onClick={() => handleAttachment("file")}
        disabled={isTyping || disabled}
      >
        <TechFileIcon className="mr-1.5" />
        <span>File</span>
      </Button>
    </div>
  </div>
  )
}
