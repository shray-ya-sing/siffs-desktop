import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, useLocation, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import AuthLayout from '../../components/auth/AuthLayout';
import { supabase } from '../../lib/supabase';
import { Loader2, Lock, AlertCircle, Check, Eye, EyeOff, KeyRound, ArrowLeft } from 'lucide-react';
import { useAuth } from '../../providers/AuthProvider';

type LocationState = {
  isOTPFlow?: boolean;
  email?: string;
};

export default function ResetPasswordPage() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [step, setStep] = useState<'otp' | 'password'>('otp');
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { verifyOtp, updatePassword } = useAuth();

  // Check if we have the required tokens from the URL (legacy email link flow)
  const accessToken = searchParams.get('access_token');
  const refreshToken = searchParams.get('refresh_token');
  
  // Type cast location state
  const locationState = location.state as LocationState;
  
  // Check if this is an OTP flow
  const isOTPFlow = locationState?.isOTPFlow && locationState?.email;
  
  // Get email from location state
  const email = locationState?.email || '';

  useEffect(() => {
    // If we have tokens, set the session and go directly to password step
    if (accessToken && refreshToken) {
      supabase.auth.setSession({
        access_token: accessToken,
        refresh_token: refreshToken,
      });
      setStep('password');
    }
    
    // If this is an OTP flow, start with OTP verification
    if (isOTPFlow) {
      setStep('otp');
    }
  }, [accessToken, refreshToken, isOTPFlow]);

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

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!otpCode || !email) {
      setError('Please enter the verification code');
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      const { error } = await verifyOtp(email, otpCode, 'recovery');
      
      if (error) {
        throw error;
      }
      
      // OTP verified successfully, user is now authenticated, proceed to password reset
      setStep('password');
    } catch (error) {
      console.error('OTP verification error:', error);
      setError('Invalid verification code. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!password || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!allValid) {
      setError('Please ensure your password meets all requirements');
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    try {
      const { error } = await updatePassword(password);
      
      if (error) {
        throw error;
      }
      
      // Navigate to login with success message
      navigate('/auth/login', {
        state: {
          message: 'Password updated successfully! Please sign in with your new password.'
        }
      });
    } catch (error) {
      console.error('Password update error:', error);
      setError(error instanceof Error ? error.message : 'Failed to update password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // If we don't have the required tokens AND it's not an OTP flow, show an error
  if (!isOTPFlow && (!accessToken || !refreshToken)) {
    return (
      <AuthLayout>
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <AlertCircle className="h-12 w-12 text-red-400" />
          </div>
          <h2 className="text-2xl font-bold text-white">Invalid Reset Link</h2>
          <p className="text-white/70">
            This password reset link is invalid or has expired. Please request a new one.
          </p>
          <Button
            onClick={() => navigate('/auth/forgot-password')}
            className="bg-blue-600 hover:bg-blue-700"
          >
            Request New Reset Link
          </Button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          className="w-full"
        >
          {step === 'otp' ? (
            <form onSubmit={handleOtpSubmit} className="space-y-6 w-full">
              <div className="space-y-2 text-center">
                <motion.h2 
                  className="text-3xl font-bold text-white"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  Enter Verification Code
                </motion.h2>
                <motion.p 
                  className="text-sm text-white/70"
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 }}
                >
                  We've sent a 6-digit code to <span className="font-medium text-blue-300">{email}</span>
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

              <motion.div 
                className="space-y-2"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Label htmlFor="otpCode" className="text-sm font-medium text-white/80">Verification Code</Label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <KeyRound className="h-5 w-5 text-white/40" />
                  </div>
                  <Input
                    id="otpCode"
                    type="text"
                    placeholder="123456"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    maxLength={6}
                    required
                    className="w-full pl-10 bg-white/5 border-white/10 text-white placeholder:text-white/40 
                             focus-visible:ring-2 focus-visible:ring-blue-500/50 focus-visible:border-transparent
                             transition-all duration-200 rounded-lg h-11 text-center text-lg tracking-widest"
                  />
                </div>
                <p className="text-xs text-white/60 text-center mt-2">
                  Enter the 6-digit code from your email
                </p>
              </motion.div>

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
                  disabled={isLoading || otpCode.length !== 6}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    'Verify Code'
                  )}
                </Button>
              </motion.div>
              
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-center pt-4 border-t border-white/5"
              >
                <Link 
                  to="/auth/login" 
                  className="text-sm font-medium text-white/60 hover:text-white transition-colors flex items-center justify-center gap-1.5 group"
                >
                  <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
                  Back to sign in
                </Link>
              </motion.div>
            </form>
          ) : (
            <form onSubmit={handlePasswordSubmit} className="space-y-6 w-full">
              <div className="space-y-2 text-center">
                <motion.h2 
                  className="text-3xl font-bold text-white"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  Set New Password
                </motion.h2>
                <motion.p 
                  className="text-sm text-white/70"
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 }}
                >
                  Choose a strong password for your account
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
                  <Label htmlFor="password" className="text-sm font-medium text-white/80">New Password</Label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-white/40" />
                    </div>
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
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

                  {password && (
                    <motion.div 
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-2 space-y-1.5 text-xs text-white/60"
                    >
                      {passwordValidations.map((validation) => {
                        const isValid = validation.validator(password);
                        return (
                          <div key={validation.label} className="flex items-center">
                            <div className={`mr-2 flex-shrink-0 ${isValid ? 'text-green-400' : 'text-white/30'}`}>
                              {isValid ? (
                                <Check className="h-3.5 w-3.5" />
                              ) : (
                                <div className="h-3.5 w-3.5 rounded-full border border-current" />
                              )}
                            </div>
                            <span className={isValid ? 'text-white/80' : ''}>{validation.label}</span>
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
                  transition={{ delay: 0.25 }}
                >
                  <Label htmlFor="confirmPassword" className="text-sm font-medium text-white/80">
                    Confirm New Password
                  </Label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-white/40" />
                    </div>
                    <Input
                      id="confirmPassword"
                      type={showConfirmPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      minLength={8}
                      className={`w-full pl-10 pr-10 bg-white/5 border ${
                        confirmPassword
                          ? passwordsMatch
                            ? 'border-green-500/50'
                            : 'border-red-500/50'
                          : 'border-white/10'
                      } text-white placeholder:text-white/40 
                      focus-visible:ring-2 focus-visible:ring-blue-500/50 focus-visible:border-transparent
                      transition-all duration-200 rounded-lg h-11`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-white/40 hover:text-white/70 transition-colors"
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
                      <AlertCircle className="h-3.5 w-3.5 mr-1" />
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
                  transition={{ delay: 0.3 }}
                >
                  <Button 
                    type="submit" 
                    className={`w-full py-3 rounded-lg ${
                      !allValid || !passwordsMatch || !password || !confirmPassword
                        ? 'bg-white/5 text-white/40 cursor-not-allowed'
                        : 'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white hover:shadow-blue-500/20 transform hover:-translate-y-0.5'
                    } font-medium shadow-lg transition-all duration-300`}
                    disabled={isLoading || !allValid || !passwordsMatch || !password || !confirmPassword}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Updating Password...
                      </>
                    ) : (
                      'Update Password'
                    )}
                  </Button>
                </motion.div>
              </div>
            </form>
          )}
        </motion.div>
      </AnimatePresence>
    </AuthLayout>
  );
}
