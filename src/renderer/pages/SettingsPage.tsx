import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';

interface UserData {
  name: string;
  email: string;
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

type ActiveTab = 'profile' | 'password';

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
    <div className="flex h-screen bg-[#0a0f1a] text-gray-200 font-sans font-thin overflow-hidden">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-[#ffffff0f] p-4 flex justify-between items-center bg-[#1a2035]/20 backdrop-blur-md">
          <h1 className="font-semibold text-lg tracking-wide text-white">Settings</h1>
        </header>
        
        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-[#0a0f1a] to-[#1a2035]/30">
          <div className="max-w-5xl w-full mx-auto space-y-6">
            {/* Tabs */}
            <div className="border-b border-[#ffffff0f]">
              <div className="flex space-x-4">
                <button
                  onClick={() => handleTabChange('profile')}
                  className={`px-4 py-2 text-sm font-medium rounded-md ${
                    activeTab === 'profile'
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }`}
                >
                  Profile
                </button>
                <button
                  onClick={() => handleTabChange('password')}
                  className={`px-4 py-2 text-sm font-medium rounded-md ${
                    activeTab === 'password'
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }`}
                >
                  Password
                </button>
              </div>
            </div>
            
            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <div className="bg-[#1a2035]/30 p-6 rounded-lg border border-[#ffffff0f] backdrop-blur-sm shadow-lg">
                <div className="space-y-4">
                  <div>
                    <h2 className="text-xl font-semibold text-white">Profile Information</h2>
                    <p className="text-gray-400 text-sm">Update your account's profile information and email address.</p>
                  </div>
                  <form onSubmit={handleProfileUpdate} className="space-y-4">
                    <div className="space-y-2">
                      <label htmlFor="name" className="text-gray-300">Name</label>
                      <input
                        id="name"
                        name="name"
                        value={userData.name}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 bg-[#1a2035]/50 border border-[#ffffff1a] rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="email" className="text-gray-300">Email</label>
                      <input
                        id="email"
                        name="email"
                        type="email"
                        value={userData.email}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 bg-[#1a2035]/50 border border-[#ffffff1a] rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                    <div className="pt-2">
                      <button 
                        type="submit" 
                        disabled={isLoading} 
                        className="bg-blue-600/30 hover:bg-blue-600/50 text-white border border-[#ffffff1a] px-4 py-2 rounded-md shadow-[0_0_15px_rgba(59,130,246,0.3)] transition-all duration-300 hover:shadow-[0_0_20px_rgba(59,130,246,0.5)]"
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
              <div className="bg-[#1a2035]/30 p-6 rounded-lg border border-[#ffffff0f] backdrop-blur-sm shadow-lg">
                <div className="space-y-4">
                  <div>
                    <h2 className="text-xl font-semibold text-white">Update Password</h2>
                    <p className="text-gray-400 text-sm">Ensure your account is using a long, random password to stay secure.</p>
                  </div>
                  <form onSubmit={handlePasswordChange} className="space-y-4">
                    <div className="space-y-4">
                      {!isEditingPassword ? (
                        <button
                          type="button"
                          onClick={toggleEditPassword}
                          className="bg-blue-600/30 hover:bg-blue-600/50 text-white border border-[#ffffff1a] px-4 py-2 rounded-md flex items-center gap-2"
                        >
                          🔒 Change Password
                        </button>
                      ) : (
                        <>
                          <div className="space-y-2">
                            <label htmlFor="currentPassword" className="text-gray-300">
                              Current Password
                            </label>
                            <input
                              id="currentPassword"
                              name="currentPassword"
                              type="password"
                              value={userData.currentPassword}
                              onChange={handleInputChange}
                              placeholder="Enter your current password"
                              className="w-full px-3 py-2 bg-[#1a2035]/50 border border-[#ffffff1a] rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                            />
                          </div>
                          <div className="space-y-2">
                            <label htmlFor="newPassword" className="text-gray-300">New Password</label>
                            <input
                              id="newPassword"
                              name="newPassword"
                              type="password"
                              value={userData.newPassword}
                              onChange={handleInputChange}
                              placeholder="Enter your new password"
                              className="w-full px-3 py-2 bg-[#1a2035]/50 border border-[#ffffff1a] rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                            />
                          </div>
                          <div className="space-y-2">
                            <label htmlFor="confirmPassword" className="text-gray-300">Confirm New Password</label>
                            <input
                              id="confirmPassword"
                              name="confirmPassword"
                              type="password"
                              value={userData.confirmPassword}
                              onChange={handleInputChange}
                              placeholder="Confirm your new password"
                              className="w-full px-3 py-2 bg-[#1a2035]/50 border border-[#ffffff1a] rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                            />
                          </div>
                          <div className="flex gap-2 pt-2">
                            <button 
                              type="submit" 
                              disabled={isLoading} 
                              className="bg-blue-600/30 hover:bg-blue-600/50 text-white border border-[#ffffff1a] px-4 py-2 rounded-md shadow-[0_0_15px_rgba(59,130,246,0.3)] transition-all duration-300 hover:shadow-[0_0_20px_rgba(59,130,246,0.5)]"
                            >
                              {isLoading ? 'Updating...' : 'Update Password'}
                            </button>
                            <button 
                              type="button"
                              onClick={toggleEditPassword}
                              className="text-gray-400 hover:text-white hover:bg-gray-800/50 px-4 py-2 rounded-md"
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
          </div>
        </main>
      </div>
    </div>
  );
}
