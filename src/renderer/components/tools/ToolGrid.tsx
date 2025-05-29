// src/renderer/components/tools/ToolGrid.tsx
import { Tool } from "../../lib/integrationTools"
import ToolCard from "./ToolCard"

interface ToolGridProps {
  tools: Tool[]
  className?: string
}

export default function ToolGrid({ tools = [], className = "" }: ToolGridProps) {
  if (!tools || tools.length === 0) {
    return <div className="text-gray-400">No tools available</div>
  }

  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 ${className}`}>
      {tools.map((tool) => (
        <ToolCard 
          key={tool.id} 
          tool={tool}
          onStart={() => {
            // Handle start action for this specific tool
            console.log(`Starting ${tool.name}`);
          }} 
        />
      ))}
    </div>
  )
}