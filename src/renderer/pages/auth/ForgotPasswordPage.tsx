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
// src/renderer/pages/auth/ForgotPasswordPage.tsx
import React, { useState } from 'react';
import { Link, useLocation , useNavigate} from 'react-router-dom';
import { LocationWithState } from '../../types/auth';
import { motion, AnimatePresence } from 'framer-motion';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import AuthLayout from '../../components/auth/AuthLayout';
import { Loader2, Mail, ArrowLeft, Check, AlertCircle } from 'lucide-react';
import { useAuth } from '../../providers/AuthProvider';


export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const location = useLocation() as LocationWithState;
  const navigate = useNavigate();
  const { resetPassword } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email) {
      setError('Please enter your email address');
      return;
    }
    
    setIsLoading(true);
    setError('');
    setMessage('');
    
    try {
      // Send OTP code to email for password reset
      const { error } = await resetPassword(email);
      
      if (error) {
        console.error('Password reset error:', error);
        setError('Failed to send reset code. Please try again.');
        return;
      }
      
      // Navigate to OTP verification page
      navigate('/auth/reset-password', { 
        state: { 
          email: email,
          isOTPFlow: true
        } 
      });
    } catch (err) {
      console.error('Error:', err);
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <AnimatePresence mode="wait">
        <motion.div
          key="forgot-password-form"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          className="w-full"
        >
          <div className="mb-6">
            <Link 
              to="/auth/login" 
              className="inline-flex items-center text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
              state={{ from: location.state?.from }}
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back to login
            </Link>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-6 w-full">
            <div className="space-y-2">
              <motion.h2 
                className="text-3xl font-bold text-white text-center"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                Reset Password
              </motion.h2>
              <motion.p 
                className="text-sm text-white/70 text-center"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                Enter your email and we'll send you a verification code to reset your password
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
              
              {message ? (
                <motion.div 
                  initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                  animate={{ opacity: 1, height: 'auto', marginBottom: '1rem' }}
                  className="overflow-hidden"
                >
                  <div className="flex items-start p-4 text-sm rounded-lg bg-green-500/10 border border-green-500/30 text-green-400">
                    <Check className="h-5 w-5 mr-2 mt-0.5 flex-shrink-0" />
                    <span>{message}</span>
                  </div>
                  
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="mt-4 pt-4 border-t border-white/5"
                  >
                    <p className="text-sm text-white/60 mb-4">
                      Didn't receive the email? Check your spam folder or
                    </p>
                    <Button
                      type="button"
                      onClick={() => {
                        setMessage('');
                        setEmail('');
                      }}
                      variant="outline"
                      className="w-full bg-white/5 border-white/10 text-white hover:bg-white/10"
                    >
                      Try another email
                    </Button>
                  </motion.div>
                </motion.div>
              ) : (
                <motion.div 
                  className="space-y-4"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-sm font-medium text-white/80">
                      Email
                    </Label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Mail className="h-5 w-5 text-white/40" />
                      </div>
                      <Input
                        id="email"
                        type="email"
                        placeholder="name@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="w-full pl-10 bg-white/5 border-white/10 text-white placeholder:text-white/40 
                                 focus-visible:ring-2 focus-visible:ring-blue-500/50 focus-visible:border-transparent
                                 transition-all duration-200 rounded-lg h-11"
                      />
                    </div>
                  </div>

                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 }}
                  >
                    <Button 
                      type="submit" 
                      className="w-full py-3 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 
                               hover:from-blue-500 hover:to-blue-400 text-white font-medium
                               shadow-lg hover:shadow-blue-500/20 transition-all duration-300
                               transform hover:-translate-y-0.5"
                      disabled={isLoading || !email}
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        'Reset Password'
                      )}
                    </Button>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </form>
          
          {!message && (
            <motion.div 
              className="text-center text-sm text-white/60 mt-6 pt-6 border-t border-white/5"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              Remember your password?{' '}
              <Link 
                to="/auth/login" 
                className="font-medium text-blue-400 hover:text-blue-300 transition-colors"
                state={{ from: location.state?.from }}
              >
                Sign in
              </Link>
            </motion.div>
          )}
        </motion.div>
      </AnimatePresence>
    </AuthLayout>
  );
}