import { useNavigate } from 'react-router-dom';

export function SettingsPage() {
  const navigate = useNavigate();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Settings</h1>
      <p className="mb-4">This is the settings page.</p>
      <button
        onClick={() => navigate('/')}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        Back to Home
      </button>
    </div>
  );
}
