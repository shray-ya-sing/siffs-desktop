// src/renderer/components/tools/model-qa/ModelQA.tsx
import React, { useRef, useState, useCallback, useEffect } from 'react';
import { SimpleMessageInput } from '../../conversation/SimpleMessageInput';
import { ConversationHistory } from '../../conversation/ConversationHistory';
import { FilePathInput } from '../../conversation/FilePathInput';
import { ModelQAService } from '../../../services/tools/modelQaService';
import { Message } from '../../../types/message';
import { ToolInstructions } from '../ToolInstructions';

export const ModelQA: React.FC = () => {
  // Refs
  const messageEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modelQAServiceRef = useRef<ModelQAService | null>(null);

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [filePath, setFilePath] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState('');
  const [isDataReady, setIsDataReady] = useState(false);

  // Initialize service with callbacks
  const initializeService = useCallback(() => {
    if (!modelQAServiceRef.current) {
      modelQAServiceRef.current = new ModelQAService({
        onMessage: (message: string) => {
          setMessages(prev => {
            // If last message is from assistant, update it
            if (prev.length > 0 && prev[prev.length - 1].role === 'assistant') {
              const newMessages = [...prev];
              newMessages[newMessages.length - 1] = {
                ...newMessages[newMessages.length - 1],
                content: newMessages[newMessages.length - 1].content + message
              };
              return newMessages;
            }
            // Otherwise add new assistant message
            return [...prev, { 
              id: `msg-${Date.now()}`, 
              role: 'assistant', 
              content: message, 
              timestamp: Date.now().toString() 
            }];
          });
        },
        onError: (error: string) => {
          setError(error);
          setIsProcessing(false);
          setIsTyping(false);
        },
        onProcessingChange: (processing: boolean) => {
          setIsProcessing(processing);
        },
        onTypingStart: () => {
          setIsTyping(true);
          // Add empty assistant message that will be updated with chunks
          setMessages(prev => [...prev, { 
            id: `msg-${Date.now()}`, 
            role: 'assistant', 
            content: '', 
            timestamp: Date.now().toString() 
          }]);
        },
        onTypingEnd: () => {
          setIsTyping(false);
        },
        onDataReady: (ready: boolean) => {
          setIsDataReady(ready);
        }
      });
    }
    return modelQAServiceRef.current;
  }, []);

  // Handle file path submission
  const handleFilePathSubmit = useCallback(async () => {
    if (!filePath.trim()) return;
    
    setError('');
    setIsProcessing(true);
    setMessages([]);
    
    try {
      const service = initializeService();
      await service.processExcelFile(filePath);
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
      setError('Please process an Excel file first');
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

      // Process the message
      await service.processMessage(input);

    } catch (error: any) {
      setError(error.message || 'An unexpected error occurred');
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
      if (modelQAServiceRef.current) {
        modelQAServiceRef.current.cleanup();
      }
    };
  }, []);

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Instructions on how to use the tool */}
      <div className="px-4 pt-4">
        <ToolInstructions toolId="excel-model-qa" />
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

          <SimpleMessageInput
            input={input}
            setInput={setInput}
            handleKeyDown={handleKeyDown}
            handleSendClick={handleSendMessage}
            isTyping={isTyping || isProcessing}
            disabled={!isDataReady || isProcessing}
            textareaRef={textareaRef}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
};

export default ModelQA;