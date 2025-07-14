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

declare global {
  interface Window {
    // For backward compatibility
    electronAPI: any;
    
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
    fileSystem: {
      revealInExplorer: (filePath: string) => Promise<{ success: boolean; error?: string }>;
      deleteFile: (filePath: string) => Promise<{ success: boolean; error?: string }>;
      deleteDirectory: (dirPath: string) => Promise<{ success: boolean; error?: string }>;
      renameFile: (oldPath: string, newName: string) => Promise<{ success: boolean; newPath?: string; error?: string }>;
      createFile: (dirPath: string, fileName: string, template?: string) => Promise<{ success: boolean; filePath?: string; error?: string }>;
      createDirectory: (dirPath: string, folderName: string) => Promise<{ success: boolean; folderPath?: string; error?: string }>;
      copyToClipboard: (text: string) => Promise<{ success: boolean; error?: string }>;
      openWithDefault: (filePath: string) => Promise<{ success: boolean; error?: string }>;
      copyFile: (sourcePath: string, destinationPath: string) => Promise<{ success: boolean; destinationPath?: string; error?: string }>;
      moveFile: (sourcePath: string, destinationPath: string) => Promise<{ success: boolean; destinationPath?: string; error?: string }>;
    };
      fileWatcher: {
        startWatching: (directoryPath: string) => Promise<any>;
        stopWatching: () => Promise<any>;
        getWatchedPath: () => Promise<any>;
        onFileChange: (callback: (event: any, data: any) => void) => () => void;
        onStatusChange: (callback: (event: any, data: any) => void) => () => void;
      };
    };
  }
}