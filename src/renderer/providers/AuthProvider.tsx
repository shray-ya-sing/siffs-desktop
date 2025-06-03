import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Session, User } from '@supabase/supabase-js';
import { getSupabase, supabase } from '../lib/supabase';

type AuthContextType = {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<{ data: any; error: any }>;
  signUp: (email: string, password: string) => Promise<{ data: any; error: any }>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const setupAuthListener = useCallback(async () => {
    try {
      const client = await getSupabase();
      
      // Set initial session
      const { data: { session } } = await client.auth.getSession();
      setSession(session);
      setUser(session?.user ?? null);
      
      // Listen for auth state changes
      const { data: { subscription } } = client.auth.onAuthStateChange(async (event, session) => {
        if (process.env.NODE_ENV === 'development') {
          console.debug('Auth state changed:', event);
        }
        setSession(session);
        setUser(session?.user ?? null);
      });
      
      return () => {
        subscription?.unsubscribe();
      };
    } catch (error) {
      // Only log in development
      if (process.env.NODE_ENV === 'development') {
        console.warn('Auth listener warning:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const cleanup = setupAuthListener();
    return () => {
      cleanup.then(cleanupFn => cleanupFn?.());
    };
  }, [setupAuthListener]);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      
      if (error) {
        // Handle specific error cases
        if (error.status === 400) {
          error.message = 'Invalid email or password';
        } else if (error.status === 429) {
          error.message = 'Too many attempts. Please try again later.';
        }
      }
      
      return { data, error };
    } catch (error) {
      // Don't log to console, just return a clean error
      return { 
        data: null, 
        error: { 
          message: 'Failed to sign in. Please try again later.',
          status: 500
        } 
      };
    }
  }, []);

  const signUp = async (email: string, password: string) => {
    try {
      const client = await getSupabase();
      const { data, error } = await client.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });
      return { data, error };
    } catch (error) {
      console.error('Sign up error:', error);
      return { data: null, error };
    }
  };

  const signOut = useCallback(async () => {
    try {
      await supabase.auth.signOut();
    } catch (error) {
      // Silently handle sign out errors
      if (process.env.NODE_ENV === 'development') {
        console.warn('Sign out warning:', error);
      }
      throw error;
    }
  }, []);

  const value = {
    user,
    session,
    isLoading,
    signIn,
    signUp,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
