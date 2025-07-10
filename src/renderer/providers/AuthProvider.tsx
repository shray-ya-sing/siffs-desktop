import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Session, User } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

type AuthContextType = {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<{ data: any; error: any }>;
  signUp: (email: string, password: string) => Promise<{ data: any; error: any }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ data: any; error: any }>;
  updatePassword: (newPassword: string) => Promise<{ data: any; error: any }>;
  verifyOtp: (email: string, token: string, type?: 'email' | 'recovery') => Promise<{ data: any; error: any }>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const setupAuthListener = useCallback(() => {
    try {
      // Set initial session
      supabase.auth.getSession().then(({ data: { session } }) => {
        setSession(session);
        setUser(session?.user ?? null);
        setIsLoading(false);
      });
      
      // Listen for auth state changes
      const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
        console.log('Auth state changed:', event, session?.user?.email);
        setSession(session);
        setUser(session?.user ?? null);
      });
      
      return () => {
        subscription?.unsubscribe();
      };
    } catch (error) {
      console.error('Auth setup error:', error);
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const cleanup = setupAuthListener();
    return cleanup;
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

  const signUp = useCallback(async (email: string, password: string) => {
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });
      
      if (error) {
        console.error('Sign up error:', error);
      }
      
      return { data, error };
    } catch (error) {
      console.error('Sign up exception:', error);
      return { 
        data: null, 
        error: { 
          message: 'Failed to sign up. Please try again later.',
          status: 500
        } 
      };
    }
  }, []);

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

  const resetPassword = useCallback(async (email: string) => {
    try {
      // Send OTP code to email for password recovery
      const { data, error } = await supabase.auth.signInWithOtp({
        email: email,
        options: {
          shouldCreateUser: false, // Don't create new user if doesn't exist
          data: {
            type: 'recovery' // Specify this is for password recovery
          }
        }
      });
      
      if (error) {
        console.error('Reset password error:', error);
      }
      
      return { data, error };
    } catch (error) {
      console.error('Reset password exception:', error);
      return { 
        data: null, 
        error: { 
          message: 'Failed to send reset code. Please try again later.',
          status: 500
        } 
      };
    }
  }, []);

  const updatePassword = useCallback(async (newPassword: string) => {
    try {
      const { data, error } = await supabase.auth.updateUser({
        password: newPassword
      });
      
      if (error) {
        console.error('Update password error:', error);
      }
      
      return { data, error };
    } catch (error) {
      console.error('Update password exception:', error);
      return { 
        data: null, 
        error: { 
          message: 'Failed to update password. Please try again later.',
          status: 500
        } 
      };
    }
  }, []);

  const verifyOtp = useCallback(async (email: string, token: string, type: 'email' | 'recovery' = 'recovery') => {
    try {
      const { data, error } = await supabase.auth.verifyOtp({
        email: email,
        token: token,
        type: type // Use 'recovery' for password reset, 'email' for login
      });
      
      if (error) {
        console.error('Verify OTP error:', error);
      }
      
      return { data, error };
    } catch (error) {
      console.error('Verify OTP exception:', error);
      return { 
        data: null, 
        error: { 
          message: 'Failed to verify code. Please try again later.',
          status: 500
        } 
      };
    }
  }, []);

  const value = {
    user,
    session,
    isLoading,
    signIn,
    signUp,
    signOut,
    resetPassword,
    updatePassword,
    verifyOtp,
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
