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
import { SimpleMessageInput } from '../../conversation/SimpleMessageInput';
import { ConversationHistory } from '../../conversation/ConversationHistory';
import { FilePathInput } from '../../conversation/FilePathInput';
import { ToolInstructions } from '../ToolInstructions';
import { Message } from '../../../types/message';
import { ModelEditService } from '../../../services/tools/modelEditService';
import { AcceptEditsButton } from './AcceptEditsButton';
import { RejectEditsButton } from './RejectEditsButton';


interface ModelEditCallbacks {
  onMessage: (message: string) => void;
  onError: (error: string) => void;
  onProcessingChange: (isProcessing: boolean) => void;
  onTypingStart: () => void;
  onTypingEnd: () => void;
  onDataReady: (isReady: boolean) => void;
  onEditComplete: (result: any) => void;
  onEditsAccepted: (result: any) => void;
  onEditsRejected: (result: any) => void;
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
  const [pendingEditCount, setPendingEditCount] = React.useState(0);


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
        onError: (error) => {
          setError(error);
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: `❌ ${error}`,
            timestamp: Date.now().toString()
          }]);
        },
        onProcessingChange: setIsProcessing,
        onTypingStart: () => setIsTyping(true),
        onTypingEnd: () => setIsTyping(false),
        onDataReady: setIsDataReady,
        onEditComplete: (result) => {
          console.log('Edit completed:', result);
          if (result?.request_pending_edits?.length) {
            setPendingEditCount(prev => prev + result.request_pending_edits.length);
          }
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: '✓ Edit completed successfully!',
            timestamp: Date.now().toString()
          }]);
        },
        onEditsAccepted: (result) => {
          console.log('Edits accepted:', result);
          setPendingEditCount(0);
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: '✓ Edits accepted successfully!',
            timestamp: Date.now().toString()
          }]);
        },
        onEditsRejected: (result) => {
          console.log('Edits rejected:', result);
          setPendingEditCount(0);
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: '✓ Edits rejected successfully!',
            timestamp: Date.now().toString()
          }]);
        },
      });
    }
    return modelEditServiceRef.current;
  }, []);


  // Accept edits
  const handleAcceptEdits = useCallback(async () => {
    if (!modelEditServiceRef.current) return;
    try {
      await modelEditServiceRef.current.acceptPendingEdits();
    } catch (error) {
      console.error('Error accepting edits:', error);
    }
  }, []);

  // Reject edits
  const handleRejectEdits = useCallback(async () => {
    if (!modelEditServiceRef.current) return;
    try {
      await modelEditServiceRef.current.rejectPendingEdits();
    } catch (error) {
      console.error('Error rejecting edits:', error);
    }
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
          <div className="mb-2 text-sm text-red-400 whitespace-pre-wrap">
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

        {isDataReady && (
          <div className="flex gap-2">
            <AcceptEditsButton
              onAccept={handleAcceptEdits}
              pendingCount={pendingEditCount}
              disabled={isProcessing || pendingEditCount === 0}
              className="flex-1"
            />
            <RejectEditsButton
              onReject={handleRejectEdits}
              pendingCount={pendingEditCount}
              disabled={isProcessing || pendingEditCount === 0}
              className="flex-1"
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ModelEdit;