import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  // Add subtle background animation
  useEffect(() => {
    document.body.className = 'bg-gray-950';
    return () => {
      document.body.className = '';
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col justify-center items-center p-4 relative overflow-hidden">
      {/* Animated background gradient */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900/15 via-transparent to-purple-900/10" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-indigo-900/10 via-transparent to-purple-900/15" />
        <div 
          className="absolute inset-0"
          style={{
            backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'0.02\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
            opacity: 0.5
          }}
        />
      </div>

      {/* Floating particles */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(12)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full bg-blue-500/10"
            initial={{
              x: Math.random() * 100 - 10,
              y: Math.random() * 100,
              width: Math.random() * 10 + 5,
              height: Math.random() * 10 + 5,
              opacity: Math.random() * 0.3 + 0.1,
            }}
            animate={{
              y: [null, `calc(100vh + ${Math.random() * 200}px)`],
              x: [null, `calc(${Math.random() * 200 - 100}px + ${Math.random() * 100}%)`],
            }}
            transition={{
              duration: Math.random() * 30 + 30,
              repeat: Infinity,
              ease: 'linear',
              delay: Math.random() * -30,
            }}
          />
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div 
          key="auth-card"
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.98 }}
          transition={{ 
            type: 'spring',
            stiffness: 300,
            damping: 25,
            duration: 0.5
          }}
          className="w-full max-w-md relative"
        >
          {/* Glow effect */}
          <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10 rounded-3xl blur-xl opacity-50 group-hover:opacity-70 transition duration-1000 group-hover:duration-200 animate-tilt" />
          
          {/* Glass card */}
          <div className="relative bg-white/3 backdrop-blur-xl rounded-2xl shadow-2xl p-8 border border-white/5 hover:border-white/10 transition-all duration-300 overflow-hidden group">
            {/* Subtle gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-blue-900/15 to-purple-900/10 opacity-30" />
            
            <div className="relative z-10">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                {children}
              </motion.div>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Footer */}
      <motion.div 
        className="mt-8 text-center text-sm text-white/40"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <p>© {new Date().getFullYear()} Cori. All rights reserved.</p>
      </motion.div>
    </div>
  );
}
