import { Routes, Route, Outlet } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage'

export function App() {
  return (
    <div className="flex h-screen bg-gray-100">
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