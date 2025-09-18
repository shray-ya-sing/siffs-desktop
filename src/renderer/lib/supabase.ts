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
// This file is now deprecated - we use the auth proxy instead of direct Supabase client
// Keeping this file for backward compatibility but all auth is now handled via the proxy

// Note: This app now uses the backend auth proxy at https://your-proxy-domain.vercel.app/api/auth/*
// No Supabase credentials are needed in the frontend anymore

console.warn('⚠️  supabase.ts is deprecated - this app now uses the auth proxy. Please use authAPI service instead.');

// Export empty objects to prevent breaking existing imports
export const supabase = null;
export const getCurrentSession = () => {
  throw new Error('getCurrentSession is deprecated - use sessionStorage.getSession() instead');
};
export const getCurrentUser = () => {
  throw new Error('getCurrentUser is deprecated - use sessionStorage.getUser() instead');
};
