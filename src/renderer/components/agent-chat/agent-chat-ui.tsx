import { useState, useEffect, useRef, useCallback } from "react"
import { ArrowRight, Square } from "lucide-react"

interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  timestamp: Date
}

const WatermarkLogo = () => (
  <svg
    width="400"
    height="400"
    viewBox="0 0 512 512"
    className="absolute inset-0 m-auto opacity-[0.02]"
    style={{ zIndex: 0 }}
  >
    <defs>
      <linearGradient
        id="watermark-grad1"
        x1="265.13162"
        y1="152.08855"
        x2="456.58057"
        y2="295.04551"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad2"
        x1="59.827798"
        y1="254.1107"
        x2="185.78105"
        y2="104.22633"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad3"
        x1="143.58672"
        y1="213.17589"
        x2="227.9754"
        y2="213.17589"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad4"
        x1="59.198033"
        y1="130.67651"
        x2="164.36899"
        y2="130.67651"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad5"
        x1="227.9754"
        y1="236.79212"
        x2="371.56212"
        y2="236.79212"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#f9f9f9", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#f9f9f9", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad6"
        x1="369.67282"
        y1="206.56335"
        x2="455.9508"
        y2="206.56335"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
    </defs>

    <path
      style={{ fill: "url(#watermark-grad2)", fillOpacity: 1 }}
      d="M 204.67405,379.74908 227.34563,294.73063 144.21648,151.14391 59.827798,128.47232 Z"
    />
    <path
      style={{ fill: "url(#watermark-grad1)", fillOpacity: 1 }}
      d="m 226.77254,295.04551 143.94569,-84.0738 85.86234,22.92922 -252.53629,145.21838 z"
    />
    <path
      style={{ fill: "url(#watermark-grad3)", fillOpacity: 1 }}
      d="M 227.9754,296.61992 V 253.92763 L 165.46527,129.73186 143.58672,151.07801 Z"
    />
    <path
      style={{ fill: "url(#watermark-grad4)", fillOpacity: 1 }}
      d="M 59.198033,128.4045 142.6974,151.77368 164.36899,131.00107 78.320028,109.57934 Z"
    />
    <path style={{ fill: "#333333", fillOpacity: 1 }} d="m 227.34563,295.36039 12.59533,-40.30504" />
    <path
      style={{ fill: "url(#watermark-grad5)", fillOpacity: 1 }}
      d="m 370.30258,179.48339 1.25954,31.48832 -143.58672,83.12915 0.62977,-39.04551 z"
    />
    <path
      style={{ fill: "url(#watermark-grad6)", fillOpacity: 1 }}
      d="m 369.67282,179.48339 86.27798,24.56089 -0.62977,29.59902 -83.75891,-22.67159 z"
    />
  </svg>
)

export default function AIChatUI() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const typingTimeoutRef = useRef<NodeJS.Timeout>(null)

  // Mock function for AI response
  const generateAIResponse = useCallback(async (userInput: string): Promise<string> => {
    return new Promise((resolve) => {
      // Simulate API call delay
      setTimeout(() => {
        resolve(`I received your message: "${userInput}". This is a mock response.`)
      }, 1000)
    })
  }, [])

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
      const response = await generateAIResponse(input)
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response,
        role: "assistant",
        timestamp: new Date(),
      }
      
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error("Error generating response:", error)
    } finally {
      setIsLoading(false)
    }
  }, [input, generateAIResponse])

  const handleCancel = useCallback(() => {
    setIsLoading(false)
    setIsTyping(false)
  }, [])

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

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
            ) : (
              <div className="flex justify-start">
                <div className="max-w-4xl">
                  <div className="rounded-3xl px-3 py-2 text-gray-200 text-sm transition-all duration-200 hover:bg-gray-900/20">
                    <pre className="whitespace-pre-wrap text-sm" style={{ fontFamily: "inherit" }}>
                      {message.content}
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
                  <span className="text-xs">Thinking...</span>
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
                  <span className="text-xs">AI is preparing to respond...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input - Fixed at bottom center */}
      <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 w-full max-w-2xl px-4 z-20">
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
