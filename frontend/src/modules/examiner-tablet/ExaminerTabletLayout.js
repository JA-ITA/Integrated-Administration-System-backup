import React, { useState, useEffect } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { CheckSquare, Wifi, WifiOff, Users, Activity, RefreshCw, Bell } from "lucide-react";

const ExaminerTabletLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [unsyncedCount, setUnsyncedCount] = useState(0);
  const [lastSyncTime, setLastSyncTime] = useState(null);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  useEffect(() => {
    // Check for unsynced checklists
    const checkUnsyncedChecklists = async () => {
      try {
        // This would normally come from IndexedDB when offline
        // or from the API when online
        const unsyncedItems = JSON.parse(localStorage.getItem('unsyncedChecklists') || '[]');
        setUnsyncedCount(unsyncedItems.length);
      } catch (error) {
        console.error('Error checking unsynced checklists:', error);
      }
    };

    checkUnsyncedChecklists();
    const interval = setInterval(checkUnsyncedChecklists, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const navigation = [
    {
      name: "Active Checklists",
      path: "/ui/examiner-tablet",
      icon: CheckSquare,
      active: location.pathname === "/ui/examiner-tablet"
    },
    {
      name: "New Checklist", 
      path: "/ui/examiner-tablet/new",
      icon: Users,
      active: location.pathname === "/ui/examiner-tablet/new"
    },
    {
      name: "History",
      path: "/ui/examiner-tablet/history", 
      icon: Activity,
      active: location.pathname === "/ui/examiner-tablet/history"
    }
  ];

  const handleSync = async () => {
    if (!isOnline) return;
    
    try {
      // Trigger manual sync
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/checklists/unsynced`);
      if (response.ok) {
        setLastSyncTime(new Date());
        setUnsyncedCount(0);
      }
    } catch (error) {
      console.error('Sync failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <CheckSquare className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Examiner Tablet</h1>
                <p className="text-sm text-gray-600">Driver Testing Checklist System</p>
              </div>
            </div>

            {/* Status Indicators */}
            <div className="flex items-center space-x-6">
              {/* Connection Status */}
              <div className="flex items-center space-x-2">
                {isOnline ? (
                  <Wifi className="h-5 w-5 text-green-500" />
                ) : (
                  <WifiOff className="h-5 w-5 text-red-500" />
                )}
                <span className={`text-sm font-medium ${isOnline ? 'text-green-600' : 'text-red-600'}`}>
                  {isOnline ? 'Online' : 'Offline'}
                </span>
              </div>

              {/* Sync Status */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleSync}
                  disabled={!isOnline}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isOnline 
                      ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' 
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  <Sync className="h-4 w-4" />
                  <span>Sync</span>
                </button>
                
                {unsyncedCount > 0 && (
                  <div className="flex items-center space-x-1">
                    <Bell className="h-4 w-4 text-orange-500" />
                    <span className="bg-orange-100 text-orange-700 px-2 py-1 rounded-full text-xs font-medium">
                      {unsyncedCount} unsynced
                    </span>
                  </div>
                )}
              </div>

              {/* Last Sync Time */}
              {lastSyncTime && (
                <div className="text-xs text-gray-500">
                  Last sync: {lastSyncTime.toLocaleTimeString()}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Navigation Sidebar */}
        <nav className="w-64 bg-white shadow-sm min-h-screen border-r border-gray-200">
          <div className="p-6">
            <ul className="space-y-3">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.name}>
                    <button
                      onClick={() => navigate(item.path)}
                      className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-colors ${
                        item.active
                          ? 'bg-blue-100 text-blue-700 font-medium'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <Icon className="h-5 w-5" />
                      <span>{item.name}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Quick Stats */}
          <div className="px-6 py-4 border-t border-gray-200 mt-8">
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Today's Tests:</span>
                <span className="font-medium text-gray-900">8</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Completed:</span>
                <span className="font-medium text-green-600">6</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">In Progress:</span>
                <span className="font-medium text-blue-600">2</span>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default ExaminerTabletLayout;