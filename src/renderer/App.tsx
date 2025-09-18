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
import { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate, Location } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { NotFound } from './pages/NotFound';
import AppLoading from './components/loading/AppLoading';
import LoginPage from './pages/auth/LoginPage';
import SignupPage from './pages/auth/SignupPage';
import { default as VerifyEmail } from './pages/auth/VerifyEmail';
import AuthCallbackPage from './pages/auth/AuthCallbackPage';
import { AuthProvider, useAuth } from './providers/AuthProvider';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Toaster } from './components/ui/toaster';
import { useToast } from './components/ui/use-toast';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import ResetPasswordEmailSent from './pages/auth/ResetPasswordEmailSent';
import ResetPasswordPage from './pages/auth/ResetPasswordPage';
import AuthLoading from './components/loading/AuthLoading';
import { FileItem } from './hooks/useFileTree';
import { TitleBar } from './components/titlebar/TitleBar';

// Google Analytics helper
const gtag = (window as any).gtag;
const trackPageView = (path: string) => {
  if (process.env.NODE_ENV === 'production' && gtag) {
    gtag('config', 'G-M7P8XZHLFX', {
      page_path: path,
    });
  }
};

const trackEvent = (eventName: string, parameters?: any) => {
  if (process.env.NODE_ENV === 'production' && gtag) {
    gtag('event', eventName, parameters);
  }
};

// Extend the Location interface to include state
type LocationState = {
  from?: Location;
  message?: string;
  files?: FileItem[];  // Add this line
};

type LocationWithState = Location & {
  state: LocationState | null;
};


// Component to handle auth state and routing
function AppRouter() {
  const location = useLocation() as LocationWithState;
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, isLoading } = useAuth();

  // Track page views
  useEffect(() => {
    if (user && !isLoading) {
      trackPageView(location.pathname);
    }
  }, [location.pathname, user, isLoading]);

  // Handle success message from signup
  useEffect(() => {
    if (location.state?.message) {
      toast({
        title: 'Success',
        description: location.state.message,
      });
      // Clear the state to avoid showing the message again on refresh
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.state, location.pathname, navigate, toast]);

  // Show loading spinner while checking auth
  if (isLoading) {
    return <AuthLoading />;
  }

  return (
    <>
      <Toaster />
      <Routes>
        {/* Public Auth Routes */}
        <Route path="/auth/login" element={
          user ? <Navigate to="/" replace /> : <LoginPage />
        } />
        <Route path="/auth/signup" element={
          user ? <Navigate to="/" replace /> : <SignupPage />
        } />
        <Route path="/auth/forgot-password" element={
          user ? <Navigate to="/" replace /> : <ForgotPasswordPage />
        } />
        <Route path="/auth/verify-email" element={<VerifyEmail />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/auth/reset-password" element={<ResetPasswordPage />} />
        <Route path="/auth/reset-email-sent" element={<ResetPasswordEmailSent />} />
        
        {/* Protected Routes */}
        <Route path="/" element={
          <ProtectedRoute>
            <>
              <TitleBar />
              <HomePage />
            </>
          </ProtectedRoute>
        } />
        
        {/* Fallback Routes */}
        <Route path="/404" element={<NotFound />} />
        <Route path="*" element={
          user ? <Navigate to="/" replace /> : <Navigate to="/auth/login" replace />
        } />
      </Routes>
    </>
  );
}

export function App() {
  const [isAppLoading, setIsAppLoading] = useState(true);

  const handleLoadingComplete = () => {
    setIsAppLoading(false);
  };

  // Track app session start/end
  useEffect(() => {
    if (process.env.NODE_ENV === 'production' && gtag) {
      // Track session start
      gtag('event', 'session_start', {
        engagement_time_msec: 100
      });

      // Track when user leaves/closes app
      const handleBeforeUnload = () => {
        gtag('event', 'session_end');
      };

      window.addEventListener('beforeunload', handleBeforeUnload);
      return () => {
        window.removeEventListener('beforeunload', handleBeforeUnload);
      };
    }
  }, []);

  if (isAppLoading) {
    return <AppLoading onComplete={handleLoadingComplete} />;
  }

  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}
