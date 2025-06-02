// src/renderer/components/tools/model-audit/ModelAudit.tsx
import React, { useRef, useState, useCallback, useEffect } from 'react';
import { EventCard, EventType } from '../../events/EventCard';
import { FilePathInput } from '../../conversation/FilePathInput';
import { ModelAuditService, ChunkInfo, ExtractionResult } from '../../../services/modelAuditService';

export const ModelAudit: React.FC = () => {
  // Refs
  const messageEndRef = useRef<HTMLDivElement>(null);
  const modelAuditServiceRef = useRef<ModelAuditService | null>(null);

  // State
  const [systemEvents, setSystemEvents] = useState<{id: string, type: EventType, message: string}[]>([]);
  const [filePath, setFilePath] = useState('');
  const [error, setError] = useState('');
  const [analysisResult, setAnalysisResult] = useState('');
  
  // Service state
  const [isProcessing, setIsProcessing] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingComplete, setStreamingComplete] = useState(false);
  
  // Data state
  const [chunks, setChunks] = useState<string[]>([]);
  const [chunkInfo, setChunkInfo] = useState<ChunkInfo[]>([]);
  const [metadata, setMetadata] = useState<any>(null);
  const [markdown, setMarkdown] = useState('');

  const inputRef = useRef<HTMLInputElement>(null);

  // Add system event
  const addSystemEvent = useCallback((message: string, type: EventType = 'info') => {
    const id = `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSystemEvents(prev => [...prev, { id, type, message }]);
    return id;
  }, []);

  // Clear previous results
  const clearResults = useCallback(() => {
    setChunks([]);
    setChunkInfo([]);
    setMetadata(null);
    setMarkdown('');
    setAnalysisResult('');
    setStreamingComplete(false);
    setError('');
    setSystemEvents([]);
  }, []);

  // Initialize service with callbacks
  const initializeService = useCallback(() => {
    if (!modelAuditServiceRef.current) {
      modelAuditServiceRef.current = new ModelAuditService({
        onSystemEvent: (message: string, type: EventType) => {
          addSystemEvent(message, type);
        },
        onAnalysisChunk: (chunk: string, isDone: boolean) => {
          if (!isDone && chunk) {
            setAnalysisResult(prev => prev + chunk);
          }
        },
        onAnalysisError: (error: string) => {
          setError(error);
        },
        onProgressUpdate: (current: number, total: number) => {
          const progress = Math.round((current / total) * 100);
          console.log(`Progress: ${current}/${total} (${progress}%)`);
        }
      });
    }
    return modelAuditServiceRef.current;
  }, [addSystemEvent]);

  // Main handler for the entire process
  const handleSendMessage = useCallback(async () => {
    if (!filePath.trim()) return;

    try {
      // Clear previous results and errors
      clearResults();
      setIsProcessing(true);
      
      const service = initializeService();
      
      // Start the audit process
      const extractionResult = await service.startAudit(filePath);
      
      if (extractionResult) {
        // Store the extracted data in component state
        setChunks(extractionResult.chunks);
        setChunkInfo(extractionResult.chunkInfo);
        setMetadata(extractionResult.metadata);
        setMarkdown(extractionResult.markdown);
      }

      // Update component state based on service state
      setIsProcessing(service.isProcessing);
      setIsStreaming(service.isStreaming);
      setStreamingComplete(service.streamingComplete);
      setAnalysisResult(service.analysisResult);

    } catch (error: any) {
      console.error('Error in handleSendMessage:', error);
      setError(error.message || 'An unexpected error occurred');
      setIsProcessing(false);
      setIsStreaming(false);
      setStreamingComplete(true);
    }
  }, [filePath, clearResults, initializeService]);

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
  }, [systemEvents, analysisResult]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (modelAuditServiceRef.current) {
        modelAuditServiceRef.current.cancel();
      }
    };
  }, []);

  // Cancel current operation
  const handleCancel = useCallback(() => {
    const service = modelAuditServiceRef.current;
    if (service) {
      service.cancel();
      setIsProcessing(false);
      setIsStreaming(false);
    }
  }, []);

  // Sync service state with component state periodically
  useEffect(() => {
    if (!modelAuditServiceRef.current) return;

    const interval = setInterval(() => {
      const service = modelAuditServiceRef.current!;
      setIsProcessing(service.isProcessing);
      setIsStreaming(service.isStreaming);
      setStreamingComplete(service.streamingComplete);
      setAnalysisResult(service.analysisResult);
    }, 100);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-t border-gray-700/50 bg-[#0f1117]/50 backdrop-blur-sm">
        {error && (
          <div className="mb-2 text-sm text-red-400">
            {error}
          </div>
        )}
        
        {/* Show chunk information if available */}
        {chunks.length > 0 && !isProcessing && (
          <div className="mb-2 text-xs text-gray-400">
            Loaded: {chunks.length} chunks from {new Set(chunkInfo.flatMap(info => info.sheets)).size} sheets
          </div>
        )}

        <div className="flex items-center gap-2">
          <FilePathInput
            filePath={filePath}
            setFilePath={!isProcessing ? setFilePath : undefined}
            handleKeyDown={handleKeyDown}
            handleSubmit={handleSendMessage}
            isProcessing={isProcessing}
            inputRef={inputRef}
            className="flex-1"
          />
          
          {/* Cancel button when processing */}
          {isProcessing && (
            <button
              onClick={handleCancel}
              className="px-3 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
              title="Cancel current operation"
            >
              Cancel
            </button>
          )}
        </div>
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
            {event.message.includes('Analyzing your file') && analysisResult && (
              <div className="px-4 py-2 bg-gray-800/50 border-l-4 border-blue-500">
                <div className="whitespace-pre-wrap text-sm text-gray-200 font-mono">
                  {analysisResult}
                  {isStreaming && !streamingComplete && (
                    <span className="ml-1 inline-block w-2 h-4 bg-blue-500 animate-pulse"></span>
                  )}
                </div>
              </div>
            )}
          </React.Fragment>
        ))}
        
        {/* Scroll target */}
        <div ref={messageEndRef} />
      </div>
    </div>
  );
};

export default ModelAudit;