/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  [key: string]: string | undefined; // Allow dynamic access to env vars
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// For Electron context
declare global {
  interface Window {
    electron: {
      getEnv: (key: string) => string | undefined;
      getEnvironment: () => Record<string, string>;
    };
  }
}

export {};
