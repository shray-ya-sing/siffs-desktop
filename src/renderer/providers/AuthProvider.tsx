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
        console.log('Auth state changed:', event);
        setSession(session);
        setUser(session?.user ?? null);
      });
      
      return () => {
        subscription?.unsubscribe();
      };
    } catch (error) {
      console.error('Error setting up auth listener:', error);
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

  const signIn = async (email: string, password: string) => {
    try {
      const client = await getSupabase();
      const { data, error } = await client.auth.signInWithPassword({
        email,
        password,
      });
      return { data, error };
    } catch (error) {
      console.error('Sign in error:', error);
      return { data: null, error };
    }
  };

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

  const signOut = async () => {
    try {
      const client = await getSupabase();
      await client.auth.signOut();
    } catch (error) {
      console.error('Sign out error:', error);
      throw error;
    }
  };

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
