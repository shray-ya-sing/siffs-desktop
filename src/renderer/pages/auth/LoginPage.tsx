import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import AuthLayout from '../../components/auth/AuthLayout';
import { useAuth } from '../../providers/AuthProvider';
import { Loader2, Mail, Lock, AlertCircle, Eye, EyeOff, ArrowRight } from 'lucide-react';

type LocationState = {
  from?: {
    pathname: string;
  };
  message?: string;
};

type LoginFormData = {
  email: string;
  password: string;
};

export default function LoginPage() {
  const [formData, setFormData] = useState<LoginFormData>({
    email: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as LocationState)?.from?.pathname || '/';

  // Clear any existing errors when the component mounts
  useEffect(() => {
    setError('');
    
    // If there's a message in the location state, show it
    if ((location.state as LocationState)?.message) {
      setError((location.state as LocationState).message || '');
      // Clear the message from location state
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user starts typing
    if (error) setError('');
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (!formData.email || !formData.password) {
      setError('Please fill in all fields');
      return;
    }

    setIsLoading(true);
    setError('');
    
    try {
      const { error } = await signIn(formData.email, formData.password);
      
      if (error) {
        // Handle specific Supabase error codes
        if (error.status === 400) {
          setError('Invalid email or password. Please try again.');
        } else if (error.status === 429) {
          setError('Too many attempts. Please try again later.');
        } else {
          setError('An error occurred. Please try again.');
        }
        return;
      }
      
      // On successful login, redirect to the intended page or home
      navigate(from, { replace: true });
    } catch (error) {
      // Silently handle the error without logging to console
      setError('An error occurred during sign in. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="w-full space-y-6">
        <AnimatePresence>
          {error && (
            <motion.div
              key="error-message"
              initial={{ opacity: 0, y: -10, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -10, height: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <div className="flex items-start p-3 text-sm rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
                <AlertCircle className="h-5 w-5 mr-2 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="space-y-5">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-2"
          >
            <Label htmlFor="email" className="text-sm font-medium text-gray-400">
              Email address
            </Label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Mail className="h-4 w-4 text-gray-400 group-focus-within:text-blue-400 transition-colors" />
              </div>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="name@example.com"
                value={formData.email}
                onChange={handleChange}
                disabled={isLoading}
                className="pl-10 pr-4 py-3 bg-white/5 border-white/10 text-gray-300 placeholder-gray-400 focus:ring-2 focus:ring-blue-500/50 focus:border-transparent transition-all duration-200"
                autoComplete="email"
                autoFocus
              />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="space-y-2"
          >
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-sm font-medium text-gray-400">
                Password
              </Label>
              <Link
                to="/auth/forgot-password"
                className="text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
                tabIndex={isLoading ? -1 : 0}
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-4 w-4 text-gray-400 group-focus-within:text-blue-400 transition-colors" />
              </div>
              <Input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                disabled={isLoading}
                className="pl-10 pr-10 py-3 bg-white/5 border-white/10 text-gray-300 placeholder-gray-400 focus:ring-2 focus:ring-blue-500/50 focus:border-transparent transition-all duration-200"
                autoComplete="current-password"
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-white transition-colors disabled:opacity-50"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isLoading}
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="pt-2"
          >
            <Button
              type="submit"
              disabled={isLoading}
              className={`w-full group relative overflow-hidden transition-all duration-300 ${
                isLoading 
                  ? 'bg-blue-600/80' 
                  : 'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 shadow-lg hover:shadow-blue-500/20'
              }`}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  <span className="relative z-10">Continue</span>
                  <motion.span 
                    className="absolute right-4 z-10"
                    initial={{ x: 0 }}
                    animate={{ x: isHovered ? 4 : 0 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  >
                    <ArrowRight className="h-4 w-4" />
                  </motion.span>
                  <motion.span 
                    className="absolute inset-0 bg-gradient-to-r from-blue-600/0 via-blue-500/30 to-blue-400/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    initial={{ x: '-100%' }}
                    animate={{ x: isHovered ? '100%' : '-100%' }}
                    transition={{ duration: 1, ease: 'easeInOut' }}
                  />
                </>
              )}
            </Button>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-center text-sm text-gray-400"
        >
          Don't have an account?{' '}
          <Link
            to="/auth/signup"
            className="font-medium text-blue-400 hover:text-blue-300 transition-colors"
            tabIndex={isLoading ? -1 : 0}
          >
            Sign up
          </Link>
        </motion.div>
      </form>
    </AuthLayout>
  );
}
