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
  },

  // File system operations
  fileSystem: {
    revealInExplorer: (filePath: string) => ipcRenderer.invoke('reveal-in-explorer', filePath),
    deleteFile: (filePath: string) => ipcRenderer.invoke('delete-file', filePath),
    deleteDirectory: (dirPath: string) => ipcRenderer.invoke('delete-directory', dirPath),
    renameFile: (oldPath: string, newName: string) => ipcRenderer.invoke('rename-file', oldPath, newName),
    createFile: (dirPath: string, fileName: string, template?: string) => ipcRenderer.invoke('create-file', dirPath, fileName, template),
    createDirectory: (dirPath: string, folderName: string) => ipcRenderer.invoke('create-directory', dirPath, folderName),
    copyToClipboard: (text: string) => ipcRenderer.invoke('copy-to-clipboard', text),
    openWithDefault: (filePath: string) => ipcRenderer.invoke('open-with-default', filePath),
  },

  // File watcher operations
  fileWatcher: {
    startWatching: (directoryPath: string) => ipcRenderer.invoke('file-watcher:start-watching', directoryPath),
    stopWatching: () => ipcRenderer.invoke('file-watcher:stop-watching'),
    getWatchedPath: () => ipcRenderer.invoke('file-watcher:get-watched-path'),
    
    onFileChange: (callback: (event: any, data: any) => void) => {
      console.log('Preload: Setting up file-change listener');
      const handler = (event: any, data: any) => {
        console.log('Preload: Received file-change event:', { event, data });
        // Handle case where data might be in event or as separate parameter
        const eventData = data || event;
        callback(event, eventData);
      };
      ipcRenderer.on('file-change', handler);
      return () => {
        console.log('Preload: Removing file-change listener');
        ipcRenderer.removeListener('file-change', handler);
      };
    },
    
    onStatusChange: (callback: (event: any, data: any) => void) => {
      console.log('Preload: Setting up status-change listener');
      const handler = (event: any, data: any) => {
        console.log('Preload: Received status-change event:', { event, data });
        // Handle case where data might be in event or as separate parameter
        const eventData = data || event;
        callback(event, eventData);
      };
      ipcRenderer.on('status-change', handler);
      return () => {
        console.log('Preload: Removing status-change listener');
        ipcRenderer.removeListener('status-change', handler);
      };
    }
  }
};

// Expose the API to the renderer process
contextBridge.exposeInMainWorld('electron', electronAPI);
contextBridge.exposeInMainWorld('electronAPI', electronAPI);  // For backward compatibility

// Make this file a module
export {};
