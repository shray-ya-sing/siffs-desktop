import { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate, Location } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage';
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
import { AgentChatPage } from './pages/agent-chat/AgentChatPage';
import { FileItem } from './hooks/useFileTree';

// Extend the Location interface to include state
type LocationState = {
  from?: Location;
  message?: string;
  files?: FileItem[];  // Add this line
};

type LocationWithState = Location & {
  state: LocationState | null;
};

type AgentChatLocationState = {
  files?: FileItem[];
};

// Component to handle auth state and routing
function AppRouter() {
  const location = useLocation() as LocationWithState;
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, isLoading } = useAuth();

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
            <div className="flex h-screen text-gray-200 font-sans font-thin overflow-hidden">
              <div className="flex-1 flex flex-col overflow-hidden">
                <HomePage />
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/settings" element={
          <ProtectedRoute>
            <div className="flex h-screen text-gray-200 font-sans font-thin overflow-hidden">
              <div className="flex-1 flex flex-col overflow-hidden">
                <SettingsPage />
              </div>
            </div>
          </ProtectedRoute>
        } />
        <Route path="/agent-chat" element={
          <ProtectedRoute>
            <div className="flex h-screen text-gray-200 font-sans font-thin overflow-hidden">
              <div className="flex-1 flex flex-col overflow-hidden">
                <AgentChatPage />
              </div>
            </div>
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

  if (isAppLoading) {
    return <AppLoading onComplete={handleLoadingComplete} />;
  }

  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}
