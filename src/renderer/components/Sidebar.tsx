import { Link, useLocation } from 'react-router-dom';

export function Sidebar() {
  const location = useLocation();
  
  const navigation = [
    { name: 'Home', href: '/', icon: '🏠' },
    { name: 'Settings', href: '/settings', icon: '⚙️' },
  ];

  return (
    <div className="w-64 bg-white shadow-lg">
      <div className="p-4">
        <h1 className="text-xl font-bold">Your App</h1>
      </div>
      <nav className="mt-8">
        {navigation.map((item) => (
          <Link
            key={item.name}
            to={item.href}
            className={`flex items-center px-6 py-3 ${
              location.pathname === item.href
                ? 'bg-blue-50 text-blue-600 border-r-4 border-blue-600'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <span className="mr-3 text-xl">{item.icon}</span>
            {item.name}
          </Link>
        ))}
      </nav>
    </div>
  );
}