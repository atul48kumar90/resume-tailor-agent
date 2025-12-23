import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import FileUpload from '../components/upload/FileUpload';
import PersonaSelector from '../components/upload/PersonaSelector';
import { tailorResume } from '../services/api';

const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState<string>('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [persona, setPersona] = useState<string>('general');
  const [inputMode, setInputMode] = useState<'file' | 'text'>('file');

  const mutation = useMutation({
    mutationFn: (formData: FormData) => tailorResume(formData),
    onSuccess: (data) => {
      toast.success('Resume tailoring started!');
      navigate(`/results/${data.job_id}`);
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to start tailoring process');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!resumeFile) {
      toast.error('Please upload your resume');
      return;
    }

    if (inputMode === 'file' && !jdFile) {
      toast.error('Please upload a job description file');
      return;
    }

    if (inputMode === 'text' && !jdText.trim()) {
      toast.error('Please enter job description text');
      return;
    }

    const formData = new FormData();
    formData.append('resume_file', resumeFile);
    formData.append('recruiter_persona', persona);

    if (inputMode === 'file' && jdFile) {
      formData.append('job_description_file', jdFile);
    } else if (inputMode === 'text' && jdText) {
      formData.append('job_description_text', jdText);
    }

    mutation.mutate(formData);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-md p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Tailor Your Resume
        </h1>
        <p className="text-gray-600 mb-8">
          Upload your resume and job description to get an ATS-optimized resume
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
              label="Upload Resume (PDF, DOCX, or TXT)"
            />
          </div>

          {/* Job Description Input Mode Toggle */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Job Description <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-4 mb-4">
              <button
                type="button"
                onClick={() => setInputMode('file')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  inputMode === 'file'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Upload File
              </button>
              <button
                type="button"
                onClick={() => setInputMode('text')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  inputMode === 'text'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Paste Text
              </button>
            </div>

            {inputMode === 'file' ? (
              <FileUpload
                accept=".pdf,.docx,.txt"
                onFileSelect={setJdFile}
                selectedFile={jdFile}
                label="Upload Job Description"
              />
            ) : (
              <textarea
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste job description here..."
                className="w-full h-48 px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                required
              />
            )}
          </div>

          {/* Persona Selector */}
          <PersonaSelector value={persona} onChange={setPersona} />

          {/* Submit Button */}
          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-md font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {mutation.isPending ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
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
                Processing...
              </>
            ) : (
              'Tailor Resume'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default UploadPage;

