// Type definitions for the electron context bridge API
declare namespace Electron {
  interface IpcRenderer {
    send(channel: string, ...args: any[]): void;
    on(channel: string, listener: (...args: any[]) => void): () => void;
    invoke(channel: string, ...args: any[]): Promise<any>;
  }

  interface FileSystemAPI {
    revealInExplorer(filePath: string): Promise<{ success: boolean; error?: string }>;
    deleteFile(filePath: string): Promise<{ success: boolean; error?: string }>;
    deleteDirectory(dirPath: string): Promise<{ success: boolean; error?: string }>;
    renameFile(oldPath: string, newName: string): Promise<{ success: boolean; newPath?: string; error?: string }>;
    createFile(dirPath: string, fileName: string, template?: string): Promise<{ success: boolean; filePath?: string; error?: string }>;
    createDirectory(dirPath: string, folderName: string): Promise<{ success: boolean; folderPath?: string; error?: string }>;
    copyToClipboard(text: string): Promise<{ success: boolean; error?: string }>;
    openWithDefault(filePath: string): Promise<{ success: boolean; error?: string }>;
    copyFile(sourcePath: string, destinationPath: string): Promise<{ success: boolean; destinationPath?: string; error?: string }>;
    moveFile(sourcePath: string, destinationPath: string): Promise<{ success: boolean; destinationPath?: string; error?: string }>;
  }

  interface WindowAPI {
    minimize(): Promise<void>;
    close(): Promise<void>;
    maximize(): Promise<void>;
    unmaximize(): Promise<void>;
    isMaximized(): Promise<boolean>;
  }

  interface LogAPI {
    info(message: string): void;
    error(message: string): void;
    warn(message: string): void;
    debug(message: string): void;
  }

  interface FileWatcherAPI {
    startWatching(directoryPath: string): Promise<{ success: boolean; watchedPath?: string; error?: string }>;
    stopWatching(): Promise<{ success: boolean; error?: string }>;
    getWatchedPath(): Promise<{ success: boolean; watchedPath?: string; isWatching?: boolean; error?: string }>;
    onFileChange(callback: (event: any, data: any) => void): () => void;
    onStatusChange(callback: (event: any, data: any) => void): () => void;
  }

  interface ElectronAPI {
    getEnv(key: string): string | undefined;
    getEnvironment(): Record<string, string>;
    log: LogAPI;
    ipcRenderer: IpcRenderer;
    fileSystem: FileSystemAPI;
    window: WindowAPI;
    fileWatcher: FileWatcherAPI;
  }
}

declare global {
  interface Window {
    electron: Electron.ElectronAPI;
    electronAPI: Electron.ElectronAPI; // For backward compatibility
  }
}

export {};
