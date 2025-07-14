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
