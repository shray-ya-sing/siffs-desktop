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
import React, { useRef, useState, useCallback, useEffect } from 'react';
import { ToolInstructions } from '../ToolInstructions';
import { SimpleMessageInput } from '../../conversation/SimpleMessageInput';
import { FilePathInput } from '../../conversation/FilePathInput';
import { ModelCreateService } from '../../../services/tools/modelCreateService';

export const ModelCreate: React.FC = () => {
  // Refs
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modelCreateServiceRef = useRef<ModelCreateService | null>(null);

  // State
  const [filePath, setFilePath] = useState('');
  const [instructions, setInstructions] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [statusMessage, setStatusMessage] = useState('');

  // Initialize the service
  useEffect(() => {
    modelCreateServiceRef.current = new ModelCreateService({
      onMessage: (message) => {
        setStatusMessage(message);
      },
      onError: (error) => {
        setError(error);
        setIsProcessing(false);
      },
      onProcessingChange: (processing) => {
        setIsProcessing(processing);
      },
      onProgress: (step, message) => {
        setStatusMessage(`${step}: ${message}`);
      },
      onComplete: (result) => {
        setStatusMessage('✓ Model creation completed successfully!');
        // Reset form after successful completion
        setTimeout(() => {
          setFilePath('');
          setInstructions('');
          setIsSubmitted(false);
          setStatusMessage('');
        }, 2000);
      }
    });

    return () => {
      modelCreateServiceRef.current?.cleanup();
    };
  }, []);

  // Handle file path submission
  const handleFilePathSubmit = useCallback(() => {
    if (!filePath.trim()) {
      setError('Please enter a file path');
      return;
    }
    
    setError('');
    setStatusMessage('File selected. Please enter your instructions below.');
    setIsSubmitted(true);
  }, [filePath]);

  const handleFilePathKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isProcessing) {
      e.preventDefault();
      handleFilePathSubmit();
    }
  }, [handleFilePathSubmit, isProcessing]);

  // Handle instruction submission
  const handleSubmitInstructions = useCallback(() => {
    if (!instructions.trim()) {
      setError('Please enter instructions');
      return;
    }

    if (!isSubmitted) {
      setError('Please process a file first');
      return;
    }

    setError('');
    setStatusMessage('Processing your request...');
    modelCreateServiceRef.current?.processExcelFile(filePath, instructions);
  }, [instructions, isSubmitted, filePath]);

  // Handle key down in textarea
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isProcessing) {
        handleSubmitInstructions();
      }
    }
  }, [handleSubmitInstructions, isProcessing]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4">
        <ToolInstructions toolId="create-excel-model" />
      </div>
      
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Create New Excel Model</h2>
            
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Excel File Path
                </label>
                <FilePathInput
                  filePath={filePath}
                  setFilePath={setFilePath}
                  handleSubmit={handleFilePathSubmit}
                  handleKeyDown={handleFilePathKeyDown}
                  isProcessing={isProcessing}
                  isSubmitted={isSubmitted}
                  inputRef={fileInputRef}
                  disabled={isProcessing}
                  className="w-full"
                />
              </div>

              {isSubmitted && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Instructions for Model Creation
                  </label>
                  <SimpleMessageInput
                    input={instructions}
                    setInput={setInstructions}
                    handleKeyDown={handleKeyDown}
                    handleSendClick={handleSubmitInstructions}
                    isTyping={isProcessing}
                    textareaRef={textareaRef}
                    disabled={isProcessing}
                    className="w-full"
                  />
                </div>
              )}

              {(statusMessage || error) && (
                <div className={`text-sm px-3 py-2 rounded ${
                  error ? 'bg-red-900/30 text-red-400' : 'bg-blue-900/30 text-blue-400'
                }`}>
                  {error || statusMessage}
                </div>
              )}

              {isProcessing && (
                <div className="flex items-center justify-center py-2">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelCreate;