import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';

const SpecialAdminLayout = () => {
  const location = useLocation();

  const navigation = [
    {
      name: 'Special Test Types',
      path: '/modules/special-admin',
      description: 'Manage test types, fees, and validity'
    },
    {
      name: 'Question Upload',
      path: '/modules/special-admin/questions',
      description: 'Upload CSV questions with SPECIAL-TEST tagging'
    },
    {
      name: 'Certificate Designer',
      path: '/modules/special-admin/certificates',
      description: 'Drag-and-drop certificate template designer'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="border-b bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <Link to="/modules/special-admin" className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">SA</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">Special Admin</h1>
                  <p className="text-xs text-gray-500">Configuration Management</p>
                </div>
              </Link>
            </div>
            <div className="flex items-center space-x-2">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Live
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Navigation Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Modules</h2>
              <nav className="space-y-2">
                {navigation.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={cn(
                      'block p-3 rounded-lg transition-colors duration-200',
                      location.pathname === item.path
                        ? 'bg-blue-50 border border-blue-200 text-blue-700'
                        : 'hover:bg-gray-50 text-gray-600 hover:text-gray-900'
                    )}
                  >
                    <div className="font-medium text-sm">{item.name}</div>
                    <div className="text-xs text-gray-500 mt-1">{item.description}</div>
                  </Link>
                ))}
              </nav>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
};

export default SpecialAdminLayout;