import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Default values for development (fallback only)
const DEFAULT_SUPABASE_URL = 'https://otnlburbcvilvzgbjzqi.supabase.co';
const DEFAULT_SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90bmxidXJiY3ZpbHZ6Z2JqenFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc5MDU3NDEsImV4cCI6MjA2MzQ4MTc0MX0.zjP0acdJxkhzqwSIE6Vexw6XoBk4fUAssb8LiGHxY3Y';

// Get environment variables from the preload script
const getEnv = async (key: string): Promise<string> => {
  if (!window.electron?.getEnv) {
    throw new Error('Electron context bridge is not available');
  }
  
  const value = await window.electron.getEnv(key);
  if (!value) {
    throw new Error(`Missing environment variable: ${key}`);
  }
  return value;
};

let supabaseInstance: SupabaseClient | null = null;

// Initialize and export Supabase client
export const getSupabase = async (): Promise<SupabaseClient> => {
  if (supabaseInstance) {
    return supabaseInstance;
  }

  try {
    const [supabaseUrl, supabaseAnonKey] = await Promise.all([
      getEnv('REACT_APP_SUPABASE_URL'),
      getEnv('REACT_APP_SUPABASE_ANON_KEY')
    ]);

    supabaseInstance = createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: false, // Important for Electron
      },
    });

    return supabaseInstance;
  } catch (error) {
    console.error('Failed to initialize Supabase:', error);
    
    // Fallback to default values in development
    if (process.env.NODE_ENV === 'development') {
      console.warn('Using default Supabase URL and key');
      return createClient(DEFAULT_SUPABASE_URL, DEFAULT_SUPABASE_KEY, {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: false,
        },
      });
    }
    
    throw error;
  }
};

// For backward compatibility
export const supabase = {
  ...createClient(DEFAULT_SUPABASE_URL, DEFAULT_SUPABASE_KEY),
  // This will be properly initialized on first use
  auth: {
    signInWithPassword: async (credentials: any) => {
      const client = await getSupabase();
      return client.auth.signInWithPassword(credentials);
    },
    signUp: async (credentials: any) => {
      const client = await getSupabase();
      return client.auth.signUp(credentials);
    },
    signOut: async () => {
      const client = await getSupabase();
      return client.auth.signOut();
    },
    // Add other auth methods as needed
  },
  // Add other Supabase methods as needed
} as unknown as SupabaseClient;

// Helper function to get the current session
export const getCurrentSession = async () => {
  const { data: { session } } = await supabase.auth.getSession();
  return session;
};

// Helper function to get the current user
export const getCurrentUser = async () => {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
};
