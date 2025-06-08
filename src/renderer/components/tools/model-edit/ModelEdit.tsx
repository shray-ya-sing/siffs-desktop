import React, { useRef, useState, useCallback, useEffect } from 'react';
import { SimpleMessageInput } from '../../conversation/SimpleMessageInput';
import { ConversationHistory } from '../../conversation/ConversationHistory';
import { FilePathInput } from '../../conversation/FilePathInput';
import { ToolInstructions } from '../ToolInstructions';
import { Message } from '../../../types/message';
import { ModelEditService } from '../../../services/tools/modelEditService';

interface ModelEditCallbacks {
  onMessage: (message: string) => void;
  onError: (error: string) => void;
  onProcessingChange: (isProcessing: boolean) => void;
  onTypingStart: () => void;
  onTypingEnd: () => void;
  onDataReady: (isReady: boolean) => void;
  onEditComplete: (result: any) => void;
}



export const ModelEdit: React.FC = () => {
  // Refs
  const messageEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modelEditServiceRef = useRef<ModelEditService | null>(null);

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [filePath, setFilePath] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState('');
  const [isDataReady, setIsDataReady] = useState(false);

  // Initialize service
  const initializeService = useCallback(() => {
    if (!modelEditServiceRef.current) {
      modelEditServiceRef.current = new ModelEditService({
        onMessage: (message) => {
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: message,
            timestamp: Date.now().toString()
          }]);
        },
        onError: setError,
        onProcessingChange: setIsProcessing,
        onTypingStart: () => setIsTyping(true),
        onTypingEnd: () => setIsTyping(false),
        onDataReady: setIsDataReady,
        onEditComplete: (result) => {
          // Handle edit completion if needed
          console.log('Edit completed:', result);
        }
      });
    }
    return modelEditServiceRef.current;
  }, []);

  // Handle file path submission
  const handleFilePathSubmit = useCallback(async () => {
    if (!filePath.trim()) {
      setError('Please enter a file path');
      return;
    }
    
    setError('');
    const service = initializeService();
    await service.processExcelFile(filePath);
  }, [filePath, initializeService]);

  const handleFilePathKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isProcessing) {
      e.preventDefault();
      handleFilePathSubmit();
    }
  }, [handleFilePathSubmit, isProcessing]);

  // Handle sending a message
  const handleSendMessage = useCallback(async () => {
    if (!input.trim()) return;
    if (!isDataReady) {
      setError('Please load an Excel file first');
      return;
    }
  
    const service = initializeService();
    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: Date.now().toString()
    };
  
    setMessages(prev => [...prev, userMessage]);
    setInput('');
  
    try {
      await service.processEditRequest(input);
    } catch (error: any) {
      setError(error.message || 'An error occurred while processing your request');
    }
  }, [input, isDataReady, initializeService]);

  useEffect(() => {
    if (isDataReady && messages.length === 0) {
      setMessages([{
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: 'I\'ve loaded your Excel file. What changes would you like to make?',
        timestamp: Date.now().toString()
      }]);
    }
  }, [isDataReady, messages.length]);

  // Handle key down in textarea
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isProcessing) {
        handleSendMessage();
      }
    }
  }, [handleSendMessage, isProcessing]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (modelEditServiceRef.current) {
        modelEditServiceRef.current.cleanup();
      }
    };
  }, []);

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Instructions on how to use the tool */}
      <div className="px-4 pt-4">
        <ToolInstructions toolId="edit-excel-model" />
      </div>

      {/* Scrollable conversation area */}
      <div className="px-4 pt-4">
        <ConversationHistory
          messages={messages}
          messageGroups={[]}
          isTyping={isTyping}
          activeTypingIndex={null}
          displayedText={{}}
          scrollAreaRef={scrollAreaRef}
          messageEndRef={messageEndRef}
          systemEvents={[]}
          className="flex-1"
        />
        <div className="h-4" />
      </div>
      
      {/* Fixed input area at the bottom */}
      <div className="sticky bottom-0 p-4 border-t border-gray-700/50 bg-[#0f1117]/50 backdrop-blur-sm space-y-3">
        {error && (
          <div className="mb-2 text-sm text-red-400">
            {error}
          </div>
        )}

        <div className="space-y-3">
          <FilePathInput
            filePath={filePath}
            setFilePath={setFilePath}
            handleSubmit={handleFilePathSubmit}
            isProcessing={isProcessing}
            isSubmitted={isDataReady}
            inputRef={fileInputRef}
            disabled={isProcessing}
            className="w-full"
            handleKeyDown={handleFilePathKeyDown}
          />

          {isDataReady && (
            <SimpleMessageInput
              input={input}
              setInput={setInput}
              handleKeyDown={handleKeyDown}
              handleSendClick={handleSendMessage}
              isTyping={isTyping || isProcessing}
              disabled={isProcessing}
              textareaRef={textareaRef}
              className="w-full"
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ModelEdit;