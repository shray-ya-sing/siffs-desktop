import { Tool } from "../../lib/integrationTools"
import { ArrowRight, ExternalLink } from 'lucide-react';
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
        "relative overflow-hidden rounded-xl border border-slate-700/50 bg-slate-800/50 backdrop-blur-sm",
        "transition-all duration-300 hover:border-slate-600/50 hover:bg-slate-800/70",
        "flex flex-col h-full",
        className   
      )}
    >
      <div className="p-6 flex-1 flex flex-col">
        {/* Header with icon and title */}
        <div className="flex items-start justify-between mb-4">
          <div 
            className="w-12 h-12 rounded-xl flex items-center justify-center" 
            style={{ 
              backgroundColor: `${tool.color}20`, // 20% opacity of the tool color
              color: tool.color
            }}
          >
            <IconComponent className="w-6 h-6" />
          </div>
          <button className="text-slate-400 hover:text-white transition-colors">
            <ExternalLink className="w-5 h-5" />
          </button>
        </div>
        
        {/* Title and Category */}
        <h2 className="text-lg font-semibold text-white mb-1">
          {tool.name}
        </h2>
        <div className="text-sm text-slate-400 mb-4">
          {tool.category}
        </div>

        {/* Description (always visible) */}
        <p className="text-slate-300 text-sm mb-6 flex-1">
          {tool.description}
        </p>

        {/* Start Button */}
        <button
          onClick={onStart}
          className={cn(
            "w-full mt-auto flex items-center justify-between px-4 py-2 rounded-lg",
            "text-sm font-medium transition-colors duration-200",
            "bg-slate-700/50 hover:bg-slate-600/50 text-white"
          )}
        >
          <span>Start</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}