import { contextBridge, ipcRenderer } from 'electron';

// Define allowed environment variables
const ALLOWED_KEYS = [
  'NODE_ENV'
];

// Create a safe environment object with only the allowed keys from process.env
const env = ALLOWED_KEYS.reduce((acc, key) => {
  acc[key] = process.env[key] || '';
  return acc;
}, {} as Record<string, string>);

// Expose a safe API to the renderer process
const electronAPI = {
  // Get a single environment variable
  getEnv: (key: string): string | undefined => {
    // Check if the key is allowed
    if (!ALLOWED_KEYS.includes(key) && !key.startsWith('REACT_APP_')) {
      console.warn(`Attempted to access unauthorized environment variable: ${key}`);
      return undefined;
    }
    return env[key];
  },
  
  // Get all environment variables
  getEnvironment: () => {
    return { ...env };
  },
  
  // Expose logging methods
  log: {
    info: (message: string) => {
      console.log(`[INFO] ${message}`);
      ipcRenderer.send('log:info', message);
    },
    error: (message: string) => {
      console.error(`[ERROR] ${message}`);
      ipcRenderer.send('log:error', message);
    },
    warn: (message: string) => {
      console.warn(`[WARN] ${message}`);
      ipcRenderer.send('log:warn', message);
    },
    debug: (message: string) => {
      console.debug(`[DEBUG] ${message}`);
      ipcRenderer.send('log:debug', message);
    }
  },
  
  // Expose IPC methods
  ipcRenderer: {
    send: (channel: string, ...args: any[]) => {
      ipcRenderer.send(channel, ...args);
    },
    on: (channel: string, listener: (...args: any[]) => void) => {
      const subscription = (event: any, ...args: any[]) => {
        console.log(`Preload: Forwarding IPC event - Channel: ${channel}, Event:`, event, 'Args:', args);
        // Forward the event and args correctly - event as first param, data as second
        listener(event, ...args);
      };
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
};

// Expose the API to the renderer process
contextBridge.exposeInMainWorld('electron', electronAPI);
contextBridge.exposeInMainWorld('electronAPI', electronAPI);  // For backward compatibility

// Make this file a module
export {};
