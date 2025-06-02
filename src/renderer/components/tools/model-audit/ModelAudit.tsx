// src/renderer/components/tools/model-audit/ModelAudit.tsx
import React, { useRef, useState, useCallback, useEffect } from 'react';
import { MessageInput } from '../../conversation/MessageInput';
import { Message } from '../../../types/message';
import { EventCard, EventType } from '../../events/EventCard';
import { FilePathInput } from '../../conversation/FilePathInput';
import apiService from '../../../services/pythonApiService';

// Define types for better type safety
interface ChunkInfo {
  chunk_index: number;
  token_count: number;
  line_count: number;
  character_count: number;
  sheets: string[];
  table_rows: number;
  has_dependency_summary: boolean;
  has_header: boolean;
  token_efficiency: number;
}

export const ModelAudit: React.FC = () => {
  // Refs
  const messageEndRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<(() => void) | null>(null);

  // State
  const [systemEvents, setSystemEvents] = useState<{id: string, type: EventType, message: string}[]>([]);
  const [filePath, setFilePath] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [analysisResult, setAnalysisResult] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingComplete, setStreamingComplete] = useState(false);
  
  // New state for chunks
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

  // Validate file path
  const validateFilePath = (path: string): boolean => {
    return path.trim().toLowerCase().endsWith('.xlsx');
  };

  // Clear previous results
  const clearResults = useCallback(() => {
    setChunks([]);
    setChunkInfo([]);
    setMetadata(null);
    setMarkdown('');
    setAnalysisResult('');
    setStreamingComplete(false);
    setError('');
  }, []);

  // Handle extraction phase
  const handleExtraction = useCallback(async (): Promise<boolean> => {
    try {
      addSystemEvent('Getting the data from your file...', 'extracting');
      
      const metadataResponse = await apiService.extractExcelMetadata(filePath);
      
      // Validate response
      if (metadataResponse.data.status !== 'success') {
        addSystemEvent('Failed to extract data from your file', 'error');
        return false;
      }

      // Check that chunks were created
      if (!metadataResponse.data.chunks || metadataResponse.data.chunks.length === 0) {
        addSystemEvent('No data chunks created from your file', 'error');
        return false;
      }

      // Check that chunks contain data
      const nonEmptyChunks = metadataResponse.data.chunks.filter(chunk => chunk.trim().length > 0);
      if (nonEmptyChunks.length === 0) {
        addSystemEvent('Failed to extract meaningful data from your file', 'error');
        return false;
      }

      // Store the extracted data
      setChunks(metadataResponse.data.chunks);
      setChunkInfo(metadataResponse.data.chunk_info || []);
      setMetadata(metadataResponse.data.metadata);
      setMarkdown(metadataResponse.data.markdown || '');

      // Calculate statistics for user feedback
      const totalTokens = metadataResponse.data.chunk_info?.reduce((sum, info) => sum + info.token_count, 0) || 0;
      const sheetsFound = new Set(
        metadataResponse.data.chunk_info?.flatMap(info => info.sheets) || []
      ).size;

      addSystemEvent(
        `Data extracted successfully - ${metadataResponse.data.chunks.length} chunks created (${totalTokens.toLocaleString()} tokens, ${sheetsFound} sheets)`, 
        'completed'
      );

      return true;

    } catch (error) {
      console.error('Extraction error:', error);
      addSystemEvent('Failed to extract data from your file', 'error');
      return false;
    }
  }, [filePath, addSystemEvent]);

  // Handle analysis phase
  const handleAnalysis = useCallback(async (): Promise<void> => {
    if (chunks.length === 0) {
      addSystemEvent('No chunks available for analysis', 'error');
      return;
    }

    try {
      setIsStreaming(true);
      setStreamingComplete(false);
      setAnalysisResult('');

      // Show analysis progress
      const totalTokens = chunkInfo.reduce((sum, info) => sum + info.token_count, 0);
      addSystemEvent(
        `Analyzing your file (${chunks.length} chunks, ${totalTokens.toLocaleString()} tokens)...`, 
        'reviewing'
      );

      // Track analysis progress
      let fullAnalysis = '';
      let chunksProcessed = 0;
      
      // Call the analyze chunks API
      const { cancel } = apiService.analyzeExcelChunks(
        chunks,
        (chunk, isDone) => {
          if (isDone) {
            setStreamingComplete(true);
            setIsStreaming(false);
            setIsProcessing(false);
            
            // Add completion event after a small delay
            setTimeout(() => {
              addSystemEvent('Analysis completed successfully', 'completed');
            }, 500);
            return;
          }
          
          // Handle chunk content
          if (chunk) {
            // Check if this is a chunk separator/header
            if (chunk.includes('--- ANALYZING CHUNK') || chunk.includes('--- END OF CHUNK')) {
              // Track progress
              if (chunk.includes('--- ANALYZING CHUNK')) {
                chunksProcessed++;
                const progress = Math.round((chunksProcessed / chunks.length) * 100);
                console.log(`Processing chunk ${chunksProcessed}/${chunks.length} (${progress}%)`);
              }
            }
            
            // Append chunk to analysis result
            fullAnalysis += chunk;
            setAnalysisResult(prev => prev + chunk);
          }
        },
        (error) => {
          console.error('Analysis error:', error);
          addSystemEvent(`Analysis error: ${error}`, 'error');
          setIsStreaming(false);
          setStreamingComplete(true);
          setIsProcessing(false);
        }
      );

      // Store the cancel function
      cancelRef.current = cancel;

    } catch (error) {
      console.error('Error during analysis:', error);
      addSystemEvent('Failed to analyze file', 'error');
      setIsStreaming(false);
      setStreamingComplete(true);
      setIsProcessing(false);
    }
  }, [chunks, chunkInfo, addSystemEvent]);

  // Main handler for the entire process
  const handleSendMessage = useCallback(async () => {
    if (!filePath.trim() || isProcessing) return;

    // Validate file path
    if (!validateFilePath(filePath)) {
      setError('File path must end with .xlsx. Don\'t include quotes around the file name.');
      return;
    }

    // Clear previous results and errors
    clearResults();
    setIsProcessing(true);
    
    // Add initial system event
    addSystemEvent('Starting model audit...', 'info');

    try {
      // Phase 1: Extract data and create chunks
      const extractionSuccess = await handleExtraction();
      
      if (!extractionSuccess) {
        setIsProcessing(false);
        return;
      }

      // Small delay to let the user see the extraction completion
      await new Promise(resolve => setTimeout(resolve, 500));

      // Phase 2: Analyze the chunks
      await handleAnalysis();

    } catch (error) {
      console.error('Error in handleSendMessage:', error);
      addSystemEvent('Unexpected error during processing', 'error');
      setIsProcessing(false);
      setIsStreaming(false);
      setStreamingComplete(true);
    }
  }, [filePath, isProcessing, clearResults, addSystemEvent, handleExtraction, handleAnalysis]);

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
      if (cancelRef.current) {
        cancelRef.current();
        cancelRef.current = null;
      }
    };
  }, []);

  // Cancel current operation
  const handleCancel = useCallback(() => {
    if (cancelRef.current) {
      cancelRef.current();
      cancelRef.current = null;
    }
    setIsProcessing(false);
    setIsStreaming(false);
    addSystemEvent('Operation cancelled by user', 'info');
  }, [addSystemEvent]);

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