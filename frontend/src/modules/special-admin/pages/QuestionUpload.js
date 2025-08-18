import React, { useState, useEffect, useRef } from 'react';
import { Upload, File, Check, X, AlertTriangle, Download, Eye, Trash2 } from 'lucide-react';
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

const QuestionUpload = () => {
  const [modules, setModules] = useState([]);
  const [selectedModule, setSelectedModule] = useState('');
  const [csvFile, setCsvFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const sampleCSV = `question_text,option_a,option_b,option_c,option_d,correct_answer,difficulty,explanation
"What is the maximum speed limit for dangerous goods vehicles in urban areas?","30 mph","40 mph","50 mph","60 mph","A","medium","Urban areas require reduced speeds for dangerous goods transport"
"Which document must be carried when transporting hazardous materials?","ADR certificate","Driving license","Vehicle registration","Insurance document","A","easy","ADR certificate is mandatory for hazardous materials transport"
"What does UN number 1203 represent?","Gasoline","Diesel","Kerosene","Motor spirit","A","hard","UN 1203 specifically designates motor spirit/gasoline"`;

  useEffect(() => {
    loadModules();
  }, []);

  const loadModules = async () => {
    try {
      const data = await specialAdminApi.getQuestionModules();
      setModules(data);
      
      // Auto-select SPECIAL-TEST if available
      const specialTestModule = data.find(m => m.code === 'SPECIAL-TEST');
      if (specialTestModule) {
        setSelectedModule(specialTestModule.code);
      }
    } catch (error) {
      toast.error('Failed to load question modules');
      console.error('Error loading modules:', error);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (file) => {
    if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
      toast.error('Please select a CSV file');
      return;
    }

    setCsvFile(file);
    
    const reader = new FileReader();
    reader.onload = (e) => {
      const csv = e.target.result;
      const lines = csv.split('\n').filter(line => line.trim());
      const header = lines[0];
      const preview = lines.slice(0, 4); // Header + 3 data rows
      
      setCsvPreview({
        header: header.split(','),
        rows: preview.slice(1).map(row => row.split(',')),
        totalRows: lines.length - 1
      });
    };
    reader.readAsText(file);
  };

  const validateCSVFormat = (csvText) => {
    const lines = csvText.split('\n').filter(line => line.trim());
    if (lines.length < 2) {
      return { valid: false, error: 'CSV must contain at least a header and one data row' };
    }

    const requiredColumns = ['question_text', 'correct_answer'];
    const header = lines[0].toLowerCase();
    
    for (const col of requiredColumns) {
      if (!header.includes(col)) {
        return { valid: false, error: `Missing required column: ${col}` };
      }
    }

    return { valid: true };
  };

  const handleUpload = async () => {
    if (!selectedModule) {
      toast.error('Please select a module');
      return;
    }

    if (!csvFile) {
      toast.error('Please select a CSV file');
      return;
    }

    setIsUploading(true);
    
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const csvText = e.target.result;
        
        // Validate CSV format
        const validation = validateCSVFormat(csvText);
        if (!validation.valid) {
          toast.error(validation.error);
          setIsUploading(false);
          return;
        }

        try {
          const result = await specialAdminApi.uploadQuestions({
            module_code: selectedModule,
            csv_data: csvText,
            created_by: 'admin' // This would come from auth context
          });

          setUploadResults(result);
          toast.success(`Successfully processed ${result.questions_processed} questions`);
          
          // Clear form
          setCsvFile(null);
          setCsvPreview(null);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
          
          // Reload modules to update question counts
          loadModules();
        } catch (error) {
          toast.error('Failed to upload questions');
          console.error('Upload error:', error);
        } finally {
          setIsUploading(false);
        }
      };
      reader.readAsText(csvFile);
    } catch (error) {
      toast.error('Error reading file');
      setIsUploading(false);
    }
  };

  const downloadSample = () => {
    const blob = new Blob([sampleCSV], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'sample_questions.csv';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const clearFile = () => {
    setCsvFile(null);
    setCsvPreview(null);
    setUploadResults(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Question Upload</h2>
          <p className="text-gray-600 mt-1">Upload CSV questions with SPECIAL-TEST tagging</p>
        </div>
        <Button onClick={downloadSample} variant="outline">
          <Download className="w-4 h-4 mr-2" />
          Download Sample CSV
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Form */}
        <Card>
          <CardHeader>
            <CardTitle>Upload Questions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="module">Target Module *</Label>
              <Select value={selectedModule} onValueChange={setSelectedModule}>
                <SelectTrigger>
                  <SelectValue placeholder="Select module for questions" />
                </SelectTrigger>
                <SelectContent>
                  {modules.map(module => (
                    <SelectItem key={module.code} value={module.code}>
                      <div className="flex items-center justify-between w-full">
                        <span>{module.code}</span>
                        <Badge variant="secondary" className="ml-2">
                          {module.question_count} questions
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedModule && (
                <p className="text-xs text-gray-500 mt-1">
                  Questions will be tagged with module: {selectedModule}
                </p>
              )}
            </div>

            {/* File Drop Zone */}
            <div>
              <Label>CSV File *</Label>
              <div
                className={`mt-2 flex justify-center px-6 pt-5 pb-6 border-2 border-dashed rounded-md transition-colors ${
                  dragActive
                    ? 'border-blue-400 bg-blue-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <div className="space-y-1 text-center">
                  {csvFile ? (
                    <div className="flex items-center justify-center space-x-2">
                      <File className="w-8 h-8 text-blue-500" />
                      <div className="text-left">
                        <p className="text-sm font-medium text-gray-900">{csvFile.name}</p>
                        <p className="text-xs text-gray-500">
                          {(csvFile.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={clearFile}
                        className="text-red-600 hover:text-red-800"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ) : (
                    <>
                      <Upload className="mx-auto h-12 w-12 text-gray-400" />
                      <div className="flex text-sm text-gray-600">
                        <label
                          htmlFor="file-upload"
                          className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500"
                        >
                          <span>Upload a file</span>
                          <input
                            id="file-upload"
                            name="file-upload"
                            type="file"
                            accept=".csv"
                            className="sr-only"
                            ref={fileInputRef}
                            onChange={(e) => e.target.files[0] && handleFileSelect(e.target.files[0])}
                          />
                        </label>
                        <p className="pl-1">or drag and drop</p>
                      </div>
                      <p className="text-xs text-gray-500">CSV files only</p>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="flex space-x-2">
              <Button
                onClick={handleUpload}
                disabled={!csvFile || !selectedModule || isUploading}
                className="flex-1"
              >
                {isUploading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                ) : (
                  <Upload className="w-4 h-4 mr-2" />
                )}
                {isUploading ? 'Processing...' : 'Upload Questions'}
              </Button>
              {csvFile && (
                <Button type="button" variant="outline" onClick={clearFile}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Preview/Results */}
        <Card>
          <CardHeader>
            <CardTitle>
              {uploadResults ? 'Upload Results' : csvPreview ? 'CSV Preview' : 'Upload Status'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {uploadResults && (
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Check className="w-5 h-5 text-green-500" />
                  <span className="font-medium text-green-700">Upload Completed</span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Module</p>
                    <p className="font-medium">{uploadResults.module_code}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Processed</p>
                    <p className="font-medium">{uploadResults.questions_processed} questions</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Created</p>
                    <p className="font-medium text-green-600">{uploadResults.questions_created} new</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Updated</p>
                    <p className="font-medium text-blue-600">{uploadResults.questions_updated} existing</p>
                  </div>
                </div>
                {uploadResults.errors && uploadResults.errors.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-medium text-red-600 mb-2">Errors:</p>
                    <div className="space-y-1">
                      {uploadResults.errors.map((error, index) => (
                        <p key={index} className="text-xs text-red-600 bg-red-50 p-2 rounded">
                          {error}
                        </p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {csvPreview && !uploadResults && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Eye className="w-4 h-4 text-blue-500" />
                    <span className="font-medium">CSV Preview</span>
                  </div>
                  <Badge variant="secondary">{csvPreview.totalRows} rows</Badge>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-xs">
                    <thead>
                      <tr className="border-b">
                        {csvPreview.header.map((col, index) => (
                          <th key={index} className="text-left p-1 font-medium bg-gray-50">
                            {col.replace(/"/g, '')}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {csvPreview.rows.map((row, rowIndex) => (
                        <tr key={rowIndex} className="border-b">
                          {row.map((cell, cellIndex) => (
                            <td key={cellIndex} className="p-1 max-w-24 truncate">
                              {cell.replace(/"/g, '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {csvPreview.totalRows > 3 && (
                  <p className="text-xs text-gray-500 text-center">
                    ... and {csvPreview.totalRows - 3} more rows
                  </p>
                )}
              </div>
            )}

            {!csvPreview && !uploadResults && (
              <div className="text-center py-8">
                <AlertTriangle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Select a CSV file to see preview</p>
                <p className="text-xs text-gray-400 mt-1">
                  Required columns: question_text, correct_answer
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* CSV Format Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>CSV Format Instructions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-2">Required Columns</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• <code className="bg-gray-100 px-1 rounded">question_text</code> - The question content</li>
                <li>• <code className="bg-gray-100 px-1 rounded">correct_answer</code> - Correct answer (A, B, C, D, or true/false)</li>
              </ul>

              <h4 className="font-medium mb-2 mt-4">Optional Columns</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• <code className="bg-gray-100 px-1 rounded">option_a, option_b, option_c, option_d</code> - Multiple choice options</li>
                <li>• <code className="bg-gray-100 px-1 rounded">difficulty</code> - easy, medium, hard</li>
                <li>• <code className="bg-gray-100 px-1 rounded">explanation</code> - Answer explanation</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Important Notes</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Questions are automatically tagged with the selected module</li>
                <li>• Existing questions with matching text will be updated</li>
                <li>• Use quotes around text containing commas</li>
                <li>• Ensure correct_answer matches option letters (A-D)</li>
                <li>• For true/false questions, use "true" or "false" as correct_answer</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default QuestionUpload;