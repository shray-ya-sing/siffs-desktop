import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { APIKeyManagement } from '../components/settings/APIKeyManagement';

interface UserData {
  name: string;
  email: string;
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

type ActiveTab = 'profile' | 'password' | 'api-keys';

export function SettingsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<ActiveTab>('profile');
  const [isEditingPassword, setIsEditingPassword] = useState(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [userData, setUserData] = useState<UserData>({
    name: 'User Name',
    email: 'user@example.com',
    currentPassword: '••••••••',
    newPassword: '',
    confirmPassword: ''
  });

  const handleTabChange = (tab: ActiveTab): void => {
    setActiveTab(tab);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const { name, value } = e.target;
    if (name === 'currentPassword' && userData.currentPassword === '••••••••') {
      setUserData(prev => ({
        ...prev,
        [name]: ''
      }));
    } else {
      setUserData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };
  
  const toggleEditPassword = () => {
    setIsEditingPassword(!isEditingPassword);
    if (!isEditingPassword) {
      setUserData(prev => ({
        ...prev,
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      }));
    } else {
      setUserData(prev => ({
        ...prev,
        currentPassword: '••••••••',
        newPassword: '',
        confirmPassword: ''
      }));
    }
  };

  const handleProfileUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
    }, 1000);
  };

  const handlePasswordChange = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      setIsEditingPassword(false);
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white overflow-hidden">
      {/* Main Content */}
      <div className="max-w-6xl w-full mx-auto px-4 space-y-6 pt-20">
        {/* Header */}
        <div className="text-center space-y-4 mb-8">
          <h1 className="text-4xl font-thin text-white">Settings</h1>
          <p className="text-gray-400 text-lg font-light">Configure your preferences and API keys</p>
        </div>
        
        {/* Tabs */}
        <div className="flex justify-center mb-8">
          <div className="flex space-x-4 p-1 bg-gray-900/60 backdrop-blur-sm rounded-full border border-gray-700/50">
            <button
              onClick={() => handleTabChange('profile')}
              className={`px-6 py-3 text-sm font-light rounded-full transition-all duration-300 ${
                activeTab === 'profile'
                  ? 'bg-gray-800/70 text-white border border-gray-700/50 shadow-lg'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
              }`}
            >
              Profile
            </button>
            <button
              onClick={() => handleTabChange('password')}
              className={`px-6 py-3 text-sm font-light rounded-full transition-all duration-300 ${
                activeTab === 'password'
                  ? 'bg-gray-800/70 text-white border border-gray-700/50 shadow-lg'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
              }`}
            >
              Password
            </button>
            <button
              onClick={() => handleTabChange('api-keys')}
              className={`px-6 py-3 text-sm font-light rounded-full transition-all duration-300 ${
                activeTab === 'api-keys'
                  ? 'bg-gray-800/70 text-white border border-gray-700/50 shadow-lg'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
              }`}
            >
              API Keys
            </button>
          </div>
        </div>
            
        {/* Content Area */}
        <div className="flex justify-center">
          <div className="w-full max-w-3xl">
            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <div className="bg-gray-900/60 backdrop-blur-sm p-8 rounded-2xl border border-gray-700/50 shadow-2xl">
                <div className="space-y-6">
                  <div className="text-center">
                    <h2 className="text-2xl font-light text-white mb-2">Profile Information</h2>
                    <p className="text-gray-400 font-light">Update your account's profile information and email address.</p>
                  </div>
                  <form onSubmit={handleProfileUpdate} className="space-y-6">
                    <div className="space-y-3">
                      <label htmlFor="name" className="text-gray-300 font-light text-sm">Name</label>
                      <input
                        id="name"
                        name="name"
                        value={userData.name}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gray-600 focus:ring-2 focus:ring-gray-600/50 transition-all duration-300"
                      />
                    </div>
                    <div className="space-y-3">
                      <label htmlFor="email" className="text-gray-300 font-light text-sm">Email</label>
                      <input
                        id="email"
                        name="email"
                        type="email"
                        value={userData.email}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gray-600 focus:ring-2 focus:ring-gray-600/50 transition-all duration-300"
                      />
                    </div>
                    <div className="pt-4 text-center">
                      <button 
                        type="submit" 
                        disabled={isLoading} 
                        className="bg-gray-800/70 hover:bg-gray-700/80 text-white border border-gray-700/50 px-8 py-3 rounded-full font-light transition-all duration-300 shadow-lg hover:shadow-xl"
                      >
                        {isLoading ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
            
            {/* Password Tab */}
            {activeTab === 'password' && (
              <div className="bg-gray-900/60 backdrop-blur-sm p-8 rounded-2xl border border-gray-700/50 shadow-2xl">
                <div className="space-y-6">
                  <div className="text-center">
                    <h2 className="text-2xl font-light text-white mb-2">Update Password</h2>
                    <p className="text-gray-400 font-light">Ensure your account is using a long, random password to stay secure.</p>
                  </div>
                  <form onSubmit={handlePasswordChange} className="space-y-6">
                    <div className="space-y-6">
                      {!isEditingPassword ? (
                        <div className="text-center">
                          <button
                            type="button"
                            onClick={toggleEditPassword}
                            className="bg-gray-800/70 hover:bg-gray-700/80 text-white border border-gray-700/50 px-8 py-3 rounded-full font-light transition-all duration-300 shadow-lg hover:shadow-xl flex items-center justify-center gap-2 mx-auto"
                          >
                            🔒 Change Password
                          </button>
                        </div>
                      ) : (
                        <>
                          <div className="space-y-3">
                            <label htmlFor="currentPassword" className="text-gray-300 font-light text-sm">
                              Current Password
                            </label>
                            <input
                              id="currentPassword"
                              name="currentPassword"
                              type="password"
                              value={userData.currentPassword}
                              onChange={handleInputChange}
                              placeholder="Enter your current password"
                              className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gray-600 focus:ring-2 focus:ring-gray-600/50 transition-all duration-300"
                            />
                          </div>
                          <div className="space-y-3">
                            <label htmlFor="newPassword" className="text-gray-300 font-light text-sm">New Password</label>
                            <input
                              id="newPassword"
                              name="newPassword"
                              type="password"
                              value={userData.newPassword}
                              onChange={handleInputChange}
                              placeholder="Enter your new password"
                              className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gray-600 focus:ring-2 focus:ring-gray-600/50 transition-all duration-300"
                            />
                          </div>
                          <div className="space-y-3">
                            <label htmlFor="confirmPassword" className="text-gray-300 font-light text-sm">Confirm New Password</label>
                            <input
                              id="confirmPassword"
                              name="confirmPassword"
                              type="password"
                              value={userData.confirmPassword}
                              onChange={handleInputChange}
                              placeholder="Confirm your new password"
                              className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gray-600 focus:ring-2 focus:ring-gray-600/50 transition-all duration-300"
                            />
                          </div>
                          <div className="flex gap-4 pt-4 justify-center">
                            <button 
                              type="submit" 
                              disabled={isLoading} 
                              className="bg-gray-800/70 hover:bg-gray-700/80 text-white border border-gray-700/50 px-8 py-3 rounded-full font-light transition-all duration-300 shadow-lg hover:shadow-xl"
                            >
                              {isLoading ? 'Updating...' : 'Update Password'}
                            </button>
                            <button 
                              type="button"
                              onClick={toggleEditPassword}
                              className="text-gray-400 hover:text-white hover:bg-gray-800/50 px-8 py-3 rounded-full font-light transition-all duration-300"
                            >
                              Cancel
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </form>
                </div>
              </div>
            )}
            
            {/* API Keys Tab */}
            {activeTab === 'api-keys' && (
              <div className="bg-gray-900/60 backdrop-blur-sm p-8 rounded-2xl border border-gray-700/50 shadow-2xl">
                <APIKeyManagement />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
