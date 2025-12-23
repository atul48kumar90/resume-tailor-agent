import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import ATSScoreCard from '../components/results/ATSScoreCard';
import SkillGapAnalysis from '../components/results/SkillGapAnalysis';
import ResumePreview from '../components/results/ResumePreview';
import DownloadButtons from '../components/results/DownloadButtons';
import SkillApproval from '../components/results/SkillApproval';
import { getJobStatus, getATSCompare, getSkillGap } from '../services/api';
import LoadingSpinner from '../components/common/LoadingSpinner';

const ResultsPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [shouldPoll, setShouldPoll] = useState(true);

  // Poll job status
  // Always enable the query so it can check status, but control polling via refetchInterval
  const { data: jobStatus, isLoading: jobLoading, error: jobError } = useQuery({
    queryKey: ['jobStatus', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId, // Always enabled when jobId exists
    refetchInterval: shouldPoll ? 2000 : false, // Stop polling when shouldPoll is false
    retry: 2, // Retry failed requests
  });

  // Stop polling when job is completed or failed
  useEffect(() => {
    if (!jobStatus) return;
    
    const isCompleted = jobStatus.status === 'completed' || 
                       jobStatus.status === 'finished' || 
                       jobStatus.status === 'failed';
    
    // Only stop polling if status is actually completed/finished/failed
    // Don't stop just because result exists (result can exist during processing)
    if (isCompleted) {
      setShouldPoll(false);
      if (jobStatus.status === 'failed') {
        toast.error('Job processing failed');
      }
    } else {
      // Keep polling for queued/processing/pending statuses
      setShouldPoll(true);
    }
  }, [jobStatus]);

  // Get ATS comparison when job is completed
  const { data: atsData, isLoading: atsLoading } = useQuery({
    queryKey: ['atsCompare', jobId],
    queryFn: () => getATSCompare(jobId!),
    enabled: !!jobId && jobStatus?.status === 'completed',
  });

  // Get skill gap analysis
  const { data: skillGap, isLoading: skillGapLoading } = useQuery({
    queryKey: ['skillGap', jobId],
    queryFn: () => getSkillGap(jobId!),
    enabled: !!jobId && jobStatus?.status === 'completed',
  });

  // Handle loading state
  if (jobLoading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <LoadingSpinner message="Loading job status..." />
      </div>
    );
  }

  // Handle error state
  if (jobError) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-xl font-bold text-red-900 mb-2">Error Loading Job</h2>
          <p className="text-red-700">{jobError instanceof Error ? jobError.message : 'Failed to load job status'}</p>
          <button
            onClick={() => navigate('/upload')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // Handle case where jobStatus is null/undefined
  if (!jobStatus) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h2 className="text-xl font-bold text-yellow-900 mb-2">Job Not Found</h2>
          <p className="text-yellow-700">The requested job could not be found. Please check the job ID and try again.</p>
          <button
            onClick={() => navigate('/upload')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  if (jobStatus.status === 'failed') {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-xl font-bold text-red-900 mb-2">Processing Failed</h2>
          <p className="text-red-700">{jobStatus.error || 'An error occurred during processing'}</p>
          <button
            onClick={() => navigate('/upload')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Handle all pending/processing statuses
  if (jobStatus.status === 'queued' || jobStatus.status === 'processing' || jobStatus.status === 'pending') {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-md p-8 text-center">
          <LoadingSpinner message="Tailoring your resume..." />
          <div className="mt-4">
            <p className="text-gray-600">
              Status: <span className="font-medium">{jobStatus.status}</span>
            </p>
            {jobStatus.queue_position && (
              <p className="text-sm text-gray-500 mt-2">
                Queue position: {jobStatus.queue_position}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Check if approval is needed
  const needsApproval = jobStatus.result?.needs_approval === true && 
                       jobStatus.result?.pending_skills_approval?.length > 0;
  const pendingSkills = jobStatus.result?.pending_skills_approval || [];

  // Show approval step if needed
  if (needsApproval) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
        <SkillApproval
          pendingSkills={pendingSkills}
          jobId={jobId!}
          onApprovalComplete={() => {
            // Invalidate all related queries to force refetch with updated data
            queryClient.invalidateQueries({ queryKey: ['jobStatus', jobId] });
            queryClient.invalidateQueries({ queryKey: ['skillGap', jobId] });
            queryClient.invalidateQueries({ queryKey: ['atsCompare', jobId] });
            // Wait a bit for the backend to update, then refetch
            setTimeout(() => {
              queryClient.refetchQueries({ queryKey: ['jobStatus', jobId] });
              queryClient.refetchQueries({ queryKey: ['skillGap', jobId] });
              queryClient.refetchQueries({ queryKey: ['atsCompare', jobId] });
            }, 500);
          }}
        />
      </div>
    );
  }

  // If job is completed but no result, show error
  if (jobStatus.status === 'completed' && !jobStatus.result) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h2 className="text-xl font-bold text-yellow-900 mb-2">Results Not Available</h2>
          <p className="text-yellow-700">The job completed but no results were found. Please try again.</p>
          <button
            onClick={() => navigate('/upload')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Resume Tailoring Results</h1>
        <p className="text-gray-600">Your resume has been optimized for the job description</p>
      </div>

      {/* ATS Score Card */}
      {/* Use atsData from /ats/compare endpoint, or fallback to jobStatus.result.ats */}
      {(atsData || jobStatus.result?.ats) && (
        <ATSScoreCard
          beforeScore={atsData?.before?.score || jobStatus.result?.ats?.before?.score || 0}
          afterScore={atsData?.after?.score || jobStatus.result?.ats?.after?.score || 0}
          beforeDetails={atsData?.before || jobStatus.result?.ats?.before}
          afterDetails={atsData?.after || jobStatus.result?.ats?.after}
        />
      )}

      {/* Skill Gap Analysis */}
      {skillGap && <SkillGapAnalysis skillGap={skillGap} />}

      {/* Resume Preview */}
      {jobStatus.result && (
        <ResumePreview
          originalResume={jobStatus.result.original_resume}
          tailoredResume={jobStatus.result.resume || jobStatus.result.rewritten}
        />
      )}

      {/* Download Section */}
      {(jobStatus.status === 'completed' || jobStatus.status === 'finished') && jobId && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Download Your Tailored Resume</h2>
          <p className="text-sm text-gray-600 mb-4">
            Choose your preferred format to download the optimized resume
          </p>
          <DownloadButtons jobId={jobId} resumeData={jobStatus.result?.resume || jobStatus.result?.rewritten} />
        </div>
      )}

      {/* Show message if no data available */}
      {!atsData && !skillGap && !jobStatus.result && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
          <p className="text-gray-600">Loading results...</p>
        </div>
      )}
    </div>
  );
};

export default ResultsPage;

