import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Get Supabase credentials from environment variables
const SUPABASE_URL = 'https://aahtbntnjeppixdounji.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhaHRibnRuamVwcGl4ZG91bmppIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg0NTgyMzQsImV4cCI6MjA2NDAzNDIzNH0.-2u_pZiayWoqyNBW4iUaROyvQqtVpFJ-VLxhkAqmPJA';

// Create the Supabase client with consistent configuration
const createSupabaseClient = () => {
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false, // Important for Electron apps
      storageKey: 'cori-auth-token',
    },
    global: {
      headers: {
        'X-Client-Info': 'cori-app'
      }
    }
  });
};

// Single consistent client instance
export const supabase = createSupabaseClient();

// Helper functions using the consistent client
export const getCurrentSession = async () => {
  const { data: { session } } = await supabase.auth.getSession();
  return session;
};

export const getCurrentUser = async () => {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
};
