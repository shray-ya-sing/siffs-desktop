import React, { useEffect, useState } from 'react';

interface AppLoadingProps {
  onComplete?: () => void;
}

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'unhealthy' | 'checking';
  error?: string;
}

interface HealthCheckResult {
  allServicesHealthy: boolean;
  services: Record<string, ServiceStatus>;
}

export default function AppLoading({ onComplete }: AppLoadingProps) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<{
    loading: boolean;
    message: string;
    allServicesReady: boolean;
    error?: string;
  }>({
    loading: true,
    message: 'Starting up...',
    allServicesReady: false,
  });

  // Progress bar animation effect
  useEffect(() => {
    if (status.loading) {
      const interval = setInterval(() => {
        setProgress(prev => {
          let increment;
          if (prev < 30) {
            increment = 1.0;
          } else if (prev < 60) {
            increment = 0.65;
          } else if (prev < 85) {
            increment = 0.4;
          } else {
            increment = 0.12;
          }
          return Math.min(prev + increment, 95);
        });
      }, 400);

      return () => clearInterval(interval);
    } else if (!status.error) {
      setProgress(100);
    }
  }, [status.loading, status.error]);

  useEffect(() => {
    const checkServices = async () => {
      const startTime = Date.now();
      try {
        setStatus(prev => ({
          ...prev,
          loading: true,
          message: 'Checking backend services...',
          error: undefined,
        }));
        setProgress(10);

        // Simulate service checks
        await new Promise(resolve => setTimeout(resolve, 10000 - (Date.now() - startTime)));
        
        // In a real app, you would check actual services here
        const mockResult: HealthCheckResult = {
          allServicesHealthy: true,
          services: {
            'backend': { name: 'Backend', status: 'healthy' },
            'database': { name: 'Database', status: 'healthy' },
            'auth': { name: 'Authentication', status: 'healthy' }
          }
        };

        if (mockResult.allServicesHealthy) {
          setStatus(prev => ({
            ...prev,
            loading: false,
            message: 'All services are ready!',
            allServicesReady: true,
          }));
          setProgress(100);
          
          // Call onComplete when loading is done
          if (onComplete) {
            // Small delay to show the completion state
            setTimeout(onComplete, 1000);
          }
          // You can navigate to your main app here
          // For example: history.push('/dashboard');
        } else {
          throw new Error('There was a problem setting up the app. Please try again.');
        }
      } catch (error) {
        setStatus(prev => ({
          ...prev,
          loading: false,
          error: error instanceof Error ? error.message : 'Failed to start application'
        }));
      }
    };

    checkServices();
  }, [onComplete]);

  // In your AppLoading.tsx
return (
  <div className="min-h-screen bg-background">
    <div className="container relative h-screen flex items-center justify-center lg:max-w-none lg:px-0">
      <div className="mx-auto flex w-full flex-col items-center justify-center space-y-6 sm:w-[400px] p-8">
        <div className="flex flex-col items-center mb-8 w-full">
          <div className="w-16 h-16 mb-4">
            <div className="w-full h-full rounded-full bg-primary flex items-center justify-center">
              <span className="text-2xl font-bold text-primary-foreground">C</span>
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground">Cori</h1>
          <p className="text-muted-foreground">
            {status.allServicesReady ? 'All systems ready!' : 'Loading application...'}
          </p>
        </div>

        <div className="w-full mb-6">
          <div className="h-2 bg-muted rounded-full overflow-hidden mb-4">
            <div 
              className={`h-full ${
                status.loading 
                  ? 'bg-primary' 
                  : status.error 
                    ? 'bg-destructive' 
                    : 'bg-green-500'
              } transition-all duration-300 ease-out`}
              style={{
                width: `${progress}%`,
              }}
            />
          </div>
          <p className="text-center text-sm text-muted-foreground">
            {status.message}
          </p>
        </div>

        {status.error && (
          <div className="w-full bg-destructive/10 border border-destructive/20 rounded-lg p-4">
            <p className="text-destructive text-sm">{status.error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-3 px-4 py-2 bg-destructive hover:bg-destructive/90 text-destructive-foreground text-sm font-medium rounded-md transition-colors"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  </div>
);
}