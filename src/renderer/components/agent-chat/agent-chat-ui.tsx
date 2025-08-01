import React, { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { ArrowRight, Square, Paperclip, X, Image } from "lucide-react"
import { ProviderDropdown, ModelOption } from './ProviderDropdown'
import WatermarkLogo from '../logo/WaterMarkLogo'
import { webSocketService } from '../../services/websocket/websocket.service';
import { v4 as uuidv4 } from 'uuid';
import { useMention } from '../../hooks/useMention'
import MentionDropdown from './MentionDropdown'
import { useFileTree, FileItem } from '../../hooks/useFileTree'
import { EventCard, EventType } from '../events/EventCard'
import {MarkdownRenderer} from './MarkdownRenderer'
import {
  TechThumbsUpIcon,
  TechThumbsDownIcon,
  TechClockIcon,
} from '../tech-icons/TechIcons'

type MessageType = 'user' | 'assistant' | 'tool_call' | 'custom_event';

// Utility function to format timestamps
const formatTimestamp = (timestamp: Date): string => {
  const now = new Date();
  const diff = now.getTime() - timestamp.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  
  return timestamp.toLocaleDateString();
};

interface BaseMessage {
  id: string;
  content: string;
  role: MessageType;
  timestamp: Date;
}

interface UserMessage extends BaseMessage {
  role: 'user';
  attachments?: Array<{type: 'image', data: string, mimeType: string, filename?: string}>;
}

interface AssistantMessage extends BaseMessage {
  role: 'assistant';
}

interface ToolCallMessage extends BaseMessage {
  role: 'tool_call';
  toolName: string;
  status: 'started' | 'completed';
  requestId: string;
  result?: any;
}

interface CustomEventMessage extends BaseMessage {
  role: 'custom_event';
  event_type: string;
  event_message: string;
  requestId: string;
  done: boolean;
}

type Message = UserMessage | AssistantMessage | ToolCallMessage | CustomEventMessage;

const MODEL_OPTIONS: ModelOption[] = [
  // OpenAI Models
  { id: "o3-mini-2025-01-31", name: "o3-mini", provider: "OpenAI" },
  { id: "o4-mini-2025-04-16", name: "o4-mini", provider: "OpenAI" },
  
  // Anthropic Models
  { id: "claude-3-7-sonnet-latest", name: "Claude 3.7 Sonnet", provider: "Anthropic" },
  
  // Google Models
  { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", provider: "Google" },
]


// Memoized message component to prevent re-renders
const MessageComponent = React.memo(({ message, isLastMessage, isLoading, messageFeedback, onFeedback }: { 
  message: Message; 
  isLastMessage: boolean; 
  isLoading: boolean;
  messageFeedback: {[messageId: string]: 'up' | 'down' | null};
  onFeedback: (messageId: string, feedback: 'up' | 'down') => void;
}) => {
  if (message.role === "user") {
    const userMessage = message as UserMessage;
    return (
      <div className="flex justify-center">
        <div className="max-w-full w-full px-8">
          <div
            className="rounded-lg px-3 py-2 text-gray-300 text-sm transition-all duration-200 hover:shadow-lg hover:scale-[1.02]"
            style={{
              background: "linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%)",
            }}
          >
            <div className="mb-2">{message.content}</div>
            {userMessage.attachments && userMessage.attachments.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {userMessage.attachments.map((attachment, index) => (
                  <div key={index} className="relative">
                    <img
                      src={attachment.data}
                      alt={attachment.filename || 'Attached image'}
                      className="max-w-48 max-h-48 rounded-lg border border-gray-600 object-cover"
                      style={{ maxWidth: '12rem', maxHeight: '12rem' }}
                    />
                    {attachment.filename && (
                      <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-70 text-white text-xs px-2 py-1 rounded-b-lg truncate">
                        {attachment.filename}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
  
  if (message.role === 'custom_event') {
    return (
      <div className="flex justify-center">
        <div className="max-w-full w-full px-8">
          <EventCard
            type={message.event_type as EventType}
            message={message.event_message}
            className="w-full"
            isStreaming={message.done !== true}
            timestamp={message.timestamp.getTime()}
          />
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex justify-center">
      <div className="max-w-full w-full px-8">
        <div className="rounded-3xl px-3 py-2 text-gray-200 text-sm transition-all duration-200 hover:bg-gray-900/20 [&>pre]:m-0 [&>pre]:p-0">
          <pre className="whitespace-pre-wrap text-sm" style={{ fontFamily: "inherit" }}>
            <MarkdownRenderer content={message.content} />
            {isLoading && isLastMessage && (
              <span className="inline-block w-2 h-4 bg-blue-400 ml-1 animate-pulse"></span>
            )}
          </pre>
          {message.role === 'assistant' && (
            <div className="flex items-center justify-start mt-2 pt-2 border-t border-gray-700/30">
              <div className="flex items-center gap-1 text-gray-500 text-xs">
                <TechClockIcon className="w-3 h-3" aria-hidden="true" />
                <span aria-label={`Message sent ${formatTimestamp(message.timestamp)}`}>{formatTimestamp(message.timestamp)}</span>
                <button
                  onClick={() => onFeedback(message.id, 'up')}
                  className={`p-0.5 rounded hover:bg-gray-700/20 transition-colors ${
                    messageFeedback[message.id] === 'up' ? 'text-green-400' : 'text-gray-500 hover:text-gray-300'
                  }`}
                  title="Helpful"
                  aria-label="Mark message as helpful"
                >
                  <TechThumbsUpIcon className="w-3 h-3" />
                </button>
                <button
                  onClick={() => onFeedback(message.id, 'down')}
                  className={`p-0.5 rounded hover:bg-gray-700/20 transition-colors ${
                    messageFeedback[message.id] === 'down' ? 'text-red-400' : 'text-gray-500 hover:text-gray-300'
                  }`}
                  title="Not helpful"
                  aria-label="Mark message as not helpful"
                >
                  <TechThumbsDownIcon className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

MessageComponent.displayName = 'MessageComponent';

export default function AIChatUI({ isSidebarOpen }: { isSidebarOpen: boolean }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const typingTimeoutRef = useRef<NodeJS.Timeout>(null)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [selectedModel, setSelectedModel] = useState("gemini-2.5-flash-lite-preview-06-17")
  const [attachments, setAttachments] = useState<Array<{type: 'image', data: string, mimeType: string, filename?: string}>>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [messageFeedback, setMessageFeedback] = useState<{[messageId: string]: 'up' | 'down' | null}>({})

  // Handle feedback buttons
  const handleFeedback = useCallback((messageId: string, feedback: 'up' | 'down') => {
    setMessageFeedback(prev => ({
      ...prev,
      [messageId]: prev[messageId] === feedback ? null : feedback
    }));
  }, []);

  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [threadId, setThreadId] = useState<string>(() => localStorage.getItem('threadId') || uuidv4());
  const [streamingMessage, setStreamingMessage] = useState<{
    requestId: string | null;
    content: string;
  }>({ requestId: null, content: '' });
  const [currentRequestId, setCurrentRequestId] = useState<string | null>(null);
  

  const { fileTree } = useFileTree()
  const {
    showMentions,
    mentionQuery,
    selectedMentionIndex,
    mentionPosition,
    mentionResults,
    handleMentionInput,
    handleMentionKeyDown,
    setShowMentions
  } = useMention(fileTree)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "40px"
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`
    }
  }, [input])

  // Smooth scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Memoized input change handler
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    handleMentionInput(e, textareaRef.current)

    if (!isTyping && e.target.value.length > 0) {
      setIsTyping(true)
    }

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
    }

    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false)
    }, 1000)
  }, [isTyping, handleMentionInput])

  const handleSend = useCallback(async () => {
    if (!input.trim()) return

    const requestId = uuidv4();
    setCurrentRequestId(requestId);

    const userMessage: UserMessage = {
      id: Date.now().toString(),
      content: input,
      role: "user",
      timestamp: new Date(),
      attachments: attachments.length > 0 ? attachments : undefined,
    }

    setMessages(prev => [...prev, userMessage])
    setInput("")
    setAttachments([])
    setIsLoading(true)
    setIsTyping(false)

    // Reset textarea height after clearing input
    if (textareaRef.current) {
      textareaRef.current.style.height = "40px";
    }

    try {
      webSocketService.sendChatMessage(input, selectedModel, threadId, requestId, attachments.length > 0 ? attachments : undefined);
    } catch (error) {
      console.error("Error sending message:", error);
      setIsLoading(false);
      setCurrentRequestId(null);
    }
  }, [input, selectedModel, threadId, attachments]);

  const handleCancel = useCallback(() => {
    // Send cancellation request to backend
    if (currentRequestId) {
      console.log('Sending cancellation request for:', currentRequestId);
      webSocketService.sendCancelRequest(currentRequestId);
    }
    
    // Reset UI state
    setIsLoading(false)
    setIsTyping(false)
    setCurrentRequestId(null)
  }, [currentRequestId])

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    handleMentionKeyDown(e, handleMentionSelect)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend, handleMentionKeyDown])

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onload = (e) => {
          const base64Data = e.target?.result as string
          setAttachments(prev => [...prev, {
            type: 'image',
            data: base64Data,
            mimeType: file.type,
            filename: file.name
          }])
        }
        reader.readAsDataURL(file)
      }
    })

    // Clear the input so the same file can be selected again
    event.target.value = ''
  }, [])

  const removeAttachment = useCallback((index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index))
  }, [])

  const handleAttachClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleMentionSelect = useCallback((file: FileItem) => {
    const atIndex = input.lastIndexOf('@')
    const newInput = input.substring(0, atIndex) + `@${file.name} `
    setInput(newInput)
    setShowMentions(false)
    textareaRef.current?.focus()
  }, [input, setShowMentions])

  const handleModelChange = useCallback((modelId: string) => {
    setSelectedModel(modelId);
    setIsDropdownOpen(false);
  }, []);

  useEffect(() => {
    const handleChatResponse = (response: any) => {
      const assistantMessage: AssistantMessage = {
        id: `msg_${Date.now()}`,
        content: response.data.content,
        role: "assistant",
        timestamp: new Date(response.timestamp),
      };
      setMessages(prev => [...prev, assistantMessage]);
      setIsLoading(false);
    };

    const handleAssistantChunk = (message: any) => {
      console.log('handleAssistantChunk triggered');
      if (!message || typeof message !== 'object') {
        console.error('Invalid message format:', message);
        return;
      }
    
      if (message.type === 'ASSISTANT_MESSAGE_CHUNK' && message.content) {
        console.log('handleAssistantChunk received ASSISTANT_MESSAGE_CHUNK for streaming');
        setMessages(prev => {
          // If last message is from custom event, update its status to completed
          if (prev.length > 0 && prev[prev.length - 1].role === 'custom_event') {
            const newMessages = [...prev];
            const lastMessage = prev[prev.length - 1];
            newMessages[newMessages.length - 1] = {
              ...lastMessage as CustomEventMessage,
              done: true
            };
            // Then add the new assistant message
            return [
              ...newMessages,
              { 
                id: `msg-${Date.now()}`,
                role: 'assistant',
                content: message.content,
                timestamp: new Date()
              }
            ];
          }
          // If last message is from assistant, update it
          else if (prev.length > 0 && prev[prev.length - 1].role === 'assistant') {
            console.log('handleAssistantChunk updating last assistant message');
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = {
              ...newMessages[newMessages.length - 1],
              content: newMessages[newMessages.length - 1].content + message.content
            };
            return newMessages;
          }
          // Otherwise add new assistant message
          console.log('handleAssistantChunk adding new assistant message');
          return [...prev, { 
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: message.content,
            timestamp: new Date()
          }];
        });
      }
      else if (message.type === 'ASSISTANT_MESSAGE_DONE') {
        console.log('handleAssistantChunk received message done streaming signal', message);
        setIsLoading(false);
        setCurrentRequestId(null);
      }
    };

    const handleCustomEvent = (message: any) => {
      console.log('handleCustomEvent triggered');
      if (!message || typeof message !== 'object') {
        console.error('Invalid message format:', message);
        return;
      }
    
      if (message.type === 'CUSTOM_EVENT' && message.event_message) {
        console.log('handleCustomEvent received CUSTOM_EVENT for streaming');
        
        // If this is an error message, clear the loading state
        if (message.event_type === 'error') {
          setIsLoading(false);
          setCurrentRequestId(null);
        }

        /**
         * Add a new message for a custom event to the conversation history.
         *
         * The callback function takes the previous messages as an argument and
         * returns a new array with the new message added to the end.
         *
         * Always adds the message as a new one, even if there is already a message
         * with the same requestId. This is because the requestId is not unique for
         * custom events, and we want to show all custom events in the conversation
         * history.
         *
         * @param prev The previous messages in the conversation history.
         * @return A new array with the new message added to the end.
         */
        setMessages(prev => {

          // If last message is from custom event, update its status to completed
          if (prev.length > 0 && prev[prev.length - 1].role === 'custom_event') {
            const newMessages = [...prev];
            const lastMessage = prev[prev.length - 1];
            newMessages[newMessages.length - 1] = {
              ...lastMessage as CustomEventMessage,
              done: true
            };
            // Then add the new custom event message
            return [...newMessages, { 
              id: `msg-${Date.now()}`,
              role: 'custom_event',
              event_type: message.event_type,
              event_message: message.event_message,
              content: message.event_message,
              done: message.done,
              requestId: message.requestId,
              timestamp: new Date()
            }];
          }
          // Always add it as a new message if the previous message was an assistant message
          else if (prev.length > 0 && prev[prev.length - 1].role === 'assistant') {
            return [...prev, { 
              id: `msg-${Date.now()}`,
              role: 'custom_event',
              event_type: message.event_type,
              event_message: message.event_message,
              content: message.event_message,
              done: message.done,
              requestId: message.requestId,
              timestamp: new Date()
            }];
          }
          // Otherwise add it as a new message
          else {
            return [...prev, { 
              id: `msg-${Date.now()}`,
              role: 'custom_event',
              event_type: message.event_type,
              event_message: message.event_message,
              content: message.event_message,
              done: message.done,
              requestId: message.requestId,
              timestamp: new Date()
            }];
          }
        });
      }
    };

    const handleToolCall = (data: any) => {
      const toolCallMessage: ToolCallMessage = {
        id: `tool_${Date.now()}`,
        content: data.query || `Using ${data.toolName}...`,
        role: 'tool_call',
        toolName: data.toolName,
        status: data.status,
        requestId: data.requestId,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, toolCallMessage]);
    };

    const handleToolResult = (data: any) => {
      setMessages(prev => {
        // Find the corresponding tool call message
        const updatedMessages = [...prev];
        const toolCallIndex = updatedMessages.findIndex(
          msg => msg.role === 'tool_call' && 
                'requestId' in msg && 
                msg.requestId === data.requestId
        );

        if (toolCallIndex !== -1) {
          // Update the existing tool call message
          const updatedToolCall = {
            ...updatedMessages[toolCallIndex],
            status: 'completed' as const,
            content: `Completed: ${updatedMessages[toolCallIndex].content}`,
            result: data.result
          };
          updatedMessages[toolCallIndex] = updatedToolCall as ToolCallMessage;
        }
        return updatedMessages;
      });
    };
  
    const handleCancellationResponse = (message: any) => {
      console.log('Cancellation response received:', message);
      if (message.type === 'REQUEST_CANCELLED' && message.success) {
        setIsLoading(false);
        setCurrentRequestId(null);
        // Optionally show a notification that the request was cancelled
        console.log('Request cancelled successfully');
      } else if (message.type === 'CLIENT_REQUESTS_CANCELLED') {
        setIsLoading(false);
        setCurrentRequestId(null);
        console.log(`${message.cancelled_count} requests cancelled`);
      }
    };

    webSocketService.on('CHAT_RESPONSE', handleChatResponse);
    webSocketService.on('TOOL_CALL', handleToolCall);
    webSocketService.on('TOOL_RESULT', handleToolResult);
    webSocketService.on('ASSISTANT_MESSAGE_CHUNK', handleAssistantChunk);
    webSocketService.on('ASSISTANT_MESSAGE_DONE', handleAssistantChunk);
    webSocketService.on('CUSTOM_EVENT', handleCustomEvent);
    webSocketService.on('REQUEST_CANCELLED', handleCancellationResponse);
    webSocketService.on('CLIENT_REQUESTS_CANCELLED', handleCancellationResponse);
    webSocketService.on('CANCELLATION_FAILED', handleCancellationResponse);
    
    
    
    return () => {
      webSocketService.off('CHAT_RESPONSE', handleChatResponse);
      webSocketService.off('TOOL_CALL', handleToolCall);
      webSocketService.off('TOOL_RESULT', handleToolResult);
      webSocketService.off('ASSISTANT_MESSAGE_CHUNK', handleAssistantChunk);
      webSocketService.off('ASSISTANT_MESSAGE_DONE', handleAssistantChunk);
      webSocketService.off('CUSTOM_EVENT', handleCustomEvent);
      webSocketService.off('REQUEST_CANCELLED', handleCancellationResponse);
      webSocketService.off('CLIENT_REQUESTS_CANCELLED', handleCancellationResponse);
      webSocketService.off('CANCELLATION_FAILED', handleCancellationResponse);
    };
  }, []);

  useEffect(() => {
    localStorage.setItem('threadId', threadId);
  }, [threadId]);

  

  return (
    <div
      className="flex flex-col h-screen text-white relative overflow-hidden"
      style={{ backgroundColor: "#0a0a0a" }}
    >
      {/* Transparent background for assistant messages */}
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden="true"
        style={{
          backgroundColor: "transparent",
          zIndex: 1,
        }}
      />

      {/* Watermark logo */}
      <div>
        <WatermarkLogo />
      </div>

      {/* Messages */}
      <div 
        className="flex-1 overflow-y-auto px-4 py-4 space-y-6 relative z-10" 
        style={{ paddingBottom: '200px' }}
        aria-label="Chat messages"
        role="log"
        aria-live="polite"
      >
        {messages.map((message, index) => (
          <div key={message.id} className="space-y-2" role="article" aria-label={`Message from ${message.role}`}>
            <MessageComponent
              message={message} 
              isLastMessage={index === messages.length - 1}
              isLoading={isLoading}
              messageFeedback={messageFeedback}
              onFeedback={handleFeedback}
            />
          </div>
        ))}

        {useMemo(() => {
          if (!isLoading) return null;
          
          // Check if the latest message is a custom event with error type
          const latestMessage = messages[messages.length - 1];
          const isLatestMessageError = latestMessage && 
            latestMessage.role === 'custom_event' && 
            (latestMessage as CustomEventMessage).event_type === 'error';
          
          // Don't show generating text if latest message is an error
          if (isLatestMessageError) {
            return null;
          }
          
          return (
            <div className="flex justify-center animate-fade-in">
              <div className="max-w-full w-full px-8">
                <div className="rounded-3xl px-3 py-2">
                  <div className="flex items-center gap-2 text-gray-400">
                    <div className="flex gap-1">
                      <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-pulse"></div>
                      <div
                        className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-pulse"
                        style={{ animationDelay: "0.2s" }}
                      ></div>
                      <div
                        className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-pulse"
                        style={{ animationDelay: "0.4s" }}
                      ></div>
                    </div>
                    <span className="text-xs">Generating...</span>
                  </div>
                </div>
              </div>
            </div>
          );
        }, [isLoading, messages])}

        {isTyping && !isLoading && (
          <div className="flex justify-center animate-fade-in">
            <div className="max-w-full w-full px-8">
              <div className="rounded-3xl px-3 py-2">
                <div className="flex items-center gap-2 text-gray-500">
                  <div className="flex gap-1">
                    <div className="w-1 h-1 bg-gray-600 rounded-full animate-bounce"></div>
                    <div
                      className="w-1 h-1 bg-gray-600 rounded-full animate-bounce"
                      style={{ animationDelay: "0.1s" }}
                    ></div>
                    <div
                      className="w-1 h-1 bg-gray-600 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                  </div>
                  <span className="text-xs">User is typing...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input - Fixed at bottom center */}
      <div 
        className={`fixed bottom-4 w-full max-w-2xl px-8 z-20 space-y-2 transition-all duration-300 ${
          isSidebarOpen 
            ? 'left-1/2 transform -translate-x-1/2 ml-36' 
            : 'left-1/2 transform -translate-x-1/2'
        }`} 
        style={{ marginBottom: '10px' }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          const files = Array.from(e.dataTransfer.files);
          files.forEach((file) => {
            if (file.type.startsWith('image/')) {
              const reader = new FileReader();
              reader.onload = (event) => {
                const base64Data = event.target?.result as string;
                setAttachments((prev) => [
                  ...prev,
                  {
                    type: 'image',
                    data: base64Data,
                    mimeType: file.type,
                    filename: file.name,
                  },
                ]);
              };
              reader.readAsDataURL(file);
            }
          });
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
        onDragEnter={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
      >
      {/* ProviderDropdown positioned above the input */}
        <div className="relative w-full">
          <ProviderDropdown 
            value={selectedModel}
            options={MODEL_OPTIONS}
            onChange={handleModelChange}
            isOpen={isDropdownOpen}
            onToggle={setIsDropdownOpen}
            className="w-full"
          />
        </div>

        {showMentions && (
          <MentionDropdown
            files={mentionResults}
            selectedIndex={selectedMentionIndex}
            position={mentionPosition}
            onSelect={handleMentionSelect}
          />
        )}
        
        {/* Attachment preview */}
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {attachments.map((attachment, index) => (
              <div key={index} className="relative group">
                <div className="flex items-center gap-1.5 px-2 py-1.5 bg-gray-800 rounded-lg border border-gray-600" aria-label={`Attachment: ${attachment.filename || 'Image'}`}>
                  <Image size={12} className="text-blue-400" aria-hidden="true" />
                  <span className="text-xs text-gray-300 truncate max-w-24" aria-hidden="true">
                    {attachment.filename || 'Image'}
                  </span>
                  <button
                    onClick={() => removeAttachment(index)}
                    className="p-0.5 hover:bg-red-900/20 rounded transition-colors"
                    title="Remove attachment"
                    aria-label={`Remove attachment: ${attachment.filename || 'Image'}`}
                  >
                    <X size={10} className="text-gray-400 hover:text-red-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Message input */}
        <div className="relative">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyPress}
            placeholder="Ask anything... (Shift+Enter for new line)"
            className="w-full rounded-3xl px-3 py-2 pr-20 text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-gray-600 text-sm transition-all duration-200 hover:shadow-lg focus:shadow-xl"
            aria-label="Message input"
            style={{
              background: "linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%)",
              border: "1px solid #333333",
              minHeight: "40px",
              maxHeight: "120px",
            }}
            disabled={isLoading}
          />
          <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex gap-1">
            <button
              onClick={handleAttachClick}
              disabled={isLoading}
              className="p-1.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-110 hover:bg-gray-700/20 rounded"
              title="Attach image"
              aria-label="Attach image"
            >
              <Paperclip size={12} className="text-gray-400 hover:text-gray-300" />
            </button>
            {isLoading && (
              <button
                onClick={handleCancel}
                className="p-1.5 transition-all duration-200 hover:scale-110 hover:bg-red-900/20 rounded"
                title="Cancel"
                aria-label="Cancel message"
              >
                <Square size={10} className="text-gray-400 hover:text-red-400" />
              </button>
            )}
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="p-1.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-110 hover:bg-blue-900/20 rounded"
              title="Send message"
              aria-label="Send message"
            >
              <ArrowRight size={12} className="text-gray-300 hover:text-blue-300" />
            </button>
          </div>
        </div>
        
        {/* Important note about file edits */}
        <div className="text-center mt-2">
          <p className="text-gray-500 text-xs">
            Volute makes all file edits in temporary copies to avoid corrupting workspace originals. You can save Volute's copies in your preferred locations once you finish iterating. Otherwise, you may not be able to access Volute's copies again.
          </p>
        </div>
      </div>
    </div>
  )
}
