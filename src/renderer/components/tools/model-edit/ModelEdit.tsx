import React, { useState } from 'react';
import { ToolInstructions } from '../ToolInstructions';

export const ModelEdit: React.FC = () => {
  const [filePath, setFilePath] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Get the file path from the file input
      const path = (file as any).path || file.name; // Fallback to name if path is not available
      setFilePath(path);
    }
  };

  const handleSubmit = () => {
    if (!filePath) {
      setError('Please select a file to edit');
      return;
    }
    // Handle file processing here
    setIsProcessing(true);
    setError('');
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4">
        <ToolInstructions toolId="edit-excel-model" />
      </div>
      
      <div className="p-4 flex-1">
        <div className="max-w-2xl mx-auto">
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Edit Excel Model</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Select Excel File
                </label>
                <div className="flex space-x-2">
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload"
                    disabled={isProcessing}
                  />
                  <label
                    htmlFor="file-upload"
                    className="flex-1 px-4 py-2 bg-slate-700/50 hover:bg-slate-700/70 text-slate-200 rounded-md cursor-pointer border border-slate-600/50 text-sm"
                  >
                    {filePath || 'Choose file...'}
                  </label>
                  <button
                    onClick={handleSubmit}
                    disabled={!filePath || isProcessing}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isProcessing ? 'Opening...' : 'Open'}
                  </button>
                </div>
                {error && (
                  <p className="mt-1 text-sm text-red-400">{error}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelEdit;