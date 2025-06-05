"use client"

import React, { useEffect } from "react"
import { Button } from "../ui/button"
import { Textarea } from "../ui/textarea"
import { TechArrowUpIcon } from "../tech-icons/TechIcons"

interface SimpleMessageInputProps {
  input: string;
  setInput: (value: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  handleSendClick: () => void;
  isTyping: boolean;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  className?: string;
  disabled?: boolean;
}

export function SimpleMessageInput({
  input,
  setInput,
  handleKeyDown,
  handleSendClick,
  isTyping,
  textareaRef,
  disabled = false,
  className,
}: SimpleMessageInputProps) {
  // Auto-resize textarea as content grows
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "40px"
      const scrollHeight = textareaRef.current.scrollHeight
      textareaRef.current.style.height = `${Math.min(scrollHeight, 120)}px`
    }
  }, [input, textareaRef])

  return (
    <div className={className}>
      <div className="relative">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Send a message..."
          className="bg-[#1a2035]/30 border-[#ffffff0f] pr-10 text-sm backdrop-blur-md shadow-[inset_0_0_20px_rgba(0,0,0,0.1)] placeholder:text-gray-500 min-h-[40px] max-h-[120px] resize-none py-2 px-3 transition-all duration-300 focus:shadow-[0_0_15px_rgba(59,130,246,0.2)] gradient-border"
          style={{ overflow: "hidden" }}
          disabled={isTyping || disabled}
        />
        <Button
          onClick={handleSendClick}
          className="absolute right-1 top-1 h-7 w-7 p-0 bg-blue-600/80 hover:bg-blue-700/80 text-white rounded-md backdrop-blur-sm shadow-[0_0_10px_rgba(59,130,246,0.3)] transition-all duration-300 hover:shadow-[0_0_15px_rgba(59,130,246,0.5)] disabled:opacity-50 disabled:hover:bg-blue-600/80 disabled:hover:shadow-[0_0_10px_rgba(59,130,246,0.3)]"
          disabled={!input.trim() || isTyping || disabled}
        >
          <TechArrowUpIcon />
        </Button>
      </div>
    </div>
  )
}
