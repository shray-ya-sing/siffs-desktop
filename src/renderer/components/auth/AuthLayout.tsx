import React from 'react';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-gradient-to-br from-[#0a0f1a] to-[#1a2035] p-4">
      <div className="w-full max-w-md bg-white/5 backdrop-blur-sm rounded-xl shadow-lg p-8 border border-white/10">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center mb-4">
            <span className="text-2xl font-bold text-white">C</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Cori</h1>
        </div>
        {children}
      </div>
    </div>
  );
}
