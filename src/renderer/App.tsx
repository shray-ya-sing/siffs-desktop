import { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage';
import { NotFound } from './pages/NotFound';
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
    <div className="flex h-screen bg-[#0a0f1a] text-gray-200 font-sans font-thin overflow-hidden">      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/404" element={<NotFound />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
      </div>
    </div>
  );
}