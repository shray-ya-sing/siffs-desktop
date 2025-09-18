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
import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { LocationWithState } from '../../types/auth';
import { motion, AnimatePresence } from 'framer-motion';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import AuthLayout from '../../components/auth/AuthLayout';
import { useAuth } from '../../providers/AuthProvider';
import { Loader2, Mail, Lock, AlertCircle, Eye, EyeOff, Check, X, ArrowRight } from 'lucide-react';

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (!email || !password || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      const { error } = await signUp(email, password);
      
      if (error) {
        throw error;
      }
      
      // On successful signup, redirect to verify email page
      navigate('/auth/verify-email', { state: { email } });
    } catch (error) {
      console.error('Signup error:', error);
      setError(error instanceof Error ? error.message : 'Failed to create account. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);
  const location = useLocation() as LocationWithState;

  const passwordValidations = [
    {
      label: 'At least 8 characters',
      validator: (p: string) => p.length >= 8,
    },
    {
      label: 'Contains a number',
      validator: (p: string) => /[0-9]/.test(p),
    },
    {
      label: 'Contains a special character',
      validator: (p: string) => /[!@#$%^&*(),.?":{}|<>]/.test(p),
    },
  ];

  const allValid = passwordValidations.every(validation => validation.validator(password));
  const passwordsMatch = password === confirmPassword;

  return (
    <AuthLayout>
      <AnimatePresence mode="wait">
        <motion.div
          key="signup-form"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          className="w-full"
        >
          <form onSubmit={handleSubmit} className="space-y-6 w-full">
            <div className="space-y-2 text-center">
              <motion.h2 
                className="text-3xl font-bold text-gray-700"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                Create an account
              </motion.h2>
              <motion.p 
                className="text-sm text-gray-400"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                Enter your details to get started
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
                <Label htmlFor="email" className="text-sm font-medium text-gray-400">Email</Label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-gray-500" />
                  </div>
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                    required
                    className="w-full pl-10 bg-white/5 border-white/10 text-gray-800 placeholder:text-gray-400 
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
                <Label htmlFor="password" className="text-sm font-medium text-gray-400">Password</Label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-500" />
                  </div>
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                    onFocus={() => setPasswordFocused(true)}
                    onBlur={() => setPasswordFocused(false)}
                    required
                    minLength={8}
                    className="w-full pl-10 pr-10 bg-white/5 border-white/10 text-gray-800 placeholder:text-gray-400 
                             focus-visible:ring-2 focus-visible:ring-blue-500/50 focus-visible:border-transparent
                             transition-all duration-200 rounded-lg h-11"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-gray-600 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>

                {(passwordFocused || password) && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-2 space-y-1.5 text-xs text-gray-400"
                  >
                    {passwordValidations.map((validation) => {
                      const isValid = validation.validator(password);
                      return (
                        <div key={validation.label} className="flex items-center">
                          <div className={`mr-2 flex-shrink-0 ${isValid ? 'text-green-500' : 'text-gray-500'}`}>
                            {isValid ? (
                              <Check className="h-3.5 w-3.5" />
                            ) : (
                              <X className="h-3.5 w-3.5" />
                            )}
                          </div>
                          <span className={isValid ? 'text-gray-600' : 'text-gray-600'}>{validation.label}</span>
                        </div>
                      );
                    })}
                  </motion.div>
                )}
              </motion.div>

              <motion.div 
                className="space-y-2"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Label htmlFor="confirmPassword" className="text-sm font-medium text-gray-400">
                  Confirm Password
                </Label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-500" />
                  </div>
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfirmPassword(e.target.value)}
                    required
                    minLength={8}
                    className={`w-full pl-10 pr-10 bg-white/5 border ${
                      confirmPassword
                        ? passwordsMatch
                          ? 'border-green-500/50'
                          : 'border-red-500/50'
                        : 'border-white/10'
                    } text-gray-800 placeholder:text-gray-400 
                    focus-visible:ring-2 focus-visible:ring-blue-500/50 focus-visible:border-transparent
                    transition-all duration-200 rounded-lg h-11`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-gray-600 transition-colors"
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
                {confirmPassword && !passwordsMatch && (
                  <motion.p 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-1 text-xs text-red-400 flex items-center"
                  >
                    <X className="h-3.5 w-3.5 mr-1" />
                    Passwords do not match
                  </motion.p>
                )}
                {confirmPassword && passwordsMatch && (
                  <motion.p 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-1 text-xs text-green-400 flex items-center"
                  >
                    <Check className="h-3.5 w-3.5 mr-1" />
                    Passwords match
                  </motion.p>
                )}
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="flex justify-end"
              >
                <button
                  type="submit" 
                  className={`group p-3 rounded-full bg-transparent hover:bg-white/5 transition-all duration-200 ${
                    !allValid || !passwordsMatch || !email
                      ? 'opacity-50 cursor-not-allowed'
                      : ''
                  }`}
                  disabled={isLoading || !allValid || !passwordsMatch || !email}
                >
                  {isLoading ? (
                    <Loader2 className="h-6 w-6 text-gray-600 animate-spin" />
                  ) : (
                    <motion.div
                      initial={{ x: 0 }}
                      animate={{ x: (!allValid || !passwordsMatch || !email) ? 0 : 2 }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                      whileHover={{ x: (!allValid || !passwordsMatch || !email) ? 0 : 2 }}
                    >
                      <ArrowRight className={`h-6 w-6 transition-colors ${
                        !allValid || !passwordsMatch || !email
                          ? 'text-gray-500'
                          : 'text-gray-600 group-hover:text-gray-700'
                      }`} />
                    </motion.div>
                  )}
                </button>
              </motion.div>
            </div>

            <motion.div 
              className="text-center text-sm text-gray-400"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              Already have an account?{' '}
              <Link 
                to="/auth/login" 
                className="font-medium text-blue-400 hover:text-blue-300 transition-colors"
                state={{ from: location.state?.from }}
              >
                Sign in
              </Link>
            </motion.div>
          </form>
        </motion.div>
      </AnimatePresence>
    </AuthLayout>
  );
}
