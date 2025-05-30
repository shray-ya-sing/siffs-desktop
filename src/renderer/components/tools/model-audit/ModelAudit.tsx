// src/renderer/components/tools/model-audit/ModelAudit.tsx
import React, { useRef, useState, useCallback, useEffect } from 'react';
import { MessageInput } from '../../conversation/MessageInput';
import { ConversationHistory } from '../../conversation/ConversationHistory';
import { Message, MessageGroup} from '../../../types/message';

export const ModelAudit: React.FC = () => {
  // Refs
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messageEndRef = useRef<HTMLDivElement>(null);

  // State
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [attachedFiles, setAttachedFiles] = useState({
    images: [] as File[],
    documents: [] as File[],
  });

  // Group messages by time proximity
  const groupMessages = useCallback((msgs: Message[]): MessageGroup[] => {
    if (msgs.length === 0) return [];
    
    const groups: MessageGroup[] = [];
    let currentGroup: Message[] = [msgs[0]];

    for (let i = 1; i < msgs.length; i++) {
      const prevTime = new Date(msgs[i - 1].timestamp).getTime();
      const currTime = new Date(msgs[i].timestamp).getTime();
      
      if (currTime - prevTime < 5 * 60 * 1000) { // 5 minutes
        currentGroup.push(msgs[i]);
      } else {
        groups.push([...currentGroup]);
        currentGroup = [msgs[i]];
      }
    }

    if (currentGroup.length > 0) {
      groups.push(currentGroup);
    }

    return groups;
  }, []);

  const messageGroups = groupMessages(messages);

  // Handle sending a message
  const handleSendMessage = useCallback(() => {
    if ((!input.trim() && attachedFiles.images.length === 0 && attachedFiles.documents.length === 0) || isTyping) {
      return;
    }

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: Date.now().toString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    
    // Simulate typing
    setIsTyping(true);
    
    // Simulate response after a delay
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "This is a simulated response. In a real implementation, this would come from your AI service.",
        role: 'assistant',
        timestamp: Date.now().toString(),
        thinkingTime: 2 // seconds
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      setIsTyping(false);
      
      // Status updates are no longer used in the UI
      
    }, 2000);
  }, [input, attachedFiles, isTyping]);

  // Handle key down in textarea
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  // Handle file attachment
  const handleAttachment = useCallback((type: 'general' | 'image' | 'file') => {
    // Create a file input element
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = type === 'image' ? 'image/*' : type === 'file' ? '.xlsx,.xls,.csv' : '*';
    
    input.onchange = (e) => {
      const files = Array.from((e.target as HTMLInputElement).files || []);
      if (files.length === 0) return;
      
      if (type === 'image') {
        setAttachedFiles(prev => ({
          ...prev,
          images: [...prev.images, ...files]
        }));
      } else {
        setAttachedFiles(prev => ({
          ...prev,
          documents: [...prev.documents, ...files]
        }));
      }
    };
    
    input.click();
  }, []);

  // Handle file removal
  const handleRemoveFile = useCallback((type: 'image' | 'document', index: number) => {
    if (type === 'image') {
      setAttachedFiles(prev => ({
        ...prev,
        images: prev.images.filter((_, i) => i !== index)
      }));
    } else {
      setAttachedFiles(prev => ({
        ...prev,
        documents: prev.documents.filter((_, i) => i !== index)
      }));
    }
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className="flex flex-col h-full">
        <div className="p-4 border-t border-gray-700/50 bg-[#0f1117]/50 backdrop-blur-sm">
        <MessageInput
          input={input}
          setInput={setInput}
          handleKeyDown={handleKeyDown}
          handleSendClick={handleSendMessage}
          handleAttachment={handleAttachment}
          isTyping={isTyping}
          textareaRef={textareaRef}
          attachedFiles={attachedFiles}
          onRemoveFile={handleRemoveFile}
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        <ConversationHistory
          messages={messages}
          messageGroups={messageGroups}
          isTyping={isTyping}
          activeTypingIndex={isTyping ? messages.length : null}
          displayedText={{}}
          scrollAreaRef={scrollAreaRef}
          messageEndRef={messageEndRef}
        />
      </div>  
    </div>
  );
};

export default ModelAudit;