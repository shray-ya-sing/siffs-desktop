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


  return (
    <>
      <Toaster />
      <div className="flex h-screen text-gray-200 font-sans font-thin overflow-hidden">
        <div className="flex-1 flex flex-col overflow-hidden">
          <Routes>
            <Route path="/" element={
               <HomePage />
            } />
            <Route path="/settings" element={
              <SettingsPage />
            } />

            <Route path="/agent-chat" element={
              <AgentChatPage />
            } />
            <Route path="/404" element={<NotFound />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Routes>
        </div>
      </div>
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
      <AppRouter />
  );
}