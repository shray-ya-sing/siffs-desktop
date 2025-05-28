import React, { useState, FormEvent, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { AuthLocationState, LocationWithState } from '../../types/auth';
import { motion, AnimatePresence } from 'framer-motion';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import AuthLayout from '../../components/auth/AuthLayout';
import { useAuth } from '../../providers/AuthProvider';
import { Loader2, Mail, Lock, AlertCircle, Eye, EyeOff } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }

    setIsLoading(true);
    setError('');
    
    try {
      const { error } = await signIn(email, password);
      
      if (error) {
        throw error;
      }
      
      // On successful login, the auth state will update and redirect
      navigate('/');
    } catch (error) {
      console.error('Login error:', error);
      setError(error instanceof Error ? error.message : 'Failed to sign in. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  interface LocationState {
    from?: {
      pathname: string;
    };
  }

  const location = useLocation() as LocationWithState;
  const [showPassword, setShowPassword] = useState(false);

  return (
    <AuthLayout>
      <AnimatePresence mode="wait">
        <motion.div
          key="login-form"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          className="w-full"
        >
          <form onSubmit={handleSubmit} className="space-y-6 w-full">
            <div className="space-y-2 text-center">
              <motion.h2 
                className="text-3xl font-bold text-white"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                Welcome back
              </motion.h2>
              <motion.p 
                className="text-sm text-white/70"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                Enter your email and password to sign in
              </motion.p>
            </div>

            <AnimatePresence>
              {error && (
                <motion.div 
                  initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                  animate={{ opacity: 1, height: 'auto', marginBottom: '1rem' }}
                  exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                  className="overflow-hidden"
                >
                  <div className="flex items-start p-3 text-sm rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
                    <AlertCircle className="h-5 w-5 mr-2 mt-0.5 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="space-y-5">
              <motion.div 
                className="space-y-2"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Label htmlFor="email" className="text-sm font-medium text-white/80">Email</Label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-white/40" />
                  </div>
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                    required
                    className="w-full pl-10 bg-white/5 border-white/10 text-white placeholder:text-white/40 
                             focus-visible:ring-2 focus-visible:ring-blue-500/50 focus-visible:border-transparent
                             transition-all duration-200 rounded-lg h-11"
                  />
                </div>
              </motion.div>

              <motion.div 
                className="space-y-2"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
              >
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium text-white/80">Password</Label>
                  <Link 
                    to="/auth/forgot-password" 
                    className="text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
                    state={{ from: (location.state as any)?.from }}
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-white/40" />
                  </div>
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                    required
                    className="w-full pl-10 pr-10 bg-white/5 border-white/10 text-white placeholder:text-white/40 
                             focus-visible:ring-2 focus-visible:ring-blue-500/50 focus-visible:border-transparent
                             transition-all duration-200 rounded-lg h-11"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-white/40 hover:text-white/70 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Button 
                  type="submit" 
                  className="w-full py-3 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 
                           hover:from-blue-500 hover:to-blue-400 text-white font-medium
                           shadow-lg hover:shadow-blue-500/20 transition-all duration-300
                           transform hover:-translate-y-0.5"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Signing in...
                    </>
                  ) : (
                    'Sign In'
                  )}
                </Button>
              </motion.div>
            </div>

            <motion.div 
              className="text-center text-sm text-white/60"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
            >
              Don't have an account?{' '}
              <Link 
                to="/auth/signup" 
                className="font-medium text-blue-400 hover:text-blue-300 transition-colors"
                state={{ from: location.state?.from }}
              >
                Sign up
              </Link>
            </motion.div>
          </form>
        </motion.div>
      </AnimatePresence>
    </AuthLayout>
  );
}
