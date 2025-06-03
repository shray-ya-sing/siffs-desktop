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
import { ModelAuditPage } from './pages/tools/ModelAuditPage';
import AuthLoading from './components/loading/AuthLoading';

// Extend the Location interface to include state
type LocationState = {
  from?: Location;
  message?: string;
};

type LocationWithState = Location & {
  state: LocationState | null;
};

// Component to handle auth state and routing
function AppRouter() {
  const { isLoading, user } = useAuth();
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <AuthLoading />
      </div>
    );
  }

  // If user is not authenticated and not on an auth page, redirect to login
  if (!user && !location.pathname.startsWith('/auth')) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  // If user is authenticated and on an auth page, redirect to home
  if (user && location.pathname.startsWith('/auth') && !location.pathname.startsWith('/auth/callback')) {
    return <Navigate to="/" replace />;
  }

  return (
    <>
      <Toaster />
      <div className="flex h-screen bg-[#0a0f1a] text-gray-200 font-sans font-thin overflow-hidden">
        <div className="flex-1 flex flex-col overflow-hidden">
          <Routes>
            <Route path="/" element={
              <ProtectedRoute>
                <HomePage />
              </ProtectedRoute>
            } />
            <Route path="/settings" element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            } />
            <Route path="/auth/login" element={<LoginPage />} />
            <Route path="/auth/signup" element={<SignupPage />} />
            <Route path="/auth/verify-email" element={<VerifyEmail />} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route path="/404" element={<NotFound />} />
            <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/auth/reset-email-sent" element={<ResetPasswordEmailSent />} />
            <Route path="/tools/model-audit" element={<ModelAuditPage />} />
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
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}