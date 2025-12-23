import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import FileUpload from '../components/upload/FileUpload';
import { batchProcess } from '../services/api';

const BatchPage: React.FC = () => {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jdFiles, setJdFiles] = useState<File[]>([]);

  const mutation = useMutation({
    mutationFn: (formData: FormData) => batchProcess(formData),
    onSuccess: (data) => {
      toast.success(`Processed ${data.results?.length || 0} job descriptions!`);
    },
    onError: (error: any) => {
      toast.error(error.message || 'Batch processing failed');
    },
  });

  const handleJdFileAdd = (file: File) => {
    if (jdFiles.length >= 20) {
      toast.error('Maximum 20 job descriptions allowed');
      return;
    }
    setJdFiles([...jdFiles, file]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!resumeFile) {
      toast.error('Please upload your resume');
      return;
    }

    if (jdFiles.length === 0) {
      toast.error('Please upload at least one job description');
      return;
    }

    const formData = new FormData();
    formData.append('resume', resumeFile);
    jdFiles.forEach((file, index) => {
      formData.append('jd_files', file);
    });

    mutation.mutate(formData);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-md p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Batch Process</h1>
        <p className="text-gray-600 mb-8">
          Upload your resume and multiple job descriptions to process them all at once
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Resume Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Resume <span className="text-red-500">*</span>
            </label>
            <FileUpload
              accept=".pdf,.docx,.txt"
              onFileSelect={setResumeFile}
              selectedFile={resumeFile}
              label="Upload Resume"
            />
          </div>

          {/* JD Files Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Job Descriptions <span className="text-red-500">*</span>
              <span className="text-gray-500 text-xs ml-2">(Up to 20 files)</span>
            </label>
            <FileUpload
              accept=".pdf,.docx,.txt"
              onFileSelect={handleJdFileAdd}
              selectedFile={null}
              label="Add Job Description File"
            />

            {jdFiles.length > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-sm font-medium text-gray-700">
                  Selected Files ({jdFiles.length}/20):
                </p>
                {jdFiles.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                  >
                    <span className="text-sm text-gray-700">{file.name}</span>
                    <button
                      type="button"
                      onClick={() => setJdFiles(jdFiles.filter((_, i) => i !== index))}
                      className="text-red-600 hover:text-red-700"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={mutation.isPending || !resumeFile || jdFiles.length === 0}
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-md font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? 'Processing...' : `Process ${jdFiles.length} Job Description${jdFiles.length !== 1 ? 's' : ''}`}
          </button>
        </form>
      </div>
    </div>
  );
};

export default BatchPage;

