import { v4 as uuidv4 } from 'uuid';
type EventHandler = (data: any) => void;
type ConnectionHandler = (isConnected: boolean) => void;
type ErrorHandler = (error: Error) => void;


export interface AssistantChunkMessage {
  type: 'ASSISTANT_MESSAGE_CHUNK';
  content: string;
  done: boolean;
  requestId: string;
}

export interface CustomEventMessage {
  type: 'CUSTOM_EVENT';
  event_type: string;
  event_message: string;
  requestId: string;
  done: boolean;
}

class WebSocketService {
  private socket: WebSocket | null = null;
  private static instance: WebSocketService;
  private eventHandlers: Map<string, EventHandler[]> = new Map();
  private messageQueue: string[] = [];
  private isConnected = false;

  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();

  // Add these new methods
  onConnectionChange(handler: ConnectionHandler): void {
    this.connectionHandlers.add(handler);
  }

  offConnectionChange(handler: ConnectionHandler): void {
    this.connectionHandlers.delete(handler);
  }

  onError(handler: ErrorHandler): void {
    this.errorHandlers.add(handler);
  }

  offError(handler: ErrorHandler): void {
    this.errorHandlers.delete(handler);
  }

  serviceIsConnected(): boolean {
    return this.isConnected;
  }

  async reconnect(): Promise<void> {
    if (this.socket) {
      this.socket.close();
    }
    return new Promise((resolve, reject) => {
      this.initialize();
      // You might want to add a timeout here
      const checkConnected = () => {
        if (this.isConnected) {
          resolve();
        } else {
          setTimeout(checkConnected, 100);
        }
      };
      checkConnected();
    });
  }

  private constructor() {
    this.initialize();
  }

  private initialize() {
    const isDev = process.env.NODE_ENV === 'development';
    const clientId = uuidv4(); 
    const wsUrl = isDev 
      ? `ws://localhost:3001/ws/${clientId}` 
      : `ws://localhost:5001/ws/${clientId}`;
    
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.isConnected = true;
      
      // Send user ID to backend for API key association
      this.sendUserIdToBackend();
      
      // Process any queued messages
      this.messageQueue.forEach(message => {
        this.socket?.send(message);
      });
      this.messageQueue = [];
    };
    
    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('Raw WebSocket message received:', message); // Debug log
        
        // Special debug for API key messages
        if (message.type === 'API_KEY_STATUS') {
          console.log('=== API_KEY_STATUS RECEIVED ===');
          console.log('Full message:', JSON.stringify(message, null, 2));
          console.log('Status data:', message.status);
          console.log('Request ID:', message.requestId);
          console.log('===============================');
        }
        
        // Special handling for chunked messages
        if (message.type === 'ASSISTANT_MESSAGE_CHUNK' || 
            message.type === 'ASSISTANT_MESSAGE_DONE') {
          const handlers = this.eventHandlers.get(message.type) || [];
          handlers.forEach(handler => handler(message)); // Pass the entire message
          return;
        }

        // Special handling for custom events
        if (message.type === 'CUSTOM_EVENT') {
          const handlers = this.eventHandlers.get(message.type) || [];
          handlers.forEach(handler => handler(message)); // Pass the entire message
          return;
        }
        
        // Normal message handling
        const handlers = this.eventHandlers.get(message.type) || [];
        handlers.forEach(handler => handler(message)); // Pass the entire message
      } catch (error) {
        console.error('Error processing WebSocket message:', error, event.data);
      }
    };

    this.socket.onclose = () => {
      this.isConnected = false;
      // Attempt to reconnect after a delay
      setTimeout(() => this.initialize(), 3000);
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  public static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService();
    }
    return WebSocketService.instance;
  }

  public on(event: string, handler: EventHandler): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)?.push(handler);
  }

  public off(event: string, handler?: EventHandler): void {
    if (!handler) {
      this.eventHandlers.delete(event);
      return;
    }

    const handlers = this.eventHandlers.get(event) || [];
    const index = handlers.indexOf(handler);
    if (index > -1) {
      handlers.splice(index, 1);
    }
  }

  public sendMessage(message: any): void {
    const messageStr = JSON.stringify(message);
    if (this.isConnected && this.socket) {
      this.socket.send(messageStr);
    } else {
      this.messageQueue.push(messageStr);
    }
  }

  sendChatMessage(message: string, model: string, threadId: string, requestId: string) {
    const payload = {
      type: 'CHAT_MESSAGE',
      timestamp: new Date().toISOString(),
      data: {
        message,
        model,
        threadId,
        requestId
      }
    };
    this.sendMessage(payload);
    return payload; // Return the payload in case you need the ID/timestamp
  }

  sendToolCallEvent(toolName: string, query: string, requestId: string) {
    const payload = {
      type: 'TOOL_CALL',
      timestamp: new Date().toISOString(),
      data: {
        toolName,
        query,
        requestId,
        status: 'started'
      }
    };
    this.sendMessage(payload);
  }

  sendToolResultEvent(toolName: string, result: any, requestId: string) {
    const payload = {
      type: 'TOOL_RESULT',
      timestamp: new Date().toISOString(),
      data: {
        toolName,
        result,
        requestId,
        status: 'completed'
      }
    };
    this.sendMessage(payload);
  }

  private handleIncomingMessage(event: MessageEvent) {
    try {
      console.log('WEBSOCKET_SERVICE: handleIncomingMessage received message', event.data)
      const message = JSON.parse(event.data);
      const handlers = this.eventHandlers.get(message.type) || [];
      
      // Special handling for chunked messages
      if (message.type === 'ASSISTANT_MESSAGE_CHUNK' || 
          message.type === 'ASSISTANT_MESSAGE_DONE') {
        // Forward the message with its data
        console.log('WEBSOCKET_SERVICE: handleIncomingMessage received assistant message from backend server, forwarding to handler in agent-chat-ui.tsx')
        const handlers = this.eventHandlers.get(message.type) || [];
        handlers.forEach(handler => handler(message));
        return;
      }
      
      // Special handling for custom events
      if (message.type === 'CUSTOM_EVENT') {
        // Forward the message with its data
        console.log('WEBSOCKET_SERVICE: handleIncomingMessage received custom event from backend server, forwarding to handler in agent-chat-ui.tsx')
        const handlers = this.eventHandlers.get(message.type) || [];
        handlers.forEach(handler => handler(message));
        return;
      }
      
      // Normal message handling
      handlers.forEach(handler => handler(message.data));
    } catch (error) {
      console.error('Error processing message:', error);
    }
  }

  public emit(event: string, data: any): void {
    const message = { type: event, data };
    this.sendMessage(message);
  }

  private async sendUserIdToBackend(): Promise<void> {
    try {
      const { supabase } = require('../../lib/supabase');
      const { data } = await supabase.auth.getUser();
      if (data?.user?.id) {
        console.log('Sending user ID to backend:', data.user.id);
        this.sendMessage({
          type: 'USER_AUTHENTICATION',
          data: {
            user_id: data.user.id,
            email: data.user.email
          }
        });
      } else {
        console.log('No authenticated user found for API key association');
      }
    } catch (error) {
      console.warn('Failed to send user ID to backend:', error);
    }
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.isConnected = false;
    }
  }
}

export const webSocketService = WebSocketService.getInstance();