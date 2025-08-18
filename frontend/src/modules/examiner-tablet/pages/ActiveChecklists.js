import React, { useState, useEffect } from "react";
import { Plus, Search, Filter, CheckCircle, AlertTriangle, Clock, Eye } from "lucide-react";
import { useNavigate } from "react-router-dom";

const ActiveChecklists = () => {
  const navigate = useNavigate();
  const [checklists, setChecklists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterTestType, setFilterTestType] = useState("all");

  useEffect(() => {
    fetchChecklists();
  }, [filterStatus, filterTestType]);

  const fetchChecklists = async () => {
    try {
      setLoading(true);
      
      // Build query parameters
      const params = new URLSearchParams();
      if (filterStatus !== "all") params.append("status", filterStatus);
      if (filterTestType !== "all") params.append("test_type", filterTestType);
      
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/checklists?${params}`
      );
      
      if (response.ok) {
        const data = await response.json();
        setChecklists(data.data || []);
      } else {
        // Fallback to local storage when offline
        const localChecklists = JSON.parse(localStorage.getItem('checklists') || '[]');
        setChecklists(localChecklists);
      }
    } catch (error) {
      console.error('Error fetching checklists:', error);
      // Fallback to local storage
      const localChecklists = JSON.parse(localStorage.getItem('checklists') || '[]');
      setChecklists(localChecklists);
    } finally {
      setLoading(false);
    }
  };

  const filteredChecklists = checklists.filter(checklist => {
    const matchesSearch = checklist.driver_record_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         checklist.examiner_id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const getStatusIcon = (status, majorBreaches, minorBreaches) => {
    if (status === "completed") {
      if (majorBreaches > 0) {
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      }
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    }
    return <Clock className="h-5 w-5 text-orange-500" />;
  };

  const getStatusColor = (status, majorBreaches) => {
    if (status === "completed") {
      return majorBreaches > 0 ? "text-red-600 bg-red-100" : "text-green-600 bg-green-100";
    }
    return "text-orange-600 bg-orange-100";
  };

  const getStatusText = (status, passFailStatus) => {
    if (status === "completed" && passFailStatus) {
      return passFailStatus.toUpperCase();
    }
    return status.replace('_', ' ').toUpperCase();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading checklists...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Active Checklists</h2>
          <p className="text-gray-600 mt-1">Manage ongoing driver examinations</p>
        </div>
        
        <button
          onClick={() => navigate("/ui/examiner-tablet/new")}
          className="flex items-center space-x-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          <Plus className="h-5 w-5" />
          <span>New Checklist</span>
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex flex-wrap items-center space-x-4 space-y-2">
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

          {/* Status Filter */}
          <div className="flex items-center space-x-2">
            <Filter className="h-5 w-5 text-gray-500" />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Status</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="submitted">Submitted</option>
            </select>
          </div>

          {/* Test Type Filter */}
          <div>
            <select
              value={filterTestType}
              onChange={(e) => setFilterTestType(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Test Types</option>
              <option value="Class B">Class B</option>
              <option value="Class C">Class C</option>
              <option value="PPV">PPV</option>
              <option value="Special">Special</option>
            </select>
          </div>
        </div>
      </div>

      {/* Checklists Grid */}
      {filteredChecklists.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <CheckCircle className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No checklists found</h3>
          <p className="text-gray-600 mb-6">
            {searchTerm || filterStatus !== "all" || filterTestType !== "all"
              ? "No checklists match your current filters."
              : "Get started by creating a new checklist for a driver examination."}
          </p>
          <button
            onClick={() => navigate("/ui/examiner-tablet/new")}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Create First Checklist
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredChecklists.map((checklist) => (
            <div
              key={checklist.id}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => navigate(`/ui/examiner-tablet/checklist/${checklist.id}`)}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">
                    Driver: {checklist.driver_record_id.slice(-6)}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {checklist.test_type} • {checklist.test_category}
                  </p>
                </div>
                
                <div className="flex items-center space-x-2">
                  {getStatusIcon(checklist.status, checklist.major_breaches, checklist.minor_breaches)}
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(checklist.status, checklist.major_breaches)}`}
                  >
                    {getStatusText(checklist.status, checklist.pass_fail_status)}
                  </span>
                </div>
              </div>

              {/* Progress */}
              <div className="mb-4">
                <div className="flex justify-between text-sm text-gray-600 mb-2">
                  <span>Progress</span>
                  <span>{checklist.checked_items}/{checklist.total_items}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{
                      width: `${checklist.total_items > 0 ? (checklist.checked_items / checklist.total_items) * 100 : 0}%`
                    }}
                  ></div>
                </div>
              </div>

              {/* Breach Summary */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-1">
                    <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                    <span className="text-gray-600">Minor: {checklist.minor_breaches}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                    <span className="text-gray-600">Major: {checklist.major_breaches}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2 text-gray-500">
                  <Eye className="h-4 w-4" />
                  <span className="text-xs">View</span>
                </div>
              </div>

              {/* Footer */}
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Examiner: {checklist.examiner_id.slice(-4)}</span>
                  <span>
                    {new Date(checklist.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ActiveChecklists;