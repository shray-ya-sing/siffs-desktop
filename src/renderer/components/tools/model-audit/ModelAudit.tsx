// src/renderer/components/tools/model-audit/ModelAudit.tsx
import React, { useRef, useState, useCallback, useEffect } from 'react';
import { MessageInput } from '../../conversation/MessageInput';
import { Message } from '../../../types/message';
import { EventCard, EventType } from '../../events/EventCard';
import { FilePathInput } from '../../conversation/FilePathInput';
import apiService from '../../../services/pythonApiService';

export const ModelAudit: React.FC = () => {
  // Refs
  const messageEndRef = useRef<HTMLDivElement>(null);

  // State
  const [systemEvents, setSystemEvents] = useState<{id: string, type: EventType, message: string}[]>([]);
  const [filePath, setFilePath] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');

  // Add system event
  const addSystemEvent = useCallback((message: string, type: EventType = 'info') => {
    const id = `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSystemEvents(prev => [...prev, { id, type, message }]);
    return id;
  }, []);

  const inputRef = useRef<HTMLInputElement>(null);

  // Validate file path
  const validateFilePath = (path: string): boolean => {
    return path.trim().toLowerCase().endsWith('.xlsx');
  };

  // Handle sending a message
  const handleSendMessage = useCallback(async () => {
    if (!filePath.trim() || isProcessing) return;

    // Validate file path
    if (!validateFilePath(filePath)) {
        setError('File path must end with .xlsx. Don\'t include quotes around the file name.');
        return;
      }

    setError('');
    setIsProcessing(true);  
    // Add initial system event
    addSystemEvent('Starting model audit...', 'info');
  
    try {
      // Show loading state
      const loadingId = addSystemEvent('Getting the data from your file...', 'extracting');
  
      // Call the mock API
      await apiService.extractExcelMetadata(filePath);
      
      // Add completion event
      addSystemEvent('Data extracted successfully', 'completed');
      
    } catch (error) {
      // Add error event
      addSystemEvent('Failed to extract data from your file', 'error');
    } finally {
      setIsProcessing(false);
    }
    try {
        setIsProcessing(true); 
        // Show loading state
        const loadingId = addSystemEvent('Analyzing your file...', 'reviewing');
    
        // Call the mock API
        await apiService.mockApiCall(
          true, // success
          10000, // 10 second delay
          { result: 'success', step: 1 }
        );
        
        // Add completion event
        addSystemEvent('Analyzed file successfully', 'completed');
        
      } catch (error) {
        // Add error event
        addSystemEvent('Failed to analyze file', 'error');
      } finally {
        setIsProcessing(false);
      }
  }, [filePath, isProcessing, addSystemEvent]);

  // Handle key down in textarea
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  // Auto-scroll to bottom when messages or events change
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [systemEvents]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-t border-gray-700/50 bg-[#0f1117]/50 backdrop-blur-sm">
      {error && (
          <div className="mb-2 text-sm text-red-400">
            {error}
          </div>
        )}
        <FilePathInput
          filePath={filePath}
          setFilePath={!isProcessing ? setFilePath : undefined}
          handleKeyDown={handleKeyDown}
          handleSubmit={handleSendMessage}
          isProcessing={isProcessing}
          inputRef={inputRef}
          className="w-full"
        />
      </div>

      <div className="flex-1 overflow-y-auto">
            {systemEvents.map((event, index) => (
            <EventCard
                key={event.id}
                type={event.type}
                message={event.message}
                className="w-full"
                showBadge={true}
                isStreaming={index === systemEvents.length - 1 && isProcessing}
            />
            ))}
      </div>
    </div>
  );
};

export default ModelAudit;