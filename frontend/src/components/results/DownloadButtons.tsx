import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { downloadJobResume } from '../../services/api';

interface DownloadButtonsProps {
  jobId: string;
  resumeData?: any; // Optional fallback for backward compatibility
}

const DownloadButtons: React.FC<DownloadButtonsProps> = ({ jobId, resumeData }) => {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleDownload = async (format: 'docx' | 'pdf' | 'txt' | 'zip') => {
    if (!jobId) {
      toast.error('Job ID is required for download');
      return;
    }

    try {
      setDownloading(format);
      
      // Use the new job-based download endpoint
      const blob = await downloadJobResume(jobId, format);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const extension = format === 'zip' ? 'zip' : format;
      a.download = `tailored_resume.${extension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      toast.success(`Resume downloaded as ${format.toUpperCase()}`);
    } catch (error: any) {
      toast.error(error.message || 'Failed to download resume');
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <button
        onClick={() => handleDownload('docx')}
        disabled={downloading !== null}
        className="flex flex-col items-center justify-center p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {downloading === 'docx' ? (
          <svg className="animate-spin h-6 w-6 text-blue-600 mb-2" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          <svg className="h-8 w-8 text-blue-600 mb-2" fill="currentColor" viewBox="0 0 20 20">
            <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
          </svg>
        )}
        <span className="text-sm font-medium text-gray-700">DOCX</span>
      </button>

      <button
        onClick={() => handleDownload('pdf')}
        disabled={downloading !== null}
        className="flex flex-col items-center justify-center p-4 border-2 border-gray-300 rounded-lg hover:border-red-500 hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {downloading === 'pdf' ? (
          <svg className="animate-spin h-6 w-6 text-red-600 mb-2" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          <svg className="h-8 w-8 text-red-600 mb-2" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
              clipRule="evenodd"
            />
          </svg>
        )}
        <span className="text-sm font-medium text-gray-700">PDF</span>
      </button>

      <button
        onClick={() => handleDownload('txt')}
        disabled={downloading !== null}
        className="flex flex-col items-center justify-center p-4 border-2 border-gray-300 rounded-lg hover:border-gray-500 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {downloading === 'txt' ? (
          <svg className="animate-spin h-6 w-6 text-gray-600 mb-2" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          <svg className="h-8 w-8 text-gray-600 mb-2" fill="currentColor" viewBox="0 0 20 20">
            <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
          </svg>
        )}
        <span className="text-sm font-medium text-gray-700">TXT</span>
      </button>

      <button
        onClick={() => handleDownload('zip')}
        disabled={downloading !== null}
        className="flex flex-col items-center justify-center p-4 border-2 border-gray-300 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {downloading === 'zip' ? (
          <svg className="animate-spin h-6 w-6 text-purple-600 mb-2" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          <svg className="h-8 w-8 text-purple-600 mb-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 2a1 1 0 011 1v1h10V3a1 1 0 011-1h2a1 1 0 011 1v14a1 1 0 01-1 1H3a1 1 0 01-1-1V3a1 1 0 011-1h2zm3 4a1 1 0 00-1 1v6a1 1 0 001 1h6a1 1 0 001-1V7a1 1 0 00-1-1H7z" clipRule="evenodd" />
          </svg>
        )}
        <span className="text-sm font-medium text-gray-700">ZIP (All)</span>
      </button>
    </div>
  );
};

export default DownloadButtons;

