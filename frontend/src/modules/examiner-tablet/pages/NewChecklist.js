import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Car, Truck, Users, Star, FileText, ArrowRight } from "lucide-react";

const NewChecklist = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    driver_record_id: "",
    examiner_id: "",
    test_type: "",
    test_category: ""
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const testTypes = [
    {
      id: "Class B",
      name: "Class B",
      description: "Standard passenger vehicle license",
      icon: Car,
      color: "blue"
    },
    {
      id: "Class C", 
      name: "Class C",
      description: "Commercial vehicles over 7000kg",
      icon: Truck,
      color: "green"
    },
    {
      id: "PPV",
      name: "PPV",
      description: "Passenger Public Vehicle",
      icon: Users,
      color: "purple"
    },
    {
      id: "Special",
      name: "Special",
      description: "Special circumstances testing",
      icon: Star,
      color: "orange"
    }
  ];

  const testCategories = [
    {
      id: "Yard",
      name: "Yard Test",
      description: "Maneuvering and parking skills",
      items: "Pre-inspection, parking, 3-point turns, hill starts"
    },
    {
      id: "Road",
      name: "Road Test", 
      description: "Traffic and road driving assessment",
      items: "Traffic awareness, signaling, hazard perception, junctions"
    }
  ];

  const validateForm = () => {
    const newErrors = {};

    if (!formData.driver_record_id.trim()) {
      newErrors.driver_record_id = "Driver Record ID is required";
    } else if (formData.driver_record_id.length < 6) {
      newErrors.driver_record_id = "Driver Record ID must be at least 6 characters";
    }

    if (!formData.examiner_id.trim()) {
      newErrors.examiner_id = "Examiner ID is required";
    }

    if (!formData.test_type) {
      newErrors.test_type = "Test type is required";
    }

    if (!formData.test_category) {
      newErrors.test_category = "Test category is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setLoading(true);
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/checklists`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        const data = await response.json();
        // Save to local storage for offline access
        const existingChecklists = JSON.parse(localStorage.getItem('checklists') || '[]');
        existingChecklists.push(data);
        localStorage.setItem('checklists', JSON.stringify(existingChecklists));
        
        navigate(`/ui/examiner-tablet/checklist/${data.id}`);
      } else {
        // If offline, save to local storage with sync flag
        const checklistData = {
          ...formData,
          id: `local-${Date.now()}`,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          status: "in_progress",
          synced: false,
          items: [],
          total_items: 0,
          checked_items: 0,
          minor_breaches: 0,
          major_breaches: 0
        };

        const existingChecklists = JSON.parse(localStorage.getItem('checklists') || '[]');
        existingChecklists.push(checklistData);
        localStorage.setItem('checklists', JSON.stringify(existingChecklists));

        // Also add to unsynced list
        const unsyncedChecklists = JSON.parse(localStorage.getItem('unsyncedChecklists') || '[]');
        unsyncedChecklists.push(checklistData);
        localStorage.setItem('unsyncedChecklists', JSON.stringify(unsyncedChecklists));

        navigate(`/ui/examiner-tablet/checklist/${checklistData.id}`);
      }
    } catch (error) {
      console.error('Error creating checklist:', error);
      setErrors({ submit: 'Failed to create checklist. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const getIconColor = (color) => {
    const colors = {
      blue: "text-blue-600 bg-blue-100",
      green: "text-green-600 bg-green-100", 
      purple: "text-purple-600 bg-purple-100",
      orange: "text-orange-600 bg-orange-100"
    };
    return colors[color] || colors.blue;
  };

  const getBorderColor = (color, selected) => {
    if (!selected) return "border-gray-200";
    const colors = {
      blue: "border-blue-500 bg-blue-50",
      green: "border-green-500 bg-green-50",
      purple: "border-purple-500 bg-purple-50", 
      orange: "border-orange-500 bg-orange-50"
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Create New Checklist</h2>
        <p className="text-gray-600 mt-1">Set up a new driver examination checklist</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Basic Information */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <FileText className="h-5 w-5 mr-2" />
            Basic Information
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Driver Record ID *
              </label>
              <input
                type="text"
                value={formData.driver_record_id}
                onChange={(e) => setFormData({ ...formData, driver_record_id: e.target.value })}
                className={`w-full px-4 py-3 text-lg border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  errors.driver_record_id ? 'border-red-300' : 'border-gray-300'
                }`}
                placeholder="Enter driver record ID"
              />
              {errors.driver_record_id && (
                <p className="text-red-600 text-sm mt-1">{errors.driver_record_id}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Examiner ID *
              </label>
              <input
                type="text"
                value={formData.examiner_id}
                onChange={(e) => setFormData({ ...formData, examiner_id: e.target.value })}
                className={`w-full px-4 py-3 text-lg border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  errors.examiner_id ? 'border-red-300' : 'border-gray-300'
                }`}
                placeholder="Enter examiner ID"
              />
              {errors.examiner_id && (
                <p className="text-red-600 text-sm mt-1">{errors.examiner_id}</p>
              )}
            </div>
          </div>
        </div>

        {/* Test Type Selection */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Select Test Type *
          </h3>
          {errors.test_type && (
            <p className="text-red-600 text-sm mb-4">{errors.test_type}</p>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {testTypes.map((testType) => {
              const Icon = testType.icon;
              const isSelected = formData.test_type === testType.id;
              
              return (
                <button
                  key={testType.id}
                  type="button"
                  onClick={() => setFormData({ ...formData, test_type: testType.id })}
                  className={`p-6 border-2 rounded-lg text-left transition-all hover:shadow-md ${
                    getBorderColor(testType.color, isSelected)
                  }`}
                >
                  <div className="flex items-start space-x-4">
                    <div className={`p-3 rounded-lg ${getIconColor(testType.color)}`}>
                      <Icon className="h-6 w-6" />
                    </div>
                    <div className="flex-1">
                      <h4 className="text-lg font-semibold text-gray-900">{testType.name}</h4>
                      <p className="text-gray-600 mt-1">{testType.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Test Category Selection */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Select Test Category *
          </h3>
          {errors.test_category && (
            <p className="text-red-600 text-sm mb-4">{errors.test_category}</p>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {testCategories.map((category) => {
              const isSelected = formData.test_category === category.id;
              
              return (
                <button
                  key={category.id}
                  type="button"
                  onClick={() => setFormData({ ...formData, test_category: category.id })}
                  className={`p-6 border-2 rounded-lg text-left transition-all hover:shadow-md ${
                    isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">{category.name}</h4>
                  <p className="text-gray-600 mb-3">{category.description}</p>
                  <p className="text-sm text-gray-500">
                    <strong>Includes:</strong> {category.items}
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end space-x-4">
          <button
            type="button"
            onClick={() => navigate("/ui/examiner-tablet")}
            className="px-6 py-3 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors font-medium"
          >
            Cancel
          </button>
          
          <button
            type="submit"
            disabled={loading}
            className="flex items-center space-x-2 bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Creating...</span>
              </>
            ) : (
              <>
                <span>Create Checklist</span>
                <ArrowRight className="h-5 w-5" />
              </>
            )}
          </button>
        </div>

        {errors.submit && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-600">{errors.submit}</p>
          </div>
        )}
      </form>
    </div>
  );
};

export default NewChecklist;