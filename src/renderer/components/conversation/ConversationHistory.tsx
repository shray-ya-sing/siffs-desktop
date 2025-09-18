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
// src/renderer/components/conversation/ConversationHistory.tsx
import React, { useMemo } from 'react';
import { ScrollArea } from '../ui/scroll-area';
import { Message, MessageGroup } from '../../types/message';
import { EventCard } from '../events/EventCard';

// Import EventType if it's not already imported from EventCard
type EventType = 'extracting' | 'checking' | 'completed' | 'analyzing' | 'generating' | 'executing' | 'reviewing' | 'info';

interface SystemEvent {
  id: string;
  type: EventType;
  message: string;
}

interface ConversationHistoryProps {
  messages: Message[];
  messageGroups: MessageGroup[];
  isTyping: boolean;
  activeTypingIndex: number | null;
  displayedText: Record<number, string>;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  messageEndRef: React.RefObject<HTMLDivElement | null>;
  className?: string;
  formatAIResponse?: (text: string) => React.ReactNode;
  systemEvents: SystemEvent[];
}

export const ConversationHistory: React.FC<ConversationHistoryProps> = ({
  messages,
  messageGroups,
  isTyping,
  activeTypingIndex,
  displayedText,
  scrollAreaRef,
  messageEndRef,
  systemEvents = [],
  className = '',
  formatAIResponse = (text: string) => text.split('\n').map((line, i) => (
    <React.Fragment key={i}>
      {line}
      <br />
    </React.Fragment>
  )),
}) => {
  // Merge and sort all items (messages and system events)
  const allItems = useMemo(() => {
    // Convert system events to a format we can sort with messages
    const eventItems = systemEvents.map(event => ({
      id: event.id,
      type: 'event' as const,
      timestamp: parseInt(event.id.split('-')[1]) || Date.now(),
      data: event
    }));

    // Convert messages to a sortable format
    const messageItems = messages.map(message => ({
      id: message.id,
      type: 'message' as const,
      timestamp: parseInt(message.timestamp) || Date.now(),
      data: message
    }));

    // Combine and sort by timestamp
    return [...eventItems, ...messageItems]
      .sort((a, b) => a.timestamp - b.timestamp);
  }, [messages, systemEvents]);

  // Helper to render a message
  const renderMessage = (message: Message, index: number) => {
    const isAssistant = message.role === "system" || message.role === "assistant";
    
    return (
      <div
        key={`msg-${message.id}-${index}`}
        className={`mb-4 transition-all duration-300 hover:translate-x-1 ${
          isAssistant ? "hover:bg-blue-900/5" : "hover:bg-gray-700/5"
        } rounded-md p-1`}
      >
        <div className="flex items-center gap-2 mb-1">
          {isAssistant ? (
            <>
              <div className="h-5 w-5 bg-blue-600/80 rounded flex items-center justify-center text-xs backdrop-blur-sm shadow-[0_0_10px_rgba(59,130,246,0.3)]">
                C
              </div>
              <span className="text-sm tracking-wide">Cori</span>
            </>
          ) : (
            <>
              <div className="h-5 w-5 bg-gray-600/50 rounded flex items-center justify-center text-xs backdrop-blur-sm">
                SH
              </div>
              <span className="text-sm tracking-wide">shreya</span>
            </>
          )}
          <span className="text-xs text-gray-500">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        <div className="pl-7">
          <div className="text-xs text-gray-200/90 leading-relaxed font-mono font-normal tracking-tight">
            {formatAIResponse(message.content)}
          </div>
          {message.thinkingTime && (
            <div className="mt-1 text-[10px] text-blue-400/60 font-mono">
              Thought for {message.thinkingTime} {message.thinkingTime === 1 ? "second" : "seconds"}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Helper to render an event
  const renderEvent = (event: SystemEvent) => (
    <div key={`event-${event.id}`} className="mb-4 px-2">
      <EventCard
        type={event.type}
        message={event.message}
        className="w-full"
      />
    </div>
  );

  return (
    <div className={`flex-1 rounded-lg overflow-hidden relative backdrop-blur-md bg-[#1a2035]/30 border border-[#ffffff0f] shadow-[inset_0_0_20px_rgba(0,0,0,0.2)] before:absolute before:inset-0 before:bg-gradient-to-b before:from-[#ffffff08] before:to-transparent before:pointer-events-none gradient-border ${className}`}>
      <ScrollArea className="h-full px-4 pt-4 pb-4 custom-scrollbar" ref={scrollAreaRef}>
        {allItems.map((item, index) => {
          // Handle events
          if (item.type === 'event') {
            return renderEvent(item.data as SystemEvent);
          }
          
          // Handle messages
          const message = item.data as Message;
          return renderMessage(message, index);
        })}

        {/* Typing indicator */}
        {isTyping && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-1">
              <div className="h-5 w-5 bg-blue-600/80 rounded flex items-center justify-center text-xs backdrop-blur-sm shadow-[0_0_10px_rgba(59,130,246,0.3)]">
                C
              </div>
              <span className="text-sm">Cori</span>
              <span className="text-xs text-gray-500">
                {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
            <div className="pl-7">
              <div className="py-1 px-2 rounded-md bg-blue-900/10 inline-block">
                <span className="text-xs font-mono">Cori is thinking</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messageEndRef} />
      </ScrollArea>
    </div>
  );
};

export default ConversationHistory;