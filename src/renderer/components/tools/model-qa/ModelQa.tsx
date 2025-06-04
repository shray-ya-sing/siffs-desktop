// src/renderer/components/tools/model-qa/ModelQA.tsx
import React, { useRef, useState, useCallback, useEffect } from 'react';
import { MessageInput } from '../../conversation/MessageInput';
import { ConversationHistory } from '../../conversation/ConversationHistory';
import { FilePathInput } from '../../conversation/FilePathInput';
import { ModelQAService } from '../../../services/modelQaService';
import { Message } from '../../../types/message';

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

  // Initialize service with callbacks
  const initializeService = useCallback(() => {
    if (!modelQAServiceRef.current) {
      modelQAServiceRef.current = new ModelQAService({
        onMessage: (message: string) => {
          setMessages(prev => [...prev, { id: `msg-${Date.now()}`, role: 'assistant', content: message, timestamp: Date.now().toString() }]);
        },
        onError: (error: string) => {
          setError(error);
          setIsProcessing(false);
          setIsTyping(false);
        },
        onProcessingChange: (isProcessing: boolean) => {
          setIsProcessing(isProcessing);
        },
        onTypingStart: () => {
          setIsTyping(true);
        },
        onTypingEnd: () => {
          setIsTyping(false);
        }
      });
    }
    return modelQAServiceRef.current;
  }, []);

  // Handle file path submission
  const handleFilePathSubmit = useCallback(() => {
    if (!filePath.trim()) return;
    setError(''); // Clear any previous errors
  }, [filePath]);

  // Handle key down in file path input
  const handleFilePathKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleFilePathSubmit();
    }
  }, [handleFilePathSubmit]);

  // Handle sending a message
  const handleSendMessage = useCallback(async () => {
    if (!input.trim() || !filePath.trim()) {
      if (!filePath.trim()) {
        setError('Please select an Excel file first');
        fileInputRef.current?.focus();
      }
      return;
    }

    try {
      setIsProcessing(true);
      setError(''); // Clear any previous errors
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

      // Process the message with the file path
      await service.processMessage(filePath, userMessage.content);

    } catch (error: any) {
      console.error('Error in handleSendMessage:', error);
      setError(error.message || 'An unexpected error occurred');
    } finally {
      setIsProcessing(false);
    }
  }, [input, filePath, initializeService]);

  // Handle key down in textarea
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

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
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-hidden">
        <ConversationHistory
          messages={messages}
          messageGroups={[]}
          isTyping={isTyping}
          activeTypingIndex={null}
          displayedText={{}}
          scrollAreaRef={scrollAreaRef}
          messageEndRef={messageEndRef}
          systemEvents={[]}
          className="h-full"
        />
      </div>

      <div className="p-4 border-t border-gray-700/50 bg-[#0f1117]/50 backdrop-blur-sm space-y-3">
        {error && (
          <div className="mb-2 text-sm text-red-400">
            {error}
          </div>
        )}

        <div className="space-y-3">
          <FilePathInput
            filePath={filePath}
            setFilePath={setFilePath}
            handleKeyDown={handleFilePathKeyDown}
            handleSubmit={handleFilePathSubmit}
            isProcessing={isProcessing}
            inputRef={fileInputRef}
            className="w-full"
          />

          <MessageInput
            input={input}
            setInput={setInput}
            handleKeyDown={handleKeyDown}
            handleSendClick={handleSendMessage}
            handleAttachment={(type) => {
              // Handle file attachments if needed
              console.log(`Attaching ${type}`);
            }}
            isTyping={isTyping || isProcessing}
            textareaRef={textareaRef}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
};

export default ModelQA;