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
import { cn } from "../../lib/utils"

interface ToolInstructionsProps {
  toolId: string
  className?: string
}

const toolInstructions = {
  'excel-model-audit': {
    title: 'Excel Model Audit',
    description: 'Comprehensive auditing and error checking for Excel financial models',
    steps: [
      'Upload your Excel model file',
      'The system will automatically analyze formulas and structure',
      'Review the highlighted issues and recommendations',    ]
  },
  'excel-model-qa': {
    title: 'Excel Model QA',
    description: 'Question answering and analysis for Excel financial models',
    steps: [
      'Upload your Excel model or connect to an existing one',
      'Ask questions about the model\'s structure or data',
      'Get instant answers with relevant references',
      'Explore suggested insights and validations'
    ]
  },
  'edit-excel-model': {
    title: 'Edit Excel Model',
    description: 'Make changes to an existing Excel model',
    steps: [
      'Open an existing Excel model',
      'Make your changes using the built-in editor',
      'Validate your changes with real-time feedback',
      'Save your updated model'
    ]
  },
  'create-excel-model': {
    title: 'Create Excel Model',
    description: 'Create a new Excel model from scratch',
    steps: [
      'Select a template or start from scratch',
      'Define your model structure and formulas',
      'Add data and configure calculations',
      'Save and validate your new model'
    ]
  }
}

export function ToolInstructions({ toolId, className }: ToolInstructionsProps) {
  const instructions = toolInstructions[toolId as keyof typeof toolInstructions] || {
    title: 'Instructions',
    description: 'No instructions available for this tool',
    steps: []
  }

  return (
    <div className={cn("mb-6 bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 backdrop-blur-sm", className)}>
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white mb-1">{instructions.title}</h2>
          <p className="text-slate-300 text-sm mb-4">{instructions.description}</p>
          
          <div className="space-y-2">
            {instructions.steps.map((step, index) => (
              <div key={index} className="flex items-start">
                <div className="flex-shrink-0 h-5 w-5 flex items-center justify-center rounded-full bg-slate-700/50 text-slate-300 text-xs font-medium mr-2 mt-0.5">
                  {index + 1}
                </div>
                <span className="text-slate-300 text-sm">{step}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
