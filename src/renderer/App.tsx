import { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage';
import AppLoading from './components/loading/AppLoading';

export function App() {
  const [isLoading, setIsLoading] = useState(true);

  const handleLoadingComplete = () => {
    setIsLoading(false);
  };

  if (isLoading) {
    return <AppLoading onComplete={handleLoadingComplete} />;
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          {/* Add more routes as needed */}
        </Routes>
      </main>
    </div>
  );
}