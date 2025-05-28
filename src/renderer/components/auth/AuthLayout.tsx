import React from 'react';
import { motion } from 'framer-motion';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-gradient-to-br from-[#0a0f1a] via-[#141b31] to-[#1a2035] p-4 transition-colors duration-300">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md bg-white/5 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/10 hover:border-white/20 transition-all duration-300"
      >
        <motion.div 
          className="flex flex-col items-center mb-8"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <motion.div 
            className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-500 flex items-center justify-center mb-4 shadow-lg"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <span className="text-3xl font-bold text-white">C</span>
          </motion.div>
          <h1 className="text-3xl font-bold text-white bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-blue-300">
            Cori
          </h1>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          {children}
        </motion.div>
      </motion.div>
    </div>
  );
}
