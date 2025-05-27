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

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}