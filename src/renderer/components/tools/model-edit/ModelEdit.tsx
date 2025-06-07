import React, { useRef, useState, useCallback, useEffect } from 'react';
import { SimpleMessageInput } from '../../conversation/SimpleMessageInput';
import { ConversationHistory } from '../../conversation/ConversationHistory';
import { FilePathInput } from '../../conversation/FilePathInput';
import { ToolInstructions } from '../ToolInstructions';
import { Message } from '../../../types/message';

// Mock service - replace with your actual service
class ModelEditService {
  async processExcelFile(filePath: string) {
    // Implement file processing logic
    console.log('Processing file:', filePath);
  }

  async processMessage(message: string) {
    // Implement message processing logic
    console.log('Processing message:', message);
    return 'This is a mock response. Implement your actual service logic.';
  }

  cleanup() {
    // Cleanup logic
  }
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
      modelEditServiceRef.current = new ModelEditService();
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
    setIsProcessing(true);
    setMessages([]);
    
    try {
      const service = initializeService();
      await service.processExcelFile(filePath);
      setIsDataReady(true);
      
      // Add welcome message
      const welcomeMessage: Message = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: `I've loaded your Excel file. What changes would you like to make?`,
        timestamp: Date.now().toString()
      };
      setMessages([welcomeMessage]);
    } catch (error: any) {
      setError(error.message || 'Failed to process file');
    } finally {
      setIsProcessing(false);
    }
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

    try {
      const service = initializeService();
      const userMessage: Message = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content: input,
        timestamp: Date.now().toString()
      };

      // Add user message to the conversation
      setMessages(prev => [...prev, userMessage]);
      setInput('');
      setIsTyping(true);

      // Process the message and get response
      const response = await service.processMessage(input);
      
      // Add assistant's response
      const assistantMessage: Message = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: response,
        timestamp: Date.now().toString()
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      setError(error.message || 'An error occurred while processing your request');
    } finally {
      setIsTyping(false);
    }
  }, [input, isDataReady, initializeService]);

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