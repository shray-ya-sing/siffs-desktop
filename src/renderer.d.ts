// Type definitions for the electron context bridge API
declare namespace Electron {
  interface IpcRenderer {
    send(channel: string, ...args: any[]): void;
    on(channel: string, listener: (...args: any[]) => void): () => void;
    invoke(channel: string, ...args: any[]): Promise<any>;
  }

  interface ElectronAPI {
    getEnv(key: string): string | null;
    getEnvironment(): Record<string, string>;
    ipcRenderer: IpcRenderer;
  }
}

declare global {
  interface Window {
    electron: Electron.ElectronAPI;
  }
}

export {};
