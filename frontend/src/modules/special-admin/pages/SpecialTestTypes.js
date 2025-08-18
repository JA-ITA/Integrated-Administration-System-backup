import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Save, X, Check, AlertTriangle } from 'lucide-react';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { Badge } from '../../../components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../../components/ui/dialog';
import { specialAdminApi } from '../services/mockApi';
import { toast } from 'sonner';

const SpecialTestTypes = () => {
  const [testTypes, setTestTypes] = useState([]);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    fee: '',
    validity_months: '',
    required_docs: [],
    pass_percentage: '75',
    time_limit_minutes: '25',
    questions_count: '20',
    status: 'active'
  });

  const documentTypes = [
    'Identity Proof',
    'Medical Certificate MC1',
    'Medical Certificate MC2',
    'Address Proof',
    'Photo ID',
    'Training Certificate',
    'Experience Letter',
    'Eye Test Report'
  ];

  const statusOptions = [
    { value: 'active', label: 'Active', color: 'bg-green-100 text-green-800' },
    { value: 'inactive', label: 'Inactive', color: 'bg-gray-100 text-gray-800' },
    { value: 'draft', label: 'Draft', color: 'bg-yellow-100 text-yellow-800' }
  ];

  useEffect(() => {
    loadTestTypes();
  }, []);

  const loadTestTypes = async () => {
    try {
      setLoading(true);
      const data = await specialAdminApi.getSpecialTestTypes();
      setTestTypes(data);
    } catch (error) {
      toast.error('Failed to load special test types');
      console.error('Error loading test types:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        fee: parseFloat(formData.fee),
        validity_months: parseInt(formData.validity_months),
        pass_percentage: parseInt(formData.pass_percentage),
        time_limit_minutes: parseInt(formData.time_limit_minutes),
        questions_count: parseInt(formData.questions_count),
        created_by: 'admin' // This would come from auth context in real app
      };

      if (editingId) {
        await specialAdminApi.updateSpecialTestType(editingId, payload);
        toast.success('Special test type updated successfully');
      } else {
        await specialAdminApi.createSpecialTestType(payload);
        toast.success('Special test type created successfully');
      }

      setIsCreateDialogOpen(false);
      setEditingId(null);
      resetForm();
      loadTestTypes();
    } catch (error) {
      toast.error('Failed to save special test type');
      console.error('Error saving test type:', error);
    }
  };

  const handleEdit = (testType) => {
    setFormData({
      name: testType.name,
      description: testType.description || '',
      fee: testType.fee.toString(),
      validity_months: testType.validity_months.toString(),
      required_docs: testType.required_docs || [],
      pass_percentage: testType.pass_percentage.toString(),
      time_limit_minutes: testType.time_limit_minutes.toString(),
      questions_count: testType.questions_count.toString(),
      status: testType.status
    });
    setEditingId(testType.id);
    setIsCreateDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this special test type?')) {
      try {
        await specialAdminApi.deleteSpecialTestType(id);
        toast.success('Special test type deleted successfully');
        loadTestTypes();
      } catch (error) {
        toast.error('Failed to delete special test type');
        console.error('Error deleting test type:', error);
      }
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      fee: '',
      validity_months: '',
      required_docs: [],
      pass_percentage: '75',
      time_limit_minutes: '25',
      questions_count: '20',
      status: 'active'
    });
  };

  const toggleRequiredDoc = (docType) => {
    setFormData(prev => ({
      ...prev,
      required_docs: prev.required_docs.includes(docType)
        ? prev.required_docs.filter(doc => doc !== docType)
        : [...prev.required_docs, docType]
    }));
  };

  const getStatusBadge = (status) => {
    const statusConfig = statusOptions.find(s => s.value === status);
    return (
      <Badge className={statusConfig?.color || 'bg-gray-100 text-gray-800'}>
        {statusConfig?.label || status}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Special Test Types</h2>
          <p className="text-gray-600 mt-1">Manage special test configurations, fees, and validity periods</p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" />
              Create Test Type
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingId ? 'Edit Special Test Type' : 'Create New Special Test Type'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Test Type Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Dangerous Goods Handling"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="status">Status</Label>
                  <Select value={formData.status} onValueChange={(value) => setFormData(prev => ({ ...prev, status: value }))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {statusOptions.map(option => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Describe the special test type..."
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="fee">Fee (£) *</Label>
                  <Input
                    id="fee"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.fee}
                    onChange={(e) => setFormData(prev => ({ ...prev, fee: e.target.value }))}
                    placeholder="0.00"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="validity_months">Validity (months) *</Label>
                  <Input
                    id="validity_months"
                    type="number"
                    min="1"
                    max="120"
                    value={formData.validity_months}
                    onChange={(e) => setFormData(prev => ({ ...prev, validity_months: e.target.value }))}
                    placeholder="12"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="pass_percentage">Pass % *</Label>
                  <Input
                    id="pass_percentage"
                    type="number"
                    min="50"
                    max="100"
                    value={formData.pass_percentage}
                    onChange={(e) => setFormData(prev => ({ ...prev, pass_percentage: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="time_limit_minutes">Time (minutes) *</Label>
                  <Input
                    id="time_limit_minutes"
                    type="number"
                    min="5"
                    max="180"
                    value={formData.time_limit_minutes}
                    onChange={(e) => setFormData(prev => ({ ...prev, time_limit_minutes: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="questions_count">Questions *</Label>
                  <Input
                    id="questions_count"
                    type="number"
                    min="5"
                    max="100"
                    value={formData.questions_count}
                    onChange={(e) => setFormData(prev => ({ ...prev, questions_count: e.target.value }))}
                    required
                  />
                </div>
              </div>

              <div>
                <Label className="text-base font-medium">Required Documents</Label>
                <p className="text-sm text-gray-600 mb-3">Select documents required for this test type</p>
                <div className="grid grid-cols-2 gap-2">
                  {documentTypes.map(docType => (
                    <label
                      key={docType}
                      className="flex items-center space-x-2 p-2 rounded border cursor-pointer hover:bg-gray-50"
                    >
                      <input
                        type="checkbox"
                        checked={formData.required_docs.includes(docType)}
                        onChange={() => toggleRequiredDoc(docType)}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <span className="text-sm">{docType}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setIsCreateDialogOpen(false);
                    setEditingId(null);
                    resetForm();
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit">
                  <Save className="w-4 h-4 mr-2" />
                  {editingId ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-6">
        {testTypes.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No special test types found</h3>
              <p className="text-gray-600 mb-4">Get started by creating your first special test type.</p>
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create Test Type
              </Button>
            </CardContent>
          </Card>
        ) : (
          testTypes.map((testType) => (
            <Card key={testType.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-4">
                <div className="space-y-1">
                  <CardTitle className="text-lg">{testType.name}</CardTitle>
                  <p className="text-sm text-gray-600">{testType.description}</p>
                </div>
                <div className="flex items-center space-x-2">
                  {getStatusBadge(testType.status)}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEdit(testType)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(testType.id)}
                    className="text-red-600 hover:text-red-800"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <p className="text-xs text-gray-500">Fee</p>
                    <p className="text-sm font-medium">£{testType.fee}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Validity</p>
                    <p className="text-sm font-medium">{testType.validity_months} months</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Pass Rate / Time</p>
                    <p className="text-sm font-medium">{testType.pass_percentage}% / {testType.time_limit_minutes}min</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Questions</p>
                    <p className="text-sm font-medium">{testType.questions_count} questions</p>
                  </div>
                </div>
                {testType.required_docs && testType.required_docs.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-500 mb-2">Required Documents</p>
                    <div className="flex flex-wrap gap-1">
                      {testType.required_docs.map((doc) => (
                        <Badge key={doc} variant="secondary" className="text-xs">
                          {doc}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default SpecialTestTypes;