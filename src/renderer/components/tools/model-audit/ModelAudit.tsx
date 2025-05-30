// src/renderer/components/tools/model-audit/ModelAudit.tsx
import React, { useRef, useState, useCallback, useEffect } from 'react';
import { MessageInput } from '../../conversation/MessageInput';
import { Message } from '../../../types/message';
import { EventCard, EventType } from '../../events/EventCard';
import apiService from '../../../services/pythonApiService';

export const ModelAudit: React.FC = () => {
  // Refs
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messageEndRef = useRef<HTMLDivElement>(null);

  // State
  const [systemEvents, setSystemEvents] = useState<{id: string, type: EventType, message: string}[]>([]);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const addSystemEvent = useCallback((message: string, type: EventType = 'info') => {
    const id = `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSystemEvents(prev => [...prev, { id, type, message }]);
    return id;
  }, []);

  // Handle sending a message
  const handleSendMessage = useCallback(async () => {
    if (!input.trim() || isProcessing) return;
  
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: Date.now().toString(),
    };
  
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsProcessing(true);  
    // Add initial system event
    addSystemEvent('Starting model audit...', 'info');
  
    try {
      // Show loading state
      const loadingId = addSystemEvent('Getting the data from your file...', 'extracting');
  
      // Call the mock API
      await apiService.mockApiCall(
        true, // success
        10000, // 10 second delay
        { result: 'success', step: 1 }
      );
      
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
  }, [input, isProcessing, addSystemEvent]);

  // Handle key down in textarea
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  // Auto-scroll to bottom when messages or events change
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, systemEvents]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-t border-gray-700/50 bg-[#0f1117]/50 backdrop-blur-sm">
        <MessageInput
            input={input}
            setInput={setInput}
            handleKeyDown={handleKeyDown}
            handleSendClick={handleSendMessage}
            handleAttachment={() => {}} // Empty handler since we're not using attachments
            isTyping={isProcessing}
            textareaRef={textareaRef}
            attachedFiles={{ images: [], documents: [] }} // Empty files object
            onRemoveFile={() => {}} // Empty handler since we're not using file removal
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-4">
          {messages.map((message) => (
            <div 
              key={message.id}
              className={`p-3 rounded-lg ${
                message.role === 'user' 
                  ? 'bg-blue-500/10 ml-auto max-w-3/4' 
                  : 'bg-gray-700/30 mr-auto max-w-3/4'
              }`}
            >
              <div className="text-sm text-gray-200">
                {message.content}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {new Date(parseInt(message.timestamp)).toLocaleTimeString()}
              </div>
            </div>
          ))}

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

          <div ref={messageEndRef} />
        </div>
      </div>
    </div>
  );
};

export default ModelAudit;