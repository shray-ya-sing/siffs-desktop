/*
 * Siffs - Fast File Search Desktop Application
 * Copyright (C) 2025  Siffs
 * 
 * Contact: github.suggest277@passinbox.com
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
/**
 * Session Storage Service
 * Handles secure storage of authentication tokens and session data
 */

import { AuthUser, AuthSession } from './auth-api.service';

export interface StoredSession {
  user: AuthUser;
  session: AuthSession;
  stored_at: number;
}

class SessionStorageService {
  private static readonly SESSION_KEY = 'cori-auth-session';
  private static readonly USER_KEY = 'cori-auth-user';

  /**
   * Store session data securely
   */
  setSession(user: AuthUser, session: AuthSession): void {
    try {
      const sessionData: StoredSession = {
        user,
        session,
        stored_at: Date.now(),
      };

      localStorage.setItem(SessionStorageService.SESSION_KEY, JSON.stringify(sessionData));
      localStorage.setItem(SessionStorageService.USER_KEY, JSON.stringify(user));
    } catch (error) {
      console.error('Failed to store session:', error);
    }
  }

  /**
   * Get stored session data
   */
  getSession(): StoredSession | null {
    try {
      const stored = localStorage.getItem(SessionStorageService.SESSION_KEY);
      if (!stored) return null;

      const sessionData: StoredSession = JSON.parse(stored);
      
      // Check if session is expired
      if (this.isSessionExpired(sessionData.session)) {
        this.clearSession();
        return null;
      }

      return sessionData;
    } catch (error) {
      console.error('Failed to retrieve session:', error);
      this.clearSession();
      return null;
    }
  }

  /**
   * Get stored user data
   */
  getUser(): AuthUser | null {
    try {
      const stored = localStorage.getItem(SessionStorageService.USER_KEY);
      if (!stored) return null;

      return JSON.parse(stored) as AuthUser;
    } catch (error) {
      console.error('Failed to retrieve user:', error);
      return null;
    }
  }

  /**
   * Get access token
   */
  getAccessToken(): string | null {
    const session = this.getSession();
    return session?.session.access_token || null;
  }

  /**
   * Check if session is expired
   */
  isSessionExpired(session: AuthSession): boolean {
    if (!session.expires_at) return false;
    
    const now = Math.floor(Date.now() / 1000);
    const buffer = 60; // 1 minute buffer
    
    return now >= (session.expires_at - buffer);
  }

  /**
   * Clear all session data
   */
  clearSession(): void {
    try {
      localStorage.removeItem(SessionStorageService.SESSION_KEY);
      localStorage.removeItem(SessionStorageService.USER_KEY);
    } catch (error) {
      console.error('Failed to clear session:', error);
    }
  }

  /**
   * Update user data only (keeping session intact)
   */
  updateUser(user: AuthUser): void {
    try {
      const currentSession = this.getSession();
      if (currentSession) {
        this.setSession(user, currentSession.session);
      }
    } catch (error) {
      console.error('Failed to update user:', error);
    }
  }

  /**
   * Check if user is authenticated (has valid session)
   */
  isAuthenticated(): boolean {
    const session = this.getSession();
    return session !== null && !this.isSessionExpired(session.session);
  }

  /**
   * Generic method to store any data with a key
   */
  set(key: string, value: any): void {
    try {
      localStorage.setItem(`cori-${key}`, JSON.stringify(value));
    } catch (error) {
      console.error(`Failed to store ${key}:`, error);
    }
  }

  /**
   * Generic method to retrieve any data by key
   */
  get(key: string): any {
    try {
      const stored = localStorage.getItem(`cori-${key}`);
      if (!stored) return null;
      return JSON.parse(stored);
    } catch (error) {
      console.error(`Failed to retrieve ${key}:`, error);
      return null;
    }
  }

  /**
   * Clear all stored data
   */
  clear(): void {
    try {
      // Clear all cori-related items
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.startsWith('cori-')) {
          localStorage.removeItem(key);
        }
      });
    } catch (error) {
      console.error('Failed to clear storage:', error);
    }
  }
}

export const sessionStorage = new SessionStorageService();
