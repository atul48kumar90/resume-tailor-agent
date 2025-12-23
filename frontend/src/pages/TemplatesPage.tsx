import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getTemplates } from '../services/api';
import LoadingSpinner from '../components/common/LoadingSpinner';

const TemplatesPage: React.FC = () => {
  const { data: templates, isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: getTemplates,
  });

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <LoadingSpinner message="Loading templates..." />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Resume Templates</h1>

      {templates && templates.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template: any) => (
            <div
              key={template.id}
              className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
            >
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {template.name || template.id}
              </h3>
              {template.description && (
                <p className="text-sm text-gray-600 mb-4">{template.description}</p>
              )}
              {template.ats_friendly && (
                <span className="inline-block px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium mb-4">
                  ATS Friendly
                </span>
              )}
              <div className="flex gap-2 mt-4">
                <button className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700">
                  Preview
                </button>
                <button className="flex-1 bg-gray-200 text-gray-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-300">
                  Customize
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <p className="text-gray-600">No templates available</p>
        </div>
      )}
    </div>
  );
};

export default TemplatesPage;

