// src/renderer/pages/auth/ForgotPasswordPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
import AuthLayout from '../../components/auth/AuthLayout';
import { Loader2 } from 'lucide-react';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      // TODO: Call your password reset API here
      // Example: await resetPassword(email);
      setMessage('If an account exists with this email, you will receive a password reset link.');
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="space-y-6 w-full">
        <div className="space-y-2 text-center">
          <h2 className="text-2xl font-bold text-white">Reset Password</h2>
          <p className="text-sm text-white/70">
            Enter your email and we'll send you a link to reset your password
          </p>
        </div>

        {message && (
          <div className="bg-green-500/10 border border-green-500/30 text-green-500 p-3 rounded-md text-sm">
            {message}
          </div>
        )}

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-white/80">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="bg-white/5 border-white/10 text-white placeholder:text-white/40 focus-visible:ring-white/30"
            />
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              'Send Reset Link'
            )}
          </Button>

          <div className="text-center text-sm text-white/60">
            Remember your password?{' '}
            <Link to="/auth/login" className="text-blue-400 hover:underline">
              Back to login
            </Link>
          </div>
        </div>
      </form>
    </AuthLayout>
  );
}