// src/renderer/components/conversation/ConversationHistory.tsx
import React from 'react';
import { ScrollArea } from '../ui/scroll-area';
import { Message, MessageGroup } from '../../types/message';

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
}

export const ConversationHistory: React.FC<ConversationHistoryProps> = ({
  messages,
  messageGroups,
  isTyping,
  activeTypingIndex,
  displayedText,
  scrollAreaRef,
  messageEndRef,
  className = '',
  formatAIResponse = (text: string) => text.split('\n').map((line, i) => (
    <React.Fragment key={i}>
      {line}
      <br />
    </React.Fragment>
  )),
}) => {
  // Convert text to JSX (simple implementation)
  const textToJSX = (text: string) => {
    return text;
  };

  return (
    <div className={`flex-1 rounded-lg overflow-hidden relative backdrop-blur-md bg-[#1a2035]/30 border border-[#ffffff0f] shadow-[inset_0_0_20px_rgba(0,0,0,0.2)] before:absolute before:inset-0 before:bg-gradient-to-b before:from-[#ffffff08] before:to-transparent before:pointer-events-none gradient-border ${className}`}>
      <ScrollArea className="h-full px-4 pt-4 pb-4 custom-scrollbar" ref={scrollAreaRef}>

        {messageGroups.map((group, groupIndex) => (
          <div key={groupIndex} className="mb-8">
            {/* Time divider */}
            {groupIndex > 0 && (
              <div className="flex items-center my-6">
                <div className="flex-grow h-px bg-gray-700/30"></div>
                <div className="mx-4 text-xs text-gray-500">
                  {new Date(group[0].timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: true,
                  })}
                </div>
                <div className="flex-grow h-px bg-gray-700/30"></div>
              </div>
            )}

            {/* Messages in this group */}
            {group.map((message, index) => {
              const globalIndex = messages.findIndex(
                (m) => m.timestamp === message.timestamp && m.content === message.content,
              );

              return (
                <div
                  key={`${groupIndex}-${index}`}
                  className={`mb-4 transition-all duration-300 hover:translate-x-1 ${
                    message.role === "system" ? "hover:bg-blue-900/5" : "hover:bg-gray-700/5"
                  } rounded-md p-1`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    {message.role === "system" || message.role === "assistant" ? (
                      <>
                        <div className="h-5 w-5 bg-blue-600/80 rounded flex items-center justify-center text-xs backdrop-blur-sm shadow-[0_0_10px_rgba(59,130,246,0.3)] transition-all duration-300 hover:shadow-[0_0_15px_rgba(59,130,246,0.5)]">
                          C
                        </div>
                        <span className="text-sm tracking-wide">Cori</span>
                      </>
                    ) : (
                      <>
                        <div className="h-5 w-5 bg-gray-600/50 rounded flex items-center justify-center text-xs backdrop-blur-sm transition-all duration-300 hover:bg-gray-600/70">
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
            })}
          </div>
        ))}

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