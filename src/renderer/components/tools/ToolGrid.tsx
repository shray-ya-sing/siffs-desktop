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