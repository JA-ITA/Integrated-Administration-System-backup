// Mock API service for Special Admin functionality
// This will be replaced with real API calls once the backend is fully connected

const MOCK_DELAY = 800; // Simulate network delay

// Mock data
let mockSpecialTestTypes = [
  {
    id: '1',
    name: 'Dangerous Goods Handling',
    description: 'Certification for handling dangerous goods in transport',
    fee: 150.00,
    validity_months: 24,
    required_docs: ['Identity Proof', 'Medical Certificate MC1', 'Training Certificate'],
    pass_percentage: 75,
    time_limit_minutes: 30,
    questions_count: 25,
    status: 'active',
    created_by: 'admin',
    created_at: '2024-12-10T10:00:00Z',
    updated_at: '2024-12-10T10:00:00Z'
  },
  {
    id: '2',
    name: 'Hazardous Materials Transport',
    description: 'Special certification for hazardous materials transportation',
    fee: 200.00,
    validity_months: 36,
    required_docs: ['Identity Proof', 'Medical Certificate MC2', 'Experience Letter'],
    pass_percentage: 80,
    time_limit_minutes: 45,
    questions_count: 30,
    status: 'active',
    created_by: 'admin',
    created_at: '2024-12-08T14:30:00Z',
    updated_at: '2024-12-08T14:30:00Z'
  }
];

let mockQuestionModules = [
  {
    id: '1',
    code: 'SPECIAL-TEST',
    description: 'Special test questions for enhanced certifications',
    category: 'Special Assessments',
    status: 'active',
    question_count: 120,
    created_by: 'admin',
    created_at: '2024-12-10T10:00:00Z',
    updated_at: '2024-12-10T10:00:00Z'
  },
  {
    id: '2',
    code: 'DANGEROUS-GOODS',
    description: 'Questions specifically for dangerous goods handling',
    category: 'Dangerous Materials',
    status: 'active',
    question_count: 85,
    created_by: 'admin',
    created_at: '2024-12-08T14:30:00Z',
    updated_at: '2024-12-08T14:30:00Z'
  },
  {
    id: '3',
    code: 'HAZMAT',
    description: 'Hazardous materials transportation questions',
    category: 'Hazmat Transport',
    status: 'active',
    question_count: 95,
    created_by: 'admin',
    created_at: '2024-12-05T09:15:00Z',
    updated_at: '2024-12-05T09:15:00Z'
  }
];

let mockCertificateTemplates = [
  {
    id: '1',
    name: 'Dangerous Goods Certificate',
    type: 'Dangerous Goods Certificate',
    description: 'Standard template for dangerous goods handling certification',
    hbs_content: '<!DOCTYPE html><html>...</html>',
    css_content: 'body { font-family: Arial; }',
    json_config: {
      elements: [
        {
          id: 'header',
          type: 'text',
          content: '{{organization_name}}',
          style: { position: 'absolute', top: '20px', left: '50%', fontSize: '24px' }
        }
      ]
    },
    preview_html: null,
    status: 'active',
    is_default: true,
    created_by: 'admin',
    created_at: '2024-12-10T10:00:00Z',
    updated_at: '2024-12-10T10:00:00Z'
  },
  {
    id: '2',
    name: 'Special Assessment Certificate',
    type: 'Special Test Certificate',
    description: 'Template for special assessment certifications',
    hbs_content: '<!DOCTYPE html><html>...</html>',
    css_content: 'body { font-family: Arial; }',
    json_config: {
      elements: [
        {
          id: 'title',
          type: 'text',
          content: 'Certificate of Achievement',
          style: { position: 'absolute', top: '60px', left: '50%', fontSize: '28px' }
        }
      ]
    },
    preview_html: null,
    status: 'draft',
    is_default: false,
    created_by: 'admin',
    created_at: '2024-12-08T14:30:00Z',
    updated_at: '2024-12-08T14:30:00Z'
  }
];

// Utility function to simulate async operations
const delay = (ms = MOCK_DELAY) => new Promise(resolve => setTimeout(resolve, ms));

// Generate unique IDs
const generateId = () => Math.random().toString(36).substr(2, 9);

// API functions
export const specialAdminApi = {
  // Special Test Types
  async getSpecialTestTypes() {
    await delay();
    return [...mockSpecialTestTypes];
  },

  async getSpecialTestType(id) {
    await delay();
    const testType = mockSpecialTestTypes.find(t => t.id === id);
    if (!testType) {
      throw new Error('Special test type not found');
    }
    return testType;
  },

  async createSpecialTestType(data) {
    await delay();
    const newTestType = {
      ...data,
      id: generateId(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    mockSpecialTestTypes.push(newTestType);
    return newTestType;
  },

  async updateSpecialTestType(id, data) {
    await delay();
    const index = mockSpecialTestTypes.findIndex(t => t.id === id);
    if (index === -1) {
      throw new Error('Special test type not found');
    }
    mockSpecialTestTypes[index] = {
      ...mockSpecialTestTypes[index],
      ...data,
      updated_at: new Date().toISOString()
    };
    return mockSpecialTestTypes[index];
  },

  async deleteSpecialTestType(id) {
    await delay();
    const index = mockSpecialTestTypes.findIndex(t => t.id === id);
    if (index === -1) {
      throw new Error('Special test type not found');
    }
    mockSpecialTestTypes.splice(index, 1);
    return { success: true };
  },

  // Question Modules
  async getQuestionModules() {
    await delay();
    return [...mockQuestionModules];
  },

  async getQuestionModule(id) {
    await delay();
    const module = mockQuestionModules.find(m => m.id === id);
    if (!module) {
      throw new Error('Question module not found');
    }
    return module;
  },

  async createQuestionModule(data) {
    await delay();
    const newModule = {
      ...data,
      id: generateId(),
      question_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    mockQuestionModules.push(newModule);
    return newModule;
  },

  async updateQuestionModule(id, data) {
    await delay();
    const index = mockQuestionModules.findIndex(m => m.id === id);
    if (index === -1) {
      throw new Error('Question module not found');
    }
    mockQuestionModules[index] = {
      ...mockQuestionModules[index],
      ...data,
      updated_at: new Date().toISOString()
    };
    return mockQuestionModules[index];
  },

  // Question Upload
  async uploadQuestions(data) {
    await delay();
    
    // Parse CSV and simulate processing
    const csvLines = data.csv_data.split('\n').filter(line => line.trim());
    const header = csvLines[0];
    const dataRows = csvLines.slice(1);
    
    // Simulate processing results
    const questionsProcessed = dataRows.length;
    const questionsCreated = Math.floor(questionsProcessed * 0.8);
    const questionsUpdated = questionsProcessed - questionsCreated;
    
    // Update module question count
    const moduleIndex = mockQuestionModules.findIndex(m => m.code === data.module_code);
    if (moduleIndex !== -1) {
      mockQuestionModules[moduleIndex].question_count += questionsCreated;
      mockQuestionModules[moduleIndex].updated_at = new Date().toISOString();
    }

    return {
      success: true,
      module_code: data.module_code,
      questions_processed: questionsProcessed,
      questions_created: questionsCreated,
      questions_updated: questionsUpdated,
      errors: questionsProcessed > 10 ? ['Row 15: Invalid answer format'] : [],
      message: `Successfully processed ${questionsProcessed} questions for module ${data.module_code}`
    };
  },

  // Certificate Templates
  async getCertificateTemplates() {
    await delay();
    return [...mockCertificateTemplates];
  },

  async getCertificateTemplate(id) {
    await delay();
    const template = mockCertificateTemplates.find(t => t.id === id);
    if (!template) {
      throw new Error('Certificate template not found');
    }
    return template;
  },

  async createCertificateTemplate(data) {
    await delay();
    const newTemplate = {
      ...data,
      id: generateId(),
      preview_html: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    mockCertificateTemplates.push(newTemplate);
    return newTemplate;
  },

  async updateCertificateTemplate(id, data) {
    await delay();
    const index = mockCertificateTemplates.findIndex(t => t.id === id);
    if (index === -1) {
      throw new Error('Certificate template not found');
    }
    mockCertificateTemplates[index] = {
      ...mockCertificateTemplates[index],
      ...data,
      updated_at: new Date().toISOString()
    };
    return mockCertificateTemplates[index];
  },

  async deleteCertificateTemplate(id) {
    await delay();
    const index = mockCertificateTemplates.findIndex(t => t.id === id);
    if (index === -1) {
      throw new Error('Certificate template not found');
    }
    mockCertificateTemplates.splice(index, 1);
    return { success: true };
  },

  // Template Preview
  async previewTemplate(data) {
    await delay();
    
    // Simulate template compilation
    const sampleData = {
      organization_name: 'ITADIAS Training Center',
      candidate_name: 'John Smith',
      test_type: 'Dangerous Goods Handling',
      completion_date: '2024-12-15',
      certificate_id: 'DGH-2024-001234'
    };
    
    let previewHtml = data.hbs_content;
    Object.entries(sampleData).forEach(([key, value]) => {
      previewHtml = previewHtml.replace(new RegExp(`{{${key}}}`, 'g'), value);
    });

    return {
      preview_html: previewHtml,
      compiled_template: data.hbs_content,
      status: 'success'
    };
  }
};