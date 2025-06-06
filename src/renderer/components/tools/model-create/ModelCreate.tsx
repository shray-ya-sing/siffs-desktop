import React, { useState } from 'react';
import { ToolInstructions } from '../ToolInstructions';

export const ModelCreate: React.FC = () => {
  const [modelName, setModelName] = useState('');
  const [template, setTemplate] = useState('blank');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!modelName.trim()) {
      setError('Please enter a model name');
      return;
    }
    
    // Handle model creation here
    setIsCreating(true);
    setError('');
    console.log('Creating model:', { modelName, template });
    
    // Simulate API call
    setTimeout(() => {
      setIsCreating(false);
      // Navigate to editor or show success message
    }, 1500);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4">
        <ToolInstructions toolId="create-excel-model" />
      </div>
      
      <div className="p-4 flex-1">
        <div className="max-w-2xl mx-auto">
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-6">Create New Excel Model</h2>
            
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="modelName" className="block text-sm font-medium text-slate-300 mb-1">
                  Model Name
                </label>
                <input
                  type="text"
                  id="modelName"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-md text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., Financial Forecast Q3 2023"
                  disabled={isCreating}
                />
              </div>
              
              <div>
                <label htmlFor="template" className="block text-sm font-medium text-slate-300 mb-1">
                  Template
                </label>
                <select
                  id="template"
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-md text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isCreating}
                >
                  <option value="blank">Blank Workbook</option>
                  <option value="financial">Financial Model</option>
                  <option value="budget">Budget Planner</option>
                  <option value="inventory">Inventory Tracker</option>
                </select>
              </div>
              
              {error && (
                <div className="text-red-400 text-sm">{error}</div>
              )}
              
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isCreating || !modelName.trim()}
                  className={`w-full py-2 px-4 rounded-md text-white font-medium ${
                    isCreating || !modelName.trim() 
                      ? 'bg-blue-600/50 cursor-not-allowed' 
                      : 'bg-blue-600 hover:bg-blue-700'
                  } transition-colors`}
                >
                  {isCreating ? 'Creating...' : 'Create Model'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelCreate;