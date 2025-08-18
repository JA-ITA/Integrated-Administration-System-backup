import { useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import axios from "axios";

// Special Admin Components
import SpecialAdminLayout from "./modules/special-admin/SpecialAdminLayout";
import SpecialTestTypes from "./modules/special-admin/pages/SpecialTestTypes";
import QuestionUpload from "./modules/special-admin/pages/QuestionUpload";
import CertificateDesigner from "./modules/special-admin/pages/CertificateDesigner";

// Examiner Tablet Components
import ExaminerTabletLayout from "./modules/examiner-tablet/ExaminerTabletLayout";
import ActiveChecklists from "./modules/examiner-tablet/pages/ActiveChecklists";
import NewChecklist from "./modules/examiner-tablet/pages/NewChecklist";
import ChecklistDetail from "./modules/examiner-tablet/pages/ChecklistDetail";
import ChecklistHistory from "./modules/examiner-tablet/pages/ChecklistHistory";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Home = () => {
  const helloWorldApi = async () => {
    try {
      const response = await axios.get(`${API}/`);
      console.log(response.data.message);
    } catch (e) {
      console.error(e, `errored out requesting / api`);
    }
  };

  useEffect(() => {
    helloWorldApi();
  }, []);

  return (
    <div>
      <header className="App-header">
        <a
          className="App-link"
          href="https://emergent.sh"
          target="_blank"
          rel="noopener noreferrer"
        >
          <img src="https://avatars.githubusercontent.com/in/1201222?s=120&u=2686cf91179bbafbc7a71bfbc43004cf9ae1acea&v=4" alt="Emergent Logo" />
        </a>
        <p className="mt-5">Building something incredible ~!</p>
        
        {/* Quick Navigation to Special Admin */}
        <div className="mt-8">
          <a
            href="/modules/special-admin"
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Access Special Admin Module
          </a>
        </div>
      </header>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          
          {/* Special Admin Module Routes */}
          <Route path="/modules/special-admin" element={<SpecialAdminLayout />}>
            <Route index element={<SpecialTestTypes />} />
            <Route path="questions" element={<QuestionUpload />} />
            <Route path="certificates" element={<CertificateDesigner />} />
          </Route>
          
          {/* Fallback route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      
      {/* Toast notifications */}
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;