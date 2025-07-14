import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authAPI, AuthUser, AuthSession } from '../services/auth-api.service';
import { sessionStorage } from '../services/session-storage.service';

type AuthContextType = {
  user: AuthUser | null;
  session: AuthSession | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<{ data: any; error: any }>;
  signUp: (email: string, password: string) => Promise<{ data: any; error: any }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ data: any; error: any }>;
  updatePassword: (email: string, newPassword: string) => Promise<{ data: any; error: any }>;
  verifyOtp: (email: string, token: string, type?: 'email' | 'recovery') => Promise<{ data: any; error: any }>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const initializeAuth = useCallback(async () => {
    try {
      // Try to load existing session from storage
      const savedSession = sessionStorage.getSession();
      const savedUser = sessionStorage.getUser();
      
      if (savedSession && savedUser) {
        // Validate the session by trying to get user profile
        try {
          const { data: profileData, error } = await authAPI.getUserProfile();
          if (!error && profileData) {
            setSession(savedSession.session);
            setUser(savedUser);
          } else {
            // Session is invalid, clear it
            sessionStorage.clear();
          }
        } catch (error) {
          // Session validation failed, clear it
          sessionStorage.clear();
        }
      }
      
      setIsLoading(false);
    } catch (error) {
      console.error('Auth initialization error:', error);
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const { data, error } = await authAPI.signIn(email, password);
      
      if (!error && data && data.user && data.session) {
        setUser(data.user);
        setSession(data.session);
        sessionStorage.setSession(data.user, data.session);
      }
      
      return { data, error };
    } catch (error) {
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
      const { data, error } = await authAPI.signUp(email, password);
      return { data, error };
    } catch (error) {
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
      await authAPI.signOut();
      setUser(null);
      setSession(null);
      sessionStorage.clear();
    } catch (error) {
      // Even if the API call fails, clear local state
      setUser(null);
      setSession(null);
      sessionStorage.clear();
      
      if (process.env.NODE_ENV === 'development') {
        console.warn('Sign out warning:', error);
      }
    }
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    try {
      const { data, error } = await authAPI.resetPassword(email);
      return { data, error };
    } catch (error) {
      return { 
        data: null, 
        error: { 
          message: 'Failed to send reset code. Please try again later.',
          status: 500
        } 
      };
    }
  }, []);

  const updatePassword = useCallback(async (email: string, newPassword: string) => {
    try {
      const { data, error } = await authAPI.updatePassword(email, newPassword);
      return { data, error };
    } catch (error) {
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
      const { data, error } = await authAPI.verifyOtp(email, token, type);
      
      if (!error && data && data.user && data.session) {
        setUser(data.user);
        setSession(data.session);
        sessionStorage.setSession(data.user, data.session);
      }
      
      return { data, error };
    } catch (error) {
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
