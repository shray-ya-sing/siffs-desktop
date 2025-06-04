
import React, { useEffect } from "react"
import { Button } from "../ui/button"
import { Input } from "../ui/input"
import { TechArrowUpIcon } from "../tech-icons/TechIcons"

interface FilePathInputProps {
  filePath: string;
  setFilePath?: (value: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  handleSubmit: () => void;
  isProcessing: boolean;
  isSubmitted?: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
  className?: string;
}

export function FilePathInput({
  filePath,
  setFilePath,
  handleKeyDown,
  handleSubmit,
  isProcessing,
  isSubmitted = false,
  inputRef,
  className,
}: FilePathInputProps) {
  // Auto-focus the input when component mounts
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [inputRef]);

  return (
    <div className={className}>
      <div className="relative">
        <Input
          ref={inputRef}
          value={filePath}
          onChange={(e) => !isSubmitted && setFilePath?.(e.target.value)}
          onKeyDown={isSubmitted ? undefined : handleKeyDown}
          placeholder={isSubmitted ? 'File path submitted' : 'Enter file path...'}
          className="bg-[#1a2035]/30 border-[#ffffff0f] pr-10 text-sm backdrop-blur-md shadow-[inset_0_0_20px_rgba(0,0,0,0.1)] placeholder:text-gray-500 h-10 resize-none py-2 px-3 transition-all duration-300 focus:shadow-[0_0_15px_rgba(59,130,246,0.2)] gradient-border disabled:opacity-70 disabled:cursor-not-allowed"
          disabled={isProcessing || isSubmitted}
        />
        <Button
          onClick={isSubmitted ? undefined : handleSubmit}
          className={`absolute right-1 top-1 h-7 w-7 p-0 rounded-md backdrop-blur-sm transition-all duration-300 ${
            isSubmitted
              ? 'bg-green-600/80 text-white cursor-default'
              : 'bg-blue-600/80 hover:bg-blue-700/80 text-white hover:shadow-[0_0_15px_rgba(59,130,246,0.5)]'
          } shadow-[0_0_10px_rgba(59,130,246,0.3)] disabled:opacity-50 disabled:hover:bg-blue-600/80 disabled:hover:shadow-[0_0_10px_rgba(59,130,246,0.3)]`}
          disabled={!filePath.trim() || isProcessing || isSubmitted}
        >
          <TechArrowUpIcon />
        </Button>
      </div>
    </div>
  )
}