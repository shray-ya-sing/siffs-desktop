export interface Message {
    role: "user" | "system" | "assistant";
    content: string;
    timestamp: string;
    thinkingTime?: number;
    id?: string; // Add optional id for tracking messages
  }
  
  export type MessageGroup = Message[];
  