import { contextBridge, ipcRenderer } from 'electron';

// Only expose specific environment variables to the renderer
const ALLOWED_KEYS = ['REACT_APP_SUPABASE_URL','REACT_APP_SUPABASE_ANON_KEY','SUPABASE_URL', 'SUPABASE_ANON_KEY'];

// Create a safe environment object with only the allowed keys
const env = ALLOWED_KEYS.reduce((acc, key) => {
  acc[key] = process.env[key] || '';
  return acc;
}, {} as Record<string, string>);

// Environment variables we want to expose to the renderer
const ALLOWED_ENV_KEYS = [
  'REACT_APP_SUPABASE_URL',
  'REACT_APP_SUPABASE_ANON_KEY',
  'NODE_ENV'
];

// Debug: Log available environment variables
console.log('Available environment variables:', Object.keys(process.env).filter(k => k.startsWith('REACT_APP_')));

// Cache for environment variables
const envCache = new Map<string, string>();

// Expose a safe API to the renderer process
contextBridge.exposeInMainWorld('electron', {
  // Get a single environment variable via IPC
  getEnv: async (key: string): Promise<string | null> => {
    // Check if the key is allowed
    if (!ALLOWED_ENV_KEYS.includes(key) && !key.startsWith('REACT_APP_')) {
      console.warn(`Attempted to access unauthorized environment variable: ${key}`);
      return null;
    }
    
    // Check cache first
    if (envCache.has(key)) {
      return envCache.get(key) || null;
    }
    
    try {
      // Get the value via IPC
      const value = await ipcRenderer.invoke('get-env', key);
      if (value) {
        envCache.set(key, value);
      }
      return value || null;
    } catch (error) {
      console.error('Error getting environment variable:', error);
      return null;
    }
  },
  
  // For debugging
  getEnvironment: async () => {
    const env: Record<string, string | null> = {};
    
    // Get all allowed environment variables
    for (const key of ALLOWED_ENV_KEYS) {
      try {
        const value = await ipcRenderer.invoke('get-env', key);
        if (value) {
          env[key] = value;
          envCache.set(key, value);
        }
      } catch (error) {
        console.error(`Error getting environment variable ${key}:`, error);
        env[key] = null;
      }
    }
    
    return {
      node: process.versions.node,
      chrome: process.versions.chrome,
      electron: process.versions.electron,
      env
    };
  },
});

// Make this file a module
export {};
