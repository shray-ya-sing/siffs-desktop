// websocket.service.ts
import { io, Socket } from 'socket.io-client';

class WebSocketService {
  private socket: Socket | null = null;
  private static instance: WebSocketService;

  private constructor() {
    const isDev = process.env.NODE_ENV === 'development';
    const wsUrl = isDev ? 'ws://localhost:3001' : 'ws://localhost:5001';
    
    this.socket = io(wsUrl, {
      auth: {
        token: localStorage.getItem('token')
      },
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });
  }

  public static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService();
    }
    return WebSocketService.instance;
  }

  public on(event: string, callback: (data: any) => void) {
    this.socket?.on(event, callback);
  }

  public off(event: string, callback?: (data: any) => void) {
    this.socket?.off(event, callback);
  }

  public emit(event: string, data: any, callback?: (response: any) => void) {
    if (callback) {
      this.socket?.emit(event, data, callback);
    } else {
      this.socket?.emit(event, data);
    }
  }

  public disconnect() {
    this.socket?.disconnect();
  }
}

export const webSocketService = WebSocketService.getInstance();