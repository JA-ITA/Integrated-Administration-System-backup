import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { 
  CheckSquare, Square, AlertTriangle, MinusCircle, 
  Save, CheckCircle, ArrowLeft, Wifi, WifiOff, 
  StickyNote, Clock, Users 
} from "lucide-react";

const ChecklistDetail = () => {
  const { checklistId } = useParams();
  const navigate = useNavigate();
  const [checklist, setChecklist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [activeNoteId, setActiveNoteId] = useState(null);

  useEffect(() => {
    fetchChecklist();
    
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [checklistId]);

  const fetchChecklist = async () => {
    try {
      setLoading(true);
      
      if (checklistId.startsWith('local-')) {
        // Load from local storage
        const localChecklists = JSON.parse(localStorage.getItem('checklists') || '[]');
        const foundChecklist = localChecklists.find(c => c.id === checklistId);
        
        if (foundChecklist) {
          // Generate default items if not present
          if (!foundChecklist.items || foundChecklist.items.length === 0) {
            foundChecklist.items = generateDefaultItems(foundChecklist.test_type, foundChecklist.test_category);
            foundChecklist.total_items = foundChecklist.items.length;
          }
          setChecklist(foundChecklist);
        }
      } else {
        // Try to fetch from API
        const response = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/checklists/${checklistId}`
        );
        
        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            setChecklist(data.data);
          }
        } else {
          // Fallback to local storage
          const localChecklists = JSON.parse(localStorage.getItem('checklists') || '[]');
          const foundChecklist = localChecklists.find(c => c.driver_record_id === checklistId);
          setChecklist(foundChecklist);
        }
      }
    } catch (error) {
      console.error('Error fetching checklist:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateDefaultItems = (testType, testCategory) => {
    const items = [];
    
    // Pre-inspection items for all tests
    const preInspectionItems = [
      "Vehicle exterior condition check",
      "Mirrors properly adjusted", 
      "Seat and steering wheel adjustment",
      "Safety equipment present and functional",
      "Documents and identification verified"
    ];

    // Test category specific items
    const yardItems = [
      "Reverse parking maneuver",
      "Three-point turn execution", 
      "Hill start procedure",
      "Emergency stop demonstration",
      "Parallel parking (if applicable)"
    ];

    const roadItems = [
      "Traffic observation and awareness",
      "Signal usage and timing",
      "Lane discipline maintenance", 
      "Speed control and adaptation",
      "Hazard perception and response",
      "Junction approach and execution",
      "Overtaking procedure (if applicable)",
      "Roundabout navigation"
    ];

    // Add class-specific items
    if (testType === "Class C") {
      preInspectionItems.push(
        "Commercial vehicle pre-trip inspection",
        "Load securement verification", 
        "Air brake system check"
      );
    }

    if (testType === "PPV") {
      preInspectionItems.push(
        "Passenger safety equipment check",
        "Emergency exit operation",
        "Wheelchair accessibility features"
      );
    }

    // Build category sections
    const categoryItems = {
      "Pre-inspection": preInspectionItems,
      "Yard Maneuvers": testCategory === "Yard" ? yardItems : [],
      "Road Driving": testCategory === "Road" ? roadItems : []
    };

    let itemId = 1;
    for (const [category, descriptions] of Object.entries(categoryItems)) {
      for (const desc of descriptions) {
        if (desc) {
          items.push({
            id: `item-${itemId++}`,
            category,
            description: desc,
            checked: false,
            breach_type: null,
            notes: "",
            timestamp: new Date().toISOString()
          });
        }
      }
    }

    return items;
  };

  const saveChecklist = async (updatedChecklist) => {
    setSaving(true);
    try {
      // Always save to local storage first
      const localChecklists = JSON.parse(localStorage.getItem('checklists') || '[]');
      const checklistIndex = localChecklists.findIndex(c => c.id === updatedChecklist.id);
      
      if (checklistIndex >= 0) {
        localChecklists[checklistIndex] = updatedChecklist;
      } else {
        localChecklists.push(updatedChecklist);
      }
      localStorage.setItem('checklists', JSON.stringify(localChecklists));

      // Try to save to server if online
      if (isOnline && !updatedChecklist.id.startsWith('local-')) {
        const response = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/checklists/${updatedChecklist.id}`,
          {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              status: updatedChecklist.status,
              items: updatedChecklist.items,
              synced: true
            })
          }
        );

        if (response.ok) {
          updatedChecklist.synced = true;
        } else {
          updatedChecklist.synced = false;
        }
      } else {
        // Mark as unsynced if offline or local-only
        updatedChecklist.synced = false;
        
        // Add to unsynced list
        const unsyncedChecklists = JSON.parse(localStorage.getItem('unsyncedChecklists') || '[]');
        const unsyncedIndex = unsyncedChecklists.findIndex(c => c.id === updatedChecklist.id);
        if (unsyncedIndex >= 0) {
          unsyncedChecklists[unsyncedIndex] = updatedChecklist;
        } else {
          unsyncedChecklists.push(updatedChecklist);
        }
        localStorage.setItem('unsyncedChecklists', JSON.stringify(unsyncedChecklists));
      }

      setChecklist(updatedChecklist);
    } catch (error) {
      console.error('Error saving checklist:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleItemCheck = (itemId, checked) => {
    const updatedItems = checklist.items.map(item => 
      item.id === itemId ? { ...item, checked, timestamp: new Date().toISOString() } : item
    );
    
    const checkedItems = updatedItems.filter(item => item.checked).length;
    const updatedChecklist = {
      ...checklist,
      items: updatedItems,
      checked_items: checkedItems,
      updated_at: new Date().toISOString()
    };

    saveChecklist(updatedChecklist);
  };

  const handleBreachToggle = (itemId, breachType) => {
    const updatedItems = checklist.items.map(item => {
      if (item.id === itemId) {
        const newBreachType = item.breach_type === breachType ? null : breachType;
        return { 
          ...item, 
          breach_type: newBreachType,
          timestamp: new Date().toISOString()
        };
      }
      return item;
    });
    
    const minorBreaches = updatedItems.filter(item => item.breach_type === 'minor').length;
    const majorBreaches = updatedItems.filter(item => item.breach_type === 'major').length;
    
    const updatedChecklist = {
      ...checklist,
      items: updatedItems,
      minor_breaches: minorBreaches,
      major_breaches: majorBreaches,
      updated_at: new Date().toISOString()
    };

    saveChecklist(updatedChecklist);
  };

  const handleNoteChange = (itemId, notes) => {
    const updatedItems = checklist.items.map(item =>
      item.id === itemId ? { ...item, notes, timestamp: new Date().toISOString() } : item
    );
    
    const updatedChecklist = {
      ...checklist,
      items: updatedItems,
      updated_at: new Date().toISOString()
    };

    saveChecklist(updatedChecklist);
  };

  const handleCompleteChecklist = () => {
    const passFailStatus = checklist.major_breaches > 0 ? 'fail' : 
                          checklist.minor_breaches > 3 ? 'fail' : 'pass';
    
    const updatedChecklist = {
      ...checklist,
      status: 'completed',
      pass_fail_status: passFailStatus,
      updated_at: new Date().toISOString()
    };

    saveChecklist(updatedChecklist);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading checklist...</span>
      </div>
    );
  }

  if (!checklist) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Checklist not found</h3>
        <button
          onClick={() => navigate("/ui/examiner-tablet")}
          className="text-blue-600 hover:text-blue-700"
        >
          Return to checklists
        </button>
      </div>
    );
  }

  const groupedItems = checklist.items.reduce((acc, item) => {
    if (!acc[item.category]) {
      acc[item.category] = [];
    }
    acc[item.category].push(item);
    return acc;
  }, {});

  const progressPercentage = checklist.total_items > 0 
    ? (checklist.checked_items / checklist.total_items) * 100 
    : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate("/ui/examiner-tablet")}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="h-5 w-5 text-gray-600" />
            </button>
            
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Driver: {checklist.driver_record_id}
              </h1>
              <div className="flex items-center space-x-4 text-sm text-gray-600 mt-1">
                <span>{checklist.test_type}</span>
                <span>•</span>
                <span>{checklist.test_category} Test</span>
                <span>•</span>
                <div className="flex items-center space-x-1">
                  <Users className="h-4 w-4" />
                  <span>Examiner: {checklist.examiner_id}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Sync Status */}
            <div className="flex items-center space-x-2">
              {checklist.synced ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <>
                  {isOnline ? (
                    <Wifi className="h-5 w-5 text-orange-500" />
                  ) : (
                    <WifiOff className="h-5 w-5 text-red-500" />
                  )}
                </>
              )}
              <span className={`text-sm ${
                checklist.synced ? 'text-green-600' : 'text-orange-600'
              }`}>
                {checklist.synced ? 'Synced' : 'Unsynced'}
              </span>
            </div>

            {/* Save Status */}
            {saving && (
              <div className="flex items-center space-x-2 text-blue-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="text-sm">Saving...</span>
              </div>
            )}
          </div>
        </div>

        {/* Progress & Status */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-gray-900">{checklist.checked_items}/{checklist.total_items}</div>
            <div className="text-sm text-gray-600">Items Completed</div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${progressPercentage}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-orange-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-orange-600">{checklist.minor_breaches}</div>
            <div className="text-sm text-gray-600">Minor Breaches</div>
            <div className="text-xs text-gray-500 mt-1">Small deviations</div>
          </div>

          <div className="bg-red-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-red-600">{checklist.major_breaches}</div>
            <div className="text-sm text-gray-600">Major Breaches</div>
            <div className="text-xs text-gray-500 mt-1">Safety-critical</div>
          </div>

          <div className="bg-green-50 rounded-lg p-4">
            <div className={`text-2xl font-bold ${
              checklist.status === 'completed' 
                ? (checklist.pass_fail_status === 'pass' ? 'text-green-600' : 'text-red-600')
                : 'text-gray-600'
            }`}>
              {checklist.status === 'completed' 
                ? (checklist.pass_fail_status?.toUpperCase() || 'N/A')
                : 'IN PROGRESS'}
            </div>
            <div className="text-sm text-gray-600">Status</div>
          </div>
        </div>
      </div>

      {/* Checklist Items */}
      {Object.entries(groupedItems).map(([category, items]) => (
        <div key={category} className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">{category}</h3>
          </div>
          
          <div className="divide-y divide-gray-100">
            {items.map((item) => (
              <div key={item.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-start space-x-4">
                  {/* Checkbox */}
                  <button
                    onClick={() => handleItemCheck(item.id, !item.checked)}
                    className="mt-1 flex-shrink-0"
                  >
                    {item.checked ? (
                      <CheckSquare className="h-6 w-6 text-green-600" />
                    ) : (
                      <Square className="h-6 w-6 text-gray-400 hover:text-gray-600" />
                    )}
                  </button>

                  <div className="flex-1">
                    <div className="flex items-start justify-between">
                      <p className={`text-base ${item.checked ? 'text-gray-600 line-through' : 'text-gray-900'}`}>
                        {item.description}
                      </p>

                      {/* Breach Buttons */}
                      <div className="flex items-center space-x-2 ml-4">
                        <button
                          onClick={() => handleBreachToggle(item.id, 'minor')}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                            item.breach_type === 'minor'
                              ? 'bg-orange-100 text-orange-700 border-2 border-orange-300'
                              : 'bg-gray-100 text-gray-600 hover:bg-orange-50 hover:text-orange-600'
                          }`}
                        >
                          Minor
                        </button>

                        <button
                          onClick={() => handleBreachToggle(item.id, 'major')}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                            item.breach_type === 'major'
                              ? 'bg-red-100 text-red-700 border-2 border-red-300'
                              : 'bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600'
                          }`}
                        >
                          Major
                        </button>

                        <button
                          onClick={() => setActiveNoteId(activeNoteId === item.id ? null : item.id)}
                          className={`p-2 rounded-lg transition-colors ${
                            item.notes || activeNoteId === item.id
                              ? 'bg-blue-100 text-blue-600'
                              : 'hover:bg-gray-100 text-gray-400'
                          }`}
                        >
                          <StickyNote className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    {/* Notes Section */}
                    {(activeNoteId === item.id || item.notes) && (
                      <div className="mt-3">
                        <textarea
                          value={item.notes || ''}
                          onChange={(e) => handleNoteChange(item.id, e.target.value)}
                          placeholder="Add notes..."
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                          rows={3}
                        />
                      </div>
                    )}

                    {/* Timestamp */}
                    {item.checked && (
                      <div className="flex items-center space-x-2 mt-2 text-xs text-gray-500">
                        <Clock className="h-3 w-3" />
                        <span>Completed: {new Date(item.timestamp).toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Complete Checklist Button */}
      {checklist.status !== 'completed' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Complete Assessment</h3>
              <p className="text-gray-600 mt-1">
                Review all items and mark the assessment as complete
              </p>
              
              {checklist.major_breaches > 0 && (
                <div className="flex items-center space-x-2 mt-2 text-red-600">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm">Major breaches detected - assessment will be marked as FAIL</span>
                </div>
              )}
              
              {checklist.minor_breaches > 3 && (
                <div className="flex items-center space-x-2 mt-2 text-red-600">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm">Too many minor breaches - assessment will be marked as FAIL</span>
                </div>
              )}
            </div>

            <button
              onClick={handleCompleteChecklist}
              className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              Complete Assessment
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChecklistDetail;