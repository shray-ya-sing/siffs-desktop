import React, { useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';

export default function VerifyEmailPage() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Get the email from the navigation state or default to empty string
  const email = (location.state as { email?: string })?.email || '';
  
  // If no email is provided, redirect to signup
  useEffect(() => {
    if (!email) {
      navigate('/auth/signup');
    }
  }, [email, navigate]);
  
  const handleResendEmail = () => {
    // TODO: Implement resend verification email logic
    console.log('Resending verification email to:', email);
    // Show a success message
    alert(`Verification email resent to ${email}`);
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4 bg-gradient-to-b from-gray-900 to-gray-800">
      <div className="w-full max-w-md space-y-6 rounded-xl bg-gray-800/50 p-8 shadow-lg backdrop-blur-sm border border-gray-700/50">
        <div className="space-y-4 text-center">
          <h1 className="text-2xl font-bold text-white">Check Your Email</h1>
          
          <div className="space-y-6">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-500/10">
              <svg
                className="h-8 w-8 text-blue-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
                />
              </svg>
            </div>
            
            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-white">Verify your email address</h2>
              
              <p className="text-gray-300">
                We've sent a confirmation email to:
              </p>
              
              <div className="font-medium text-blue-300">
                {email}
              </div>
              
              <p className="text-gray-400 text-sm">
                Please check your inbox and click the verification link to complete your sign up.
              </p>
            </div>
            
            <div className="pt-2 space-y-4">
              <button
                type="button"
                onClick={handleResendEmail}
                className="w-full py-2 px-4 text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
              >
                Didn't receive the email? <span className="underline">Resend verification</span>
              </button>
              
              <div className="pt-2 border-t border-gray-700">
                <Link 
                  to="/auth/login" 
                  className="text-sm font-medium text-gray-400 hover:text-white transition-colors flex items-center justify-center gap-1"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                  </svg>
                  Back to login
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
  