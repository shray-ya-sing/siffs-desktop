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
  const cancelRef = useRef<() => void>(null);

  // State
  const [systemEvents, setSystemEvents] = useState<{id: string, type: EventType, message: string}[]>([]);
  const [filePath, setFilePath] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [analysisResult, setAnalysisResult] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingComplete, setStreamingComplete] = useState(false);
  const [metadata, setMetadata] = useState('');
  let markdown = '';

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

  // Function to handle the typewriter effect
  const typeWriter = useCallback((text: string, speed: number, onComplete?: () => void) => {
    let i = 0;
    setAnalysisResult('');

    const typing = () => {
      if (i < text.length) {
        setAnalysisResult(prev => prev + text.charAt(i));
        i++;
        setTimeout(typing, speed);
      } else if (onComplete) {
        onComplete();
      }
    };

    typing();
  }, []);

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
      const metadataResponse = await apiService.extractExcelMetadata(filePath);
      // Check that markdown returned is non empty
      if (metadataResponse.data.markdown.trim() === '') {
        addSystemEvent('Failed to extract data from your file', 'error');
        return;
      }
      setMetadata(metadataResponse.data.markdown);
      markdown = metadataResponse.data.markdown;

      if (metadataResponse.data.status === 'success') {
        // Add completion event
        addSystemEvent('Data extracted successfully', 'completed');
      }
      else{
        addSystemEvent('Failed to extract data from your file', 'error');
      }   

    } catch (error) {
      // Add error event
      addSystemEvent('Failed to extract data from your file', 'error');
    } finally {
      setIsProcessing(false);
    }
    try {
        setIsProcessing(true); 
        setIsStreaming(true);
        setStreamingComplete(false);
        setAnalysisResult('');
        // Show loading state
        const loadingId = addSystemEvent('Analyzing your file...', 'reviewing');

        // Create a variable to store the full analysis text
        let fullAnalysis = '';
    
        // Call the analyze API
        const { cancel } = apiService.analyzeExcelMetadata(
          markdown, // or your metadata object
          (chunk, isDone) => {
            if (isDone) {
              setStreamingComplete(true);
              setIsStreaming(false);
              // Add completion event after a small delay
              setTimeout(() => {
                addSystemEvent('Analyzed file successfully', 'completed');
              }, 500);
              return;
            }
            
            // Append the new chunk to the full analysis
            fullAnalysis += chunk;
            
            // Update the typewriter with the full text so far
            // This will make it look like it's typing out the full response
            typeWriter(fullAnalysis, 10);
          },
          (error) => {
            console.error('Analysis error:', error);
            addSystemEvent(`Analysis error: ${error}`, 'error');
            setIsStreaming(false);
            setStreamingComplete(true);
          }
        );

        // Store the cancel function in case we need to abort
        
        cancelRef.current = cancel;

        // Clean up on unmount
        return () => {
          if (cancelRef.current) {
            cancelRef.current();
          }
        };

      } catch (error) {
        console.error('Error during analysis:', error);
        addSystemEvent('Failed to analyze file', 'error');
        setIsStreaming(false);
        setStreamingComplete(true);
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
          <React.Fragment key={event.id}>
            <EventCard
              type={event.type}
              message={event.message}
              className="w-full"
              showBadge={true}
              isStreaming={index === systemEvents.length - 1 && isProcessing}
            />
            {event.message === 'Analyzing your file...' && analysisResult && (
              <div className="px-4 py-2 bg-gray-800/50 border-l-4 border-blue-500">
                <div className="whitespace-pre-wrap text-sm text-gray-200">
                  {analysisResult}
                  {isStreaming && !streamingComplete && (
                    <span className="ml-1 inline-block w-2 h-4 bg-blue-500 animate-pulse"></span>
                  )}
                </div>
              </div>
            )}
          </React.Fragment>
      ))}            
      </div>
    </div>
  );
};

export default ModelAudit;