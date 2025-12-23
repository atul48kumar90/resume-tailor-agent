import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-800 text-gray-300 mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid md:grid-cols-3 gap-8">
          <div>
            <h3 className="text-white font-bold text-lg mb-4">Resume Tailor</h3>
            <p className="text-sm">
              AI-powered resume optimization for maximum ATS compatibility
            </p>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-4">Features</h4>
            <ul className="space-y-2 text-sm">
              <li>ATS Optimization</li>
              <li>Skill Gap Analysis</li>
              <li>Batch Processing</li>
              <li>Resume Templates</li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-4">Support</h4>
            <ul className="space-y-2 text-sm">
              <li>Documentation</li>
              <li>API Reference</li>
              <li>Contact</li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-gray-700 text-center text-sm">
          <p>&copy; 2024 Resume Tailor Agent. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

