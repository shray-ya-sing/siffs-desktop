// Import your preload type
import { ElectronAPI } from '../main/preload';

// Support for CSS modules
declare module '*.module.css' {
  const classes: { [key: string]: string };
  export default classes;
}

// Support for CSS
declare module '*.css';

// Support for images
declare module '*.png';
declare module '*.jpg';
declare module '*.jpeg';
declare module '*.gif';
declare module '*.svg' {
  const content: string;
  export default content;
}

// Support for React JSX
import 'react';

declare module 'react' {
  interface HTMLAttributes<T> extends AriaAttributes, DOMAttributes<T> {
    // Add any custom HTML attributes here
    class?: string;
  }
}

// Support for process.env
declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV: 'development' | 'production' | 'test';
    // Add other environment variables here
  }
}

// Extend the existing ElectronAPI interface to include ipcRenderer and log
interface ExtendedElectronAPI extends ElectronAPI {
  log: {
    info: (message: string) => void;
    error: (message: string) => void;
    warn: (message: string) => void;
    debug: (message: string) => void;
  };
  ipcRenderer: {
    invoke: (channel: string, ...args: any[]) => Promise<any>;
    send: (channel: string, ...args: any[]) => void;
    on: (channel: string, listener: (...args: any[]) => void) => () => void;
  };
}

declare global {
  interface Window {
    // For backward compatibility
    electronAPI: ElectronAPI;
    
    // New electron object with extended API
    electron: {
      getEnv: (key: string) => string | undefined;
      log: {
        info: (message: string) => void;
        error: (message: string) => void;
        warn: (message: string) => void;
        debug: (message: string) => void;
      };
      ipcRenderer: {
        invoke: (channel: string, ...args: any[]) => Promise<any>;
        send: (channel: string, ...args: any[]) => void;
        on: (channel: string, listener: (...args: any[]) => void) => () => void;
      };
    };
  }
}