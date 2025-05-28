import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

export default function VerifyEmailPage() {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-4">
        <div className="w-full max-w-md space-y-6 rounded-lg bg-card p-8 shadow-md">
          <div className="space-y-4 text-center">
            <h1 className="text-2xl font-bold text-white">Check Your Email</h1>
            
            <div className="space-y-4">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
                <svg
                  className="h-6 w-6 text-blue-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
              </div>
              
              <h2 className="text-lg font-medium text-white">Verify your email address</h2>
              
              <p className="text-gray-300">
                We've sent a confirmation email to your inbox. 
                Please check your email and click the verification link to complete your sign up.
              </p>
              
              <p className="text-sm text-gray-400">
                Didn't receive the email?{' '}
                <Link to="/auth/signup" className="text-blue-400 hover:underline">
                  Resend verification email
                </Link>
              </p>
              
              <div className="pt-4">
                <Link 
                  to="/auth/login" 
                  className="text-sm font-medium text-blue-400 hover:underline"
                >
                  ← Back to login
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
  