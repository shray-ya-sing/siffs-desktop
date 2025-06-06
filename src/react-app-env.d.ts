/// <reference types="react-scripts" />

// Extend the NodeJS namespace to include your environment variables
declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV: 'development' | 'production' | 'test';
    REACT_APP_SUPABASE_URL: string;
    REACT_APP_SUPABASE_ANON_KEY: string;
  }
}
