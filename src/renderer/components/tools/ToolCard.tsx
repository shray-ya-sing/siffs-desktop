import { Tool } from "../../lib/integrationTools"
import { ComponentType, SVGProps } from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from "../../lib/utils"

interface ToolCardProps {
  tool: Tool
  className?: string
  onStart?: () => void 
}



export default function ToolCard({ tool, className, onStart }: ToolCardProps) {
  const IconComponent = tool.icon

  return (
    <div 
      className={cn(
        "relative overflow-hidden h-[300px] rounded-lg shadow-md group transition-all duration-300 hover:shadow-lg",
        "bg-gray-100 border border-gray-200", // Changed to light gray background
        className   
      )}
    >
      <div className="absolute inset-0 p-6 flex flex-col">
        <div 
          className="w-12 h-12 rounded-lg flex items-center justify-center mb-4" 
          style={{ backgroundColor: `${tool.color}` }}
        >
          <IconComponent className="w-6 h-6"/>
        </div>
        
        <h2 className="text-lg font-semibold mb-1 text-gray-900">
          {tool.name}
        </h2>
        
        <div className="text-sm text-[#0a0f1a] mb-4"> {/* Changed to dark blue-black */}
          {tool.category}
        </div>

        {/* Start Button */}
        <button
          onClick={onStart}
          className="flex items-center text-gray-500 hover:text-gray-700 transition-colors duration-200 text-sm font-medium mb-4 self-start"
        >
          Start <ArrowRight className="ml-1 w-4 h-4" />
        </button>       
        
        
        <div className="mt-4 pt-3 border-t border-gray-200 group-hover:opacity-100 opacity-0 transition-opacity duration-300">
          <button 
            className="text-sm font-medium hover:underline"
            style={{ color: tool.color }}
          >
            Description →
          </button>
          <div className="flex-1 overflow-hidden">
            <div className="transition-all duration-300 ease-in-out max-h-[3.6em] group-hover:max-h-[calc(100%-2rem)] overflow-hidden">
                <p className="text-sm text-gray-700"> {/* Slightly darker text for better readability */}
                {tool.description}
                </p>
            </div>
        </div>
        </div>
      </div>
    </div>
  )
}