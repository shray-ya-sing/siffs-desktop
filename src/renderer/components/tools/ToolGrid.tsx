// src/renderer/components/tools/ToolGrid.tsx
import { Tool } from "../../lib/integrationTools"
import ToolCard from "./ToolCard"
import { useNavigate } from "react-router-dom"

interface ToolGridProps {
  tools: Tool[]
  className?: string
}

export default function ToolGrid({ tools = [], className = "" }: ToolGridProps) {
  const navigate = useNavigate();
  
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
            if (tool.id === 'excel-model-audit') {
              navigate('/tools/model-audit');
            }
            if (tool.id === 'excel-model-qa') {
              navigate('/tools/model-qa');
            }
            if (tool.id === 'edit-excel-model') {
              navigate('/tools/model-edit');
            }
            if (tool.id === 'create-excel-model') {
              navigate('/tools/model-create');
            }
          }} 
        />
      ))}
    </div>
  )
}