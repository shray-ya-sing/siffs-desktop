import React, { useEffect, useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { LocationWithState } from '../../types/auth';
import { motion } from 'framer-motion';
import { Mail, ArrowLeft, Check, AlertCircle, RotateCw } from 'lucide-react';

interface LocationState {
  email?: string;
  from?: {
    pathname: string;
  };
}

export default function VerifyEmailPage() {
  const location = useLocation() as LocationWithState;
  const navigate = useNavigate();
  const [isResending, setIsResending] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resendError, setResendError] = useState('');
  
  // Get the email from the navigation state or default to empty string
  const email = location.state?.email || '';
  
  // If no email is provided, redirect to signup
  useEffect(() => {
    if (!email) {
      navigate('/auth/signup');
    }
  }, [email, navigate]);
  
  const handleResendEmail = async () => {
    if (isResending) return;
    
    setIsResending(true);
    setResendError('');
    
    try {
      // TODO: Implement actual resend verification email logic
      console.log('Resending verification email to:', email);
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      
      setResendSuccess(true);
      setTimeout(() => setResendSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to resend verification email:', err);
      setResendError('Failed to resend verification email. Please try again.');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4 bg-gradient-to-br from-[#0a0f1a] via-[#141b31] to-[#1a2035]">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md space-y-6 rounded-2xl bg-white/5 backdrop-blur-lg p-8 shadow-2xl border border-white/10 hover:border-white/20 transition-all duration-300"
      >
        <div className="space-y-6 text-center">
          <motion.div 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, type: 'spring', stiffness: 200, damping: 15 }}
            className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-blue-500 shadow-lg"
          >
            <Mail className="h-10 w-10 text-white" strokeWidth={1.5} />
          </motion.div>
          
          <motion.div 
            className="space-y-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h1 className="text-2xl font-bold text-white">Verify your email</h1>
            
            <p className="text-white/80">
              We've sent a verification link to
            </p>
            
            <div className="font-medium text-blue-300 break-all px-4 py-2 bg-white/5 rounded-lg">
              {email}
            </div>
            
            <p className="text-sm text-white/60">
              Check your email and click the verification link to complete your sign up.
            </p>
          </motion.div>
          
          <motion.div 
            className="pt-2 space-y-4"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <div className="space-y-3">
              <button
                type="button"
                onClick={handleResendEmail}
                disabled={isResending || resendSuccess}
                className={`w-full py-2.5 px-4 text-sm font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2 ${
                  isResending || resendSuccess
                    ? 'text-blue-400/70 cursor-not-allowed'
                    : 'text-blue-400 hover:text-blue-300 hover:bg-white/5'
                }`}
              >
                {isResending ? (
                  <>
                    <RotateCw className="h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : resendSuccess ? (
                  <>
                    <Check className="h-4 w-4" />
                    Email sent!
                  </>
                ) : (
                  <>
                    <RotateCw className="h-4 w-4" />
                    Resend verification email
                  </>
                )}
              </button>
              
              {resendError && (
                <div className="flex items-start p-2.5 text-sm rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
                  <AlertCircle className="h-4 w-4 mr-1.5 mt-0.5 flex-shrink-0" />
                  <span>{resendError}</span>
                </div>
              )}
              
              {resendSuccess && (
                <motion.div 
                  initial={{ opacity: 0, height: 0, marginTop: 0 }}
                  animate={{ opacity: 1, height: 'auto', marginTop: '0.5rem' }}
                  exit={{ opacity: 0, height: 0, marginTop: 0 }}
                  className="overflow-hidden"
                >
                  <div className="flex items-center p-2.5 text-sm rounded-lg bg-green-500/10 border border-green-500/30 text-green-400">
                    <Check className="h-4 w-4 mr-1.5 flex-shrink-0" />
                    Verification email sent successfully!
                  </div>
                </motion.div>
              )}
            </div>
            
            <div className="pt-2 border-t border-white/5">
              <Link 
                to="/auth/login" 
                className="text-sm font-medium text-white/60 hover:text-white transition-colors flex items-center justify-center gap-1.5 group"
                state={{ from: location.state?.from }}
              >
                <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
                Back to login
              </Link>
            </div>
          </motion.div>
        </div>
      </motion.div>
      
      <motion.div 
        className="mt-8 text-center text-sm text-white/40"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <p>Didn't receive the email? Check your spam folder or try again.</p>
      </motion.div>
    </div>
  );
}
  