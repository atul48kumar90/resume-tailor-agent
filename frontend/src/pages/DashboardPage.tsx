import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getResumes } from '../services/api';
import LoadingSpinner from '../components/common/LoadingSpinner';

const DashboardPage: React.FC = () => {
  const { data: resumes, isLoading } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => getResumes('test_user'), // Replace with actual user ID
  });

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <LoadingSpinner message="Loading your resumes..." />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-gray-900">My Resumes</h1>
        <button className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors">
          + New Resume
        </button>
      </div>

      {resumes && resumes.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {resumes.map((resume: any) => (
            <div
              key={resume.id || resume.resume_id}
              className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
            >
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {resume.title || 'Untitled Resume'}
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Created: {new Date(resume.created_at).toLocaleDateString()}
              </p>
              {resume.tags && resume.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {resume.tags.map((tag: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex gap-2 mt-4">
                <button className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700">
                  View
                </button>
                <button className="flex-1 bg-gray-200 text-gray-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-300">
                  Edit
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <p className="text-gray-600 mb-4">No resumes saved yet</p>
          <button className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700">
            Create Your First Resume
          </button>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;

