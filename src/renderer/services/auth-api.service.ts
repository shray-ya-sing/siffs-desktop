/**
 * Auth API Service for Backend Proxy Integration
 * Replaces direct Supabase calls with secure backend proxy calls
 */

export interface AuthUser {
  id: string;
  email: string;
  email_confirmed_at?: string;
  created_at: string;
  updated_at?: string;
  last_sign_in_at?: string;
  user_metadata?: any;
  app_metadata?: any;
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  expires_in: number;
}

export interface AuthResponse {
  user: AuthUser | null;
  session: AuthSession | null;
  message?: string;
}

export interface AuthError {
  message: string;
  status?: number;
}

class AuthAPIService {
  private baseURL: string;

  constructor() {
    // Use the deployed Vercel proxy
    this.baseURL = 'https://volute-auth-proxy.vercel.app/api';
  }

  private async makeRequest(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers: defaultHeaders,
      });

      const data = await response.json();

      if (!response.ok) {
        throw {
          message: data.error || 'Request failed',
          status: response.status,
        };
      }

      return data;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw {
          message: 'Network error. Please check your connection.',
          status: 0,
        };
      }
      throw error;
    }
  }

  async signIn(email: string, password: string): Promise<{ data: AuthResponse | null; error: AuthError | null }> {
    try {
      const data = await this.makeRequest('/auth/signin', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });

      return { data, error: null };
    } catch (error) {
      return { data: null, error: error as AuthError };
    }
  }

  async signUp(email: string, password: string): Promise<{ data: AuthResponse | null; error: AuthError | null }> {
    try {
      const data = await this.makeRequest('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });

      return { data, error: null };
    } catch (error) {
      return { data: null, error: error as AuthError };
    }
  }

  async signOut(): Promise<{ error: AuthError | null }> {
    try {
      // Get access token from session storage
      const { sessionStorage } = require('./session-storage.service');
      const accessToken = sessionStorage.getAccessToken();
      
      if (accessToken) {
        await this.makeRequest('/auth/signout', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });
      }

      return { error: null };
    } catch (error) {
      return { error: error as AuthError };
    }
  }

  async resetPassword(email: string): Promise<{ data: any; error: AuthError | null }> {
    try {
      const data = await this.makeRequest('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });

      return { data, error: null };
    } catch (error) {
      return { data: null, error: error as AuthError };
    }
  }

  async updatePassword(email: string, newPassword: string): Promise<{ data: any; error: AuthError | null }> {
    try {
      const data = await this.makeRequest('/auth/update-password', {
        method: 'POST',
        body: JSON.stringify({ email, newPassword }),
      });

      // Clear reset tokens after successful password update (if any exist)
      const { sessionStorage } = require('./session-storage.service');
      const resetTokens = sessionStorage.get('reset_tokens');
      if (resetTokens) {
        localStorage.removeItem('cori-reset_tokens');
      }

      return { data, error: null };
    } catch (error) {
      console.error('Password update error:', error);
      return { data: null, error: error as AuthError };
    }
  }

  async verifyOtp(email: string, token: string, type: 'email' | 'recovery' = 'recovery'): Promise<{ data: AuthResponse | null; error: AuthError | null }> {
    try {
      const data = await this.makeRequest('/auth/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ email, token, type }),
      });

      return { data, error: null };
    } catch (error) {
      return { data: null, error: error as AuthError };
    }
  }

  async getUserProfile(): Promise<{ data: { user: AuthUser } | null; error: AuthError | null }> {
    try {
      // Get access token from session storage
      const { sessionStorage } = require('./session-storage.service');
      const accessToken = sessionStorage.getAccessToken();
      
      if (!accessToken) {
        throw {
          message: 'No authentication token available',
          status: 401,
        };
      }
      
      const data = await this.makeRequest('/user/profile', {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      return { data, error: null };
    } catch (error) {
      return { data: null, error: error as AuthError };
    }
  }
}

export const authAPI = new AuthAPIService();
