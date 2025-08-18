import React, { useState, useEffect } from "react";
import { 
  Search, Filter, Calendar, CheckCircle, AlertTriangle, 
  Clock, Eye, Download, BarChart3, Archive 
} from "lucide-react";
import { useNavigate } from "react-router-dom";

const ChecklistHistory = () => {
  const navigate = useNavigate();
  const [checklists, setChecklists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filters, setFilters] = useState({
    status: "all",
    test_type: "all",
    test_category: "all",
    date_range: "all"
  });
  const [stats, setStats] = useState({
    total: 0,
    completed: 0,
    passed: 0,
    failed: 0
  });

  useEffect(() => {
    fetchChecklistHistory();
  }, [filters]);

  const fetchChecklistHistory = async () => {
    try {
      setLoading(true);
      
      // Build query parameters
      const params = new URLSearchParams();
      if (filters.status !== "all") params.append("status", filters.status);
      if (filters.test_type !== "all") params.append("test_type", filters.test_type);
      params.append("limit", "100"); // Get more for history view

      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/checklists?${params}`
      );

      if (response.ok) {
        const data = await response.json();
        const allChecklists = data.data || [];
        setChecklists(allChecklists);
        calculateStats(allChecklists);
      } else {
        // Fallback to local storage
        const localChecklists = JSON.parse(localStorage.getItem('checklists') || '[]');
        setChecklists(localChecklists);
        calculateStats(localChecklists);
      }
    } catch (error) {
      console.error('Error fetching checklist history:', error);
      // Fallback to local storage
      const localChecklists = JSON.parse(localStorage.getItem('checklists') || '[]');
      setChecklists(localChecklists);
      calculateStats(localChecklists);
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (checklistData) => {
    const completed = checklistData.filter(c => c.status === 'completed');
    const passed = completed.filter(c => c.pass_fail_status === 'pass');
    const failed = completed.filter(c => c.pass_fail_status === 'fail');

    setStats({
      total: checklistData.length,
      completed: completed.length,
      passed: passed.length,
      failed: failed.length
    });
  };

  const filterByDateRange = (checklist) => {
    if (filters.date_range === "all") return true;
    
    const checklistDate = new Date(checklist.created_at);
    const now = new Date();
    
    switch (filters.date_range) {
      case "today":
        return checklistDate.toDateString() === now.toDateString();
      case "week":
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        return checklistDate >= weekAgo;
      case "month":
        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        return checklistDate >= monthAgo;
      default:
        return true;
    }
  };

  const filteredChecklists = checklists
    .filter(checklist => {
      const matchesSearch = checklist.driver_record_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           checklist.examiner_id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesTestCategory = filters.test_category === "all" || checklist.test_category === filters.test_category;
      const matchesDateRange = filterByDateRange(checklist);
      
      return matchesSearch && matchesTestCategory && matchesDateRange;
    })
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  const getStatusIcon = (status, passFailStatus, majorBreaches) => {
    if (status === "completed") {
      if (passFailStatus === "pass") {
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      } else if (passFailStatus === "fail") {
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      }
    }
    return <Clock className="h-5 w-5 text-orange-500" />;
  };

  const getStatusColor = (status, passFailStatus) => {
    if (status === "completed") {
      return passFailStatus === "pass" 
        ? "text-green-600 bg-green-100" 
        : "text-red-600 bg-red-100";
    }
    return "text-orange-600 bg-orange-100";
  };

  const getStatusText = (status, passFailStatus) => {
    if (status === "completed" && passFailStatus) {
      return passFailStatus.toUpperCase();
    }
    return status.replace('_', ' ').toUpperCase();
  };

  const exportToCSV = () => {
    const headers = [
      'Driver Record ID',
      'Examiner ID', 
      'Test Type',
      'Test Category',
      'Status',
      'Result',
      'Total Items',
      'Completed Items',
      'Minor Breaches',
      'Major Breaches',
      'Created Date',
      'Completed Date'
    ];

    const csvData = filteredChecklists.map(checklist => [
      checklist.driver_record_id,
      checklist.examiner_id,
      checklist.test_type,
      checklist.test_category, 
      checklist.status,
      checklist.pass_fail_status || 'N/A',
      checklist.total_items,
      checklist.checked_items,
      checklist.minor_breaches,
      checklist.major_breaches,
      new Date(checklist.created_at).toLocaleString(),
      checklist.status === 'completed' ? new Date(checklist.updated_at).toLocaleString() : 'N/A'
    ]);

    const csvContent = [
      headers.join(','),
      ...csvData.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `checklist-history-${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading checklist history...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Checklist History</h2>
          <p className="text-gray-600 mt-1">View completed and archived driver examinations</p>
        </div>
        
        <button
          onClick={exportToCSV}
          className="flex items-center space-x-2 bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
        >
          <Download className="h-4 w-4" />
          <span>Export CSV</span>
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Assessments</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
            <Archive className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Completed</p>
              <p className="text-2xl font-bold text-blue-600">{stats.completed}</p>
            </div>
            <CheckCircle className="h-8 w-8 text-blue-400" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Passed</p>
              <p className="text-2xl font-bold text-green-600">{stats.passed}</p>
            </div>
            <CheckCircle className="h-8 w-8 text-green-400" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Failed</p>
              <p className="text-2xl font-bold text-red-600">{stats.failed}</p>
            </div>
            <AlertTriangle className="h-8 w-8 text-red-400" />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="flex-1 min-w-80">
            <div className="relative">
              <Search className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by driver record ID or examiner..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Filter Controls */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="h-5 w-5 text-gray-500" />
              <span className="text-sm text-gray-700">Filter:</span>
            </div>

            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="border border-gray-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Status</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="submitted">Submitted</option>
            </select>

            <select
              value={filters.test_type}
              onChange={(e) => setFilters({ ...filters, test_type: e.target.value })}
              className="border border-gray-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Test Types</option>
              <option value="Class B">Class B</option>
              <option value="Class C">Class C</option>
              <option value="PPV">PPV</option>
              <option value="Special">Special</option>
            </select>

            <select
              value={filters.test_category}
              onChange={(e) => setFilters({ ...filters, test_category: e.target.value })}
              className="border border-gray-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Categories</option>
              <option value="Yard">Yard Test</option>
              <option value="Road">Road Test</option>
            </select>

            <select
              value={filters.date_range}
              onChange={(e) => setFilters({ ...filters, date_range: e.target.value })}
              className="border border-gray-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Time</option>
              <option value="today">Today</option>
              <option value="week">Past Week</option>
              <option value="month">Past Month</option>
            </select>
          </div>
        </div>
      </div>

      {/* History Table */}
      {filteredChecklists.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <Archive className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No history found</h3>
          <p className="text-gray-600">
            {searchTerm || Object.values(filters).some(f => f !== "all")
              ? "No checklists match your current filters."
              : "No completed assessments to display."}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Driver & Test
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status & Result
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Progress
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Breaches
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredChecklists.map((checklist) => (
                  <tr key={checklist.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          Driver: {checklist.driver_record_id.slice(-6)}
                        </div>
                        <div className="text-sm text-gray-500">
                          {checklist.test_type} • {checklist.test_category}
                        </div>
                        <div className="text-xs text-gray-400">
                          Examiner: {checklist.examiner_id.slice(-4)}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(checklist.status, checklist.pass_fail_status, checklist.major_breaches)}
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(checklist.status, checklist.pass_fail_status)}`}
                        >
                          {getStatusText(checklist.status, checklist.pass_fail_status)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-1">
                          <div className="text-sm text-gray-900">
                            {checklist.checked_items}/{checklist.total_items}
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{
                                width: `${checklist.total_items > 0 ? (checklist.checked_items / checklist.total_items) * 100 : 0}%`
                              }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-3 text-sm">
                        <div className="flex items-center space-x-1">
                          <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                          <span className="text-gray-600">{checklist.minor_breaches}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                          <span className="text-gray-600">{checklist.major_breaches}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div>
                        <div>{new Date(checklist.created_at).toLocaleDateString()}</div>
                        <div className="text-xs text-gray-400">
                          {new Date(checklist.created_at).toLocaleTimeString()}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => navigate(`/ui/examiner-tablet/checklist/${checklist.id}`)}
                        className="text-blue-600 hover:text-blue-900 flex items-center space-x-1"
                      >
                        <Eye className="h-4 w-4" />
                        <span>View</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChecklistHistory;