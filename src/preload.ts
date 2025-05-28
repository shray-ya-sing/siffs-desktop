import { contextBridge, ipcRenderer } from 'electron';

// Define allowed environment variables
const ALLOWED_KEYS = [
  'REACT_APP_SUPABASE_URL',
  'REACT_APP_SUPABASE_ANON_KEY',
  'NODE_ENV'
];

// Create a safe environment object with only the allowed keys from process.env
const env = ALLOWED_KEYS.reduce((acc, key) => {
  acc[key] = process.env[key] || '';
  return acc;
}, {} as Record<string, string>);

// Expose a safe API to the renderer process
contextBridge.exposeInMainWorld('electron', {
  // Get a single environment variable
  getEnv: (key: string): string | null => {
    // Check if the key is allowed
    if (!ALLOWED_KEYS.includes(key) && !key.startsWith('REACT_APP_')) {
      console.warn(`Attempted to access unauthorized environment variable: ${key}`);
      return null;
    }
    return env[key] || null;
  },
  
  // Get all environment variables
  getEnvironment: () => {
    return { ...env };
  },
  
  // Expose IPC methods
  ipcRenderer: {
    send: (channel: string, ...args: any[]) => {
      ipcRenderer.send(channel, ...args);
    },
    on: (channel: string, listener: (...args: any[]) => void) => {
      const subscription = (_event: any, ...args: any[]) => listener(...args);
      ipcRenderer.on(channel, subscription);
      
      // Return cleanup function
      return () => {
        ipcRenderer.removeListener(channel, subscription);
      };
    },
    invoke: (channel: string, ...args: any[]) => {
      return ipcRenderer.invoke(channel, ...args);
    }
  }
});

// Make this file a module
export {};
