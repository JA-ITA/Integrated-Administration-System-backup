import React, { useState, useEffect, useRef } from 'react';
import { 
  Save, Eye, Download, Upload, Palette, Type, Image as ImageIcon, 
  Move, RotateCcw, Trash2, Plus, Settings, Code, Monitor 
} from 'lucide-react';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/card';
import { Badge } from '../../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../../components/ui/dialog';
import { specialAdminApi } from '../services/mockApi';
import { toast } from 'sonner';

const CertificateDesigner = () => {
  const [templates, setTemplates] = useState([]);
  const [activeTemplate, setActiveTemplate] = useState(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [previewMode, setPreviewMode] = useState('design'); // design, preview, code
  const [draggedElement, setDraggedElement] = useState(null);
  const [selectedElement, setSelectedElement] = useState(null);
  const [loading, setLoading] = useState(true);

  const canvasRef = useRef(null);
  
  const [templateForm, setTemplateForm] = useState({
    name: '',
    type: '',
    description: '',
    hbs_content: '',
    css_content: '',
    json_config: {},
    status: 'draft'
  });

  const [designElements, setDesignElements] = useState([
    {
      id: 'header',
      type: 'text',
      content: '{{organization_name}}',
      style: { 
        position: 'absolute', 
        top: '20px', 
        left: '50%', 
        transform: 'translateX(-50%)',
        fontSize: '24px', 
        fontWeight: 'bold',
        textAlign: 'center',
        color: '#000000'
      }
    },
    {
      id: 'title',
      type: 'text',
      content: 'Certificate of Completion',
      style: { 
        position: 'absolute', 
        top: '80px', 
        left: '50%', 
        transform: 'translateX(-50%)',
        fontSize: '32px', 
        fontWeight: 'bold',
        textAlign: 'center',
        color: '#1f2937'
      }
    },
    {
      id: 'candidate-name',
      type: 'text',
      content: '{{candidate_name}}',
      style: { 
        position: 'absolute', 
        top: '180px', 
        left: '50%', 
        transform: 'translateX(-50%)',
        fontSize: '28px', 
        fontWeight: 'normal',
        textAlign: 'center',
        color: '#374151',
        fontStyle: 'italic'
      }
    },
    {
      id: 'completion-text',
      type: 'text',
      content: 'has successfully completed the',
      style: { 
        position: 'absolute', 
        top: '220px', 
        left: '50%', 
        transform: 'translateX(-50%)',
        fontSize: '16px',
        textAlign: 'center',
        color: '#6b7280'
      }
    },
    {
      id: 'test-type',
      type: 'text',
      content: '{{test_type}}',
      style: { 
        position: 'absolute', 
        top: '250px', 
        left: '50%', 
        transform: 'translateX(-50%)',
        fontSize: '20px', 
        fontWeight: 'bold',
        textAlign: 'center',
        color: '#1f2937'
      }
    },
    {
      id: 'date',
      type: 'text',
      content: 'Date: {{completion_date}}',
      style: { 
        position: 'absolute', 
        bottom: '60px', 
        left: '40px',
        fontSize: '14px',
        color: '#6b7280'
      }
    },
    {
      id: 'certificate-id',
      type: 'text',
      content: 'Certificate ID: {{certificate_id}}',
      style: { 
        position: 'absolute', 
        bottom: '40px', 
        left: '40px',
        fontSize: '12px',
        color: '#9ca3af'
      }
    }
  ]);

  const elementTypes = [
    { type: 'text', icon: Type, label: 'Text' },
    { type: 'image', icon: ImageIcon, label: 'Image' },
    { type: 'signature', icon: Settings, label: 'Signature' }
  ];

  const templateTypes = [
    'Special Test Certificate',
    'Dangerous Goods Certificate',
    'Training Completion',
    'Assessment Pass',
    'Custom Certificate'
  ];

  const sampleData = {
    organization_name: 'ITADIAS Training Center',
    candidate_name: 'John Smith',
    test_type: 'Dangerous Goods Handling Certification',
    completion_date: '2024-12-15',
    certificate_id: 'DGH-2024-001234',
    score: '85%',
    validity_date: '2026-12-15'
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const data = await specialAdminApi.getCertificateTemplates();
      setTemplates(data);
    } catch (error) {
      toast.error('Failed to load certificate templates');
      console.error('Error loading templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateHandlebarsTemplate = () => {
    let hbs = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Certificate</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: white;
        }
        .certificate-container {
            width: 800px;
            height: 600px;
            position: relative;
            border: 2px solid #333;
            margin: 0 auto;
        }
`;

    designElements.forEach(element => {
      hbs += `        .element-${element.id} {
`;
      Object.entries(element.style).forEach(([key, value]) => {
        const cssKey = key.replace(/([A-Z])/g, '-$1').toLowerCase();
        hbs += `            ${cssKey}: ${value};
`;
      });
      hbs += `        }
`;
    });

    hbs += `    </style>
</head>
<body>
    <div class="certificate-container">
`;

    designElements.forEach(element => {
      hbs += `        <div class="element-${element.id}">${element.content}</div>
`;
    });

    hbs += `    </div>
</body>
</html>`;

    return hbs;
  };

  const renderPreview = () => {
    let html = generateHandlebarsTemplate();
    
    // Replace Handlebars variables with sample data
    Object.entries(sampleData).forEach(([key, value]) => {
      html = html.replace(new RegExp(`{{${key}}}`, 'g'), value);
    });

    return html;
  };

  const handleSaveTemplate = async () => {
    if (!templateForm.name || !templateForm.type) {
      toast.error('Please fill in required fields');
      return;
    }

    try {
      const hbsContent = generateHandlebarsTemplate();
      const cssContent = '/* Generated CSS styles are embedded in template */';
      const jsonConfig = { elements: designElements };

      const payload = {
        ...templateForm,
        hbs_content: hbsContent,
        css_content: cssContent,
        json_config: jsonConfig,
        created_by: 'admin'
      };

      if (activeTemplate) {
        await specialAdminApi.updateCertificateTemplate(activeTemplate.id, payload);
        toast.success('Template updated successfully');
      } else {
        await specialAdminApi.createCertificateTemplate(payload);
        toast.success('Template created successfully');
      }

      setIsCreateDialogOpen(false);
      loadTemplates();
    } catch (error) {
      toast.error('Failed to save template');
      console.error('Error saving template:', error);
    }
  };

  const handleElementDrag = (elementId, newStyle) => {
    setDesignElements(prev => 
      prev.map(el => 
        el.id === elementId 
          ? { ...el, style: { ...el.style, ...newStyle } }
          : el
      )
    );
  };

  const addElement = (type) => {
    const newElement = {
      id: `element-${Date.now()}`,
      type,
      content: type === 'text' ? 'New Text Element' : type === 'image' ? '{{image_url}}' : '{{signature}}',
      style: {
        position: 'absolute',
        top: '100px',
        left: '100px',
        fontSize: '16px',
        color: '#000000'
      }
    };

    setDesignElements(prev => [...prev, newElement]);
  };

  const updateElementContent = (elementId, content) => {
    setDesignElements(prev =>
      prev.map(el =>
        el.id === elementId ? { ...el, content } : el
      )
    );
  };

  const updateElementStyle = (elementId, styleUpdate) => {
    setDesignElements(prev =>
      prev.map(el =>
        el.id === elementId 
          ? { ...el, style: { ...el.style, ...styleUpdate } }
          : el
      )
    );
  };

  const deleteElement = (elementId) => {
    setDesignElements(prev => prev.filter(el => el.id !== elementId));
    setSelectedElement(null);
  };

  const loadTemplate = (template) => {
    setActiveTemplate(template);
    setTemplateForm({
      name: template.name,
      type: template.type,
      description: template.description || '',
      status: template.status
    });
    
    if (template.json_config && template.json_config.elements) {
      setDesignElements(template.json_config.elements);
    }
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
          <h2 className="text-2xl font-bold text-gray-900">Certificate Designer</h2>
          <p className="text-gray-600 mt-1">Drag-and-drop certificate template designer</p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={() => setPreviewMode('design')} variant={previewMode === 'design' ? 'default' : 'outline'}>
            <Palette className="w-4 h-4 mr-2" />
            Design
          </Button>
          <Button onClick={() => setPreviewMode('preview')} variant={previewMode === 'preview' ? 'default' : 'outline'}>
            <Eye className="w-4 h-4 mr-2" />
            Preview
          </Button>
          <Button onClick={() => setPreviewMode('code')} variant={previewMode === 'code' ? 'default' : 'outline'}>
            <Code className="w-4 h-4 mr-2" />
            Code
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Templates Sidebar */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Templates</CardTitle>
              <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" className="w-full">
                    <Plus className="w-4 h-4 mr-2" />
                    New Template
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>Create Certificate Template</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="template-name">Template Name *</Label>
                      <Input
                        id="template-name"
                        value={templateForm.name}
                        onChange={(e) => setTemplateForm(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="e.g., Dangerous Goods Certificate"
                      />
                    </div>
                    <div>
                      <Label htmlFor="template-type">Type *</Label>
                      <Select value={templateForm.type} onValueChange={(value) => setTemplateForm(prev => ({ ...prev, type: value }))}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select template type" />
                        </SelectTrigger>
                        <SelectContent>
                          {templateTypes.map(type => (
                            <SelectItem key={type} value={type}>{type}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="template-description">Description</Label>
                      <Textarea
                        id="template-description"
                        value={templateForm.description}
                        onChange={(e) => setTemplateForm(prev => ({ ...prev, description: e.target.value }))}
                        placeholder="Template description..."
                        rows={3}
                      />
                    </div>
                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                        Cancel
                      </Button>
                      <Button onClick={handleSaveTemplate}>
                        Create & Design
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="space-y-2">
              {templates.map(template => (
                <div
                  key={template.id}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    activeTemplate?.id === template.id 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => loadTemplate(template)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{template.name}</p>
                      <p className="text-xs text-gray-500">{template.type}</p>
                    </div>
                    <Badge 
                      className={template.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}
                    >
                      {template.status}
                    </Badge>
                  </div>
                </div>
              ))}
              
              {templates.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <Settings className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                  <p className="text-sm">No templates yet</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Element Toolbox */}
          {previewMode === 'design' && (
            <Card className="mt-4">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Elements</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {elementTypes.map(({ type, icon: Icon, label }) => (
                  <Button
                    key={type}
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => addElement(type)}
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    Add {label}
                  </Button>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Main Design Area */}
        <div className="lg:col-span-3">
          <Card className="h-96">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-center">
                <CardTitle className="text-lg">
                  {previewMode === 'design' && 'Design Canvas'}
                  {previewMode === 'preview' && 'Live Preview'}
                  {previewMode === 'code' && 'Generated Code'}
                </CardTitle>
                <div className="flex space-x-2">
                  {activeTemplate && (
                    <Button onClick={handleSaveTemplate} size="sm">
                      <Save className="w-4 h-4 mr-2" />
                      Save
                    </Button>
                  )}
                  <Button variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-2" />
                    Export
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="h-full">
              {previewMode === 'design' && (
                <div className="relative w-full h-80 border-2 border-dashed border-gray-300 overflow-hidden">
                  <div 
                    className="relative w-full h-full bg-white"
                    style={{ transform: 'scale(0.7)', transformOrigin: 'top left' }}
                  >
                    {designElements.map(element => (
                      <div
                        key={element.id}
                        className={`draggable-element ${selectedElement === element.id ? 'ring-2 ring-blue-500' : ''}`}
                        style={element.style}
                        onClick={() => setSelectedElement(element.id)}
                        draggable
                      >
                        {element.content.replace(/{{(\w+)}}/g, (match, key) => sampleData[key] || match)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {previewMode === 'preview' && (
                <div className="w-full h-80 border overflow-auto">
                  <iframe
                    srcDoc={renderPreview()}
                    className="w-full h-full border-none"
                    title="Certificate Preview"
                  />
                </div>
              )}

              {previewMode === 'code' && (
                <div className="w-full h-80 overflow-auto">
                  <pre className="text-xs bg-gray-50 p-4 rounded">
                    <code>{generateHandlebarsTemplate()}</code>
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Element Properties */}
          {previewMode === 'design' && selectedElement && (
            <Card className="mt-4">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle className="text-lg">Element Properties</CardTitle>
                  <Button 
                    variant="destructive" 
                    size="sm"
                    onClick={() => deleteElement(selectedElement)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {(() => {
                  const element = designElements.find(el => el.id === selectedElement);
                  if (!element) return null;

                  return (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Content</Label>
                        <Input
                          value={element.content}
                          onChange={(e) => updateElementContent(selectedElement, e.target.value)}
                        />
                      </div>
                      <div>
                        <Label>Font Size</Label>
                        <Input
                          value={element.style.fontSize || '16px'}
                          onChange={(e) => updateElementStyle(selectedElement, { fontSize: e.target.value })}
                        />
                      </div>
                      <div>
                        <Label>Color</Label>
                        <Input
                          type="color"
                          value={element.style.color || '#000000'}
                          onChange={(e) => updateElementStyle(selectedElement, { color: e.target.value })}
                        />
                      </div>
                      <div>
                        <Label>Font Weight</Label>
                        <Select 
                          value={element.style.fontWeight || 'normal'}
                          onValueChange={(value) => updateElementStyle(selectedElement, { fontWeight: value })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="normal">Normal</SelectItem>
                            <SelectItem value="bold">Bold</SelectItem>
                            <SelectItem value="lighter">Light</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  );
                })()}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default CertificateDesigner;