import React, { useState } from 'react';

interface ResumePreviewProps {
  originalResume?: string;
  tailoredResume: any;
}

const ResumePreview: React.FC<ResumePreviewProps> = ({
  originalResume,
  tailoredResume,
}) => {
  const [viewMode, setViewMode] = useState<'original' | 'tailored' | 'compare'>('tailored');

  const formatResume = (resume: any): string => {
    if (typeof resume === 'string') return resume;
    
    let formatted = '';
    if (resume.summary) {
      formatted += `SUMMARY\n${resume.summary}\n\n`;
    }
    if (resume.experience && Array.isArray(resume.experience)) {
      formatted += 'EXPERIENCE\n';
      resume.experience.forEach((exp: any) => {
        if (exp.title) formatted += `${exp.title}\n`;
        if (exp.company) formatted += `${exp.company}\n`;
        if (exp.bullets && Array.isArray(exp.bullets)) {
          exp.bullets.forEach((bullet: string) => {
            formatted += `• ${bullet}\n`;
          });
        }
        formatted += '\n';
      });
    }
    if (resume.skills && Array.isArray(resume.skills)) {
      formatted += `SKILLS\n${resume.skills.join(', ')}\n`;
    }
    return formatted;
  };

  const tailoredText = formatResume(tailoredResume);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Resume Preview</h2>
        <div className="flex gap-2">
          {originalResume && (
            <>
              <button
                onClick={() => setViewMode('original')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'original'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Original
              </button>
              <button
                onClick={() => setViewMode('compare')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'compare'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Compare
              </button>
            </>
          )}
          <button
            onClick={() => setViewMode('tailored')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewMode === 'tailored'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Tailored
          </button>
        </div>
      </div>

      <div className="border border-gray-300 rounded-lg p-6 bg-gray-50 min-h-[400px]">
        {viewMode === 'compare' && originalResume ? (
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">Original</h3>
              <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans">
                {originalResume}
              </pre>
            </div>
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">Tailored</h3>
              <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans">
                {tailoredText}
              </pre>
            </div>
          </div>
        ) : (
          <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans">
            {viewMode === 'original' && originalResume ? originalResume : tailoredText}
          </pre>
        )}
      </div>
    </div>
  );
};

export default ResumePreview;

