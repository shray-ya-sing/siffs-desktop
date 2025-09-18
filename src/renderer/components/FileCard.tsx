import React, { useState } from "react"
import { ChevronRight, Expand, X } from "lucide-react"

interface FileCardProps {
  fileName: string
  slideCount: number
  versions?: string[]
  className?: string
  filePath?: string
  slideNumber?: number
  imageBase64?: string
  score?: number
  onCopyPath?: (filePath: string, fileName: string) => void
}

function cn(...classes: (string | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export function FileCard({ 
  fileName, 
  slideCount, 
  versions = ["v1", "v2"], 
  className,
  filePath,
  slideNumber,
  imageBase64,
  score,
  onCopyPath
}: FileCardProps) {
  const [currentSlide, setCurrentSlide] = useState(0)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % slideCount)
  }

  const openModal = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
  }

  const handleCardClick = () => {
    if (filePath && onCopyPath) {
      onCopyPath(filePath, fileName)
    }
  }

  return (
    <>
      <div
        className={cn(
          "w-full aspect-square backdrop-blur-sm rounded-lg border border-gray-200/50 p-6 flex flex-col bg-transparent",
          "transition-all duration-300 ease-out hover:scale-105 hover:border-gray-300/60 hover:shadow-lg",
          "cursor-pointer group min-w-0 relative", // added relative positioning
          className,
        )}
        onClick={handleCardClick}
      >
        <button
          onClick={openModal}
          className="absolute top-3 right-3 p-1.5 rounded-full backdrop-blur-sm border border-gray-200/50 opacity-0 group-hover:opacity-100 transition-all duration-200 hover:bg-white shadow-sm z-10 bg-transparent"
        >
          <Expand className="w-3 h-3 text-gray-600" />
        </button>

        {/* Image Stage - Center focal point */}
        <div className="flex-1 min-h-[50%] relative bg-white rounded-lg mb-4 overflow-hidden border border-gray-100/50">
          {/* Slide image or placeholder */}
          {imageBase64 ? (
            <img 
              src={`data:image/png;base64,${imageBase64}`}
              alt={`Slide ${slideNumber || currentSlide + 1} from ${fileName}`}
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="w-full h-full bg-white flex items-center justify-center">
              <div className="text-gray-400 text-sm font-medium">
                Slide {slideNumber || currentSlide + 1}/{slideCount}
              </div>
            </div>
          )}

          {/* Navigation chevron */}
          {slideCount > 1 && !slideNumber && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                nextSlide()
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full bg-white/90 backdrop-blur-sm border border-gray-200/50 opacity-0 group-hover:opacity-100 transition-all duration-200 hover:bg-white shadow-sm"
            >
              <ChevronRight className="w-3 h-3 text-gray-600" />
            </button>
          )}
        </div>

        {/* File metadata */}
        <div className="space-y-3 min-w-0">
          {/* Versions indicator or score */}
          <div className="flex gap-1 flex-wrap">
            {score !== undefined ? (
              <div className="px-2 py-1 text-xs rounded-full bg-blue-100/50 text-blue-600 border border-blue-200/30 whitespace-nowrap">
                {(score * 100).toFixed(1)}%
              </div>
            ) : (
              versions.map((version, index) => (
                <div
                  key={version}
                  className="px-2 py-1 text-xs rounded-full bg-gray-100/50 text-gray-500 border border-gray-200/30 whitespace-nowrap"
                >
                  {version}
                </div>
              ))
            )}
          </div>

          {/* Slide count */}
          <div className="text-sm text-gray-400">
            {slideNumber ? `Slide ${slideNumber}` : `${slideCount} slide${slideCount !== 1 ? "s" : ""}`}
          </div>
        </div>

        {/* File name at bottom */}
        <div className="mt-4 pt-3 border-t border-gray-200/30 min-w-0">
          <div className="text-sm text-gray-500 break-words font-medium" title={fileName}>
            {fileName}
          </div>
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-8">
          <div className="bg-white/95 backdrop-blur-md rounded-2xl border border-gray-200/50 shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-auto">
            {/* Modal header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200/30">
              <h2 className="text-xl font-semibold text-gray-800">{fileName}</h2>
              <button onClick={closeModal} className="p-2 rounded-full hover:bg-gray-100/50 transition-colors">
                <X className="w-5 h-5 text-gray-600" />
              </button>
            </div>

            {/* Modal content - expanded card */}
            <div className="p-8">
              {/* Large image stage */}
              <div className="aspect-video bg-white rounded-xl mb-6 border border-gray-200/50 flex items-center justify-center">
                {imageBase64 ? (
                  <img 
                    src={`data:image/png;base64,${imageBase64}`}
                    alt={`Slide ${slideNumber || currentSlide + 1} from ${fileName}`}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="text-gray-400 text-lg font-medium">
                    Slide {slideNumber || currentSlide + 1}/{slideCount}
                  </div>
                )}
              </div>

              {/* Navigation and metadata */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex gap-2">
                  {score !== undefined ? (
                    <div className="px-3 py-1.5 text-sm rounded-full bg-blue-100/50 text-blue-600 border border-blue-200/30">
                      Score: {(score * 100).toFixed(1)}%
                    </div>
                  ) : (
                    versions.map((version) => (
                      <div
                        key={version}
                        className="px-3 py-1.5 text-sm rounded-full bg-gray-100/50 text-gray-600 border border-gray-200/30"
                      >
                        {version}
                      </div>
                    ))
                  )}
                </div>

                {slideCount > 1 && !slideNumber && (
                  <button
                    onClick={nextSlide}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100/50 hover:bg-gray-200/50 transition-colors text-gray-700"
                  >
                    Next Slide
                    <ChevronRight className="w-4 h-4" />
                  </button>
                )}
              </div>

              <div className="text-gray-500">
                {slideNumber ? `Slide ${slideNumber} of ${slideCount}` : `${slideCount} slide${slideCount !== 1 ? "s" : ""} total`}
              </div>
              
              {filePath && (
                <div className="mt-4 text-xs text-gray-400 break-all">
                  Path: {filePath}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
