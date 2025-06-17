import { v4 as uuidv4 } from 'uuid';
type EventHandler = (data: any) => void;

class WebSocketService {
  private socket: WebSocket | null = null;
  private static instance: WebSocketService;
  private eventHandlers: Map<string, EventHandler[]> = new Map();
  private messageQueue: string[] = [];
  private isConnected = false;

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
      
      // Process any queued messages
      this.messageQueue.forEach(message => {
        this.socket?.send(message);
      });
      this.messageQueue = [];
    };
    
    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const handlers = this.eventHandlers.get(message.type) || [];
        handlers.forEach(handler => handler(message.data));
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
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

  sendChatMessage(message: string, model: string, metadata: Record<string, any> = {}) {
    const payload = {
      type: 'CHAT_MESSAGE',
      timestamp: new Date().toISOString(),
      data: {
        message,
        model,
        ...metadata
      }
    };
    this.sendMessage(payload);
    return payload; // Return the payload in case you need the ID/timestamp
  }



  public emit(event: string, data: any): void {
    const message = { type: event, data };
    this.sendMessage(message);
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