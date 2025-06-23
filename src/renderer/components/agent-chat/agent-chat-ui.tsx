import { useState, useEffect, useRef, useCallback } from "react"
import { ArrowRight, Square } from "lucide-react"
import { ProviderDropdown, ModelOption } from './ProviderDropdown'
import WatermarkLogo from '../logo/WaterMarkLogo'
import { webSocketService } from '../../services/websocket/websocket.service';
import { v4 as uuidv4 } from 'uuid';
import { useMention } from '../../hooks/useMention'
import MentionDropdown from './MentionDropdown'
import { useFileTree, FileItem } from '../../hooks/useFileTree'
import { EventCard } from '../events/EventCard'

type MessageType = 'user' | 'assistant' | 'tool_call';

interface BaseMessage {
  id: string;
  content: string;
  role: MessageType;
  timestamp: Date;
}

interface UserMessage extends BaseMessage {
  role: 'user';
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

type Message = UserMessage | AssistantMessage | ToolCallMessage;

const MODEL_OPTIONS: ModelOption[] = [
//  { id: "openai-o1", name: "OpenAI o-1", provider: "OpenAI" },
//  { id: "openai-o3", name: "OpenAI o-3", provider: "OpenAI" },
  { id: "claude-sonnet-4-20250514", name: "Claude sonnet 4", provider: "Anthropic" },
  { id: "claude-3-7-sonnet-latest", name: "Claude sonnet 3.7", provider: "Anthropic" },
//  { id: "xai-grok-3", name: "Grok-3", provider: "xAI" },
//  { id: "deepseek-v3", name: "DeepSeek v3", provider: "DeepSeek" },
//  { id: "gemini-2.5-pro", name: "Gemini 2.5 pro", provider: "Google" },
]


export default function AIChatUI() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const typingTimeoutRef = useRef<NodeJS.Timeout>(null)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [selectedModel, setSelectedModel] = useState("claude-sonnet-4")
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [threadId, setThreadId] = useState<string>(() => localStorage.getItem('threadId') || uuidv4());
  const [streamingMessage, setStreamingMessage] = useState<{
    requestId: string | null;
    content: string;
  }>({ requestId: null, content: '' });
  

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

  // Typing animation
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
  }, [isTyping])

  const handleSend = useCallback(async () => {
    if (!input.trim()) return

    const requestId = uuidv4();

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: "user",
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput("")
    setIsLoading(true)
    setIsTyping(false)

    try {
      webSocketService.sendChatMessage(input, selectedModel, threadId, requestId);
    } catch (error) {
      console.error("Error sending message:", error);
      setIsLoading(false);
    }
  }, [input, selectedModel, threadId]);

  const handleCancel = useCallback(() => {
    setIsLoading(false)
    setIsTyping(false)
  }, [])

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    handleMentionKeyDown(e, handleMentionSelect)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  const handleMentionSelect = (file: FileItem) => {
    const atIndex = input.lastIndexOf('@')
    const newInput = input.substring(0, atIndex) + `@${file.name} `
    setInput(newInput)
    setShowMentions(false)
    textareaRef.current?.focus()
  }

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
          // If last message is from assistant, update it
          if (prev.length > 0 && prev[prev.length - 1].role === 'assistant') {
            console.log('handleAssistantChunk updating last assistant message');
            const newMessages = [...prev];
            newMessages[newMessages.length - 1] = {
              ...newMessages[newMessages.length - 1],
              content: newMessages[newMessages.length - 1].content + '\n' + message.content
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
  
    webSocketService.on('CHAT_RESPONSE', handleChatResponse);
    webSocketService.on('TOOL_CALL', handleToolCall);
    webSocketService.on('TOOL_RESULT', handleToolResult);
    webSocketService.on('ASSISTANT_MESSAGE_CHUNK', handleAssistantChunk);
    webSocketService.on('ASSISTANT_MESSAGE_DONE', handleAssistantChunk);
    
    
    return () => {
      webSocketService.off('CHAT_RESPONSE', handleChatResponse);
      webSocketService.off('TOOL_CALL', handleToolCall);
      webSocketService.off('TOOL_RESULT', handleToolResult);
      webSocketService.off('ASSISTANT_MESSAGE_CHUNK', handleAssistantChunk);
      webSocketService.off('ASSISTANT_MESSAGE_DONE', handleAssistantChunk);
    };
  }, []);

  useEffect(() => {
    localStorage.setItem('threadId', threadId);
  }, [threadId]);

  

  return (
    <div
      className="flex flex-col h-screen text-white pb-20 relative overflow-hidden"
      style={{ backgroundColor: "#0a0a0a" }}
    >
      {/* Circular gradient background */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `radial-gradient(circle at center, rgba(20, 20, 20, 0.3) 0%, rgba(10, 10, 10, 0.8) 40%, rgba(10, 10, 10, 1) 70%)`,
          zIndex: 1,
        }}
      />

      {/* Watermark logo */}
      <div>
        <WatermarkLogo />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 relative z-10">
        {messages.map((message) => (
          <div key={message.id} className="space-y-2">
            {message.role === "user" ? (
              <div className="flex justify-start">
                <div className="max-w-3xl">
                  <div
                    className="rounded-3xl px-3 py-2 text-gray-300 text-sm transition-all duration-200 hover:shadow-lg hover:scale-[1.02]"
                    style={{
                      background: "linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%)",
                      border: "1px solid #333333",
                    }}
                  >
                    {message.content}
                  </div>
                </div>
              </div>
            ) : message.role === 'tool_call' ? (
              <div className="flex justify-start">
                <div className="max-w-4xl w-full">
                  <EventCard
                    type={message.status === 'completed' ? 'completed' : 'executing'}
                    message={message.content}
                    className="w-full"
                    isStreaming={message.status !== 'completed'}
                    timestamp={message.timestamp.getTime()}
                  />
                </div>
              </div>
            ) : (
              <div className="flex justify-start">
                <div className="max-w-4xl">
                  <div className="rounded-3xl px-3 py-2 text-gray-200 text-sm transition-all duration-200 hover:bg-gray-900/20">
                  <pre className="whitespace-pre-wrap text-sm" style={{ fontFamily: "inherit" }}>
                    {message.content}
                    {isLoading && messages[messages.length - 1]?.id === message.id && (
                      <span className="inline-block w-2 h-4 bg-blue-400 ml-1 animate-pulse"></span>
                    )}
                  </pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start animate-fade-in">
            <div className="max-w-4xl">
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
        )}

        {isTyping && !isLoading && (
          <div className="flex justify-start animate-fade-in">
            <div className="max-w-4xl">
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
      <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 w-full max-w-2xl px-4 z-20 space-y-2">
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
        
        {/* Message input */}
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyPress}
            placeholder="Ask anything... (Shift+Enter for new line)"
            className="w-full rounded-3xl px-3 py-2 pr-16 text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-gray-600 text-sm transition-all duration-200 hover:shadow-lg focus:shadow-xl"
            style={{
              background: "linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%)",
              border: "1px solid #333333",
              minHeight: "40px",
              maxHeight: "120px",
            }}
            disabled={isLoading}
          />
          <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex gap-1">
            {isLoading && (
              <button
                onClick={handleCancel}
                className="p-1.5 transition-all duration-200 hover:scale-110 hover:bg-red-900/20 rounded"
                title="Cancel"
              >
                <Square size={10} className="text-gray-400 hover:text-red-400" />
              </button>
            )}
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="p-1.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-110 hover:bg-blue-900/20 rounded"
              title="Send message"
            >
              <ArrowRight size={12} className="text-gray-300 hover:text-blue-300" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
